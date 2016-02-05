# Copyright (C) 2015 ycmd contributors
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

from ycmd.utils import ToUtf8IfNeeded
from ycmd.completers.completer import Completer
from ycmd import responses, utils, hmac_utils

import logging
import urlparse
import requests
import httplib
import json
import tempfile
import base64
import binascii
import threading
import os

from os import path as p

_logger = logging.getLogger( __name__ )

DIR_OF_THIS_SCRIPT = p.dirname( p.abspath( __file__ ) )
DIR_OF_THIRD_PARTY = utils.PathToNearestThirdPartyFolder( DIR_OF_THIS_SCRIPT )

RACERD_BINARY_NAME = 'racerd' + ( '.exe' if utils.OnWindows() else '' )
RACERD_BINARY = p.join( DIR_OF_THIRD_PARTY,
                         'racerd', 'target', 'release', RACERD_BINARY_NAME )

RACERD_HMAC_HEADER = 'x-racerd-hmac'
HMAC_SECRET_LENGTH = 16

BINARY_NOT_FOUND_MESSAGE = ( 'racerd binary not found. Did you build it? ' +
                             'You can do so by running ' +
                             '"./build.py --racer-completer".' )
ERROR_FROM_RACERD_MESSAGE = (
  'Received error from racerd while retrieving completions. You did not '
  'set the rust_src_path option, which is probably causing this issue. '
  'See YCM docs for details.'
)


def FindRacerdBinary( user_options ):
  """
  Find path to racerd binary

  This function prefers the 'racerd_binary_path' value as provided in
  user_options if available. It then falls back to ycmd's racerd build. If
  that's not found, attempts to use racerd from current path.
  """
  racerd_user_binary = user_options.get( 'racerd_binary_path' )
  if racerd_user_binary:
    # The user has explicitly specified a path.
    if os.path.isfile( racerd_user_binary ):
      return racerd_user_binary
    else:
      _logger.warn( 'user provided racerd_binary_path is not file' )

  if os.path.isfile( RACERD_BINARY ):
    return RACERD_BINARY

  return utils.PathToFirstExistingExecutable( [ 'racerd' ] )


class RustCompleter( Completer ):
  """
  A completer for the rust programming language backed by racerd.
  https://github.com/jwilm/racerd
  """

  def __init__( self, user_options ):
    super( RustCompleter, self ).__init__( user_options )
    self._racerd = FindRacerdBinary( user_options )
    self._racerd_host = None
    self._server_state_lock = threading.RLock()
    self._keep_logfiles = user_options[ 'server_keep_logfiles' ]
    self._hmac_secret = ''
    self._rust_source_path = self._GetRustSrcPath()

    if not self._rust_source_path:
      _logger.warn( 'No path provided for the rustc source. Please set the '
                    'rust_src_path option' )

    if not self._racerd:
      _logger.error( BINARY_NOT_FOUND_MESSAGE )
      raise RuntimeError( BINARY_NOT_FOUND_MESSAGE )

    self._StartServer()


  def _GetRustSrcPath( self ):
    """
    Attempt to read user option for rust_src_path. Fallback to environment
    variable if it's not provided.
    """
    rust_src_path = self.user_options[ 'rust_src_path' ]

    # Early return if user provided config
    if rust_src_path:
      return rust_src_path

    # Fall back to environment variable
    env_key = 'RUST_SRC_PATH'
    if env_key in os.environ:
      return os.environ[ env_key ]

    return None


  def SupportedFiletypes( self ):
    return [ 'rust' ]


  def _ComputeRequestHmac( self, method, path, body ):
    if not body:
      body = ''

    hmac = hmac_utils.CreateRequestHmac( method, path, body, self._hmac_secret )
    return binascii.hexlify( hmac )


  def _GetResponse( self, handler, request_data = None, method = 'POST' ):
    """
    Query racerd via HTTP

    racerd returns JSON with 200 OK responses. 204 No Content responses occur
    when no errors were encountered but no completions, definitions, or errors
    were found.
    """
    _logger.info( 'RustCompleter._GetResponse' )
    url = urlparse.urljoin( self._racerd_host, handler )
    parameters = self._TranslateRequest( request_data )
    body = json.dumps( parameters ) if parameters else None
    request_hmac = self._ComputeRequestHmac( method, handler, body )

    extra_headers = { 'content-type': 'application/json' }
    extra_headers[ RACERD_HMAC_HEADER ] = request_hmac

    response = requests.request( method,
                                 url,
                                 data = body,
                                 headers = extra_headers )

    response.raise_for_status()

    if response.status_code is httplib.NO_CONTENT:
      return None

    return response.json()


  def _TranslateRequest( self, request_data ):
    """
    Transform ycm request into racerd request
    """
    if not request_data:
      return None

    file_path = request_data[ 'filepath' ]
    buffers = []
    for path, obj in request_data[ 'file_data' ].items():
      buffers.append( {
          'contents': obj[ 'contents' ],
          'file_path': path
      } )

    line = request_data[ 'line_num' ]
    col = request_data[ 'column_num' ] - 1

    return {
      'buffers': buffers,
      'line': line,
      'column': col,
      'file_path': file_path
    }


  def _GetExtraData( self, completion ):
    location = {}
    if completion[ 'file_path' ]:
      location[ 'filepath' ] = ToUtf8IfNeeded( completion[ 'file_path' ] )
    if completion[ 'line' ]:
      location[ 'line_num' ] = completion[ 'line' ]
    if completion[ 'column' ]:
      location[ 'column_num' ] = completion[ 'column' ] + 1

    if location:
      return { 'location': location }

    return None


  def ComputeCandidatesInner( self, request_data ):
    try:
      completions = self._FetchCompletions( request_data )
    except requests.HTTPError:
      if not self._rust_source_path:
        raise RuntimeError( ERROR_FROM_RACERD_MESSAGE )
      raise

    if not completions:
      return []

    return [ responses.BuildCompletionData(
                insertion_text = ToUtf8IfNeeded( completion[ 'text' ] ),
                kind = ToUtf8IfNeeded( completion[ 'kind' ] ),
                extra_menu_info = ToUtf8IfNeeded( completion[ 'context' ] ),
                extra_data = self._GetExtraData( completion ) )
             for completion in completions ]


  def _FetchCompletions( self, request_data ):
    return self._GetResponse( '/list_completions', request_data )


  def _WriteSecretFile( self, secret ):
    """
    Write a file containing the `secret` argument. The path to this file is
    returned.

    Note that racerd consumes the file upon reading; removal of the temp file is
    intentionally not handled here.
    """

    # Make temp file
    secret_fd, secret_path = tempfile.mkstemp( text=True )

    # Write secret
    with os.fdopen( secret_fd, 'w' ) as secret_file:
      secret_file.write( secret )

    return secret_path


  def _StartServer( self ):
    """
    Start racerd.
    """
    with self._server_state_lock:

      self._hmac_secret = self._CreateHmacSecret()
      secret_file_path = self._WriteSecretFile( self._hmac_secret )

      port = utils.GetUnusedLocalhostPort()

      args = [ self._racerd, 'serve',
               '--port', str(port),
               '-l',
               '--secret-file', secret_file_path ]

      # Enable logging of crashes
      env = os.environ.copy()
      env[ 'RUST_BACKTRACE' ] = '1'

      if self._rust_source_path:
        args.extend( [ '--rust-src-path', self._rust_source_path ] )

      filename_format = p.join( utils.PathToTempDir(),
                                'racerd_{port}_{std}.log' )

      self._server_stdout = filename_format.format( port = port,
                                                    std = 'stdout' )
      self._server_stderr = filename_format.format( port = port,
                                                    std = 'stderr' )

      with open( self._server_stderr, 'w' ) as fstderr:
        with open( self._server_stdout, 'w' ) as fstdout:
          self._racerd_phandle = utils.SafePopen( args,
                                                  stdout = fstdout,
                                                  stderr = fstderr,
                                                  env = env )

      self._racerd_host = 'http://127.0.0.1:{0}'.format( port )
      _logger.info( 'RustCompleter using host = ' + self._racerd_host )


  def ServerIsRunning( self ):
    """
    Check racerd status.
    """
    with self._server_state_lock:
      if not self._racerd_host or not self._racerd_phandle:
        return False

      try:
        self._GetResponse( '/ping', method = 'GET' )
        return True
      except requests.HTTPError:
        self._StopServer()
        return False


  def ServerIsReady( self ):
    try:
      self._GetResponse( '/ping', method = 'GET' )
      return True
    except Exception:
      return False


  def _StopServer( self ):
    """
    Stop racerd.
    """
    with self._server_state_lock:
      if self._racerd_phandle:
        self._racerd_phandle.terminate()
        self._racerd_phandle.wait()
        self._racerd_phandle = None
        self._racerd_host = None

      if not self._keep_logfiles:
        # Remove stdout log
        if self._server_stdout and p.exists( self._server_stdout ):
          os.unlink( self._server_stdout )
          self._server_stdout = None

        # Remove stderr log
        if self._server_stderr and p.exists( self._server_stderr ):
          os.unlink( self._server_stderr )
          self._server_stderr = None


  def _RestartServer( self ):
    """
    Restart racerd
    """
    _logger.debug( 'RustCompleter restarting racerd' )

    with self._server_state_lock:
      if self.ServerIsRunning():
        self._StopServer()
      self._StartServer()

    _logger.debug( 'RustCompleter has restarted racerd' )


  def GetSubcommandsMap( self ):
    return {
      'GoTo' : ( lambda self, request_data, args:
                 self._GoToDefinition( request_data ) ),
      'GoToDefinition' : ( lambda self, request_data, args:
                           self._GoToDefinition( request_data ) ),
      'GoToDeclaration' : ( lambda self, request_data, args:
                           self._GoToDefinition( request_data ) ),
      'StopServer' : ( lambda self, request_data, args:
                           self._StopServer() ),
      'RestartServer' : ( lambda self, request_data, args:
                           self._RestartServer() ),
    }


  def _GoToDefinition( self, request_data ):
    try:
      definition = self._GetResponse( '/find_definition', request_data )
      return responses.BuildGoToResponse( definition[ 'file_path' ],
                                          definition[ 'line' ],
                                          definition[ 'column' ] + 1 )
    except Exception:
      raise RuntimeError( 'Can\'t jump to definition.' )


  def Shutdown( self ):
    self._StopServer()


  def _CreateHmacSecret( self ):
    return base64.b64encode( os.urandom( HMAC_SECRET_LENGTH ) )


  def DebugInfo( self, request_data ):
    with self._server_state_lock:
      if self.ServerIsRunning():
        return ( 'racerd\n'
                 '  listening at: {0}\n'
                 '  racerd path: {1}\n'
                 '  stdout log: {2}\n'
                 '  stderr log: {3}').format( self._racerd_host,
                                              self._racerd,
                                              self._server_stdout,
                                              self._server_stderr )

      if self._server_stdout and self._server_stderr:
        return ( 'racerd is no longer running\n',
                 '  racerd path: {0}\n'
                 '  stdout log: {1}\n'
                 '  stderr log: {2}').format( self._racerd,
                                              self._server_stdout,
                                              self._server_stderr )

      return 'racerd is not running'
