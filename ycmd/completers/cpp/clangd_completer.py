# Copyright (C) 2018-2020 ycmd contributors
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

import logging
import os
import subprocess

from ycmd import extra_conf_store, responses
from ycmd.completers.cpp.flags import ( AddMacIncludePaths,
                                        RemoveUnusedFlags,
                                        ShouldAllowWinStyleFlags )
from ycmd.completers.language_server import language_server_completer
from ycmd.completers.language_server import language_server_protocol as lsp
from ycmd.utils import ( CLANG_RESOURCE_DIR,
                         GetExecutable,
                         ExpandVariablesInPath,
                         FindExecutable,
                         LOGGER,
                         OnMac,
                         PathsToAllParentFolders,
                         re )

MIN_SUPPORTED_VERSION = ( 11, 0, 0 )
INCLUDE_REGEX = re.compile(
  '(\\s*#\\s*(?:include|import)\\s*)(?:"[^"]*|<[^>]*)' )
NOT_CACHED = 'NOT_CACHED'
CLANGD_COMMAND = NOT_CACHED
PRE_BUILT_CLANGD_DIR = os.path.abspath( os.path.join(
  os.path.dirname( __file__ ),
  '..',
  '..',
  '..',
  'third_party',
  'clangd',
  'output',
  'bin' ) )
PRE_BUILT_CLANDG_PATH = os.path.join( PRE_BUILT_CLANGD_DIR, 'clangd' )


def ParseClangdVersion( version_str ):
  version_regexp = r'(\d+)\.(\d+)\.(\d+)'
  m = re.search( version_regexp, version_str )
  try:
    version = tuple( int( x ) for x in m.groups() )
  except AttributeError:
    # Custom builds might have different versioning info.
    version = None
  return version


def GetVersion( clangd_path ):
  args = [ clangd_path, '--version' ]
  stdout, _ = subprocess.Popen( args, stdout=subprocess.PIPE ).communicate()
  return ParseClangdVersion( stdout.decode() )


def CheckClangdVersion( clangd_path ):
  version = GetVersion( clangd_path )
  if version and version < MIN_SUPPORTED_VERSION:
    return False
  return True


def GetThirdPartyClangd():
  pre_built_clangd = GetExecutable( PRE_BUILT_CLANDG_PATH )
  if not pre_built_clangd:
    LOGGER.info( 'No Clangd executable found in %s', PRE_BUILT_CLANGD_DIR )
    return None
  if not CheckClangdVersion( pre_built_clangd ):
    LOGGER.error( 'Clangd executable at %s is out-of-date', pre_built_clangd )
    return None
  LOGGER.info( 'Clangd executable found at %s and up to date',
               PRE_BUILT_CLANGD_DIR )
  return pre_built_clangd


def GetClangdExecutableAndResourceDir( user_options ):
  """Return the Clangd binary from the path specified in the
  'clangd_binary_path' option. Let the binary find its resource directory in
  that case. If no binary is found or if it's out-of-date, return nothing. If
  'clangd_binary_path' is empty, return the third-party Clangd and its resource
  directory if the user downloaded it and if it's up to date. Otherwise, return
  nothing."""
  clangd = user_options[ 'clangd_binary_path' ]
  resource_dir = None

  if clangd:
    clangd = FindExecutable( ExpandVariablesInPath( clangd ) )

    if not clangd:
      LOGGER.error( 'No Clangd executable found at %s',
                    user_options[ 'clangd_binary_path' ] )
      return None, None

    if not CheckClangdVersion( clangd ):
      LOGGER.error( 'Clangd at %s is out-of-date', clangd )
      return None, None

  # Try looking for the pre-built binary.
  else:
    third_party_clangd = GetThirdPartyClangd()
    if not third_party_clangd:
      return None, None
    clangd = third_party_clangd
    resource_dir = CLANG_RESOURCE_DIR

  LOGGER.info( 'Using Clangd from %s', clangd )
  return clangd, resource_dir


def GetClangdCommand( user_options ):
  global CLANGD_COMMAND
  # None stands for we tried to fetch command and failed, therefore it is not
  # the default.
  if CLANGD_COMMAND != NOT_CACHED:
    LOGGER.info( 'Returning cached Clangd command: %s', CLANGD_COMMAND )
    return CLANGD_COMMAND
  CLANGD_COMMAND = None

  installed_clangd, resource_dir = GetClangdExecutableAndResourceDir(
      user_options )
  if not installed_clangd:
    return None

  CLANGD_COMMAND = [ installed_clangd ]
  clangd_args = user_options[ 'clangd_args' ]
  put_resource_dir = False
  put_limit_results = False
  put_header_insertion_decorators = False
  put_log = False
  for arg in clangd_args:
    CLANGD_COMMAND.append( arg )
    put_resource_dir = put_resource_dir or arg.startswith( '-resource-dir' )
    put_limit_results = put_limit_results or arg.startswith( '-limit-results' )
    put_header_insertion_decorators = ( put_header_insertion_decorators or
                        arg.startswith( '-header-insertion-decorators' ) )
    put_log = put_log or arg.startswith( '-log' )
  if not put_header_insertion_decorators:
    CLANGD_COMMAND.append( '-header-insertion-decorators=0' )
  if resource_dir and not put_resource_dir:
    CLANGD_COMMAND.append( '-resource-dir=' + resource_dir )
  if user_options[ 'clangd_uses_ycmd_caching' ] and not put_limit_results:
    CLANGD_COMMAND.append( '-limit-results=500' )
  if LOGGER.isEnabledFor( logging.DEBUG ) and not put_log:
    CLANGD_COMMAND.append( '-log=verbose' )

  return CLANGD_COMMAND


def ShouldEnableClangdCompleter( user_options ):
  """Checks whether clangd should be enabled or not.

  - Returns True if an up-to-date binary exists either in `clangd_binary_path`
    or in third party folder and `use_clangd` is not set to `0`.
  """
  # User disabled clangd explicitly.
  if not user_options[ 'use_clangd' ]:
    return False

  clangd_command = GetClangdCommand( user_options )
  if not clangd_command:
    return False
  LOGGER.info( 'Computed Clangd command: %s', clangd_command )
  return True


def PrependCompilerToFlags( flags, enable_windows_style_flags ):
  """Removes everything before the first flag and returns the remaining flags
  prepended with clang-tool."""
  for index, flag in enumerate( flags ):
    if ( flag.startswith( '-' ) or
         ( enable_windows_style_flags and
           flag.startswith( '/' ) and
           not os.path.exists( flag ) ) ):
      flags = flags[ index: ]
      break
  return [ 'clang-tool' ] + flags


def BuildCompilationCommand( flags, filepath ):
  """Returns a compilation command from a list of flags and a file."""
  enable_windows_style_flags = ShouldAllowWinStyleFlags( flags )
  flags = PrependCompilerToFlags( flags, enable_windows_style_flags )
  flags = RemoveUnusedFlags( flags, filepath, enable_windows_style_flags )
  if OnMac():
    flags = AddMacIncludePaths( flags )
  return flags + [ filepath ]


class ClangdCompleter( language_server_completer.LanguageServerCompleter ):
  """A LSP-based completer for C-family languages, powered by Clangd.

  Supported features:
    * Code completion
    * Diagnostics and apply FixIts
    * Go to definition
  """

  def __init__( self, user_options ):
    super().__init__( user_options )

    self._clangd_command = GetClangdCommand( user_options )
    self._use_ycmd_caching = user_options[ 'clangd_uses_ycmd_caching' ]
    self._compilation_commands = {}

    self.RegisterOnFileReadyToParse(
      lambda self, request_data: self._SendFlagsFromExtraConf( request_data )
    )


  def _Reset( self ):
    super()._Reset()
    self._compilation_commands = {}


  def GetCompleterName( self ):
    return 'C-family'


  def GetServerName( self ):
    return 'Clangd'


  def GetCommandLine( self ):
    return self._clangd_command


  def Language( self ):
    return 'cfamily'


  def SupportedFiletypes( self ):
    return ( 'c', 'cpp', 'objc', 'objcpp', 'cuda' )


  def GetType( self, request_data ):
    try:
      hover_value = self.GetHoverResponse( request_data )[ 'value' ]
      # Last "paragraph" contains the signature/declaration - i.e. type info.
      type_info = hover_value.split( '\n\n' )[ -1 ]
      # The first line might contain the info of enclosing scope.
      if type_info.startswith( '// In' ):
        comment, signature = type_info.split( '\n', 1 )
        type_info = signature + '; ' + comment
      # Condense multi-line function declarations into one line.
      type_info = re.sub( r'\s+', ' ', type_info )
      return responses.BuildDisplayMessageResponse( type_info )
    except language_server_completer.NoHoverInfoException:
      raise RuntimeError( 'Unknown type.' )


  def GetDoc( self, request_data ):
    try:
      # Just pull `value` out of the textDocument/hover response
      return responses.BuildDetailedInfoResponse(
          self.GetHoverResponse( request_data )[ 'value' ] )
    except language_server_completer.NoHoverInfoException:
      raise RuntimeError( 'No documentation available.' )


  def GetTriggerCharacters( self, server_trigger_characters ):
    # The trigger characters supplied by clangd are worse than ycmd's own
    # semantic triggers which are more sophisticated (regex-based). So we
    # ignore them.
    return []


  def GetCustomSubcommands( self ):
    return {
      'GetTypeImprecise': (
        lambda self, request_data, args: self.GetType( request_data )
      ),
      # NOTE: these two commands are only kept for backward compatibility with
      # the libclang completer.
      'GoToImprecise': (
        lambda self, request_data, args: self.GoTo( request_data,
                                                    [ 'Definition' ] )
      ),
      'GoToInclude': (
        lambda self, request_data, args: self.GoTo( request_data,
                                                    [ 'Definition' ] )
      ),
      'GetDocImprecise': (
        lambda self, request_data, args: self.GetDoc( request_data )
      ),
      # To handle the commands below we need extensions to LSP. One way to
      # provide those could be to use workspace/executeCommand requset.
      # 'GetParent': (
      #   lambda self, request_data, args: self.GetType( request_data )
      # )
    }


  def ShouldCompleteIncludeStatement( self, request_data ):
    column_codepoint = request_data[ 'column_codepoint' ] - 1
    current_line = request_data[ 'line_value' ]
    return bool( INCLUDE_REGEX.match( current_line[ : column_codepoint ] ) )


  def ShouldUseNowInner( self, request_data ):
    return ( self.ServerIsReady() and
             ( super().ShouldUseNowInner( request_data ) or
               self.ShouldCompleteIncludeStatement( request_data ) ) )


  def ShouldUseNow( self, request_data ):
    """Overridden to use Clangd filtering and sorting when ycmd caching is
    disabled."""
    # Clangd should be able to provide completions in any context.
    # FIXME: Empty queries provide spammy results, fix this in Clangd.
    if self._use_ycmd_caching:
      return super().ShouldUseNow( request_data )
    return ( request_data[ 'query' ] != '' or
             super().ShouldUseNowInner( request_data ) )


  def ComputeCandidates( self, request_data ):
    """Overridden to bypass ycmd cache if disabled."""
    # Caching results means resorting them, and ycmd has fewer signals.
    if self._use_ycmd_caching:
      return super().ComputeCandidates( request_data )
    codepoint = request_data[ 'column_codepoint' ]
    candidates, _ = super().ComputeCandidatesInner( request_data,
                                                    codepoint )
    return candidates


  def _SendFlagsFromExtraConf( self, request_data ):
    """Reads the flags from the extra conf of the given request and sends them
    to Clangd as an entry of a compilation database using the
    'compilationDatabaseChanges' configuration."""
    filepath = request_data[ 'filepath' ]

    with self._server_info_mutex:
      # Replicate the logic from flags.py _GetFlagsFromCompilationDatabase:
      #  - if there's a local extra conf, use it
      #  - otherwise if there's no database, try and use a global extra conf

      module = extra_conf_store.ModuleForSourceFile( filepath )
      if not module:
        # No extra conf and no global extra conf. Just let clangd handle it.
        return

      if ( extra_conf_store.IsGlobalExtraConfModule( module ) and
           CompilationDatabaseExists( filepath ) ):
        # No local extra conf, database exists: use database (i.e. clangd)
        return

      # Use our module (either local extra conf or global extra conf when no
      # database is found)
      settings = self.GetSettings( module, request_data )

      if 'flags' not in settings:
        # No flags returned. Let Clangd find the flags.
        return

      if ( settings.get( 'do_cache', True ) and
           filepath in self._compilation_commands ):
        # Flags for this file have already been sent to Clangd.
        return

      flags = BuildCompilationCommand( settings[ 'flags' ], filepath )

      self.GetConnection().SendNotification( lsp.DidChangeConfiguration( {
        'compilationDatabaseChanges': {
          filepath: {
            'compilationCommand': flags,
            'workingDirectory': settings.get( 'include_paths_relative_to_dir',
                                              self._project_directory )
          }
        }
      } ) )

      self._compilation_commands[ filepath ] = flags


  def ExtraDebugItems( self, request_data ):
    return [
      responses.DebugInfoItem(
        'Compilation Command',
        self._compilation_commands.get( request_data[ 'filepath' ], False ) )
    ]


def CompilationDatabaseExists( file_dir ):
  for folder in PathsToAllParentFolders( file_dir ):
    if os.path.exists( os.path.join( folder, 'compile_commands.json' ) ):
      return True

  return False
