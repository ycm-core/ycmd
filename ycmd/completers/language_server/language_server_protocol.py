# Copyright (C) 2017 ycmd contributors
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

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa

import os
import json
import hashlib

from ycmd.utils import ( pathname2url,
                         ToBytes,
                         ToUnicode,
                         url2pathname,
                         urljoin )


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
]

SEVERITY = [
  None,
  'Error',
  'Warning',
  'Information',
  'Hint',
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


class ServerFileState( object ):
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

    return self._SendNewVersion( new_checksum, action )


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

    return self._SendNewVersion( new_checksum, ServerFileState.CHANGE_FILE )


  def GetFileCloseAction( self ):
    """Progress the state for a file which was closed in the client. Returns one
    of the actions to perform: either NO_ACTION or CLOSE_FILE."""
    if self.state == ServerFileState.OPEN:
      self.state = ServerFileState.CLOSED
      return ServerFileState.CLOSE_FILE

    self.state = ServerFileState.CLOSED
    return ServerFileState.NO_ACTION


  def _SendNewVersion( self, new_checksum, action ):
    self.checksum = new_checksum
    self.version = self.version + 1
    self.state = ServerFileState.OPEN

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


def Initialize( request_id, project_directory ):
  """Build the Language Server initialize request"""

  return BuildRequest( request_id, 'initialize', {
    'processId': os.getpid(),
    'rootPath': project_directory,
    'rootUri': FilePathToUri( project_directory ),
    'initializationOptions': {
      # We don't currently support any server-specific options.
    },
    'capabilities': {
      # We don't currently support any of the client capabilities, so we don't
      # include anything in here.
    },
  } )


def Initialized():
  return BuildNotification( 'initialized', {} )


def Shutdown( request_id ):
  return BuildRequest( request_id, 'shutdown', None )


def Exit():
  return BuildNotification( 'exit', None )


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
    ],
  } )


def DidCloseTextDocument( file_state ):
  return BuildNotification( 'textDocument/didClose', {
    'textDocument': {
      'uri': FilePathToUri( file_state.filename ),
      'version': file_state.version,
    },
  } )


def Completion( request_id, request_data ):
  return BuildRequest( request_id, 'textDocument/completion', {
    'textDocument': {
      'uri': FilePathToUri( request_data[ 'filepath' ] ),
    },
    'position': {
      'line': request_data[ 'line_num' ] - 1,
      'character': request_data[ 'start_codepoint' ] - 1,
    }
  } )


def ResolveCompletion( request_id, completion ):
  return BuildRequest( request_id, 'completionItem/resolve', completion )


def Hover( request_id, request_data ):
  return BuildRequest( request_id,
                       'textDocument/hover',
                       BuildTextDocumentPositionParams( request_data ) )


def Definition( request_id, request_data ):
  return BuildRequest( request_id,
                       'textDocument/definition',
                       BuildTextDocumentPositionParams( request_data ) )


def CodeAction( request_id, request_data, best_match_range, diagnostics ):
  return BuildRequest( request_id, 'textDocument/codeAction', {
    'textDocument': {
      'uri': FilePathToUri( request_data[ 'filepath' ] ),
    },
    'range': best_match_range,
    'context': {
      'diagnostics': diagnostics,
    },
  } )


def Rename( request_id, request_data, new_name ):
  return BuildRequest( request_id, 'textDocument/rename', {
    'textDocument': {
      'uri': FilePathToUri( request_data[ 'filepath' ] ),
    },
    'newName': new_name,
    'position': Position( request_data ),
  } )


def BuildTextDocumentPositionParams( request_data ):
  return {
    'textDocument': {
      'uri': FilePathToUri( request_data[ 'filepath' ] ),
    },
    'position': Position( request_data ),
  }


def References( request_id, request_data ):
  request = BuildTextDocumentPositionParams( request_data )
  request[ 'context' ] = { 'includeDeclaration': True }
  return BuildRequest( request_id, 'textDocument/references', request )


def Position( request_data ):
  # The API requires 0-based Unicode offsets.
  return {
    'line': request_data[ 'line_num' ] - 1,
    'character': request_data[ 'column_codepoint' ] - 1,
  }


def FilePathToUri( file_name ):
  return urljoin( 'file:', pathname2url( file_name ) )


def UriToFilePath( uri ):
  if uri [ : 5 ] != "file:":
    raise InvalidUriException( uri )

  return os.path.abspath( url2pathname( uri[ 5 : ] ) )


def _BuildMessageData( message ):
  message[ 'jsonrpc' ] = '2.0'
  # NOTE: sort_keys=True is needed to workaround a 'limitation' of clangd where
  # it requires keys to be in a specific order, due to a somewhat naive
  # JSON/YAML parser.
  data = ToBytes( json.dumps( message, sort_keys=True ) )
  packet = ToBytes( 'Content-Length: {0}\r\n'
                    '\r\n'.format( len(data) ) ) + data
  return packet


def Parse( data ):
  """Reads the raw language server message payload into a Python dictionary"""
  return json.loads( ToUnicode( data ) )
