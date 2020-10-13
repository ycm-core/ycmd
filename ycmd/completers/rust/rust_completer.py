# Copyright (C) 2015-2020 ycmd contributors
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
from subprocess import PIPE

from ycmd import responses, utils
from ycmd.completers.language_server import language_server_completer
from ycmd.utils import LOGGER, re


LOGFILE_FORMAT = 'ra_'
RUST_ROOT = os.path.abspath(
  os.path.join( os.path.dirname( __file__ ), '..', '..', '..', 'third_party',
                'rust-analyzer' ) )
RA_BIN_DIR = os.path.join( RUST_ROOT, 'bin' )
RUSTC_EXECUTABLE = utils.FindExecutable( os.path.join( RA_BIN_DIR, 'rustc' ) )
RA_EXECUTABLE = utils.FindExecutable( os.path.join(
    RA_BIN_DIR, 'rust-analyzer' ) )
RA_VERSION_REGEX = re.compile( r'^rust-analyzer (?P<version>.*)$' )


def _GetCommandOutput( command ):
  return utils.ToUnicode(
    utils.SafePopen( command,
                     stdin_windows = PIPE,
                     stdout = PIPE,
                     stderr = PIPE ).communicate()[ 0 ].rstrip() )


def _GetRAVersion( ra_path ):
  ra_version = _GetCommandOutput( [ ra_path, '--version' ] )
  match = RA_VERSION_REGEX.match( ra_version )
  if not match:
    LOGGER.error( 'Cannot parse Rust Language Server version: %s', ra_version )
    return None
  return match.group( 'version' )


def ShouldEnableRustCompleter( user_options ):
  if ( 'rls_binary_path' in user_options and
       not user_options[ 'rust_toolchain_root' ] ):
    LOGGER.warning( 'rls_binary_path detected. '
                    'Did you mean rust_toolchain_root?' )

  if user_options[ 'rust_toolchain_root' ]:
    # Listen to what the user wanted to use
    ra = os.path.join( user_options[ 'rust_toolchain_root' ],
                       'bin', 'rust-analyzer' )
    if not utils.FindExecutable( ra ):
      LOGGER.error( 'Not using Rust completer: no rust-analyzer '
                    'executable found at %s', ra )
      return False
    else:
      return True
  else:
    return bool( utils.FindExecutable( RA_EXECUTABLE ) )


class RustCompleter( language_server_completer.LanguageServerCompleter ):
  def __init__( self, user_options ):
    super().__init__( user_options )
    if user_options[ 'rust_toolchain_root' ]:
      self._rust_root = user_options[ 'rust_toolchain_root' ]
    else:
      self._rust_root = os.path.dirname( os.path.dirname( RA_EXECUTABLE ) )
    self._ra_path = utils.FindExecutable(
        os.path.join( self._rust_root, 'bin', 'rust-analyzer' ) )


  def _Reset( self ):
    self._server_progress = 'Not started'
    super()._Reset()


  def GetServerName( self ):
    return 'Rust Language Server'


  def GetCommandLine( self ):
    return [ self._ra_path ]


  def GetServerEnvironment( self ):
    env = os.environ.copy()
    old_path = env[ 'PATH' ]
    ra_bin_dir = os.path.join( self._rust_root, 'bin' )
    env[ 'PATH' ] = ra_bin_dir + os.pathsep + old_path
    if LOGGER.isEnabledFor( logging.DEBUG ):
      env[ 'RA_LOG' ] = 'rust_analyzer=trace'
    return env


  def GetProjectRootFiles( self ):
    # Without LSP workspaces support, RA relies on the rootUri to detect a
    # project.
    # TODO: add support for LSP workspaces to allow users to change project
    # without having to restart RA.
    return [ 'Cargo.toml' ]


  def ServerIsReady( self ):
    return ( super().ServerIsReady() and
             self._server_progress in [ 'invalid', 'ready' ] )


  def SupportedFiletypes( self ):
    return [ 'rust' ]


  def GetTriggerCharacters( self, server_trigger_characters ):
    # The trigger characters supplied by RA ('.' and ':') are worse than ycmd's
    # own semantic triggers ('.' and '::') so we ignore them.
    return []


  def ExtraDebugItems( self, request_data ):
    return [
      responses.DebugInfoItem( 'Project State', self._server_progress ),
      responses.DebugInfoItem( 'Version', _GetRAVersion( self._ra_path ) ),
      responses.DebugInfoItem( 'Rust Root', self._rust_root )
    ]


  def HandleNotificationInPollThread( self, notification ):
    if notification[ 'method' ] == 'rust-analyzer/status':
      if self._server_progress not in [ 'invalid', 'ready' ]:
        self._server_progress = notification[ 'params' ][ 'status' ]
    if notification[ 'method' ] == 'window/showMessage':
      if ( notification[ 'params' ][ 'message' ] ==
           'rust-analyzer failed to discover workspace' ):
        self._server_progress = 'invalid'

    super().HandleNotificationInPollThread( notification )


  def ConvertNotificationToMessage( self, request_data, notification ):
    if notification[ 'method' ] == 'rust-analyzer/status':
      message = notification[ 'params' ]
      if message != 'invalid': # RA produces a better message for `invalid`
        return responses.BuildDisplayMessageResponse(
          f'Initializing Rust completer: { message }' )
    return super().ConvertNotificationToMessage( request_data, notification )


  def GetType( self, request_data ):
    try:
      hover_response = self.GetHoverResponse( request_data )[ 'value' ]
    except language_server_completer.NoHoverInfoException:
      raise RuntimeError( 'Unknown type.' )

    # rust-analyzer's hover format looks like this:
    #
    # ```rust
    # namespace
    # ```
    #
    # ```rust
    # type info
    # ```
    #
    # ---
    # docstring
    #
    # To extract the type info, we take everything up to `---` line,
    # then find the last occurence of "```" as the end index and "```rust"
    # as the start index and return the slice.
    hover_response = hover_response.split( '\n---\n', 2 )[ 0 ]
    start = hover_response.rfind( '```rust\n' ) + len( '```rust\n' )
    end = hover_response.rfind( '\n```' )
    return responses.BuildDisplayMessageResponse( hover_response[ start:end ] )


  def GetDoc( self, request_data ):
    try:
      hover_response = self.GetHoverResponse( request_data )
    except language_server_completer.NoHoverInfoException:
      raise RuntimeError( 'No documentation available.' )

    # Strips all empty lines and lines starting with "```" to make the hover
    # response look like plain text. For the format, see the comment in GetType.
    lines = hover_response[ 'value' ].split( '\n' )
    documentation = '\n'.join(
      line for line in lines if line and not line.startswith( '```' ) ).strip()
    return responses.BuildDetailedInfoResponse( documentation )


  def ExtraCapabilities( self ):
    return {
      'experimental': { 'statusNotification': True },
      'workspace': { 'configuration': True }
    }


  def WorkspaceConfigurationResponse( self, request ):
    assert len( request[ 'params' ][ 'items' ] ) == 1
    return [ self._settings.get( 'ls', {} ).get( 'rust-analyzer' ) ]
