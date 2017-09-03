# Copyright (C) 2016 ycmd contributors
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

from collections import defaultdict
from ycmd.utils import ( pathname2url, ToBytes, ToUnicode, url2pathname,
                         urljoin, GetCurrentDirectory )


# FIXME: We might need a whole document management system eventually. For now,
# we just update the file version every time we refresh a file (even if it
# hasn't changed).
LAST_VERSION = defaultdict( int )


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


def Initialise( request_id ):
  """Build the Language Server initialise request"""

  # FIXME: We actually need the project_directory passed in, e.g. from the
  # request_data. For now, just get the current working directory of the server
  project_directory = GetCurrentDirectory()

  return BuildRequest( request_id, 'initialize', {
    'processId': os.getpid(),
    'rootPath': project_directory,
    'rootUri': FilePathToUri( project_directory ),
    'initializationOptions': { },
    'capabilities': { 'trace': 'verbose' }
  } )


def DidOpenTextDocument( file_name, file_types, file_contents ):
  LAST_VERSION[ file_name ] = LAST_VERSION[ file_name ] + 1
  return BuildNotification( 'textDocument/didOpen', {
    'textDocument': {
      'uri': FilePathToUri( file_name ),
      'languageId': '/'.join( file_types ),
      'version': LAST_VERSION[ file_name ],
      'text': file_contents
    }
  } )


def DidChangeTextDocument( file_name, file_types, file_contents ):
  # FIXME: The servers seem to all state they want incremental updates. It
  # remains to be seen if they really do. So far, no actual server tested has
  # actually required this, but it might be necessary for performance reasons in
  # some cases. However, as the logic for diffing previous file versions, etc.
  # is highly complex, it should only be implemented if it becomes strictly
  # necessary (perhaps with client support).
  return DidOpenTextDocument( file_name, file_types, file_contents )


def DidCloseTextDocument( file_name ):
  return BuildNotification( 'textDocument/didClose', {
    'textDocument': {
      'uri': FilePathToUri( file_name ),
      'version': LAST_VERSION[ file_name ],
    },
  } )


def Completion( request_id, request_data ):
  return BuildRequest( request_id, 'textDocument/completion', {
    'textDocument': {
      'uri': FilePathToUri( request_data[ 'filepath' ] ),
    },
    'position': Position( request_data ),
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
  # The API requires 0-based unicode offsets.
  return {
    'line': request_data[ 'line_num' ] - 1,
    'character': request_data[ 'start_column' ] - 1,
  }


def FilePathToUri( file_name ):
  return urljoin( 'file:', pathname2url( file_name ) )


def UriToFilePath( uri ):
  # NOTE: This assumes the URI starts with file:
  return os.path.normpath( url2pathname( uri[ 5 : ] ) )


def _BuildMessageData( message ):
  message[ 'jsonrpc' ] = '2.0'
  # NOTE: sort_keys=True is needed to workaround a 'limitation' of clangd where
  # it requires keys to be in a specific order, due to a somewhat naive
  # json/yaml parser.
  data = ToBytes( json.dumps( message, sort_keys=True ) )
  packet = ToBytes( 'Content-Length: {0}\r\n'
                    'Content-Type: application/vscode-jsonrpc;charset=utf8\r\n'
                    '\r\n'
                     .format( len(data) ) ) + data
  return packet


def Parse( data ):
  """Reads the raw language server data |data| into a Python dictionary"""
  return json.loads( ToUnicode( data ) )
