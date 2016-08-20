# Copyright (C) 2015 Google Inc.
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
from future import standard_library
standard_library.install_aliases()
from builtins import *  # noqa

import json
import logging
import os
import subprocess
import threading

from ycmd import responses
from ycmd import utils
from ycmd.utils import ToBytes, ToUnicode, ExecutableName
from ycmd.completers.completer import Completer

BINARY_NOT_FOUND_MESSAGE = ( '{0} binary not found. Did you build it? '
                             'You can do so by running '
                             '"./install.py --gocode-completer".' )
SHELL_ERROR_MESSAGE = ( 'Command {command} failed with code {code} and error '
                        '"{error}".' )
COMPUTE_OFFSET_ERROR_MESSAGE = ( 'Go completer could not compute byte offset '
                                 'corresponding to line {line} and column '
                                 '{column}.' )

GOCODE_PARSE_ERROR_MESSAGE = 'Gocode returned invalid JSON response.'
GOCODE_NO_COMPLETIONS_MESSAGE = 'No completions found.'
GOCODE_PANIC_MESSAGE = ( 'Gocode panicked trying to find completions, '
                         'you likely have a syntax error.' )

DIR_OF_THIRD_PARTY = os.path.abspath(
  os.path.join( os.path.dirname( __file__ ), '..', '..', '..', 'third_party' ) )
GO_BINARIES = dict( {
  'gocode': os.path.join( DIR_OF_THIRD_PARTY,
                          'gocode',
                          ExecutableName( 'gocode' ) ),
  'godef': os.path.join( DIR_OF_THIRD_PARTY,
                         'godef',
                         ExecutableName( 'godef' ) )
} )

LOG_FILENAME_FORMAT = os.path.join( utils.PathToCreatedTempDir(),
                                    'gocode_{port}_{std}.log' )

_logger = logging.getLogger( __name__ )


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
      _logger.error( BINARY_NOT_FOUND_MESSAGE.format( binary ) )
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
    self._gocode_address = None
    self._gocode_stderr = None
    self._gocode_stdout = None

    self._godef_binary_path = FindBinary( 'godef', user_options )

    self._keep_logfiles = user_options[ 'server_keep_logfiles' ]

    self._StartServer()


  def SupportedFiletypes( self ):
    return [ 'go' ]


  def ComputeCandidatesInner( self, request_data ):
    filename = request_data[ 'filepath' ]
    _logger.info( 'Gocode completion request {0}'.format( filename ) )

    contents = utils.ToBytes(
        request_data[ 'file_data' ][ filename ][ 'contents' ] )

    # NOTE: Offsets sent to gocode are byte offsets, so using start_column
    # with contents (a bytes instance) above is correct.
    offset = _ComputeOffset( contents,
                             request_data[ 'line_num' ],
                             request_data[ 'start_column' ] )

    stdoutdata = self._ExecuteCommand( [ self._gocode_binary_path,
                                         '-sock', 'tcp',
                                         '-addr', self._gocode_address,
                                         '-f=json', 'autocomplete',
                                         filename, str( offset ) ],
                                       contents = contents )

    try:
      resultdata = json.loads( ToUnicode( stdoutdata ) )
    except ValueError:
      _logger.error( GOCODE_PARSE_ERROR_MESSAGE )
      raise RuntimeError( GOCODE_PARSE_ERROR_MESSAGE )

    if len( resultdata ) != 2:
      _logger.error( GOCODE_NO_COMPLETIONS_MESSAGE )
      raise RuntimeError( GOCODE_NO_COMPLETIONS_MESSAGE )
    for result in resultdata[ 1 ]:
      if result.get( 'class' ) == 'PANIC':
        raise RuntimeError( GOCODE_PANIC_MESSAGE )

    return [ _ConvertCompletionData( x ) for x in resultdata[ 1 ] ]


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
      _logger.error( message )
      raise RuntimeError( message )

    return stdoutdata


  def _StartServer( self ):
    """Start the Gocode server."""
    with self._gocode_lock:
      _logger.info( 'Starting Gocode server' )

      self._gocode_port = utils.GetUnusedLocalhostPort()
      self._gocode_address = '127.0.0.1:{0}'.format( self._gocode_port )

      command = [ self._gocode_binary_path,
                  '-s',
                  '-sock', 'tcp',
                  '-addr', self._gocode_address ]

      if _logger.isEnabledFor( logging.DEBUG ):
        command.append( '-debug' )

      self._gocode_stdout = LOG_FILENAME_FORMAT.format(
          port = self._gocode_port, std = 'stdout' )
      self._gocode_stderr = LOG_FILENAME_FORMAT.format(
          port = self._gocode_port, std = 'stderr' )

      with open( self._gocode_stdout, 'w' ) as stdout:
        with open( self._gocode_stderr, 'w' ) as stderr:
          self._gocode_handle = utils.SafePopen( command,
                                                 stdout = stdout,
                                                 stderr = stderr )


  def _StopServer( self ):
    """Stop the Gocode server."""
    with self._gocode_lock:
      if self._ServerIsRunning():
        _logger.info( 'Stopping Gocode server with PID {0}'.format(
                          self._gocode_handle.pid ) )
        self._ExecuteCommand( [ self._gocode_binary_path,
                                '-sock', 'tcp',
                                '-addr', self._gocode_address,
                                'close' ] )
        try:
          utils.WaitUntilProcessIsTerminated( self._gocode_handle, timeout = 5 )
          _logger.info( 'Gocode server stopped' )
        except RuntimeError:
          _logger.exception( 'Error while stopping Gocode server' )

      self._CleanUp()


  def _CleanUp( self ):
    self._gocode_handle = None
    self._gocode_port = None
    self._gocode_address = None
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
    _logger.info( 'Godef GoTo request {0}'.format( filename ) )

    contents = utils.ToBytes(
      request_data[ 'file_data' ][ filename ][ 'contents' ] )
    offset = _ComputeOffset( contents,
                             request_data[ 'line_num' ],
                             request_data[ 'column_num' ] )
    try:
      stdout = self._ExecuteCommand( [ self._godef_binary_path,
                                       '-i',
                                       '-f={0}'.format( filename ),
                                       '-json',
                                       '-o={0}'.format( offset ) ],
                                     contents = contents )
    # We catch this exception type and not a more specific one because we
    # raise it in _ExecuteCommand when the command fails.
    except RuntimeError as error:
      _logger.exception( error )
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
    """Check if the Gocode server is healthy (up and serving)."""
    if not self._ServerIsRunning():
      return False

    try:
      self._ExecuteCommand( [ self._gocode_binary_path,
                              '-sock', 'tcp',
                              '-addr', self._gocode_address,
                              'status' ] )
      return True
    # We catch this exception type and not a more specific one because we
    # raise it in _ExecuteCommand when the command fails.
    except RuntimeError as error:
      _logger.exception( error )
      return False


  def ServerIsReady( self ):
    """Check if the Gocode server is ready. Same as the healthy status."""
    return self.ServerIsHealthy()


  def DebugInfo( self, request_data ):
    with self._gocode_lock:
      if self._ServerIsRunning():
        return ( 'Go completer debug information:\n'
                 '  Gocode running at: http://{0}\n'
                 '  Gocode process ID: {1}\n'
                 '  Gocode executable: {2}\n'
                 '  Gocode logfiles:\n'
                 '    {3}\n'
                 '    {4}\n'
                 '  Godef executable: {5}'.format( self._gocode_address,
                                                   self._gocode_handle.pid,
                                                   self._gocode_binary_path,
                                                   self._gocode_stdout,
                                                   self._gocode_stderr,
                                                   self._godef_binary_path ) )

      if self._gocode_stdout and self._gocode_stderr:
        return ( 'Go completer debug information:\n'
                 '  Gocode no longer running\n'
                 '  Gocode executable: {0}\n'
                 '  Gocode logfiles:\n'
                 '    {1}\n'
                 '    {2}\n'
                 '  Godef executable: {3}'.format( self._gocode_binary_path,
                                                   self._gocode_stdout,
                                                   self._gocode_stderr,
                                                   self._godef_binary_path ) )

      return ( 'Go completer debug information:\n'
               '  Gocode is not running\n'
               '  Gocode executable: {0}\n'
               '  Godef executable: {1}'.format( self._gocode_binary_path,
                                                 self._godef_binary_path ) )


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
  _logger.error( message )
  raise RuntimeError( message )


def _ConvertCompletionData( completion_data ):
  return responses.BuildCompletionData(
    insertion_text = completion_data[ 'name' ],
    menu_text = completion_data[ 'name' ],
    extra_menu_info = completion_data[ 'type' ],
    kind = completion_data[ 'class' ],
    detailed_info = ' '.join( [
        completion_data[ 'name' ],
        completion_data[ 'type' ],
        completion_data[ 'class' ] ] ) )
