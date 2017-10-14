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

import glob
import hashlib
import logging
import os
import shutil
import tempfile
import threading
from subprocess import PIPE

from ycmd import utils, responses
from ycmd.completers.language_server import language_server_completer

NO_DOCUMENTATION_MESSAGE = 'No documentation available for current context'

_logger = logging.getLogger( __name__ )

LANGUAGE_SERVER_HOME = os.path.join( os.path.dirname( __file__ ),
                                     '..',
                                     '..',
                                     '..',
                                     'third_party',
                                     'eclipse.jdt.ls',
                                     'org.eclipse.jdt.ls.product',
                                     'target',
                                     'repository')

PATH_TO_JAVA = utils.PathToFirstExistingExecutable( [ 'java' ] )

PROJECT_FILE_TAILS = [
  '.project',
  'pom.xml',
  'build.gradle'
]

WORKSPACE_ROOT_PATH = os.path.join( os.path.dirname( __file__ ),
                                    '..',
                                    '..',
                                    '..',
                                    'third_party',
                                    'eclipse.jdt.ls-workspace' )

# The authors of jdt.ls say that we should re-use workspaces. They also say that
# occasionally, the workspace becomes corrupt, and has to be deleted. This is
# frustrating.
#
# Pros for re-use:
#  - Startup time is significantly improved. This could be very meaningful on
#    larger projects
#
# Cons:
#  - A little more complexity (we hash the project path to create the workspace
#    dir)
#  - It breaks our tests which expect the logs to be deleted
#  - It can lead to multiple jdt.js instances using the same workspace (BAD)
#  - It breaks our tests which do exactly that
#
# So:
#  - By _default_ we use a clean workspace (see default_settings.json) on each
#    ycmd instance
#  - An option is available to re-use workspaces
CLEAN_WORKSPACE_OPTION = 'java_jdtls_use_clean_workspace'


def ShouldEnableJavaCompleter():
  _logger.info( 'Looking for jdt.ls' )
  if not PATH_TO_JAVA:
    _logger.warning( "Not enabling java completion: Couldn't find java" )
    return False

  if not os.path.exists( LANGUAGE_SERVER_HOME ):
    _logger.warning( 'Not using java completion: jdt.ls is not installed' )
    return False

  if not _PathToLauncherJar():
    _logger.warning( 'Not using java completion: jdt.ls is not built' )
    return False

  return True


def _PathToLauncherJar():
  # The file name changes between version of eclipse, so we use a glob as
  # recommended by the language server developers. There should only be one.
  launcher_jars = glob.glob(
    os.path.abspath(
      os.path.join(
        LANGUAGE_SERVER_HOME,
        'plugins',
        'org.eclipse.equinox.launcher_*.jar' ) ) )

  _logger.debug( 'Found launchers: {0}'.format( launcher_jars ) )

  if not launcher_jars:
    return None

  return launcher_jars[ 0 ]


def _LauncherConfiguration():
  if utils.OnMac():
    config = 'config_mac'
  elif utils.OnWindows():
    config = 'config_win'
  else:
    config = 'config_linux'

  return os.path.abspath( os.path.join( LANGUAGE_SERVER_HOME, config ) )


def _MakeProjectFilesForPath( path ):
  for tail in PROJECT_FILE_TAILS:
    yield os.path.join( path, tail )


def _FindProjectDir( starting_dir ):
  for path in utils.PathsToAllParentFolders( starting_dir ):
    for project_file in _MakeProjectFilesForPath( path ):
      if os.path.isfile( project_file ):
        return path

  return starting_dir


def _WorkspaceDirForProject( project_dir, use_clean_workspace ):
  if use_clean_workspace:
    temp_path = os.path.join( WORKSPACE_ROOT_PATH, 'temp' )

    try:
      os.makedirs( temp_path )
    except OSError:
      pass

    return tempfile.mkdtemp( dir=temp_path )

  project_dir_hash = hashlib.sha256( utils.ToBytes( project_dir ) )
  return os.path.join( WORKSPACE_ROOT_PATH,
                       utils.ToUnicode( project_dir_hash.hexdigest() ) )


class JavaCompleter( language_server_completer.LanguageServerCompleter ):
  def __init__( self, user_options ):
    super( JavaCompleter, self ).__init__( user_options )

    self._server_keep_logfiles = user_options[ 'server_keep_logfiles' ]
    self._use_clean_workspace = user_options[ CLEAN_WORKSPACE_OPTION ]

    # Used to ensure that starting/stopping of the server is synchronized
    self._server_state_mutex = threading.RLock()


    with self._server_state_mutex:
      self._connection = None
      self._server_handle = None
      self._server_stderr = None
      self._workspace_path = None
      self._CleanUp()

      try :
        # When we start the server initially, we don't have the request data, so
        # we use the ycmd working directory. The RestartServer subcommand uses
        # the client's working directory if it is supplied.
        #
        # FIXME: We could start the server in the FileReadyToParse event, though
        # this requires some additional complexity and state management.
        self._StartServer()
      except Exception:
        # We must catch any exception, to ensure that we do not end up with a
        # rogue instance of jdt.ls running.
        _logger.exception( "jdt.ls failed to start." )
        self._StopServer()


  def SupportedFiletypes( self ):
    return [ 'java' ]


  def GetSubcommandsMap( self ):
    return {
      # Handled by base class
      'GoToDeclaration': (
        lambda self, request_data, args: self.GoToDeclaration( request_data )
      ),
      'GoTo': (
        lambda self, request_data, args: self.GoToDeclaration( request_data )
      ),
      'GoToDefinition': (
        lambda self, request_data, args: self.GoToDeclaration( request_data )
      ),
      'GoToReferences': (
        lambda self, request_data, args: self.GoToReferences( request_data )
      ),
      'FixIt': (
        lambda self, request_data, args: self.CodeAction( request_data,
                                                          args )
      ),
      'RefactorRename': (
        lambda self, request_data, args: self.Rename( request_data, args )
      ),

      # Handled by us
      'RestartServer': (
        lambda self, request_data, args: self._RestartServer( request_data )
      ),
      'StopServer': (
        lambda self, request_data, args: self._StopServer()
      ),
      'GetDoc': (
        lambda self, request_data, args: self.GetDoc( request_data )
      ),
      'GetType': (
        lambda self, request_data, args: self.GetType( request_data )
      ),
    }


  def GetConnection( self ):
    return self._connection


  def DebugInfo( self, request_data ):
    items = [
      responses.DebugInfoItem( 'Startup Status', self._server_init_status ),
      responses.DebugInfoItem( 'Java Path', PATH_TO_JAVA ),
      responses.DebugInfoItem( 'Launcher Config.', self._launcher_config ),
    ]

    if self._project_dir:
      items.append( responses.DebugInfoItem( 'Project Directory',
                                             self._project_dir ) )

    if self._workspace_path:
      items.append( responses.DebugInfoItem( 'Workspace Path',
                                             self._workspace_path ) )

    return responses.BuildDebugInfoResponse(
      name = "Java",
      servers = [
        responses.DebugInfoServer(
          name = "jdt.ls Java Language Server",
          handle = self._server_handle,
          executable = self._launcher_path,
          logfiles = [
            self._server_stderr,
            ( os.path.join( self._workspace_path, '.metadata', '.log' )
              if self._workspace_path else None )
          ],
          extras = items
        )
      ] )


  def Shutdown( self ):
    self._StopServer()


  def ServerIsHealthy( self ):
    return self._ServerIsRunning()


  def ServerIsReady( self ):
    return ( self.ServerIsHealthy() and
             self._received_ready_message.is_set() and
             super( JavaCompleter, self ).ServerIsReady() )


  def _GetProjectDirectory( self ):
    return self._project_dir


  def _ServerIsRunning( self ):
    return utils.ProcessIsRunning( self._server_handle )


  def _RestartServer( self, request_data ):
    with self._server_state_mutex:
      self._StopServer()
      self._StartServer( request_data.get( 'working_dir' ) )


  def _CleanUp( self ):
    if not self._server_keep_logfiles:
      if self._server_stderr:
        utils.RemoveIfExists( self._server_stderr )
        self._server_stderr = None

    if self._workspace_path and self._use_clean_workspace:
      try:
        shutil.rmtree( self._workspace_path )
      except OSError:
        _logger.exception( 'Failed to clean up workspace dir {0}'.format(
          self._workspace_path ) )

    self._launcher_path = _PathToLauncherJar()
    self._launcher_config = _LauncherConfiguration()
    self._workspace_path = None
    self._project_dir = None
    self._received_ready_message = threading.Event()
    self._server_init_status = 'Not started'

    self._server_handle = None
    self._connection = None

    self.ServerReset()


  def _StartServer( self, working_dir=None ):
    with self._server_state_mutex:
      _logger.info( 'Starting jdt.ls Language Server...' )

      self._project_dir = _FindProjectDir(
        working_dir if working_dir else utils.GetCurrentDirectory() )
      self._workspace_path = _WorkspaceDirForProject(
        self._project_dir,
        self._use_clean_workspace )

      command = [
        PATH_TO_JAVA,
        '-Dfile.encoding=UTF-8',
        '-Declipse.application=org.eclipse.jdt.ls.core.id1',
        '-Dosgi.bundles.defaultStartLevel=4',
        '-Declipse.product=org.eclipse.jdt.ls.core.product',
        '-Dlog.level=ALL',
        '-jar', self._launcher_path,
        '-configuration', self._launcher_config,
        '-data', self._workspace_path,
      ]

      _logger.debug( 'Starting java-server with the following command: '
                     '{0}'.format( ' '.join( command ) ) )

      LOGFILE_FORMAT = 'jdt.ls_{pid}_{std}_'

      self._server_stderr = utils.CreateLogfile(
          LOGFILE_FORMAT.format( pid = os.getpid(), std = 'stderr' ) )

      with utils.OpenForStdHandle( self._server_stderr ) as stderr:
        self._server_handle = utils.SafePopen( command,
                                               stdin = PIPE,
                                               stdout = PIPE,
                                               stderr = stderr )

      if not self._ServerIsRunning():
        _logger.error( 'jdt.ls Language Server failed to start' )
        return

      _logger.info( 'jdt.ls Language Server started' )

      self._connection = (
        language_server_completer.StandardIOLanguageServerConnection(
          self._server_handle.stdin,
          self._server_handle.stdout,
          self.GetDefaultNotificationHandler() )
      )

      self._connection.start()

      try:
        self._connection.AwaitServerConnection()
      except language_server_completer.LanguageServerConnectionTimeout:
        _logger.error( 'jdt.ls failed to start, or did not connect '
                       'successfully' )
        self._StopServer()
        return

    self.SendInitialise()


  def _StopServer( self ):
    with self._server_state_mutex:
      # We don't use utils.CloseStandardStreams, because the stdin/out is
      # connected to our server connector. Just close stderr.
      if self._server_handle and self._server_handle.stderr:
        self._server_handle.stderr.close()

      # Tell the connection to expect the server to disconnect
      if self._connection:
        self._connection.stop()

      # Tell the server to exit using the shutdown request.
      self._StopServerCleanly()

      # If the server is still running, e.g. due to errors, kill it
      self._StopServerForcefully()

      # Tidy up our internal state
      self._CleanUp()


  def _StopServerCleanly( self ):
    # Try and shutdown cleanly
    if self._ServerIsRunning():
      _logger.info( 'Stopping java server with PID {0}'.format(
                        self._server_handle.pid ) )

      self.ShutdownServer()

      try:
        utils.WaitUntilProcessIsTerminated( self._server_handle,
                                            timeout = 5 )

        if self._connection:
          self._connection.join()

        _logger.info( 'jdt.ls Language server stopped' )
      except Exception:
        _logger.exception( 'Error while stopping jdt.ls server' )


  def _StopServerForcefully( self ):
    if self._ServerIsRunning():
      _logger.info( 'Killing jdt.ls server with PID {0}'.format(
                        self._server_handle.pid ) )

      self._server_handle.terminate()

      try:
        utils.WaitUntilProcessIsTerminated( self._server_handle,
                                            timeout = 5 )

        if self._connection:
          self._connection.join()

        _logger.info( 'jdt.ls Language server killed' )
      except Exception:
        _logger.exception( 'Error while killing jdt.ls server' )


  def _HandleNotificationInPollThread( self, notification ):
    if notification[ 'method' ] == 'language/status':
      message_type = notification[ 'params' ][ 'type' ]

      if message_type == 'Started':
        _logger.info( 'jdt.ls initialized successfully.' )
        self._received_ready_message.set()

      self._server_init_status = notification[ 'params' ][ 'message' ]

    super( JavaCompleter, self )._HandleNotificationInPollThread( notification )


  def _ConvertNotificationToMessage( self, request_data, notification ):
    if notification[ 'method' ] == 'language/status':
      message = notification[ 'params' ][ 'message' ]
      return responses.BuildDisplayMessageResponse(
        'Initializing Java completer: {0}'.format( message ) )

    return super( JavaCompleter, self )._ConvertNotificationToMessage(
      request_data,
      notification )


  def GetType( self, request_data ):
    hover_response = self.GetHoverResponse( request_data )

    if isinstance( hover_response, list ):
      if not len( hover_response ):
        raise RuntimeError( 'No information' )

      try:
        get_type_java = hover_response[ 0 ][ 'value' ]
      except( TypeError ):
        raise RuntimeError( 'No information' )
    else:
      get_type_java = hover_response

    return responses.BuildDisplayMessageResponse( get_type_java )


  def GetDoc( self, request_data ):
    hover_response = self.GetHoverResponse( request_data )

    if isinstance( hover_response, list ):
      if not len( hover_response ):
        raise RuntimeError( 'No information' )

      get_doc_java = ''
      for docstring in hover_response:
        if not isinstance( docstring, dict ):
          get_doc_java += docstring + '\n'
    else:
      get_doc_java = hover_response

    get_doc_java = get_doc_java.rstrip()

    if not get_doc_java:
      raise ValueError( NO_DOCUMENTATION_MESSAGE )

    return responses.BuildDisplayMessageResponse( get_doc_java.rstrip() )


  def HandleServerCommand( self, request_data, command ):
    if command[ 'command' ] == "java.apply.workspaceEdit":
      return language_server_completer.WorkspaceEditToFixIt(
        request_data,
        command[ 'arguments' ][ 0 ],
        text = command[ 'title' ] )

    return None
