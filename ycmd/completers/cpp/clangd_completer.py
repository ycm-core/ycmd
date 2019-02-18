# Copyright (C) 2018-2019 ycmd contributors
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

import subprocess
import os
import threading
import re

from ycmd import responses, utils
from ycmd.completers.completer_utils import GetFileLines
from ycmd.completers.language_server import language_server_completer
from ycmd.completers.language_server import language_server_protocol as lsp
from ycmd.utils import ( GetExecutable,
                         ExpandVariablesInPath,
                         LOGGER,
                         CLANG_RESOURCE_DIR )

MIN_SUPPORTED_VERSION = '7.0.0'
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


def DistanceOfPointToRange( point, range ):
  """Calculate the distance from a point to a range.

  Assumes point is covered by lines in the range.
  Returns 0 if point is already inside range. """
  start = range[ 'start' ]
  end = range[ 'end' ]

  # Single-line range.
  if start[ 'line' ] == end[ 'line' ]:
    # 0 if point is within range, otherwise distance from start/end.
    return max( 0, point[ 'character' ] - end[ 'character' ],
                start[ 'character' ] - point[ 'character' ] )

  if start[ 'line' ] == point[ 'line' ]:
    return max( 0, start[ 'character' ] - point[ 'character' ] )
  if end[ 'line' ] == point[ 'line' ]:
    return max( 0, point[ 'character' ] - end[ 'character' ] )
  # If not on the first or last line, then point is within range for sure.
  return 0


def GetVersion( clangd_path ):
  args = [ clangd_path, '--version' ]
  stdout, _ = subprocess.Popen( args, stdout=subprocess.PIPE ).communicate()
  version_regexp = r'(\d\.\d\.\d)'
  m = re.search( version_regexp, stdout.decode() )
  try:
    version = m.group( 1 )
  except AttributeError:
    # Custom builds might have different versioning info.
    version = None
  return version


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
    clangd = GetExecutable( ExpandVariablesInPath( clangd ) )

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
  for arg in clangd_args:
    CLANGD_COMMAND.append( arg )
    put_resource_dir = put_resource_dir or arg.startswith( '-resource-dir' )
    put_limit_results = put_limit_results or arg.startswith( '-limit-results' )
    put_header_insertion_decorators = ( put_header_insertion_decorators or
                        arg.startswith( '-header-insertion-decorators' ) )
  if not put_header_insertion_decorators:
    CLANGD_COMMAND.append( '-header-insertion-decorators=0' )
  if resource_dir and not put_resource_dir:
    CLANGD_COMMAND.append( '-resource-dir=' + resource_dir )
  if user_options[ 'clangd_uses_ycmd_caching' ] and not put_limit_results:
    CLANGD_COMMAND.append( '-limit-results=500' )

  return CLANGD_COMMAND


def ShouldEnableClangdCompleter( user_options ):
  """Checks whether clangd should be enabled or not.

  - Returns True iff an up-to-date binary exists either in `clangd_binary_path`
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


class ClangdCompleter( language_server_completer.LanguageServerCompleter ):
  """A LSP-based completer for C-family languages, powered by Clangd.

  Supported features:
    * Code completion
    * Diagnostics and apply FixIts
    * Go to definition
  """

  def __init__( self, user_options ):
    super( ClangdCompleter, self ).__init__( user_options )

    # Used to ensure that starting/stopping of the server is synchronized.
    # Guards _connection and _server_handle.
    self._server_state_mutex = threading.RLock()
    self._clangd_command = GetClangdCommand( user_options )
    self._stderr_file = None

    self._Reset()
    self._auto_trigger = user_options[ 'auto_trigger' ]
    self._use_ycmd_caching = user_options[ 'clangd_uses_ycmd_caching' ]


  def _Reset( self ):
    with self._server_state_mutex:
      self.ServerReset() # Cleanup subclass internal states.
      self._connection = None
      self._server_handle = None
      if self._stderr_file is not None:
        utils.RemoveIfExists( self._stderr_file )
        self._stderr_file = None


  def GetConnection( self ):
    with self._server_state_mutex:
      return self._connection


  def DebugInfo( self, request_data ):
    with self._server_state_mutex:
      clangd = responses.DebugInfoServer( name = 'clangd',
                                          handle = self._server_handle,
                                          executable = self._clangd_command,
                                          logfiles = [ self._stderr_file ],
                                          extras = self.CommonDebugItems() )

      return responses.BuildDebugInfoResponse( name = 'clangd',
                                               servers = [ clangd ] )


  def Language( self ):
    return 'clangd'


  def SupportedFiletypes( self ):
    return ( 'c', 'cpp', 'objc', 'objcpp', 'cuda' )


  def GetType( self, request_data ):
    return self.GetHoverResponse( request_data )[ 'value' ]


  def _GetTriggerCharacters( self, server_trigger_characters ):
    # The trigger characters supplied by clangd are worse than ycmd's own
    # semantic triggers which are more sophisticated (regex-based). So we
    # ignore them.
    return []


  def GetCustomSubcommands( self ):
    return {
      'FixIt': (
        lambda self, request_data, args: self.GetCodeActions( request_data,
                                                              args )
      ),
      'GetType': (
        # In addition to type information we show declaration.
        lambda self, request_data, args: self.GetType( request_data )
      ),
      'GetTypeImprecise': (
        lambda self, request_data, args: self.GetType( request_data )
      ),
      'GoToInclude': (
        lambda self, request_data, args: self.GoToDeclaration( request_data )
      ),
      'StopServer': (
        lambda self, request_data, args: self.Shutdown()
      ),
      # To handle the commands below we need extensions to LSP. One way to
      # provide those could be to use workspace/executeCommand requset.
      # 'GetDoc': (
      #   lambda self, request_data, args: self.GetType( request_data )
      # ),
      # 'GetParent': (
      #   lambda self, request_data, args: self.GetType( request_data )
      # )
    }


  def HandleServerCommand( self, request_data, command ):
    if command[ 'command' ] == 'clangd.applyFix':
      return language_server_completer.WorkspaceEditToFixIt(
        request_data,
        command[ 'arguments' ][ 0 ],
        text = command[ 'title' ] )

    return None


  def GetCodepointForCompletionRequest( self, request_data ):
    """Overriden to pass the actual cursor position to clangd."""

    # There are two types of codepoint offsets on the current line in ycmd:
    #   - start_codepoint: where the completion identifier starts.
    #   - column_codepoint: where the current cursor is placed.
    # ycmd uses the start_codepoint by default -- because it caches completion
    # items and does filtering/ranking. Instead, we use the filtering/ranking
    # results from clangd, thus we pass "column_codepoint" (which includes the
    # whole query string e.g. "std::u_p") to clangd.
    return request_data[ 'column_codepoint' ]


  # TODO: Turn on coverage detection when updating to LLVM8 release. It is
  # currently turned off because Clangd doesn't support it in LLVM7 release.
  def ShouldCompleteIncludeStatement( self, request_data ): # pragma: no cover
    column_codepoint = request_data[ 'column_codepoint' ] - 1
    current_line = request_data[ 'line_value' ]
    return INCLUDE_REGEX.match( current_line[ : column_codepoint ] )


  def ShouldUseNow( self, request_data ):
    """Overriden to avoid ycmd's caching/filtering logic."""
    # Clangd should be able to provide completions in any context.
    # FIXME: Empty queries provide spammy results, fix this in clangd.
    # FIXME: Add triggers for include completion with release of LLVM8.
    if self._use_ycmd_caching:
      return super( ClangdCompleter, self ).ShouldUseNow( request_data )
    return ( request_data[ 'query' ] != '' or
             super( ClangdCompleter, self ).ShouldUseNowInner( request_data ) )


  def ComputeCandidates( self, request_data ):
    """Orverriden to bypass ycmd's cache."""
    # Caching results means reranking them, and ycmd has fewer signals.
    if self._use_ycmd_caching:
      return super( ClangdCompleter, self ).ComputeCandidates( request_data )
    return super( ClangdCompleter, self ).ComputeCandidatesInner( request_data )


  def ServerIsHealthy( self ):
    with self._server_state_mutex:
      return utils.ProcessIsRunning( self._server_handle )


  def StartServer( self, request_data ):
    with self._server_state_mutex:
      # Ensure we cleanup all states.
      self._Reset()

      LOGGER.info( 'Starting clangd: %s', self._clangd_command )
      self._stderr_file = utils.CreateLogfile( 'clangd_stderr' )
      with utils.OpenForStdHandle( self._stderr_file ) as stderr:
        self._server_handle = utils.SafePopen( self._clangd_command,
                                               stdin = subprocess.PIPE,
                                               stdout = subprocess.PIPE,
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
        LOGGER.error( 'Clangd failed to start, or did not connect '
                      'successfully' )
        self.Shutdown()
        return False

    LOGGER.info( 'Clangd started' )

    return True


  def Shutdown( self ):
    with self._server_state_mutex:
      LOGGER.info( 'Shutting down clangd...' )

      # Tell the connection to expect the server to disconnect
      if self._connection:
        self._connection.Stop()

      if not self.ServerIsHealthy():
        LOGGER.info( 'Clangd is not running' )
        self._Reset()
        return

      LOGGER.info( 'Stopping Clangd with PID %s', self._server_handle.pid )

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

        LOGGER.info( 'Clangd stopped' )
      except Exception:
        LOGGER.exception( 'Error while stopping Clangd server' )
        # We leave the process running. Hopefully it will eventually die of its
        # own accord.

      # Tidy up our internal state, even if the completer server didn't close
      # down cleanly.
      self._Reset()


  def GetDetailedDiagnostic( self, request_data ):
    self._UpdateServerWithFileContents( request_data )

    current_line_lsp = request_data[ 'line_num' ] - 1
    current_file = request_data[ 'filepath' ]

    if not self._latest_diagnostics:
      return responses.BuildDisplayMessageResponse(
          'Diagnostics are not ready yet.' )

    with self._server_info_mutex:
      diagnostics = list( self._latest_diagnostics[
          lsp.FilePathToUri( current_file ) ] )

    if not diagnostics:
      return responses.BuildDisplayMessageResponse(
          'No diagnostics for current file.' )

    current_column = lsp.CodepointsToUTF16CodeUnits(
        GetFileLines( request_data, current_file )[ current_line_lsp ],
        request_data[ 'column_codepoint' ] )
    minimum_distance = None

    message = 'No diagnostics for current line.'
    for diagnostic in diagnostics:
      start = diagnostic[ 'range' ][ 'start' ]
      end = diagnostic[ 'range' ][ 'end' ]
      if current_line_lsp < start[ 'line' ] or end[ 'line' ] < current_line_lsp:
        continue
      point = { 'line': current_line_lsp, 'character': current_column }
      distance = DistanceOfPointToRange( point, diagnostic[ 'range' ] )
      if minimum_distance is None or distance < minimum_distance:
        message = diagnostic[ 'message' ]
        if distance == 0:
          break
        minimum_distance = distance

    return responses.BuildDisplayMessageResponse( message )
