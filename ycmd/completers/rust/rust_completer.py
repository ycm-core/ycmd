# Copyright (C) 2015-2018 ycmd contributors
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

from ycmd import responses, utils, hmac_utils
from ycmd.completers.completer import Completer
from ycmd.utils import ( ExpandVariablesInPath,
                         FindExecutable,
                         LOGGER,
                         ProcessIsRunning,
                         ToUnicode,
                         ToBytes,
                         SetEnviron,
                         urljoin )

from future.utils import iteritems, native
import requests
import json
import tempfile
import base64
import binascii
import threading
import os
import subprocess

from os import path as p

DIR_OF_THIRD_PARTY = p.abspath(
  p.join( p.dirname( __file__ ), '..', '..', '..', 'third_party' ) )

RACERD_BINARY_NAME = 'racerd' + ( '.exe' if utils.OnWindows() else '' )
RACERD_BINARY_RELEASE = p.join( DIR_OF_THIRD_PARTY, 'racerd', 'target',
                        'release', RACERD_BINARY_NAME )
RACERD_BINARY_DEBUG = p.join( DIR_OF_THIRD_PARTY, 'racerd', 'target',
                        'debug', RACERD_BINARY_NAME )

RACERD_HMAC_HEADER = 'x-racerd-hmac'
HMAC_SECRET_LENGTH = 16

BINARY_NOT_FOUND_MESSAGE = (
  'racerd binary not found. Did you build it? '
  'You can do so by running "./build.py --rust-completer".' )
NON_EXISTING_RUST_SOURCES_PATH_MESSAGE = (
  'Rust sources path does not exist. Check the value of the rust_src_path '
  'option or the RUST_SRC_PATH environment variable.' )
ERROR_FROM_RACERD_MESSAGE = (
  'Received error from racerd while retrieving completions. You did not '
  'set the rust_src_path option, which is probably causing this issue. '
  'See YCM docs for details.' )

LOGFILE_FORMAT = 'racerd_{port}_{std}_'


def _GetRustSysroot( rustc_exec ):
  return ToUnicode( utils.SafePopen( [ rustc_exec,
                                        '--print',
                                        'sysroot' ],
                                      stdin_windows = subprocess.PIPE,
                                      stdout = subprocess.PIPE,
                                      stderr = subprocess.PIPE )
                              .communicate()[ 0 ].rstrip() )


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
    LOGGER.warning( 'User-provided racerd_binary_path does not exist' )

  if os.path.isfile( RACERD_BINARY_RELEASE ):
    return RACERD_BINARY_RELEASE

  # We want to support using the debug binary for the sake of debugging; also,
  # building the release version on Travis takes too long.
  if os.path.isfile( RACERD_BINARY_DEBUG ):
    LOGGER.warning( 'Using racerd DEBUG binary; performance will suffer!' )
    return RACERD_BINARY_DEBUG

  return utils.PathToFirstExistingExecutable( [ 'racerd' ] )


class RustCompleter( Completer ):
  """
  A completer for the rust programming language backed by racerd.
  https://github.com/jwilm/racerd
  """

  def __init__( self, user_options ):
    super( RustCompleter, self ).__init__( user_options )
    self._racerd_binary = FindRacerdBinary( user_options )
    self._racerd_port = None
    self._racerd_host = None
    self._server_state_lock = threading.RLock()
    self._keep_logfiles = user_options[ 'server_keep_logfiles' ]
    self._hmac_secret = ''
    self._rust_source_path = self._GetRustSrcPath()

    if not self._rust_source_path:
      LOGGER.warning( 'No path provided for the rustc source. Please set the '
                      'rust_src_path option' )
    elif not p.isdir( self._rust_source_path ):
      LOGGER.error( NON_EXISTING_RUST_SOURCES_PATH_MESSAGE )
      raise RuntimeError( NON_EXISTING_RUST_SOURCES_PATH_MESSAGE )

    if not self._racerd_binary:
      LOGGER.error( BINARY_NOT_FOUND_MESSAGE )
      raise RuntimeError( BINARY_NOT_FOUND_MESSAGE )

    self._StartServer()


  def _GetRustSrcPath( self ):
    """
    Attempt to read user option for rust_src_path. Fallback to environment
    variable if it's not provided.
    Finally try to be smart and figure out the path assuming the user set up
    rust by the means of rustup.
    """
    rust_src_path = ( self.user_options[ 'rust_src_path' ] or
                      os.environ.get( 'RUST_SRC_PATH' ) )

    if rust_src_path:
      return ExpandVariablesInPath( rust_src_path )

    # Try to figure out the src path using rustup
    rustc_executable = FindExecutable( 'rustc' )
    if not rustc_executable:
      return None

    rust_sysroot = _GetRustSysroot( rustc_executable )
    rust_src_path = p.join( rust_sysroot,
                            'lib',
                            'rustlib',
                            'src',
                            'rust',
                            'src' )
    return rust_src_path if p.isdir( rust_src_path ) else None


  def SupportedFiletypes( self ):
    return [ 'rust' ]


  def _GetResponse( self, handler, request_data = None,
                    method = 'POST' ):
    """
    Query racerd via HTTP

    racerd returns JSON with 200 OK responses. 204 No Content responses occur
    when no errors were encountered but no completions, definitions, or errors
    were found.
    """
    handler = ToBytes( handler )
    method = ToBytes( method )
    url = urljoin( ToBytes( self._racerd_host ), handler )
    parameters = self._ConvertToRacerdRequest( request_data )
    body = ToBytes( json.dumps( parameters ) ) if parameters else bytes()
    extra_headers = self._ExtraHeaders( method, handler, body )

    LOGGER.debug( 'Making racerd request: %s %s %s %s',
                  method,
                  url,
                  extra_headers,
                  body )

    # Failing to wrap the method & url bytes objects in `native()` causes HMAC
    # failures (403 Forbidden from racerd) for unknown reasons. Similar for
    # request_hmac above.
    response = requests.request( native( method ),
                                 native( url ),
                                 data = body,
                                 headers = extra_headers )

    response.raise_for_status()

    if response.status_code == requests.codes.no_content:
      return None

    return response.json()


  def _ExtraHeaders( self, method, handler, body ):
    if not body:
      body = bytes()

    hmac = hmac_utils.CreateRequestHmac( method,
                                         handler,
                                         body,
                                         self._hmac_secret )
    final_hmac_value = native( ToBytes( binascii.hexlify( hmac ) ) )

    extra_headers = { 'content-type': 'application/json' }
    extra_headers[ RACERD_HMAC_HEADER ] = final_hmac_value
    return extra_headers


  def _ConvertToRacerdRequest( self, request_data ):
    """
    Transform ycm request into racerd request
    """
    if not request_data:
      return None

    file_path = request_data[ 'filepath' ]
    buffers = []
    for path, obj in iteritems( request_data[ 'file_data' ] ):
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
      location[ 'filepath' ] = completion[ 'file_path' ]
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
                insertion_text = completion[ 'text' ],
                kind = completion[ 'kind' ],
                extra_menu_info = completion[ 'context' ],
                extra_data = self._GetExtraData( completion ) )
             for completion in completions ]


  def _FetchCompletions( self, request_data ):
    return self._GetResponse( '/list_completions', request_data )


  def _StartServer( self ):
    with self._server_state_lock:
      self._racerd_port = utils.GetUnusedLocalhostPort()
      self._hmac_secret = self._CreateHmacSecret()

      # racerd will delete the secret_file after it's done reading it
      with tempfile.NamedTemporaryFile( delete = False ) as secret_file:
        secret_file.write( self._hmac_secret )
        args = [ self._racerd_binary, 'serve',
                '--port', str( self._racerd_port ),
                '-l',
                '--secret-file', secret_file.name ]

      # Enable logging of crashes
      env = os.environ.copy()
      SetEnviron( env, 'RUST_BACKTRACE', '1' )

      if self._rust_source_path:
        args.extend( [ '--rust-src-path', self._rust_source_path ] )

      self._server_stdout = utils.CreateLogfile(
          LOGFILE_FORMAT.format( port = self._racerd_port, std = 'stdout' ) )
      self._server_stderr = utils.CreateLogfile(
          LOGFILE_FORMAT.format( port = self._racerd_port, std = 'stderr' ) )

      with utils.OpenForStdHandle( self._server_stderr ) as fstderr:
        with utils.OpenForStdHandle( self._server_stdout ) as fstdout:
          self._racerd_phandle = utils.SafePopen( args,
                                                  stdout = fstdout,
                                                  stderr = fstderr,
                                                  env = env )

      self._racerd_host = 'http://127.0.0.1:{0}'.format( self._racerd_port )
      if not self._ServerIsRunning():
        raise RuntimeError( 'Failed to start racerd!' )
      LOGGER.info( 'Racerd started on: %s', self._racerd_host )


  def _ServerIsRunning( self ):
    """
    Check if racerd is alive. That doesn't necessarily mean it's ready to serve
    requests; that's checked by ServerIsHealthy.
    """
    with self._server_state_lock:
      return ( bool( self._racerd_host ) and
               ProcessIsRunning( self._racerd_phandle ) )


  def ServerIsHealthy( self ):
    """
    Check if racerd is alive AND ready to serve requests.
    """
    if not self._ServerIsRunning():
      LOGGER.debug( 'Racerd not running' )
      return False
    try:
      self._GetResponse( '/ping', method = 'GET' )
      return True
    # Do NOT make this except clause more generic! If you need to catch more
    # exception types, list them all out. Having `Exception` here caused FORTY
    # HOURS OF DEBUGGING.
    except requests.exceptions.ConnectionError:
      LOGGER.exception( 'Failed to connect to racerd' )
      return False


  def _StopServer( self ):
    with self._server_state_lock:
      if self._racerd_phandle:
        LOGGER.info( 'Stopping Racerd with PID %s', self._racerd_phandle.pid )
        self._racerd_phandle.terminate()
        try:
          utils.WaitUntilProcessIsTerminated( self._racerd_phandle,
                                              timeout = 5 )
          LOGGER.info( 'Racerd stopped' )
        except RuntimeError:
          LOGGER.exception( 'Error while stopping Racerd' )

      self._CleanUp()


  def _CleanUp( self ):
    self._racerd_phandle = None
    self._racerd_port = None
    self._racerd_host = None
    if not self._keep_logfiles:
      if self._server_stdout:
        utils.RemoveIfExists( self._server_stdout )
        self._server_stdout = None
      if self._server_stderr:
        utils.RemoveIfExists( self._server_stderr )
        self._server_stderr = None


  def _RestartServer( self ):
    LOGGER.debug( 'Restarting racerd' )

    with self._server_state_lock:
      if self._ServerIsRunning():
        self._StopServer()
      self._StartServer()

    LOGGER.debug( 'Racerd restarted' )


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
      'GetDoc' : ( lambda self, request_data, args:
                           self._GetDoc( request_data ) ),
    }


  def _GoToDefinition( self, request_data ):
    try:
      definition = self._GetResponse( '/find_definition',
                                      request_data )
      return responses.BuildGoToResponse( definition[ 'file_path' ],
                                          definition[ 'line' ],
                                          definition[ 'column' ] + 1 )
    except Exception:
      LOGGER.exception( 'Failed to find definition' )
      raise RuntimeError( 'Can\'t jump to definition.' )


  def _GetDoc( self, request_data ):
    try:
      definition = self._GetResponse( '/find_definition',
                                      request_data )

      docs = [ definition[ 'context' ], definition[ 'docs' ] ]
      return responses.BuildDetailedInfoResponse( '\n---\n'.join( docs ) )
    except Exception:
      LOGGER.exception( 'Failed to find definition' )
      raise RuntimeError( 'Can\'t lookup docs.' )

  def Shutdown( self ):
    self._StopServer()


  def _CreateHmacSecret( self ):
    return base64.b64encode( os.urandom( HMAC_SECRET_LENGTH ) )


  def DebugInfo( self, request_data ):
    with self._server_state_lock:
      racerd_server = responses.DebugInfoServer(
        name = 'Racerd',
        handle = self._racerd_phandle,
        executable = self._racerd_binary,
        address = '127.0.0.1',
        port = self._racerd_port,
        logfiles = [ self._server_stdout, self._server_stderr ] )

      rust_sources_item = responses.DebugInfoItem(
        key = 'Rust sources',
        value = self._rust_source_path )

      return responses.BuildDebugInfoResponse( name = 'Rust',
                                               servers = [ racerd_server ],
                                               items = [ rust_sources_item ] )
