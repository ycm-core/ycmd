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
from urllib import parse as urlparse

from collections import defaultdict

from ycmd.utils import ToBytes, ToUnicode


# TODO: Need a whole document management system!
LAST_VERSION = defaultdict( int )


def BuildRequest( request_id, method, parameters ):
  return _Message( {
    'id': request_id,
    'method': method,
    'params': parameters,
  } )


def BuildNotification( method, parameters ):
  return _Message( {
    'method': method,
    'params': parameters,
  } )


def Initialise( request_id ):
  return BuildRequest( request_id, 'initialize', {
    'processId': os.getpid(),
    'rootPath': os.getcwd(), # deprecated
    'rootUri': _MakeUriForFile( os.getcwd() ),
    'initializationOptions': { },
    'capabilities': { 'trace': 'verbose' }
  } )


def DidOpenTextDocument( file_name, file_types, file_contents ):
  LAST_VERSION[ file_name ] = LAST_VERSION[ file_name ] + 1
  return BuildNotification( 'textDocument/didOpen', {
    'textDocument': {
      'uri': _MakeUriForFile( file_name ),
      'languageId': '/'.join( file_types ),
      'version': LAST_VERSION[ file_name ],
      'text': file_contents
    }
  } )


def DidChangeTextDocument( file_name, file_types, file_contents ):
  # FIXME: The servers seem to all state they want incremental updates. It
  # remains to be seen if they really do.
  return DidOpenTextDocument( file_name, file_types, file_contents )


def DidCloseTextDocument( file_name ):
  return BuildNotification( 'textDocument/didClose', {
    'textDocument': {
      'uri': _MakeUriForFile( file_name ),
      'version': LAST_VERSION[ file_name ],
    },
  } )


def Completion( request_id, request_data ):
  return BuildRequest( request_id, 'textDocument/completion', {
    'textDocument': {
      'uri': _MakeUriForFile( request_data[ 'filepath' ] ),
    },
    'position': {
      # TODO: The API asks for 0-based offsets. These -1's are not good enough
      # when using multi-byte characters. See the tern completer for an
      # approach.
      'line': request_data[ 'line_num' ] - 1,
      'character': request_data[ 'start_codepoint' ] - 1,
    }
  } )


def ResolveCompletion( request_id, completion ):
  return BuildRequest( request_id, 'completionItem/resolve', completion )


def _MakeUriForFile( file_name ):
  return 'file://{0}'.format( file_name )


def UriToFilePath( uri ):
  # TODO: This assumes file://
  # TODO: work out how urlparse works with __future__
  return urlparse.urlparse( uri ).path


def _Message( message ):
  message[ 'jsonrpc' ] = '2.0'
  data = ToBytes( json.dumps( message, sort_keys=True ) )
  packet = ToBytes( 'Content-Length: {0}\r\n'
                    'Content-Type: application/vscode-jsonrpc;charset=utf8\r\n'
                    '\r\n'
                     .format( len(data) ) ) + data
  return packet


def Parse( data ):
  return json.loads( ToUnicode( data ) )
