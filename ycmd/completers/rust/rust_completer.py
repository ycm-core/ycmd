# Copyright (C) 2015-2019 ycmd contributors
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

import logging
import os
from future.utils import itervalues
from subprocess import PIPE

from ycmd import responses, utils
from ycmd.completers.language_server import simple_language_server_completer
from ycmd.utils import LOGGER, re


LOGFILE_FORMAT = 'rls_'
RLS_BIN_DIR = os.path.abspath(
  os.path.join( os.path.dirname( __file__ ), '..', '..', '..', 'third_party',
                'rls', 'bin' ) )
RUSTC_EXECUTABLE = utils.FindExecutable( os.path.join( RLS_BIN_DIR, 'rustc' ) )
RLS_EXECUTABLE = utils.FindExecutable( os.path.join( RLS_BIN_DIR, 'rls' ) )
RLS_VERSION_REGEX = re.compile( r'^rls (?P<version>.*)$' )


def _GetCommandOutput( command ):
  return utils.ToUnicode(
    utils.SafePopen( command,
                     stdin_windows = PIPE,
                     stdout = PIPE,
                     stderr = PIPE ).communicate()[ 0 ].rstrip() )


def _GetRlsVersion():
  rls_version = _GetCommandOutput( [ RLS_EXECUTABLE, '--version' ] )
  match = RLS_VERSION_REGEX.match( rls_version )
  if not match:
    LOGGER.error( 'Cannot parse Rust Language Server version: %s', rls_version )
    return None
  return match.group( 'version' )


def ShouldEnableRustCompleter():
  if not RLS_EXECUTABLE:
    LOGGER.error( 'Not using Rust completer: no RLS executable found at %s',
                  RLS_EXECUTABLE )
    return False
  LOGGER.info( 'Using Rust completer' )
  return True


class RustCompleter( simple_language_server_completer.SimpleLSPCompleter ):

  def _Reset( self ):
    with self._server_state_mutex:
      super( RustCompleter, self )._Reset()
      self._server_progress = {}


  def GetServerName( self ):
    return 'Rust Language Server'


  def GetCommandLine( self ):
    return RLS_EXECUTABLE


  def GetServerEnvironment( self ):
    env = os.environ.copy()
    # Force RLS to use the rustc from the toolchain in third_party/rls.
    # TODO: allow users to pick a custom toolchain.
    utils.SetEnviron( env, 'RUSTC', RUSTC_EXECUTABLE )
    if LOGGER.isEnabledFor( logging.DEBUG ):
      utils.SetEnviron( env, 'RUST_LOG', 'rls=trace' )
      utils.SetEnviron( env, 'RUST_BACKTRACE', '1' )
    return env


  def GetProjectDirectory( self, request_data, extra_conf_dir ):
    # Without LSP workspaces support, RLS relies on the rootUri to detect a
    # project.
    # TODO: add support for LSP workspaces to allow users to change project
    # without having to restart RLS.
    for folder in utils.PathsToAllParentFolders( request_data[ 'filepath' ] ):
      if os.path.isfile( os.path.join( folder, 'Cargo.toml' ) ):
        return folder
    return super( RustCompleter, self ).GetProjectDirectory( request_data,
                                                             extra_conf_dir )



  def ServerIsReady( self ):
    # Assume RLS is ready once building and indexing are done.
    # See
    # https://github.com/rust-lang/rls/blob/master/contributing.md#rls-to-lsp-client
    # for detail on the progress steps.
    return ( super( RustCompleter, self ).ServerIsReady() and
             self._server_progress and
             set( itervalues( self._server_progress ) ) == { 'building done',
                                                             'indexing done' } )


  def SupportedFiletypes( self ):
    return [ 'rust' ]


  def GetTriggerCharacters( self, server_trigger_characters ):
    # The trigger characters supplied by RLS ('.' and ':') are worse than ycmd's
    # own semantic triggers ('.' and '::') so we ignore them.
    return []


  def GetCustomSubcommands( self ):
    return {
      'GetDoc': (
        lambda self, request_data, args: self.GetDoc( request_data )
      ),
      'GetType': (
        lambda self, request_data, args: self.GetType( request_data )
      ),
      'RestartServer': (
        lambda self, request_data, args: self._RestartServer( request_data )
      )
    }


  def CommonDebugItems( self ):
    project_state = ', '.join(
      set( itervalues( self._server_progress ) ) ).capitalize()
    return super( RustCompleter, self ).CommonDebugItems() + [
      responses.DebugInfoItem( 'Project State', project_state ),
      responses.DebugInfoItem( 'Version', _GetRlsVersion() )
    ]


  def _ShouldResolveCompletionItems( self ):
    # RLS tells us that it can resolve a completion but there is no point since
    # no additional information is returned.
    return False


  def HandleNotificationInPollThread( self, notification ):
    # TODO: the building status is currently displayed in the debug info. We
    # should notify the client about it through a special status/progress
    # message.
    if notification[ 'method' ] == 'window/progress':
      params = notification[ 'params' ]
      progress_id = params[ 'id' ]
      message = params[ 'title' ].lower()
      if not params[ 'done' ]:
        if params[ 'message' ]:
          message += ' ' + params[ 'message' ]
        if params[ 'percentage' ]:
          message += ' ' + params[ 'percentage' ]
      else:
        message += ' done'

      with self._server_info_mutex:
        self._server_progress[ progress_id ] = message

    super( RustCompleter, self ).HandleNotificationInPollThread( notification )


  def GetType( self, request_data ):
    hover_response = self.GetHoverResponse( request_data )

    for item in hover_response:
      if isinstance( item, dict ) and 'value' in item:
        return responses.BuildDisplayMessageResponse( item[ 'value' ] )

    raise RuntimeError( 'Unknown type.' )


  def GetDoc( self, request_data ):
    hover_response = self.GetHoverResponse( request_data )

    # RLS returns a list that may contain the following elements:
    # - a documentation string;
    # - a documentation url;
    # - [{language:rust, value:<type info>}].

    documentation = '\n'.join(
      [ item.strip() for item in hover_response if isinstance( item, str ) ] )

    if not documentation:
      raise RuntimeError( 'No documentation available for current context.' )

    return responses.BuildDetailedInfoResponse( documentation )
