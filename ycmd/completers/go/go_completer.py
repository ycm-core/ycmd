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

import json
import logging
import os
import subprocess
import threading

from ycmd import responses
from ycmd import utils
from ycmd.utils import LOGGER, ToBytes, ToUnicode, ExecutableName
from ycmd.completers.completer import Completer

SHELL_ERROR_MESSAGE = ( 'Command {command} failed with code {code} and error '
                        '"{error}".' )
COMPUTE_OFFSET_ERROR_MESSAGE = ( 'Go completer could not compute byte offset '
                                 'corresponding to line {line} and column '
                                 '{column}.' )

GOCODE_PARSE_ERROR_MESSAGE = 'Gocode returned invalid JSON response.'
GOCODE_NO_COMPLETIONS_MESSAGE = 'No completions found.'
GOCODE_PANIC_MESSAGE = ( 'Gocode panicked trying to find completions, '
                         'you likely have a syntax error.' )

GO_DIR = os.path.abspath(
  os.path.join( os.path.dirname( __file__ ), '..', '..', '..', 'third_party',
                'go', 'src', 'github.com' ) )
GO_BINARIES = dict( {
  'gocode': os.path.join( GO_DIR, 'mdempsky', 'gocode',
                          ExecutableName( 'gocode' ) ),
  'godef': os.path.join( GO_DIR, 'rogpeppe', 'godef',
                         ExecutableName( 'godef' ) )
} )

LOGFILE_FORMAT = 'gocode_{port}_{std}_'


def FindBinary( binary, user_options ):
  """Find the path to the Gocode/Godef binary.

  If 'gocode_binary_path' or 'godef_binary_path'
  in the options is blank, use the version installed
  with YCM, if it exists.

  If the 'gocode_binary_path' or 'godef_binary_path' is
  specified, use it as an absolute path.

  If the resolved binary exists, return the path,
  otherwise return None."""

  def _FindPath():
    key = '{0}_binary_path'.format( binary )
    if user_options.get( key ):
      return user_options[ key ]
    return GO_BINARIES.get( binary )

  binary_path = _FindPath()
  if os.path.isfile( binary_path ):
    return binary_path
  return None


def ShouldEnableGoCompleter( user_options ):
  def _HasBinary( binary ):
    binary_path = FindBinary( binary, user_options )
    if not binary_path:
      LOGGER.error( '%s binary not found', binary_path )
    return binary_path

  return all( _HasBinary( binary ) for binary in [ 'gocode', 'godef' ] )


class GoCompleter( Completer ):
  """Completer for Go using the Gocode daemon for completions:
  https://github.com/nsf/gocode
  and the Godef binary for jumping to definitions:
  https://github.com/Manishearth/godef"""

  def __init__( self, user_options ):
    super( GoCompleter, self ).__init__( user_options )
    self._gocode_binary_path = FindBinary( 'gocode', user_options )
    self._gocode_lock = threading.RLock()
    self._gocode_handle = None
    self._gocode_port = None
    self._gocode_host = None
    self._gocode_stderr = None
    self._gocode_stdout = None

    self._godef_binary_path = FindBinary( 'godef', user_options )

    self._keep_logfiles = user_options[ 'server_keep_logfiles' ]

    self._StartServer()


  def SupportedFiletypes( self ):
    return [ 'go' ]


  def ComputeCandidatesInner( self, request_data ):
    filename = request_data[ 'filepath' ]
    LOGGER.info( 'Gocode completion request %s', filename )

    contents = utils.ToBytes(
        request_data[ 'file_data' ][ filename ][ 'contents' ] )

    # NOTE: Offsets sent to gocode are byte offsets, so using start_column
    # with contents (a bytes instance) above is correct.
    offset = _ComputeOffset( contents,
                             request_data[ 'line_num' ],
                             request_data[ 'start_column' ] )

    stdoutdata = self._ExecuteCommand( [ self._gocode_binary_path,
                                         '-sock', 'tcp',
                                         '-addr', self._gocode_host,
                                         '-f=json', 'autocomplete',
                                         filename, str( offset ) ],
                                       contents = contents )

    try:
      resultdata = json.loads( ToUnicode( stdoutdata ) )
    except ValueError:
      LOGGER.error( GOCODE_PARSE_ERROR_MESSAGE )
      raise RuntimeError( GOCODE_PARSE_ERROR_MESSAGE )

    if not isinstance( resultdata, list ) or len( resultdata ) != 2:
      LOGGER.error( GOCODE_NO_COMPLETIONS_MESSAGE )
      raise RuntimeError( GOCODE_NO_COMPLETIONS_MESSAGE )
    for result in resultdata[ 1 ]:
      if result.get( 'class' ) == 'PANIC':
        raise RuntimeError( GOCODE_PANIC_MESSAGE )

    return [ responses.BuildCompletionData(
      insertion_text = x[ 'name' ],
      extra_data = x ) for x in resultdata[ 1 ] ]


  def GetSubcommandsMap( self ):
    return {
      'StopServer'     : ( lambda self, request_data, args:
                           self._StopServer() ),
      'RestartServer'  : ( lambda self, request_data, args:
                           self._RestartServer() ),
      'GoTo'           : ( lambda self, request_data, args:
                           self._GoToDefinition( request_data ) ),
      'GoToDefinition' : ( lambda self, request_data, args:
                           self._GoToDefinition( request_data ) ),
      'GoToDeclaration': ( lambda self, request_data, args:
                           self._GoToDefinition( request_data ) ),
    }


  def _ExecuteCommand( self, command, contents = None ):
    """Run a command in a subprocess and communicate with it using the contents
    argument. Return the standard output.

    It is used to send a command to the Gocode daemon or execute the Godef
    binary."""
    phandle = utils.SafePopen( command,
                               stdin = subprocess.PIPE,
                               stdout = subprocess.PIPE,
                               stderr = subprocess.PIPE )

    stdoutdata, stderrdata = phandle.communicate( contents )

    if phandle.returncode:
      message = SHELL_ERROR_MESSAGE.format(
          command = ' '.join( command ),
          code = phandle.returncode,
          error = ToUnicode( stderrdata.strip() ) )
      LOGGER.error( message )
      raise RuntimeError( message )

    return stdoutdata


  def _StartServer( self ):
    """Start the Gocode server."""
    with self._gocode_lock:
      LOGGER.info( 'Starting Gocode server' )

      self._gocode_port = utils.GetUnusedLocalhostPort()
      self._gocode_host = '127.0.0.1:{0}'.format( self._gocode_port )

      command = [ self._gocode_binary_path,
                  '-s',
                  '-sock', 'tcp',
                  '-addr', self._gocode_host ]

      if LOGGER.isEnabledFor( logging.DEBUG ):
        command.append( '-debug' )

      self._gocode_stdout = utils.CreateLogfile(
          LOGFILE_FORMAT.format( port = self._gocode_port, std = 'stdout' ) )
      self._gocode_stderr = utils.CreateLogfile(
          LOGFILE_FORMAT.format( port = self._gocode_port, std = 'stderr' ) )

      with utils.OpenForStdHandle( self._gocode_stdout ) as stdout:
        with utils.OpenForStdHandle( self._gocode_stderr ) as stderr:
          self._gocode_handle = utils.SafePopen( command,
                                                 stdout = stdout,
                                                 stderr = stderr )


  def _StopServer( self ):
    """Stop the Gocode server."""
    with self._gocode_lock:
      if self._ServerIsRunning():
        LOGGER.info( 'Stopping Gocode server with PID %s',
                     self._gocode_handle.pid )
        try:
          self._ExecuteCommand( [ self._gocode_binary_path,
                                  '-sock', 'tcp',
                                  '-addr', self._gocode_host,
                                  'close' ] )
          utils.WaitUntilProcessIsTerminated( self._gocode_handle, timeout = 5 )
          LOGGER.info( 'Gocode server stopped' )
        except Exception:
          LOGGER.exception( 'Error while stopping Gocode server' )

      self._CleanUp()


  def _CleanUp( self ):
    self._gocode_handle = None
    self._gocode_port = None
    self._gocode_host = None
    if not self._keep_logfiles:
      if self._gocode_stdout:
        utils.RemoveIfExists( self._gocode_stdout )
        self._gocode_stdout = None
      if self._gocode_stderr:
        utils.RemoveIfExists( self._gocode_stderr )
        self._gocode_stderr = None


  def _RestartServer( self ):
    """Restart the Gocode server."""
    with self._gocode_lock:
      self._StopServer()
      self._StartServer()


  def _GoToDefinition( self, request_data ):
    filename = request_data[ 'filepath' ]
    LOGGER.info( 'Godef GoTo request %s', filename )

    contents = utils.ToBytes(
      request_data[ 'file_data' ][ filename ][ 'contents' ] )
    offset = _ComputeOffset( contents,
                             request_data[ 'line_num' ],
                             request_data[ 'column_num' ] )
    try:
      stdout = self._ExecuteCommand( [ self._godef_binary_path,
                                       '-i',
                                       '-f={}'.format( filename ),
                                       '-json',
                                       '-o={}'.format( offset ) ],
                                     contents = contents )
    # We catch this exception type and not a more specific one because we
    # raise it in _ExecuteCommand when the command fails.
    except RuntimeError:
      LOGGER.exception( 'Failed to jump to definition' )
      raise RuntimeError( 'Can\'t find a definition.' )

    return self._ConstructGoToFromResponse( stdout )


  def _ConstructGoToFromResponse( self, response_str ):
    parsed = json.loads( ToUnicode( response_str ) )
    if 'filename' in parsed and 'column' in parsed:
      return responses.BuildGoToResponse( parsed[ 'filename' ],
                                          int( parsed[ 'line' ] ),
                                          int( parsed[ 'column' ] ) )
    raise RuntimeError( 'Can\'t jump to definition.' )


  def Shutdown( self ):
    self._StopServer()


  def _ServerIsRunning( self ):
    """Check if the Gocode server is running (process is up)."""
    return utils.ProcessIsRunning( self._gocode_handle )


  def ServerIsHealthy( self ):
    """Assume the Gocode server is healthy if it's running."""
    return self._ServerIsRunning()


  def DebugInfo( self, request_data ):
    with self._gocode_lock:
      gocode_server = responses.DebugInfoServer(
        name = 'Gocode',
        handle = self._gocode_handle,
        executable = self._gocode_binary_path,
        address = '127.0.0.1',
        port = self._gocode_port,
        logfiles = [ self._gocode_stdout, self._gocode_stderr ] )

      godef_item = responses.DebugInfoItem( key = 'Godef executable',
                                            value = self._godef_binary_path )

      return responses.BuildDebugInfoResponse( name = 'Go',
                                               servers = [ gocode_server ],
                                               items = [ godef_item ] )


  def DetailCandidates( self, request_data, candidates ):
    for candidate in candidates:
      if 'kind' in candidate:
        # This candidate is already detailed
        continue
      completion = candidate[ 'extra_data' ]
      candidate[ 'menu_text' ] = completion[ 'name' ]
      candidate[ 'extra_menu_info' ] = completion[ 'type' ]
      candidate[ 'kind' ] = completion[ 'class' ]
      candidate[ 'detailed_info' ] = ' '.join( [
        completion[ 'name' ],
        completion[ 'type' ],
        completion[ 'class' ] ] )
      candidate.pop( 'extra_data' )
    return candidates


def _ComputeOffset( contents, line, column ):
  """Compute the byte offset in the file given the line and column."""
  contents = ToBytes( contents )
  current_line = 1
  current_column = 1
  newline = bytes( b'\n' )[ 0 ]
  for i, byte in enumerate( contents ):
    if current_line == line and current_column == column:
      return i
    current_column += 1
    if byte == newline:
      current_line += 1
      current_column = 1
  message = COMPUTE_OFFSET_ERROR_MESSAGE.format( line = line,
                                                 column = column )
  LOGGER.error( message )
  raise RuntimeError( message )
