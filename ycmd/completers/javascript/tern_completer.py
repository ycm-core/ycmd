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

PATH_TO_TERNJS_BINARY = os.path.abspath(
    os.path.join(
      os.path.dirname( __file__ ),
      '..',
      '..',
      '..',
      'third_party',
      'tern',
      'bin',
      'tern' ) )

PATH_TO_NODE = utils.PathToFirstExistingExecutable( [ 'node' ] )

# host name/address on which the tern server should listen
# note: we use 127.0.0.1 rather than localhost because on some platforms
# localhost might not be correctly configured as an alias for the loopback
# address. (ahem: Windows)
SERVER_HOST = '127.0.0.1'


def ShouldEnableTernCompleter():
  """Returns whether or not the tern completer is 'installed'. That is whether
  or not the tern submodule has a 'node_modules' directory. This is pretty much
  the only way we can know if the user added '--tern-completer' on
  install or manually ran 'npm install' in the tern submodule directory."""

  if not PATH_TO_NODE:
    _logger.warning( 'Not using Tern completer: unable to find node' )
    return False

  _logger.info( 'Using node binary from: ' + PATH_TO_NODE )

  installed = os.path.exists(
      os.path.join( os.path.abspath( os.path.dirname( __file__ ) ),
                    '..',
                    '..',
                    '..',
                    'third_party',
                    'tern',
                    'node_modules' ) )

  if not installed:
    _logger.info( 'Not using Tern completer: not installed' )
    return False

  return True


def GlobalConfigExists( tern_config ):
  """Returns whether or not the global config file with the supplied path
  exists. This method primarily exists to allow testability and simply returns
  whether the supplied file exists."""
  return os.path.exists( tern_config )


def FindTernProjectFile( starting_directory ):
  # We use a dummy_file here because AncestorFolders requires a file name and we
  # don't have one. Something like '.' doesn't work because, while
  # os.path.dirname( /a/b/c/. ) returns /a/b/c, AncestorFolders calls
  # os.path.abspath on it, so the /. is removed.
  starting_file = os.path.join( starting_directory, 'dummy_file' )
  for folder in utils.AncestorFolders( starting_file ):
    tern_project = os.path.join( folder, '.tern-project' )
    if os.path.exists( tern_project ):
      return tern_project

  # As described here: http://ternjs.net/doc/manual.html#server a global
  # .tern-config file is also supported for the Tern server. This can provide
  # meaningful defaults (for libs, and possibly also for require paths), so
  # don't warn if we find one. The point is that if the user has a .tern-config
  # set up, then she has deliberately done so and a ycmd warning is unlikely
  # to be anything other than annoying.
  tern_config = os.path.expanduser( '~/.tern-config' )
  if GlobalConfigExists( tern_config ):
    return tern_config

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
    # The Tern server will operate without a .tern-project file. However, it
    # does not operate optimally, and will likely lead to issues reported that
    # JavaScript completion is not working properly. So we raise a warning if we
    # aren't able to detect some semblance of manual Tern configuration.

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
                            'in the hierarchy before ' + os.getcwd() +
                            ' and no global .tern-config file was found. '
                            'This is required for accurate JavaScript '
                            'completion. Please see the User Guide for '
                            'details.' )
      else:
        _logger.info( 'Detected .tern-project file at: ' + tern_project )


  def _GetServerAddress( self ):
    return 'http://' + SERVER_HOST + ':' + str( self._server_port )


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
    _logger.debug( "Shutting down Tern server" )
    self._StopServer()


  def ServerIsReady( self, request_data = {} ):
    if not self._ServerIsRunning():
      return False

    try:
      target = self._GetServerAddress() + '/ping'
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
    data are added automatically."""

    if not self._ServerIsRunning():
      raise ValueError( 'Not connected to server' )

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
    }
    full_request.update( request )

    response = requests.post( self._GetServerAddress(),
                              data = utils.ToUtf8Json( full_request ) )

    if response.status_code != httplib.OK:
      raise RuntimeError( response.text )

    return response.json()


  def _GetResponse( self, query, request_data ):
    """Send a standard file/line request with the supplied query block, and
    return the server's response. If the server is not running, it is started.

    This method should be used for almost all requests. The exception is when
    just updating file data in which case _PostRequest should be used directly.

    The query block should contain the type and any parameters. The files,
    position, etc. are added automatically."""

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

    command = [ PATH_TO_NODE,
                PATH_TO_TERNJS_BINARY,
                '--port',
                str( self._server_port ),
                '--host',
                SERVER_HOST,
                '--persistent',
                '--no-port-file' ] + extra_args

    _logger.debug( 'Starting tern with the following command: '
                   + ' '.join( command ) )

    try:
      if utils.OnWindows():
        # FIXME:
        # For unknown reasons, redirecting stdout and stderr on windows for this
        # particular Completer does not work. It causes tern to crash with an
        # access error on startup. Rather than spending too much time trying to
        # understand this (it's either a bug in Python, node or our code, and it
        # isn't obvious which), we just suppress the log files on this platform.
        # ATOW the only output from the server is the line saying it is
        # listening anyway. Verbose logging includes requests and responses, but
        # they can be tested on other platforms.
        self._server_stdout = "<Not supported on this platform>"
        self._server_stderr = "<Not supported on this platform>"
        self._server_handle = utils.SafePopen( command )
      else:
        logfile_format = os.path.join( utils.PathToTempDir(),
                                       u'tern_{port}_{std}.log' )

        self._server_stdout = logfile_format.format(
            port = self._server_port,
            std = 'stdout' )

        self._server_stderr = logfile_format.format(
            port = self._server_port,
            std = 'stderr' )

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
