# Copyright (C) 2017-2020 ycmd contributors
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

import glob
import hashlib
import json
import os
import shutil
import tempfile
import threading

from ycmd import responses, utils
from ycmd.completers.language_server import language_server_protocol as lsp
from ycmd.completers.language_server import language_server_completer
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

PATH_TO_JAVA = None

PROJECT_FILE_TAILS = [
  '.project',
  'pom.xml',
  'build.gradle'
]

DEFAULT_WORKSPACE_ROOT_PATH = os.path.abspath( os.path.join(
  os.path.dirname( __file__ ),
  '..',
  '..',
  '..',
  'third_party',
  'eclipse.jdt.ls',
  'workspace' ) )

DEFAULT_EXTENSION_PATH = os.path.abspath( os.path.join(
  os.path.dirname( __file__ ),
  '..',
  '..',
  '..',
  'third_party',
  'eclipse.jdt.ls',
  'extensions' ) )


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

# jdt.ls workspace areas are mutable and written by the server. Putting them
# underneath the ycmd installation, even in their own directory makes it
# impossible to use a shared installation of ycmd. In order to allow that, we
# expose another (hidden) option which moves the workspace root dirdectory
# somewhere else, such as the user's home directory.
WORKSPACE_ROOT_PATH_OPTION = 'java_jdtls_workspace_root_path'

# jdt.ls supports extensions that are loaded on startup bu passing a list of jar
# files to load. The following list option is a list of paths to scan for
# directories containing extensions in the same format as expected by the
# vscode-java extension.
EXTENSION_PATH_OPTION = 'java_jdtls_extension_path'


def ShouldEnableJavaCompleter( user_options ):
  LOGGER.info( 'Looking for jdt.ls' )

  global PATH_TO_JAVA
  PATH_TO_JAVA = utils.FindExecutableWithFallback(
    user_options[ 'java_binary_path' ],
    utils.FindExecutable( 'java' ) )

  if not PATH_TO_JAVA:
    LOGGER.warning( "Not enabling java completion: Couldn't find java 11" )
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


def _CollectExtensionBundles( extension_path ):
  extension_bundles = []

  for extension_dir in extension_path:
    if not os.path.isdir( extension_dir ):
      LOGGER.info( f'extension directory does not exist: { extension_dir }' )
      continue

    for path in os.listdir( extension_dir ):
      path = os.path.join( extension_dir, path )
      manifest_file = os.path.join( path, 'package.json' )

      if not os.path.isdir( path ) or not os.path.isfile( manifest_file ):
        LOGGER.debug( f'{ path } is not an extension directory' )
        continue

      manifest_json = utils.ReadFile( manifest_file )
      try:
        manifest = json.loads( manifest_json )
      except ValueError:
        LOGGER.exception( f'Could not load bundle { manifest_file }' )
        continue

      if ( 'contributes' not in manifest or
           'javaExtensions' not in manifest[ 'contributes' ] or
           not isinstance( manifest[ 'contributes' ][ 'javaExtensions' ],
                           list ) ):
        LOGGER.info( f'Bundle { manifest_file } is not a java extension' )
        continue

      LOGGER.info( f'Found bundle: { manifest_file }' )

      extension_bundles.extend( [
        os.path.join( path, p )
        for p in manifest[ 'contributes' ][ 'javaExtensions' ]
      ] )

  return extension_bundles


def _LauncherConfiguration( workspace_root, wipe_config ):
  if utils.OnMac():
    config = 'config_mac'
  elif utils.OnWindows():
    config = 'config_win'
  else:
    config = 'config_linux'

  CONFIG_FILENAME = 'config.ini'

  # The 'config' directory is a bit of a misnomer. It is really a working area
  # for eclipse to store things that eclipse feels entitled to store,
  # that are not specific to a particular project or workspace.
  # Importantly, the server writes to this directory, which means that in order
  # to allow installations of ycmd on readonly filesystems (or shared
  # installations of ycmd), we have to make it somehow unique at least per user,
  # and possibly per ycmd instance.
  #
  # To allow this, we let the client specify the workspace root and we always
  # put the (mutable) config directory under the workspace root path. The config
  # directory is simply a writable directory with the config.ini in it.
  #
  # Note that we must re-copy the config when it changes. Otherwise, eclipse
  # just won't start. As the file is generated part of the jdt.ls build, we just
  # always copy and overwrite it.
  working_config = os.path.abspath( os.path.join( workspace_root,
                                                  config ) )
  working_config_file = os.path.join( working_config, CONFIG_FILENAME )
  base_config_file = os.path.abspath( os.path.join( LANGUAGE_SERVER_HOME,
                                                    config,
                                                    CONFIG_FILENAME ) )

  if os.path.isdir( working_config ):
    if wipe_config:
      shutil.rmtree( working_config )
      os.makedirs( working_config )
    elif os.path.isfile( working_config_file ):
      os.remove( working_config_file )
  else:
    os.makedirs( working_config )

  shutil.copy2( base_config_file, working_config_file )
  return working_config


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


def _WorkspaceDirForProject( workspace_root_path,
                             project_dir,
                             use_clean_workspace ):
  if use_clean_workspace:
    temp_path = os.path.join( workspace_root_path, 'temp' )

    try:
      os.makedirs( temp_path )
    except OSError:
      pass

    return tempfile.mkdtemp( dir=temp_path )

  project_dir_hash = hashlib.sha256( utils.ToBytes( project_dir ) )
  return os.path.join( workspace_root_path,
                       utils.ToUnicode( project_dir_hash.hexdigest() ) )


class JavaCompleter( language_server_completer.LanguageServerCompleter ):
  def __init__( self, user_options ):
    self._workspace_path = None
    super().__init__( user_options )

    self._server_keep_logfiles = user_options[ 'server_keep_logfiles' ]
    self._use_clean_workspace = user_options[ CLEAN_WORKSPACE_OPTION ]
    self._workspace_root_path = user_options[ WORKSPACE_ROOT_PATH_OPTION ]
    self._extension_path = user_options[ EXTENSION_PATH_OPTION ]

    if not self._workspace_root_path:
      self._workspace_root_path = DEFAULT_WORKSPACE_ROOT_PATH

    if not isinstance( self._extension_path, list ):
      raise ValueError( f'{ EXTENSION_PATH_OPTION } option must be a list' )

    if not self._extension_path:
      self._extension_path = [ DEFAULT_EXTENSION_PATH ]
    else:
      self._extension_path.append( DEFAULT_EXTENSION_PATH )

    self._bundles = ( _CollectExtensionBundles( self._extension_path )
                      if self._extension_path else [] )

    self._connection = None
    self._server_handle = None
    self._stderr_file = None
    self._Reset()
    self._command = []


  def DefaultSettings( self, request_data ):
    return {
      'bundles': self._bundles
    }


  def SupportedFiletypes( self ):
    return [ 'java' ]


  def GetSignatureTriggerCharacters( self, server_trigger_characters ):
    return server_trigger_characters + [ ',' ]


  def GetCustomSubcommands( self ):
    return {
      'OrganizeImports': (
        lambda self, request_data, args: self.OrganizeImports( request_data )
      ),
      'OpenProject': (
        lambda self, request_data, args: self._OpenProject( request_data, args )
      ),
      'WipeWorkspace': (
        lambda self, request_data, args: self._WipeWorkspace( request_data,
                                                              args )
      ),
    }


  def AdditionalLogFiles( self ):
    if self._workspace_path:
      return [ os.path.join( self._workspace_path, '.metadata', '.log' ) ]
    return []


  def ExtraDebugItems( self, request_data ):
    items = [
      responses.DebugInfoItem( 'Startup Status', self._server_init_status ),
      responses.DebugInfoItem( 'Java Path', PATH_TO_JAVA ),
    ]

    if self._launcher_config:
      items.append( responses.DebugInfoItem( 'Launcher Config.',
                                             self._launcher_config ) )

    if self._workspace_path:
      items.append( responses.DebugInfoItem( 'Workspace Path',
                                             self._workspace_path ) )

    items.append( responses.DebugInfoItem( 'Extension Path',
                                           self._extension_path ) )

    return items


  def ServerIsReady( self ):
    return ( self.ServerIsHealthy() and
             self._received_ready_message.is_set() and
             super().ServerIsReady() )


  def GetProjectDirectory( self, *args, **kwargs ):
    return self._java_project_dir


  def _WipeWorkspace( self, request_data, args ):
    with_config = False
    if len( args ) > 0 and '--with-config' in args:
      with_config = True

    self._RestartServer( request_data,
                         wipe_workspace = True,
                         wipe_config = with_config )


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

    self._RestartServer( request_data, project_directory = project_directory )


  def _Reset( self ):
    if self._workspace_path and self._use_clean_workspace:
      try:
        shutil.rmtree( self._workspace_path )
      except OSError:
        LOGGER.exception( 'Failed to clean up workspace dir %s',
                          self._workspace_path )

    self._launcher_path = _PathToLauncherJar()
    self._launcher_config = None
    self._workspace_path = None
    self._java_project_dir = None
    self._received_ready_message = threading.Event()
    self._server_init_status = 'Not started'

    self._started_message_sent = False

    super()._Reset()


  def _GetJvmArgs( self, request_data ):
    return self._settings.get( 'server', {} ).get( 'jvm_args', [] )


  def StartServer( self,
                   request_data,
                   project_directory = None,
                   wipe_workspace = False,
                   wipe_config = False ):
    try:
      with self._server_info_mutex:
        LOGGER.info( 'Starting jdt.ls Language Server...' )

        if project_directory:
          self._java_project_dir = project_directory
        elif 'project_directory' in self._settings:
          self._java_project_dir = utils.AbsolutePath(
            self._settings[ 'project_directory' ],
            self._extra_conf_dir )
        else:
          self._java_project_dir = _FindProjectDir(
            os.path.dirname( request_data[ 'filepath' ] ) )

        self._workspace_path = _WorkspaceDirForProject(
          self._workspace_root_path,
          self._java_project_dir,
          self._use_clean_workspace )

        if not self._use_clean_workspace and wipe_workspace:
          if os.path.isdir( self._workspace_path ):
            LOGGER.info( f'Wiping out workspace { self._workspace_path }' )
            shutil.rmtree( self._workspace_path )

        self._launcher_config = _LauncherConfiguration(
            self._workspace_root_path,
            wipe_config )

        self._command = [ PATH_TO_JAVA ] + self._GetJvmArgs( request_data ) + [
          '-Dfile.encoding=UTF-8',
          '-Declipse.application=org.eclipse.jdt.ls.core.id1',
          '-Dosgi.bundles.defaultStartLevel=4',
          '-Declipse.product=org.eclipse.jdt.ls.core.product',
          '-Dlog.level=ALL',
          '-jar', self._launcher_path,
          '-configuration', self._launcher_config,
          '-data', self._workspace_path,
        ]

        return super( JavaCompleter, self )._StartServerNoLock( request_data )
    except language_server_completer.LanguageServerConnectionTimeout:
      LOGGER.error( '%s failed to start, or did not connect successfully',
                    self.GetServerName() )
      self.Shutdown()
      return False


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
    return super().GetCodepointForCompletionRequest( request_data )


  def HandleNotificationInPollThread( self, notification ):
    if notification[ 'method' ] == 'language/status':
      message_type = notification[ 'params' ][ 'type' ]

      if message_type == 'Started':
        LOGGER.info( 'jdt.ls initialized successfully' )
        self._server_init_status = notification[ 'params' ][ 'message' ]
        self._received_ready_message.set()
      elif not self._received_ready_message.is_set():
        self._server_init_status = notification[ 'params' ][ 'message' ]

    super().HandleNotificationInPollThread( notification )


  def ConvertNotificationToMessage( self, request_data, notification ):
    if notification[ 'method' ] == 'language/status':
      message = notification[ 'params' ][ 'message' ]
      if notification[ 'params' ][ 'type' ] == 'Started':
        self._started_message_sent = True
        return responses.BuildDisplayMessageResponse(
          f'Initializing Java completer: { message }' )

      if not self._started_message_sent:
        return responses.BuildDisplayMessageResponse(
          f'Initializing Java completer: { message }' )

    return super().ConvertNotificationToMessage( request_data, notification )


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
    fixit = {
      'resolve': True,
      'command': {
        'title': 'Organize Imports',
        'command': 'java.edit.organizeImports',
        'arguments': [ lsp.FilePathToUri( request_data[ 'filepath' ] ) ]
      }
    }
    return self._ResolveFixit( request_data, fixit )


  def CodeActionCommandToFixIt( self, request_data, command ):
    # JDT wants us to special case `java.apply.workspaceEdit`
    # https://github.com/eclipse/eclipse.jdt.ls/issues/376
    if command[ 'command' ][ 'command' ] == 'java.apply.workspaceEdit':
      command[ 'edit' ] = command.pop( 'command' )[ 'arguments' ][ 0 ]
      return super().CodeActionLiteralToFixIt( request_data, command )
    return super().CodeActionCommandToFixIt( request_data, command )


  def GetServerName( self ):
    return 'jdt.ls'


  def GetCommandLine( self ):
    return self._command
