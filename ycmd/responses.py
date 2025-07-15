# Copyright (C) 2013-2020 ycmd contributors
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

import os
from ycmd.utils import ProcessIsRunning


YCM_EXTRA_CONF_FILENAME = '.ycm_extra_conf.py'

CONFIRM_CONF_FILE_MESSAGE = ( 'Found {0}. Load? \n\n(Question can be turned '
                              'off with options, see YCM docs)' )

NO_EXTRA_CONF_FILENAME_MESSAGE = ( f'No { YCM_EXTRA_CONF_FILENAME } file '
  'detected, so no compile flags are available. Thus no semantic support for '
  'C/C++/ObjC/ObjC++. Go READ THE ' 'DOCS *NOW*, DON\'T file a bug report.' )

NO_DIAGNOSTIC_SUPPORT_MESSAGE = ( 'YCM has no diagnostics support for this '
  'filetype; refer to Syntastic docs if using Syntastic.' )

EMPTY_SIGNATURE_INFO = {
  'activeSignature': 0,
  'activeParameter': 0,
  'signatures': [],
}


class SignatureHelpAvailalability:
  AVAILABLE = 'YES'
  NOT_AVAILABLE = 'NO'
  PENDING = 'PENDING'


class ServerError( Exception ):
  def __init__( self, message ):
    super().__init__( message )


class UnknownExtraConf( ServerError ):
  def __init__( self, extra_conf_file ):
    message = CONFIRM_CONF_FILE_MESSAGE.format( extra_conf_file )
    super().__init__( message )
    self.extra_conf_file = extra_conf_file


class NoExtraConfDetected( ServerError ):
  def __init__( self ):
    super().__init__( NO_EXTRA_CONF_FILENAME_MESSAGE )


class NoDiagnosticSupport( ServerError ):
  def __init__( self ):
    super().__init__( NO_DIAGNOSTIC_SUPPORT_MESSAGE )


# column_num is a byte offset
def BuildGoToResponse( filepath,
                       line_num,
                       column_num,
                       description = None,
                       file_only = False ):
  return BuildGoToResponseFromLocation(
    Location( line = line_num,
              column = column_num,
              filename = filepath ),
    description, file_only )


def BuildGoToResponseFromLocation( location,
                                   description = None,
                                   file_only = False ):
  """Build a GoTo response from a responses.Location object."""
  response = BuildLocationData( location )
  if description:
    response[ 'description' ] = description
  response[ 'file_only' ] = file_only
  return response


def BuildDescriptionOnlyGoToResponse( text ):
  return {
    'description': text,
  }


def BuildDisplayMessageResponse( text ):
  return {
    'message': text
  }


def BuildDetailedInfoResponse( text ):
  """ Returns the response object for displaying detailed information about
  types and usage, such as within a preview window"""
  return {
    'detailed_info': text
  }


def BuildCompletionData( insertion_text,
                         extra_menu_info = None,
                         detailed_info = None,
                         menu_text = None,
                         kind = None,
                         extra_data = None ):
  completion_data = {
    'insertion_text': insertion_text
  }

  if extra_menu_info:
    completion_data[ 'extra_menu_info' ] = extra_menu_info
  if menu_text:
    completion_data[ 'menu_text' ] = menu_text
  if detailed_info:
    completion_data[ 'detailed_info' ] = detailed_info
  if kind:
    completion_data[ 'kind' ] = kind
  if extra_data:
    completion_data[ 'extra_data' ] = extra_data
  return completion_data


# start_column is a byte offset
def BuildCompletionResponse( completions,
                             start_column,
                             errors=None ):
  return {
    'completions': completions,
    'completion_start_column': start_column,
    'errors': errors if errors else [],
  }


def BuildResolveCompletionResponse( completion, errors ):
  return {
    'completion': completion,
    'errors': errors if errors else [],
  }


def BuildSignatureHelpResponse( signature_info, errors = None ):
  return {
    'signature_help':
      signature_info if signature_info else EMPTY_SIGNATURE_INFO,
    'errors': errors if errors else [],
  }


def BuildSemanticTokensResponse( semantic_tokens, errors = None ):
  return {
    'semantic_tokens': semantic_tokens if semantic_tokens else {},
    'errors': errors if errors else [],
  }


def BuildInlayHintsResponse( inlay_hints, errors = None ):
  return {
    'inlay_hints': inlay_hints if inlay_hints else [],
    'errors': errors if errors else [],
  }


# location.column_number_ is a byte offset
def BuildLocationData( location ):
  return {
    'line_num': location.line_number_,
    'column_num': location.column_number_,
    'filepath': ( os.path.normpath( location.filename_ )
                  if location.filename_ else '' ),
  }


def BuildRangeData( source_range ):
  return {
    'start': BuildLocationData( source_range.start_ ),
    'end': BuildLocationData( source_range.end_ ),
  }


class Diagnostic:
  def __init__( self,
                ranges,
                location,
                location_extent,
                text,
                kind,
                fixits = [] ):
    self.ranges_ = ranges
    self.location_ = location
    self.location_extent_ = location_extent
    self.text_ = text
    self.kind_ = kind
    self.fixits_ = fixits


class UnresolvedFixIt:
  def __init__( self, command, text, kind = None ):
    self.command = command
    self.text = text
    self.resolve = True
    self.kind = kind


class Location:
  """Source code location for a diagnostic or FixIt (aka Refactor)."""

  def __init__( self, line: int, column: int, filename: str ):
    """Line is 1-based line, column is 1-based column byte offset, filename is
    absolute path of the file"""
    self.line_number_ = line
    self.column_number_ = column
    if filename:
      self.filename_ = os.path.abspath( filename )
    else:
      # When the filename passed (e.g. by a server) can't be recognized or
      # parsed, we send an empty filename. This at least allows the client to
      # know there _is_ a reference, but not exactly where it is. This can
      # happen with the Java completer which sometimes returns references using
      # a custom/undocumented URI scheme. Typically, such URIs point to .class
      # files or other binary data which clients can't display anyway.
      # FIXME: Sending a location with an empty filename could be considered a
      # strict breach of our own protocol. Perhaps completers should be required
      # to simply skip such a location.
      self.filename_ = filename


class Range:
  """Source code range relating to a diagnostic or FixIt (aka Refactor)."""

  def __init__( self, start: Location, end: Location ):
    "start of type Location, end of type Location"""
    self.start_ = start
    self.end_ = end


class FixIt:
  """A set of replacements (of type FixItChunk) to be applied to fix a single
  diagnostic. This can be used for any type of refactoring command, not just
  quick fixes. The individual chunks may span multiple files.

  NOTE: All offsets supplied in both |location| and (the members of) |chunks|
  must be byte offsets into the UTF-8 encoded version of the appropriate
  buffer.
  """
  class Kind:
    """These are LSP kinds that we use outside of LSP completers."""
    REFACTOR = 'refactor'


  def __init__( self, location: Location, chunks, text = '', kind = None ):
    """location of type Location, chunks of type list<FixItChunk>"""
    self.location = location
    self.chunks = chunks
    self.text = text
    self.kind = kind


class FixItChunk:
  """An individual replacement within a FixIt (aka Refactor)"""

  def __init__( self, replacement_text: str, range: Range ):
    """replacement_text of type string, range of type Range"""
    self.replacement_text = replacement_text
    self.range = range


def BuildDiagnosticData( diagnostic ):
  kind = ( diagnostic.kind_.name if hasattr( diagnostic.kind_, 'name' )
           else diagnostic.kind_ )

  return {
    'ranges': [ BuildRangeData( x ) for x in diagnostic.ranges_ ],
    'location': BuildLocationData( diagnostic.location_ ),
    'location_extent': BuildRangeData( diagnostic.location_extent_ ),
    'text': diagnostic.text_,
    'kind': kind,
    'fixit_available': len( diagnostic.fixits_ ) > 0,
  }


def BuildDiagnosticResponse( diagnostics,
                             filename,
                             max_diagnostics_to_display ):
  if ( max_diagnostics_to_display and
       len( diagnostics ) > max_diagnostics_to_display ):
    diagnostics = diagnostics[ : max_diagnostics_to_display ]
    location = Location( 1, 1, filename )
    location_extent = Range( location, location )
    diagnostics.append( Diagnostic(
      [ location_extent ],
      location,
      location_extent,
      'Maximum number of diagnostics exceeded.',
      'ERROR'
    ) )
  return [ BuildDiagnosticData( diagnostic ) for diagnostic in diagnostics ]


def BuildFixItResponse( fixits ):
  """Build a response from a list of FixIt (aka Refactor) objects. This response
  can be used to apply arbitrary changes to arbitrary files and is suitable for
  both quick fix and refactor operations"""

  def BuildFixitChunkData( chunk ):
    return {
      'replacement_text': chunk.replacement_text,
      'range': BuildRangeData( chunk.range ),
    }

  def BuildFixItData( fixit ):
    if hasattr( fixit, 'resolve' ):
      result = {
        'command': fixit.command,
        'text': fixit.text,
        'kind': fixit.kind,
        'resolve': fixit.resolve
      }
    else:
      result = {
        'location': BuildLocationData( fixit.location ),
        'chunks' : [ BuildFixitChunkData( x ) for x in fixit.chunks ],
        'text': fixit.text,
        'kind': fixit.kind,
        'resolve': False
      }

    if result[ 'kind' ] is None:
      result.pop( 'kind' )

    return result

  return {
    'fixits' : [ BuildFixItData( x ) for x in fixits ]
  }


def BuildExceptionResponse( exception, traceback ):
  return {
    'exception': exception,
    'message': str( exception ),
    'traceback': traceback
  }


class DebugInfoServer:
  """Store debugging information on a server:
  - name: the server name;
  - is_running: True if the server process is alive, False otherwise;
  - executable: path of the executable used to start the server;
  - address: if applicable, the address on which the server is listening. None
    otherwise;
  - port: if applicable, the port on which the server is listening. None
    otherwise;
  - pid: the process identifier of the server. None if the server is not
    running;
  - logfiles: a list of logging files used by the server;
  - extras: a list of DebugInfoItem objects for additional information on the
    server."""

  def __init__( self,
                name,
                handle,
                executable,
                address = None,
                port = None,
                logfiles = [],
                extras = [] ):
    self.name = name
    self.is_running = ProcessIsRunning( handle )
    self.executable = executable
    self.address = address
    self.port = port
    self.pid = handle.pid if self.is_running else None
    # Remove undefined logfiles from the list.
    self.logfiles = [ logfile for logfile in logfiles if logfile ]
    self.extras = extras


class DebugInfoItem:

  def __init__( self, key, value ):
    self.key = key
    self.value = value


def BuildDebugInfoResponse( name, servers = [], items = [] ):
  """Build a response containing debugging information on a semantic completer:
  - name: the completer name;
  - servers: a list of DebugInfoServer objects representing the servers used by
    the completer;
  - items: a list of DebugInfoItem objects for additional information
    on the completer."""

  def BuildItemData( item ):
    return {
      'key': item.key,
      'value': item.value
    }


  def BuildServerData( server ):
    return {
      'name': server.name,
      'is_running': server.is_running,
      'executable': server.executable,
      'address': server.address,
      'port': server.port,
      'pid': server.pid,
      'logfiles': server.logfiles,
      'extras': [ BuildItemData( item ) for item in server.extras ]
    }


  return {
    'name': name,
    'servers': [ BuildServerData( server ) for server in servers ],
    'items': [ BuildItemData( item ) for item in items ]
  }


def BuildSignatureHelpAvailableResponse( value ):
  return { 'available': value }
