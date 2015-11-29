#
# Copyright (C) 2015 ycmd contrubutors.
#
# This file is part of YouCompleteMe.
#
# YouCompleteMe is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# YouCompleteMe is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with YouCompleteMe.  If not, see <http://www.gnu.org/licenses/>.

import logging, os, requests, traceback, threading
from ycmd import utils, responses
from ycmd.completers.completer import Completer

_logger = logging.getLogger( __name__ )

PATH_TO_TERNJS_BINARY = os.path.join(
    os.path.abspath( os.path.dirname( __file__ ) ),
    '..',
    '..',
    '..',
    'third_party',
    'tern',
    'bin',
    'tern' )


class TernCompleter( Completer ):
  """Completer for javascript using tern.js: http://ternjs.net.

  The protocol is defined here: http://ternjs.net/doc/manual.html#protocol"""

  subcommands = {
    'StartServer':     ( lambda self, request_data, args:
                                        self._StartServer() ),
    'StopServer':      ( lambda self, request_data, args:
                                        self._StopServer() ),
    'ConnectToServer': ( lambda self, request_data, args:
                                       self._ConnectToServer( args ) ),
    'GoToDefinition':  ( lambda self, request_data, args:
                                        self._GoToDefinition( request_data) ),
    'GoTo':            ( lambda self, request_data, args:
                                        self._GoToDefinition( request_data) ),
    'GetType':         ( lambda self, request_data, args:
                                        self._GetType( request_data) ),
    'GetDoc':          ( lambda self, request_data, args:
                                       self._GetDoc( request_data) ),
  }

  logfile_format = os.path.join( utils.PathToTempDir(),
                                 u'tern_{port}_{std}.log' )


  # Used to ensure that access to the members _server_port, _server_handle,
  # _server_stdout, _server_stderr are synchronised.
  server_state_mutex = threading.Lock()


  def __init__( self, user_options ):
    super( TernCompleter, self ).__init__( user_options )

    self._user_options = user_options

    with TernCompleter.server_state_mutex:
      self._server_stdout = None
      self._server_stderr = None
      self._Reset()


  def ComputeCandidatesInner( self, request_data ):
    query = {
      'type': 'completions',
      'types': True,
      'docs': True,
      'filter': False,
      'caseInsensitive': True,
      'guess': True,
      'sort': False,
      'includeKeywords': False,
      'expandWordForward': False,
    }

    completions = self._GetResponse( query,
                                     request_data ).get( 'completions', [] )

    return [ responses.BuildCompletionData( completion[ 'name' ],
                                            completion.get( 'type', '?' ),
                                            completion.get( 'doc', None ) )
             for completion in completions ]


  def DefinedSubcommands( self ):
    return self.subcommands.keys()


  def OnFileReadyToParse( self, request_data ):
    self._StartServer()

    # Send a message with no "query" block. This just updates the status of all
    # the files in the request_data. We also ignore the response, because at
    # best it is an empty object.
    self._PostRequest( {}, request_data )


  def OnUserCommand( self, arguments, request_data ):
    if not arguments or arguments[ 0 ] not in TernCompleter.subcommands:
      raise ValueError( self.UserCommandsHelpMessage() )

    return TernCompleter.subcommands[ arguments[ 0 ] ]( self,
                                                        request_data,
                                                        arguments[ 1: ] )


  def SupportedFiletypes( self ):
    return [ 'javascript' ]


  def DebugInfo( self, request_data ):
    # TODO: this method is ugly, refactor it

    with TernCompleter.server_state_mutex:
      if self._server_handle is None:
        if self._server_port > 0:
          return ( ' -- Connected to external server on port: '
                   + str( self._server_port ) )

        return ' -- Tern server is not running'

      return ( ' -- Tern server is running on port: '
               + str( self._server_port )
               + ' with PID: '
               + str( self._server_handle.pid )
               + '\n -- Server stdout: '
               + self._server_stdout
               + '\n -- Server stderr: '
               + self._server_stderr )


  def Shutdown( self ):
    self._StopServer()


  def ServerIsReady( self, request_data = {} ):
    try:
      return bool(
          self._server_port > 0 and
          self._PostRequest( {'type': 'files'}, request_data ) is not None )
    except Exception:
      return False


  def _Reset( self ):
    """Callers must hold TernCompleter.server_state_mutex"""
    if not self.user_options[ 'server_keep_logfiles' ]:
      if self._server_stdout:
        os.unlink( self._server_stdout )
      if self._server_stderr:
        os.unlink( self._server_stderr )

    self._server_handle = None
    self._server_port   = 0
    self._server_stdout = None
    self._server_stderr = None


  def _PostRequest( self, request, request_data ):
    """Send a raw request with the supplied request block, and
    return the server's response. If the server is not running, it is started.

    This method is useful where the query block is not supplied, i.e. where just
    the files are being updated.

    The request block should contain the optional query block only. The file
    data and timeout are are added automatically."""

    # We access _server_port without the lock here because accessing the lock
    # would be a big bottleneck

    if self._server_port <= 0:
      raise ValueError( 'Not connected to server' )

    target = 'http://localhost:' + str( self._server_port )

    def MakeIncompleteFile( name, file_data ):
      return {
        'type': 'full',
        'name': name,
        'text': file_data[ 'contents' ],
      }

    file_data = request_data.get( 'file_data', {} )

    full_request = {
      'files': [
        MakeIncompleteFile( x, file_data[ x ] ) for x in file_data.keys()
      ],
      'timeout': 500,
    }
    full_request.update( request )

    response = requests.post( target, data = utils.ToUtf8Json( full_request ) )

    return response.json()


  def _GetResponse( self, query, request_data ):
    """Send a standard file/line request with the supplied query block, and
    return the server's response. If the server is not running, it is started.

    This method should be used for almost all requests. The exception is when
    just updating file data in which case _PostRequest should be used directly.

    The query block should contain the type and any parameters. The files,
    position, timeout etc. are added automatically."""

    def MakeTernLocation( request_data ):
      return {
        'line': request_data[ 'line_num' ] - 1,
        'ch':   request_data[ 'start_column' ] - 1
      }

    full_query = {
      'file':              request_data[ 'filepath' ],
      'end':               MakeTernLocation( request_data ),
      'lineCharPositions': True,
    }
    full_query.update( query )

    return self._PostRequest( { 'query': full_query }, request_data )


  def _StartServer( self ):
    with TernCompleter.server_state_mutex:
      self._StartServerNoLock()


  def _StartServerNoLock( self ):
    """Start the server, under the lock.

    Callers must hold TernCompleter.server_state_mutex"""

    if self._server_handle is None and self._server_port <= 0:
      _logger.info( 'Starting Tern.js server...' )

      self._server_port = utils.GetUnusedLocalhostPort()

      if _logger.isEnabledFor( logging.DEBUG ):
        extra_args = [ '--verbose' ]
      else:
        extra_args = []

      command = [ PATH_TO_TERNJS_BINARY,
                  '--port',
                  str( self._server_port ),
                  '--host',
                  'localhost',
                  '--persistent',
                  '--no-port-file' ] + extra_args

      self._server_stdout = TernCompleter.logfile_format.format(
          port = self._server_port,
          std = 'stdout' )

      self._server_stderr = TernCompleter.logfile_format.format(
          port = self._server_port,
          std = 'stderr' )

      try:
        with open( self._server_stdout, 'w' ) as stdout:
          with open( self._server_stderr, 'w' ) as stderr:
            self._server_handle = utils.SafePopen( command,
                                                   stdout = stdout,
                                                   stderr = stderr )
      except Exception:
        _logger.warning( 'Unable to start Tern.js server: '
                         + traceback.format_exc() )
        self._Reset()

      if self._server_port > 0:
        _logger.info( 'Tern.js Server started with pid: ' +
                      str( self._server_handle.pid ) +
                      ' listening on port ' +
                      str( self._server_port ) )
        _logger.info( 'Tern.js Server log files are: ' +
                      self._server_stdout +
                      ' and ' +
                      self._server_stderr )


  def _StopServer( self ):
    with TernCompleter.server_state_mutex:
      self._StopServerNoLock()


  def _StopServerNoLock( self ):
    """Stop the server, under the lock.

    Callers must hold TernCompleter.server_state_mutex"""
    if self._server_handle is not None:
      _logger.info( 'Stopping Tern.js server with pid '
                    + str( self._server_handle.pid )
                    + '...' )

      self._server_handle.kill()

      _logger.info( 'Tern.js server killed.' )

      self._Reset()


  def _ConnectToServer( self, args ):
    if not len( args ):
      raise ValueError( 'Usage ConnectTo <port>' )

    with TernCompleter.server_state_mutex:
      self._StopServer()
      _logger.info( 'Connecting to external server on port: ' + str( args[0] ) )
      self._server_port = int( args[0] )

    return responses.BuildDisplayMessageResponse( 'Connected' )


  def _GetType( self, request_data ):
    query = {
      'type': 'type',
    }

    response = self._GetResponse( query, request_data )

    return responses.BuildDisplayMessageResponse( response[ 'type' ] )


  def _GetDoc( self, request_data ):
    query = {
      'type':      'documentation',
      'docFormat': 'full',
    }

    response = self._GetResponse( query, request_data )

    return responses.BuildDetailedInfoResponse(
                    response.get( 'doc', 'No documentation available' ) )


  def _GoToDefinition( self, request_data ):
    query = {
      'type': 'definition',
    }

    response = self._GetResponse( query, request_data )

    return responses.BuildGoToResponse(
      response[ 'file' ],
      response[ 'start' ][ 'line' ] + 1,
      response[ 'start' ][ 'ch' ] + 1
    )
