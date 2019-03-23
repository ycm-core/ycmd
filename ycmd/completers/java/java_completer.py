# Copyright (C) 2017-2018 ycmd contributors
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
import os
import shutil
import tempfile
import threading
from subprocess import PIPE

from ycmd import responses, utils
from ycmd.completers.language_server import language_server_completer
from ycmd.completers.language_server import language_server_protocol as lsp
from ycmd.utils import LOGGER

NO_DOCUMENTATION_MESSAGE = 'No documentation available for current context'

LANGUAGE_SERVER_HOME = os.path.abspath( os.path.join(
  os.path.dirname( __file__ ),
  '..',
  '..',
  '..',
  'third_party',
  'eclipse.jdt.ls',
  'target',
  'repository' ) )

PATH_TO_JAVA = utils.PathToFirstExistingExecutable( [ 'java' ] )

PROJECT_FILE_TAILS = [
  '.project',
  'pom.xml',
  'build.gradle'
]

WORKSPACE_ROOT_PATH = os.path.abspath( os.path.join(
  os.path.dirname( __file__ ),
  '..',
  '..',
  '..',
  'third_party',
  'eclipse.jdt.ls',
  'workspace' ) )

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
#    directory)
#  - It breaks our tests which expect the logs to be deleted
#  - It can lead to multiple jdt.ls instances using the same workspace (BAD)
#  - It breaks our tests which do exactly that
#
# So:
#  - By _default_ we use a clean workspace (see default_settings.json) on each
#    ycmd instance
#  - An option is available to re-use workspaces
CLEAN_WORKSPACE_OPTION = 'java_jdtls_use_clean_workspace'


def ShouldEnableJavaCompleter():
  LOGGER.info( 'Looking for jdt.ls' )
  if not PATH_TO_JAVA:
    LOGGER.warning( "Not enabling java completion: Couldn't find java" )
    return False

  if not os.path.exists( LANGUAGE_SERVER_HOME ):
    LOGGER.warning( 'Not using java completion: jdt.ls is not installed' )
    return False

  if not _PathToLauncherJar():
    LOGGER.warning( 'Not using java completion: jdt.ls is not built' )
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

  LOGGER.debug( 'Found launchers: %s', launcher_jars )

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
    yield os.path.join( path, tail ), tail


def _FindProjectDir( starting_dir ):
  project_path = starting_dir
  project_type = None

  for folder in utils.PathsToAllParentFolders( starting_dir ):
    for project_file, tail in _MakeProjectFilesForPath( folder ):
      if os.path.isfile( project_file ):
        project_path = folder
        project_type = tail
        break
    if project_type:
      break

  if project_type:
    # We've found a project marker file (like build.gradle). Search parent
    # directories for that same project type file and find the topmost one as
    # the project root.
    LOGGER.debug( 'Found %s style project in %s. Searching for '
                  'project root:', project_type, project_path )

    for folder in utils.PathsToAllParentFolders( os.path.join( project_path,
                                                               '..' ) ):
      if os.path.isfile( os.path.join( folder, project_type ) ):
        LOGGER.debug( '  %s is a parent project dir', folder )
        project_path = folder
      else:
        break
    LOGGER.debug( '  Project root is %s', project_path )

  return project_path


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

    self._connection = None
    self._server_handle = None
    self._server_stderr = None
    self._workspace_path = None
    self._CleanUp()


  def SupportedFiletypes( self ):
    return [ 'java' ]


  def GetCustomSubcommands( self ):
    return {
      'FixIt': (
        lambda self, request_data, args: self.GetCodeActions( request_data,
                                                              args )
      ),
      'GetDoc': (
        lambda self, request_data, args: self.GetDoc( request_data )
      ),
      'GetType': (
        lambda self, request_data, args: self.GetType( request_data )
      ),
      'OrganizeImports': (
        lambda self, request_data, args: self.OrganizeImports( request_data )
      ),
      'OpenProject': (
        lambda self, request_data, args: self._OpenProject( request_data, args )
      ),
      'RestartServer': (
        lambda self, request_data, args: self._RestartServer( request_data )
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

    if self._workspace_path:
      items.append( responses.DebugInfoItem( 'Workspace Path',
                                             self._workspace_path ) )

    items.extend( self.CommonDebugItems() )

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


  def ServerIsHealthy( self ):
    return self._ServerIsRunning()


  def ServerIsReady( self ):
    return ( self.ServerIsHealthy() and
             self._received_ready_message.is_set() and
             super( JavaCompleter, self ).ServerIsReady() )


  def _GetProjectDirectory( self, *args, **kwargs ):
    return self._java_project_dir


  def _ServerIsRunning( self ):
    return utils.ProcessIsRunning( self._server_handle )


  def _RestartServer( self, request_data ):
    with self._server_state_mutex:
      self.Shutdown()
      self._StartAndInitializeServer( request_data )


  def _OpenProject( self, request_data, args ):
    if len( args ) != 1:
      raise ValueError( "Usage: OpenProject <project directory>" )

    project_directory = args[ 0 ]

    # If the dir is not absolute, calculate it relative to the working dir of
    # the client (if supplied).
    if not os.path.isabs( project_directory ):
      if 'working_dir' not in request_data:
        raise ValueError( "Project directory must be absolute" )

      project_directory = os.path.normpath( os.path.join(
        request_data[ 'working_dir' ],
        project_directory ) )

    with self._server_state_mutex:
      self.Shutdown()
      self._StartAndInitializeServer( request_data,
                                      project_directory = project_directory )


  def _CleanUp( self ):
    if not self._server_keep_logfiles and self._server_stderr:
      utils.RemoveIfExists( self._server_stderr )
      self._server_stderr = None

    if self._workspace_path and self._use_clean_workspace:
      try:
        shutil.rmtree( self._workspace_path )
      except OSError:
        LOGGER.exception( 'Failed to clean up workspace dir %s',
                          self._workspace_path )

    self._launcher_path = _PathToLauncherJar()
    self._launcher_config = _LauncherConfiguration()
    self._workspace_path = None
    self._java_project_dir = None
    self._received_ready_message = threading.Event()
    self._server_init_status = 'Not started'

    self._server_handle = None
    self._connection = None
    self._started_message_sent = False

    self.ServerReset()


  def Language( self ):
    return 'java'


  def StartServer( self, request_data, project_directory = None ):
    with self._server_state_mutex:
      LOGGER.info( 'Starting jdt.ls Language Server...' )

      if project_directory:
        self._java_project_dir = project_directory
      else:
        self._java_project_dir = _FindProjectDir(
          os.path.dirname( request_data[ 'filepath' ] ) )

      self._workspace_path = _WorkspaceDirForProject(
        self._java_project_dir,
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

      LOGGER.debug( 'Starting java-server with the following command: %s',
                    command )

      self._server_stderr = utils.CreateLogfile( 'jdt.ls_stderr_' )
      with utils.OpenForStdHandle( self._server_stderr ) as stderr:
        self._server_handle = utils.SafePopen( command,
                                               stdin = PIPE,
                                               stdout = PIPE,
                                               stderr = stderr )

      self._connection = (
        language_server_completer.StandardIOLanguageServerConnection(
          self._server_handle.stdin,
          self._server_handle.stdout,
          self.GetDefaultNotificationHandler() )
      )

      self._connection.Start()

      try:
        self._connection.AwaitServerConnection()
      except language_server_completer.LanguageServerConnectionTimeout:
        LOGGER.error( 'jdt.ls failed to start, or did not connect '
                      'successfully' )
        self.Shutdown()
        return False

    LOGGER.info( 'jdt.ls Language Server started' )

    return True


  def Shutdown( self ):
    with self._server_state_mutex:
      LOGGER.info( 'Shutting down jdt.ls...' )

      # Tell the connection to expect the server to disconnect
      if self._connection:
        self._connection.Stop()

      if not self._ServerIsRunning():
        LOGGER.info( 'jdt.ls Language server not running' )
        self._CleanUp()
        return

      LOGGER.info( 'Stopping java server with PID %s',
                   self._server_handle.pid )

      try:
        self.ShutdownServer()

        # By this point, the server should have shut down and terminated. To
        # ensure that isn't blocked, we close all of our connections and wait
        # for the process to exit.
        #
        # If, after a small delay, the server has not shut down we do NOT kill
        # it; we expect that it will shut itself down eventually. This is
        # predominantly due to strange process behaviour on Windows.
        if self._connection:
          self._connection.Close()

        utils.WaitUntilProcessIsTerminated( self._server_handle,
                                            timeout = 15 )

        LOGGER.info( 'jdt.ls Language server stopped' )
      except Exception:
        LOGGER.exception( 'Error while stopping jdt.ls server' )
        # We leave the process running. Hopefully it will eventually die of its
        # own accord.

      # Tidy up our internal state, even if the completer server didn't close
      # down cleanly.
      self._CleanUp()


  def GetCodepointForCompletionRequest( self, request_data ):
    """Returns the 1-based codepoint offset on the current line at which to make
    the completion request"""
    # When the user forces semantic completion, we pass the actual cursor
    # position to jdt.ls.

    # At the top level (i.e. without a semantic trigger), there are always way
    # too many possible candidates for jdt.ls to return anything useful. This is
    # because we don't send the currently typed characters to jdt.ls. The
    # general idea is that we apply our own post-filter and sort. However, in
    # practice we never get a full set of possibilities at the top-level. So, as
    # a compromise, we allow the user to force us to send the "query" to the
    # semantic engine, and thus get good completion results at the top level,
    # even if this means the "filtering and sorting" is not 100% ycmd flavor.
    if request_data[ 'force_semantic' ]:
      return request_data[ 'column_codepoint' ]
    return super( JavaCompleter, self ).GetCodepointForCompletionRequest(
      request_data )


  def HandleNotificationInPollThread( self, notification ):
    if notification[ 'method' ] == 'language/status':
      message_type = notification[ 'params' ][ 'type' ]

      if message_type == 'Started':
        LOGGER.info( 'jdt.ls initialized successfully' )
        self._server_init_status = notification[ 'params' ][ 'message' ]
        self._received_ready_message.set()
      elif not self._received_ready_message.is_set():
        self._server_init_status = notification[ 'params' ][ 'message' ]

    super( JavaCompleter, self ).HandleNotificationInPollThread( notification )


  def ConvertNotificationToMessage( self, request_data, notification ):
    if notification[ 'method' ] == 'language/status':
      message = notification[ 'params' ][ 'message' ]
      if notification[ 'params' ][ 'type' ] == 'Started':
        self._started_message_sent = True
        return responses.BuildDisplayMessageResponse(
          'Initializing Java completer: {}'.format( message ) )

      if not self._started_message_sent:
        return responses.BuildDisplayMessageResponse(
          'Initializing Java completer: {}'.format( message ) )

    return super( JavaCompleter, self ).ConvertNotificationToMessage(
      request_data,
      notification )


  def GetType( self, request_data ):
    hover_response = self.GetHoverResponse( request_data )

    # The LSP defines the hover response as either:
    # - a string
    # - a list of strings
    # - an object with keys language, value
    # - a list of objects with keys language, value
    # - an object with keys kind, value

    # That's right. All of the above.

    # However it would appear that jdt.ls only ever returns useful data when it
    # is a list of objects-with-keys-language-value, and the type information is
    # always in the first such list element, so we only handle that case and
    # throw any other time.

    # Strictly we seem to receive:
    # - ""
    #   when there really is no documentation or type info available
    # - {language:java, value:<type info>}
    #   when there only the type information is available
    # - [{language:java, value:<type info>},
    #    'doc line 1',
    #    'doc line 2',
    #    ...]
    #   when there is type and documentation information available.

    if not hover_response:
      raise RuntimeError( 'Unknown type' )

    if isinstance( hover_response, list ):
      hover_response = hover_response[ 0 ]

    if ( not isinstance( hover_response, dict ) or
         hover_response.get( 'language' ) != 'java' or
         'value' not in hover_response ):
      raise RuntimeError( 'Unknown type' )

    return responses.BuildDisplayMessageResponse( hover_response[ 'value' ] )


  def GetDoc( self, request_data ):
    hover_response = self.GetHoverResponse( request_data )

    # The LSP defines the hover response as either:
    # - a string
    # - a list of strings
    # - an object with keys language, value
    # - a list of objects with keys language, value
    # - an object with keys kind, value

    # That's right. All of the above.

    # However it would appear that jdt.ls only ever returns useful data when it
    # is a list of objects-with-keys-language-value, so we only handle that case
    # and throw any other time.

    # Strictly we seem to receive:
    # - ""
    #   when there really is no documentation or type info available
    # - {language:java, value:<type info>}
    #   when there only the type information is available
    # - [{language:java, value:<type info>},
    #    'doc line 1',
    #    'doc line 2',
    #    ...]
    #   when there is type and documentation information available.

    documentation = ''
    if isinstance( hover_response, list ):
      for item in hover_response:
        if isinstance( item, str ):
          documentation += item + '\n'

    documentation = documentation.rstrip()

    if not documentation:
      raise RuntimeError( NO_DOCUMENTATION_MESSAGE )

    return responses.BuildDetailedInfoResponse( documentation )


  def OrganizeImports( self, request_data ):
    workspace_edit = self.GetCommandResponse(
      request_data,
      'java.edit.organizeImports',
      [ lsp.FilePathToUri( request_data[ 'filepath' ] ) ] )

    fixit = language_server_completer.WorkspaceEditToFixIt( request_data,
                                                            workspace_edit )
    return responses.BuildFixItResponse( [ fixit ] )


  def HandleServerCommand( self, request_data, command ):
    if command[ 'command' ] == "java.apply.workspaceEdit":
      return language_server_completer.WorkspaceEditToFixIt(
        request_data,
        command[ 'arguments' ][ 0 ],
        text = command[ 'title' ] )

    return None
