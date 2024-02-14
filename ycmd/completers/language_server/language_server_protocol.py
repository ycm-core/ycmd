# Copyright (C) 2017-2020 ycmd contributors
#
# This file is part of ycmd.
#
# ycmd is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ycmd is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ycmd.  If not, see <http://www.gnu.org/licenses/>.

import collections
import os
import json
import hashlib
from urllib.parse import urljoin, urlparse, unquote
from urllib.request import pathname2url, url2pathname

from ycmd.utils import ( ByteOffsetToCodepointOffset,
                         ToBytes,
                         ToUnicode,
                         UpdateDict )


Error = collections.namedtuple( 'RequestError', [ 'code', 'reason' ] )


class Errors:
  # From
  # https://microsoft.github.io/language-server-protocol/specification#response-message
  #
  # JSON RPC
  ParseError = Error( -32700, "Parse error" )
  InvalidRequest = Error( -32600, "Invalid request" )
  MethodNotFound = Error( -32601, "Method not found" )
  InvalidParams = Error( -32602, "Invalid parameters" )
  InternalError = Error( -32603, "Internal error" )

  # The following sentinel values represent the range of errors for "user
  # defined" server errors. We don't define them as actual errors, as they are
  # just representing a valid range.
  #
  # export const serverErrorStart: number = -32099;
  # export const serverErrorEnd: number = -32000;

  # LSP defines the following custom server errors
  ServerNotInitialized = Error( -32002, "Server not initialized" )
  UnknownErrorCode = Error( -32001, "Unknown error code" )

  # LSP request errors
  RequestCancelled = Error( -32800, "The request was canceled" )
  ContentModified = Error( -32801, "Content was modified" )


INSERT_TEXT_FORMAT = [
  None, # 1-based
  'PlainText',
  'Snippet'
]

ITEM_KIND = [
  None,  # 1-based
  'Text',
  'Method',
  'Function',
  'Constructor',
  'Field',
  'Variable',
  'Class',
  'Interface',
  'Module',
  'Property',
  'Unit',
  'Value',
  'Enum',
  'Keyword',
  'Snippet',
  'Color',
  'File',
  'Reference',
  'Folder',
  'EnumMember',
  'Constant',
  'Struct',
  'Event',
  'Operator',
  'TypeParameter',
]

SEVERITY = [
  None,
  'Error',
  'Warning',
  'Information',
  'Hint',
]

FILE_EVENT_KIND = {
  'create': 1,
  'modify': 2,
  'delete': 3
}

SYMBOL_KIND = [
  None,
  'File',
  'Module',
  'Namespace',
  'Package',
  'Class',
  'Method',
  'Property',
  'Field',
  'Constructor',
  'Enum',
  'Interface',
  'Function',
  'Variable',
  'Constant',
  'String',
  'Number',
  'Boolean',
  'Array',
  'Object',
  'Key',
  'Null',
  'EnumMember',
  'Struct',
  'Event',
  'Operator',
  'TypeParameter',
]

TOKEN_TYPES = [
  'namespace',
  'type',
  'class',
  'enum',
  'interface',
  'struct',
  'typeParameter',
  'parameter',
  'variable',
  'property',
  'enumMember',
  'event',
  'function',
  'method',
  'member',
  'macro',
  'keyword',
  'modifier',
  'comment',
  'string',
  'number',
  'regexp',
  'operator',
]

TOKEN_MODIFIERS = []

INLAY_HINT_KIND = [
  None,
  "Type",
  "Parameter"
]


class InvalidUriException( Exception ):
  """Raised when trying to convert a server URI to a file path but the scheme
  was not supported. Only the file: scheme is supported"""
  pass


class ServerFileStateStore( dict ):
  """Trivial default-dict-like class to hold ServerFileState for a given
  filepath. Language server clients must maintain one of these for each language
  server connection."""
  def __missing__( self, key ):
    self[ key ] = ServerFileState( key )
    return self[ key ]


class ServerFileState:
  """State machine for a particular file from the server's perspective,
  including version."""

  # States
  OPEN = 'Open'
  CLOSED = 'Closed'

  # Actions
  CLOSE_FILE = 'Close'
  NO_ACTION = 'None'
  OPEN_FILE = 'Open'
  CHANGE_FILE = 'Change'

  def __init__( self, filename ):
    self.filename = filename
    self.version = 0
    self.state = ServerFileState.CLOSED
    self.checksum = None
    self.contents = ''


  def GetDirtyFileAction( self, contents ):
    """Progress the state for a file to be updated due to being supplied in the
    dirty buffers list. Returns any one of the Actions to perform."""
    new_checksum = self._CalculateCheckSum( contents )

    if ( self.state == ServerFileState.OPEN and
         self.checksum.digest() == new_checksum.digest() ):
      return ServerFileState.NO_ACTION
    elif self.state == ServerFileState.CLOSED:
      self.version = 0
      action = ServerFileState.OPEN_FILE
    else:
      action = ServerFileState.CHANGE_FILE

    return self._SendNewVersion( new_checksum, action, contents )


  def GetSavedFileAction( self, contents ):
    """Progress the state for a file to be updated due to having previously been
    opened, but no longer supplied in the dirty buffers list. Returns one of the
    Actions to perform: either NO_ACTION or CHANGE_FILE."""
    # We only need to update if the server state is open
    if self.state != ServerFileState.OPEN:
      return ServerFileState.NO_ACTION

    new_checksum = self._CalculateCheckSum( contents )
    if self.checksum.digest() == new_checksum.digest():
      return ServerFileState.NO_ACTION

    return self._SendNewVersion( new_checksum,
                                 ServerFileState.CHANGE_FILE,
                                 contents )


  def GetFileCloseAction( self ):
    """Progress the state for a file which was closed in the client. Returns one
    of the actions to perform: either NO_ACTION or CLOSE_FILE."""
    if self.state == ServerFileState.OPEN:
      self.state = ServerFileState.CLOSED
      return ServerFileState.CLOSE_FILE

    self.state = ServerFileState.CLOSED
    return ServerFileState.NO_ACTION


  def _SendNewVersion( self, new_checksum, action, contents ):
    self.checksum = new_checksum
    self.version = self.version + 1
    self.state = ServerFileState.OPEN
    self.contents = contents

    return action


  def _CalculateCheckSum( self, contents ):
    return hashlib.sha1( ToBytes( contents ) )


def BuildRequest( request_id, method, parameters ):
  """Builds a JSON RPC request message with the supplied ID, method and method
  parameters"""
  return _BuildMessageData( {
    'id': request_id,
    'method': method,
    'params': parameters,
  } )


def BuildNotification( method, parameters ):
  """Builds a JSON RPC notification message with the supplied method and
  method parameters"""
  return _BuildMessageData( {
    'method': method,
    'params': parameters,
  } )


def BuildResponse( request, parameters ):
  """Builds a JSON RPC response message to respond to the supplied |request|
  message. |parameters| should contain either 'error' or 'result'"""
  message = { 'id': request[ 'id' ] }
  message.update( parameters )
  return _BuildMessageData( message )


def Initialize( request_id, project_directory, extra_capabilities, settings ):
  """Build the Language Server initialize request"""

  capabilities = {
    'workspace': {
      'applyEdit': True,
      'didChangeWatchedFiles': {
        'dynamicRegistration': True
      },
      'workspaceEdit': { 'documentChanges': True, },
      'symbol': {
        'symbolKind': {
          'valueSet': list( range( 1, len( SYMBOL_KIND ) ) ),
        }
      },
      'workspaceFolders': True,
    },
    'textDocument': {
      'codeAction': {
        'codeActionLiteralSupport': {
          'codeActionKind': {
            'valueSet': [ '',
                          'quickfix',
                          'refactor',
                          'refactor.extract',
                          'refactor.inline',
                          'refactor.rewrite',
                          'source',
                          'source.organizeImports' ]
          }
        }
      },
      'completion': {
        'completionItemKind': {
          # ITEM_KIND list is 1-based.
          # valueSet is a list of the indices of items supported
          'valueSet': list( range( 1, len( ITEM_KIND ) ) ),
        },
        'completionItem': {
          'documentationFormat': [
            'plaintext',
            'markdown'
          ],
          # Buggy servers (jdt.ls) now require this to be set even though it's
          # the historical default
          'resolveSupport': {
            'properties': [ 'documentation', 'detail' ]
          },
        },
      },
      'documentSymbol': {
        'symbolKind': {
          'valueSet': list( range( 1, len( SYMBOL_KIND ) ) ),
        },
        'hierarchicalDocumentSymbolSupport': False,
        'labelSupport': False,
      },
      'hover': {
        'contentFormat': [
          'plaintext',
          'markdown'
        ]
      },
      'signatureHelp': {
        'signatureInformation': {
          'parameterInformation': {
            'labelOffsetSupport': True,
          },
          'documentationFormat': [
            'plaintext',
            'markdown'
          ],
        },
      },
      'semanticTokens': {
        'requests': {
          'range': True,
          'full': {
            'delta': False
          }
        },
        'tokenTypes': TOKEN_TYPES,
        'tokenModifiers': TOKEN_MODIFIERS,
        'formats': [ 'relative' ],
        'augmentSyntaxTokens': True,
      },
      'synchronization': {
        'didSave': True
      },
      'inlay_hint': {
      }
    },
  }
  return BuildRequest( request_id, 'initialize', {
    'processId': os.getpid(),
    'rootPath': project_directory,
    'rootUri': FilePathToUri( project_directory ),
    'initializationOptions': settings,
    'capabilities': UpdateDict( capabilities, extra_capabilities ),
    'workspaceFolders': WorkspaceFolders( project_directory ),
  } )


def WorkspaceFolders( *args ):
  return [
    {
      'uri': FilePathToUri( f ),
      'name': os.path.basename( f )
    } for f in args
  ]


def Initialized():
  return BuildNotification( 'initialized', {} )


def Shutdown( request_id ):
  return BuildRequest( request_id, 'shutdown', None )


def Exit():
  return BuildNotification( 'exit', None )


def Void( request ):
  return Accept( request, None )


def Reject( request, request_error, data = None ):
  msg = {
    'error': {
      'code': request_error.code,
      'message': request_error.reason,
    }
  }
  if data is not None:
    msg[ 'error' ][ 'data' ] = data

  return BuildResponse( request, msg )


def Accept( request, result ):
  msg = {
    'result': result
  }
  return BuildResponse( request, msg )


def ApplyEditResponse( request, applied ):
  msg = { 'applied': applied }
  return Accept( request, msg )


def DidChangeWorkspaceFolders( new_folder ):
  return BuildNotification( 'workspace/didChangeWorkspaceFolders', {
    'event': {
      'removed': [],
      'added': WorkspaceFolders( new_folder )
    }
  } )


def DidChangeWatchedFiles( path, kind ):
  return BuildNotification( 'workspace/didChangeWatchedFiles', {
    'changes': [ {
      'uri': FilePathToUri( path ),
      'type': FILE_EVENT_KIND[ kind ]
    } ]
  } )


def DidChangeConfiguration( config ):
  return BuildNotification( 'workspace/didChangeConfiguration', {
    'settings': config,
  } )


def DidOpenTextDocument( file_state, file_types, file_contents ):
  return BuildNotification( 'textDocument/didOpen', {
    'textDocument': {
      'uri': FilePathToUri( file_state.filename ),
      'languageId': '/'.join( file_types ),
      'version': file_state.version,
      'text': file_contents
    }
  } )


def DidChangeTextDocument( file_state, file_contents ):
  return BuildNotification( 'textDocument/didChange', {
    'textDocument': {
      'uri': FilePathToUri( file_state.filename ),
      'version': file_state.version,
    },
    'contentChanges': [
      { 'text': file_contents },
    ]
  } )


def DidSaveTextDocument( file_state, file_contents ):
  params = {
    'textDocument': {
      'uri': FilePathToUri( file_state.filename ),
      'version': file_state.version,
    },
  }
  if file_contents is not None:
    params.update( { 'text': file_contents } )

  return BuildNotification( 'textDocument/didSave', params )


def DidCloseTextDocument( file_state ):
  return BuildNotification( 'textDocument/didClose', {
    'textDocument': {
      'uri': FilePathToUri( file_state.filename ),
      'version': file_state.version,
    },
  } )


def Completion( request_id, request_data, codepoint ):
  return BuildRequest( request_id, 'textDocument/completion', {
    'textDocument': TextDocumentIdentifier( request_data ),
    'position': Position( request_data[ 'line_num' ],
                          request_data[ 'line_value' ],
                          codepoint ),
  } )


def ResolveCompletion( request_id, completion ):
  return BuildRequest( request_id, 'completionItem/resolve', completion )


def SignatureHelp( request_id, request_data ):
  return BuildRequest( request_id,
                       'textDocument/signatureHelp',
                       BuildTextDocumentPositionParams( request_data ) )


def Hover( request_id, request_data ):
  return BuildRequest( request_id,
                       'textDocument/hover',
                       BuildTextDocumentPositionParams( request_data ) )


def Definition( request_id, request_data ):
  return BuildRequest( request_id,
                       'textDocument/definition',
                       BuildTextDocumentPositionParams( request_data ) )


def Declaration( request_id, request_data ):
  return BuildRequest( request_id,
                       'textDocument/declaration',
                       BuildTextDocumentPositionParams( request_data ) )


def TypeDefinition( request_id, request_data ):
  return BuildRequest( request_id,
                       'textDocument/typeDefinition',
                       BuildTextDocumentPositionParams( request_data ) )



def Implementation( request_id, request_data ):
  return BuildRequest( request_id,
                       'textDocument/implementation',
                       BuildTextDocumentPositionParams( request_data ) )


def CodeAction( request_id, request_data, best_match_range, diagnostics ):
  return BuildRequest( request_id, 'textDocument/codeAction', {
    'textDocument': TextDocumentIdentifier( request_data ),
    'range': best_match_range,
    'context': {
      'diagnostics': diagnostics,
    },
  } )


def Rename( request_id, request_data, new_name ):
  return BuildRequest( request_id, 'textDocument/rename', {
    'textDocument': TextDocumentIdentifier( request_data ),
    'newName': new_name,
    'position': Position( request_data[ 'line_num' ],
                          request_data[ 'line_value' ],
                          request_data[ 'column_codepoint' ] )
  } )


def WorkspaceSymbol( request_id, query ):
  return BuildRequest( request_id, 'workspace/symbol', {
    'query': query,
  } )


def DocumentSymbol( request_id, request_data ):
  return BuildRequest( request_id, 'textDocument/documentSymbol', {
    'textDocument': {
      'uri': FilePathToUri( request_data[ 'filepath' ] ),
    },
  } )


def TextDocumentIdentifier( request_data ):
  return {
    'uri': FilePathToUri( request_data[ 'filepath' ] ),
  }


def BuildTextDocumentPositionParams( request_data ):
  return {
    'textDocument': TextDocumentIdentifier( request_data ),
    'position': Position( request_data[ 'line_num' ],
                          request_data[ 'line_value' ],
                          request_data[ 'column_codepoint' ] )
  }


def References( request_id, request_data ):
  request = BuildTextDocumentPositionParams( request_data )
  request[ 'context' ] = { 'includeDeclaration': True }
  return BuildRequest( request_id, 'textDocument/references', request )


def Position( line_num, line_value, column_codepoint ):
  # The API requires 0-based line number and 0-based UTF-16 offset.
  return {
    'line': line_num - 1,
    'character': CodepointsToUTF16CodeUnits( line_value, column_codepoint ) - 1
  }


def PrepareCallHierarchy( request_id, request_data ):
  return BuildRequest( request_id, 'textDocument/prepareCallHierarchy', {
    'textDocument': {
      'uri': FilePathToUri( request_data[ 'filepath' ] ),
    },
    'position': Position( request_data[ 'line_num' ],
                          request_data[ 'line_value' ],
                          request_data[ 'column_codepoint' ] )
  } )


def CallHierarchy( request_id, direction, item ):
  return BuildRequest( request_id, f'callHierarchy/{ direction }Calls', {
    'item': item
  } )


def Formatting( request_id, request_data ):
  return BuildRequest( request_id, 'textDocument/formatting', {
    'textDocument': TextDocumentIdentifier( request_data ),
    'options': FormattingOptions( request_data )
  } )


def RangeFormatting( request_id, request_data ):
  return BuildRequest( request_id, 'textDocument/rangeFormatting', {
    'textDocument': TextDocumentIdentifier( request_data ),
    'range': Range( request_data ),
    'options': FormattingOptions( request_data )
  } )


def FormattingOptions( request_data ):
  options = request_data[ 'options' ]
  format_options = {
    'tabSize': options.pop( 'tab_size' ),
    'insertSpaces': options.pop( 'insert_spaces' )
  }
  format_options.update( options )
  return format_options


def Range( request_data ):
  lines = request_data[ 'lines' ]

  if 'range' not in request_data:
    start_codepoint = request_data[ 'start_codepoint' ]
    start_line_num = request_data[ 'line_num' ]
    start_line_value = request_data[ 'line_value' ]

    end_codepoint = start_codepoint + 1
    end_line_num = start_line_num
    end_line_value = start_line_value
  else:
    start = request_data[ 'range' ][ 'start' ]
    start_line_num = start[ 'line_num' ]
    end = request_data[ 'range' ][ 'end' ]
    end_line_num = end[ 'line_num' ]

    try:
      start_line_value = lines[ start_line_num - 1 ]
      start_codepoint = ByteOffsetToCodepointOffset( start_line_value,
                                                     start[ 'column_num' ] )

      end_line_value = lines[ end_line_num - 1 ]
      end_codepoint = ByteOffsetToCodepointOffset( end_line_value,
                                                   end[ 'column_num' ] )
    except IndexError:
      raise RuntimeError( "Invalid range" )

  # LSP requires to use the start of the next line as the end position for a
  # range that ends with a newline.
  if end_codepoint >= len( end_line_value ):
    end_line_num += 1
    end_line_value = ''
    end_codepoint = 1

  return {
    'start': Position( start_line_num, start_line_value, start_codepoint ),
    'end': Position( end_line_num, end_line_value, end_codepoint )
  }


def ExecuteCommand( request_id, command, arguments ):
  return BuildRequest( request_id, 'workspace/executeCommand', {
    'command': command,
    'arguments': arguments
  } )


def SemanticTokens( request_id, range_supported, request_data ):
  if 'range' in request_data and range_supported:
    return BuildRequest( request_id, 'textDocument/semanticTokens/range', {
      'textDocument': TextDocumentIdentifier( request_data ),
      'range': Range( request_data )
    } )
  else:
    return BuildRequest( request_id, 'textDocument/semanticTokens/full', {
      'textDocument': TextDocumentIdentifier( request_data ),
    } )


def InlayHints( request_id, request_data ):
  # range is mandatory
  return BuildRequest( request_id, 'textDocument/inlayHint', {
    'textDocument': TextDocumentIdentifier( request_data ),
    'range': Range( request_data )
  } )


def FilePathToUri( file_name ):
  return urljoin( 'file:', pathname2url( file_name ) )


def UriToFilePath( uri ):
  parsed_uri = urlparse( uri )
  if parsed_uri.scheme != 'file':
    raise InvalidUriException( uri )

  # url2pathname doesn't work as expected when uri.path is percent-encoded and
  # is a windows path for ex:
  # url2pathname('/C%3a/') == 'C:\\C:'
  # whereas
  # url2pathname('/C:/') == 'C:\\'
  # Therefore first unquote pathname.
  pathname = unquote( parsed_uri.path )
  return os.path.abspath( url2pathname( pathname ) )


def _BuildMessageData( message ):
  message[ 'jsonrpc' ] = '2.0'
  # NOTE: sort_keys=True is needed to workaround a 'limitation' of clangd where
  # it requires keys to be in a specific order, due to a somewhat naive
  # JSON/YAML parser.
  data = ToBytes( json.dumps( message,
                              separators = ( ',', ':' ),
                              sort_keys=True ) )
  packet = ToBytes( f'Content-Length: { len( data ) }\r\n\r\n' ) + data
  return packet


def Parse( data ):
  """Reads the raw language server message payload into a Python dictionary"""
  return json.loads( ToUnicode( data ) )


def CodepointsToUTF16CodeUnits( line_value, codepoint_offset ):
  """Return the 1-based UTF-16 code unit offset equivalent to the 1-based
  unicode codepoint offset |codepoint_offset| in the Unicode string
  |line_value|"""
  # Language server protocol requires offsets to be in utf16 code _units_.
  # Each code unit is 2 bytes.
  # So we re-encode the line as utf-16 and divide the length in bytes by 2.
  #
  # Of course, this is a terrible API, but until all the servers support any
  # change out of
  # https://github.com/Microsoft/language-server-protocol/issues/376 then we
  # have to jump through hoops.
  if codepoint_offset > len( line_value ):
    return ( len( line_value.encode( 'utf-16-le' ) ) + 2 ) // 2

  value_as_utf16 = line_value[ : codepoint_offset ].encode( 'utf-16-le' )
  return len( value_as_utf16 ) // 2


def UTF16CodeUnitsToCodepoints( line_value, code_unit_offset ):
  """Return the 1-based codepoint offset into the unicode string |line_value|
  equivalent to the 1-based UTF-16 code unit offset |code_unit_offset| into a
  UTF-16 encoded version of |line_value|"""
  # As above, LSP returns offsets in utf16 code units. So we convert the line to
  # UTF16, snip everything up to the code_unit_offset * 2 bytes (each code unit
  # is 2 bytes), then re-encode as unicode and return the length (in
  # codepoints).
  value_as_utf16_bytes = ToBytes( line_value.encode( 'utf-16-le' ) )

  byte_offset_utf16 = code_unit_offset * 2
  if byte_offset_utf16 > len( value_as_utf16_bytes ):
    # If the offset points off the end of the string, then the codepoint offset
    # is one-past-the-end of the string in unicode codepoints
    return len( line_value ) + 1

  bytes_included = value_as_utf16_bytes[ : code_unit_offset * 2 ]
  return len( bytes_included.decode( 'utf-16-le' ) )


def ComparePositions( a, b ):
  """Returns < 0 if a is before b, 0 if a and b are equal and > 0 if a is
  after b. a and b are both LSP positions."""

  # If they are on the same line, compare character pos
  if a[ 'line' ] == b[ 'line' ]:
    return a[ 'character' ] - b[ 'character' ]
  # otherwise, just compare the lines
  return a[ 'line' ] - b[ 'line' ]


def RangesOverlap( a, b ):
  """Returns true if the LSP ranges a and b strictly overlap"""
  # if the diag ends before the start of the cursor, it's not overlapping
  if ComparePositions( a[ 'end' ], b[ 'start' ] ) < 0:
    return False

  # if the diag starts after the end of the cursor, it's not overlapping
  if ComparePositions( a[ 'start' ], b[ 'end' ] ) > 0:
    return False

  # Otherwise it overaps in at least 1 char
  return True


def RangesOverlapLines( a, b ):
  """Returns true if the LSP ranges a and b share any lines"""
  if a[ 'end' ][ 'line' ] < b[ 'start' ][ 'line' ]:
    return False

  if a[ 'start' ][ 'line' ] > b[ 'end' ][ 'line' ]:
    return False

  return True
