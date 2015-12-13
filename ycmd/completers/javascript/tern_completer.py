#
# Copyright (C) 2015 ycmd contributors.
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

import httplib, logging, os, requests, traceback, threading
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


def ShouldEnableTernCompleter():
  """Returns whether or not the tern completer is 'installed'. That is whether
  or not the tern submodule has a 'node_modules' directory. This is pretty much
  the only way we can know if the user added '--tern-completer' on
  install or manually ran 'npm install' in the tern submodule directory."""
  return os.path.exists(
      os.path.join( os.path.abspath( os.path.dirname( __file__ ) ),
                    '..',
                    '..',
                    '..',
                    'third_party',
                    'tern',
                    'node_modules' ) )


def FindTernProjectFile( starting_directory ):
  starting_file = os.path.join( starting_directory, '.' )
  for folder in utils.AncestorFolders( starting_file ):
    tern_project = os.path.join( folder, '.tern-project' )
    if os.path.exists( tern_project ):
      return tern_project

  return None


class TernCompleter( Completer ):
  """Completer for JavaScript using tern.js: http://ternjs.net.

  The protocol is defined here: http://ternjs.net/doc/manual.html#protocol"""

  def __init__( self, user_options ):
    super( TernCompleter, self ).__init__( user_options )

    self._server_keep_logfiles = user_options[ 'server_keep_logfiles' ]

    # Used to ensure that starting/stopping of the server is synchronised
    self._server_state_mutex = threading.Lock()

    self._do_tern_project_check = False

    with self._server_state_mutex:
      self._server_stdout = None
      self._server_stderr = None
      self._Reset()
      self._StartServerNoLock()


  def _WarnIfMissingTernProject( self ):
    # We do this check after the server has started because the server does
    # have nonzero use without a project file, however limited. We only do this
    # check once, though because the server can only handle one project at a
    # time. This doesn't catch opening a file which is not part of the project
    # or any of those things, but we can only do so much. We'd like to enhance
    # ycmd to handle this better, but that is a FIXME for now.
    if self._ServerIsRunning() and self._do_tern_project_check:
      self._do_tern_project_check = False

      tern_project = FindTernProjectFile( os.getcwd() )
      if not tern_project:
        _logger.warning( 'No .tern-project file detected: ' + os.getcwd() )
        raise RuntimeError( 'Warning: Unable to detect a .tern-project file '
                            'in the hierarchy before ' + os.getcwd() + '. '
                            'This is required for accurate JavaScript '
                            'completion. Please see the User Guide for '
                            'details.' )
      else:
        _logger.info( 'Detected .tern-project file at: ' + tern_project )


  def ComputeCandidatesInner( self, request_data ):
    query = {
      'type': 'completions',
      'types': True,
      'docs': True,
      'filter': False,
      'caseInsensitive': True,
      'guess': False,
      'sort': False,
      'includeKeywords': False,
      'expandWordForward': False,
      'omitObjectPrototype': False
    }

    completions = self._GetResponse( query,
                                     request_data ).get( 'completions', [] )

    def BuildDoc( completion ):
      doc = completion.get( 'type', 'Unknown type' )
      if 'doc' in completion:
        doc = doc + '\n' + completion[ 'doc' ]

      return doc

    return [ responses.BuildCompletionData( completion[ 'name' ],
                                            completion.get( 'type', '?' ),
                                            BuildDoc( completion ) )
             for completion in completions ]


  def OnFileReadyToParse( self, request_data ):
    self._WarnIfMissingTernProject()

  def GetSubcommandsMap( self ):
    return {
      'StartServer':    ( lambda self, request_data, args:
                                         self._StartServer() ),
      'StopServer':     ( lambda self, request_data, args:
                                         self._StopServer() ),
      'GoToDefinition': ( lambda self, request_data, args:
                                         self._GoToDefinition( request_data ) ),
      'GoTo':           ( lambda self, request_data, args:
                                         self._GoToDefinition( request_data ) ),
      'GoToReferences': ( lambda self, request_data, args:
                                         self._GoToReferences( request_data ) ),
      'GetType':        ( lambda self, request_data, args:
                                         self._GetType( request_data) ),
      'GetDoc':         ( lambda self, request_data, args:
                                         self._GetDoc( request_data) ),
    }


  def SupportedFiletypes( self ):
    return [ 'javascript' ]


  def DebugInfo( self, request_data ):
    if self._server_handle is None:
      # server is not running because we haven't tried to start it.
      return ' * Tern server is not running'

    if not self._ServerIsRunning():
      # The handle is set, but the process isn't running. This means either it
      # crashed or we failed to start it.
      return ( ' * Tern server is not running (crashed)'
               + '\n * Server stdout: '
               + self._server_stdout
               + '\n * Server stderr: '
               + self._server_stderr )

    # Server is up and running.
    return ( ' * Tern server is running on port: '
             + str( self._server_port )
             + ' with PID: '
             + str( self._server_handle.pid )
             + '\n * Server stdout: '
             + self._server_stdout
             + '\n * Server stderr: '
             + self._server_stderr )


  def Shutdown( self ):
    self._StopServer()


  def ServerIsReady( self, request_data = {} ):
    if not self._ServerIsRunning():
      return False

    try:
      target = 'http://localhost:' + str( self._server_port ) + '/ping'
      response = requests.get( target )
      return response.status_code == httplib.OK
    except requests.ConnectionError:
      return False


  def _Reset( self ):
    """Callers must hold self._server_state_mutex"""

    if not self._server_keep_logfiles:
      if self._server_stdout and os.path.exists( self._server_stdout ):
        os.unlink( self._server_stdout )
      if self._server_stderr and os.path.exists( self._server_stderr ):
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

    if not self._ServerIsRunning():
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
      'files': [ MakeIncompleteFile( x, file_data[ x ] )
                 for x in file_data.keys() ],
      'timeout': 500,
    }
    full_request.update( request )

    response = requests.post( target, data = utils.ToUtf8Json( full_request ) )

    if response.status_code != httplib.OK:
      raise RuntimeError( response.text )

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
    if not self._ServerIsRunning():
      with self._server_state_mutex:
        self._StartServerNoLock()


  def _StartServerNoLock( self ):
    """Start the server, under the lock.

    Callers must hold self._server_state_mutex"""

    if self._ServerIsRunning():
      return

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

    if self._server_port > 0 and self._ServerIsRunning():
      _logger.info( 'Tern.js Server started with pid: ' +
                    str( self._server_handle.pid ) +
                    ' listening on port ' +
                    str( self._server_port ) )
      _logger.info( 'Tern.js Server log files are: ' +
                    self._server_stdout +
                    ' and ' +
                    self._server_stderr )

      self._do_tern_project_check = True
    else:
      _logger.warning( 'Tern.js server did not start successfully' )


  def _StopServer( self ):
    with self._server_state_mutex:
      self._StopServerNoLock()


  def _StopServerNoLock( self ):
    """Stop the server, under the lock.

    Callers must hold self._server_state_mutex"""
    if self._ServerIsRunning():
      _logger.info( 'Stopping Tern.js server with PID '
                    + str( self._server_handle.pid )
                    + '...' )

      self._server_handle.kill()

      _logger.info( 'Tern.js server killed.' )

      self._Reset()


  def _ServerIsRunning( self ):
    return ( self._server_handle is not None and
             self._server_handle.poll() is None )


  def _GetType( self, request_data ):
    query = {
      'type': 'type',
    }

    response = self._GetResponse( query, request_data )

    return responses.BuildDisplayMessageResponse( response[ 'type' ] )


  def _GetDoc( self, request_data ):
    # Note: we use the 'type' request because this is the best
    # way to get the name, type and doc string. The 'documentation' request
    # doesn't return the 'name' (strangely), wheras the 'type' request returns
    # the same docs with extra info.
    query = {
      'type':      'type',
      'docFormat': 'full',
      'types':      True
    }

    response = self._GetResponse( query, request_data )

    doc_string = 'Name: {name}\nType: {type}\n\n{doc}'.format(
        name = response.get( 'name', 'Unknown' ),
        type = response.get( 'type', 'Unknown' ),
        doc  = response.get( 'doc', 'No documentation available' ) )

    return responses.BuildDetailedInfoResponse( doc_string )


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


  def _GoToReferences( self, request_data ):
    query = {
      'type': 'refs',
    }

    response = self._GetResponse( query, request_data )

    return [ responses.BuildGoToResponse( ref[ 'file' ],
                                          ref[ 'start' ][ 'line' ] + 1,
                                          ref[ 'start' ][ 'ch' ] + 1 )
             for ref in response[ 'refs' ] ]
