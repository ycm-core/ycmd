# Copyright (C) 2020 ycmd contributors
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

import json
import logging
import os

from ycmd import responses
from ycmd import utils
from ycmd.completers.language_server import language_server_completer


PATH_TO_GOPLS = os.path.abspath( os.path.join( os.path.dirname( __file__ ),
  '..',
  '..',
  '..',
  'third_party',
  'go',
  'bin',
  utils.ExecutableName( 'gopls' ) ) )


def ShouldEnableGoCompleter( user_options ):
  server_exists = utils.FindExecutableWithFallback(
      user_options[ 'gopls_binary_path' ],
      PATH_TO_GOPLS )
  if server_exists:
    return True
  utils.LOGGER.info( 'No gopls executable at %s.', PATH_TO_GOPLS )
  return False


class GoCompleter( language_server_completer.LanguageServerCompleter ):
  def __init__( self, user_options ):
    super().__init__( user_options )
    self._user_supplied_gopls_args = user_options[ 'gopls_args' ]
    self._gopls_path = utils.FindExecutableWithFallback(
        user_options[ 'gopls_binary_path' ],
        PATH_TO_GOPLS )


  def GetServerName( self ):
    return 'gopls'


  def GetProjectRootFiles( self ):
    # Without LSP workspaces support, GOPLS relies on the rootUri to detect a
    # project.
    # TODO: add support for LSP workspaces to allow users to change project
    # without having to restart GOPLS.
    return [ 'go.mod' ]


  def GetCommandLine( self ):
    cmdline = [ self._gopls_path ] + self._user_supplied_gopls_args + [
                '-logfile',
                self._stderr_file ]
    if utils.LOGGER.isEnabledFor( logging.DEBUG ):
      cmdline.append( '-rpc.trace' )
    return cmdline


  def SupportedFiletypes( self ):
    return [ 'go' ]


  def _SetUpSemanticTokenAtlas( self, capabilities: dict ):
    if 'semanticTokensProvider' not in capabilities:
      # gopls is broken and doesn't provide a legend, instead assuming the
      # tokens specified by the client are the legend. This is broken, but
      # easily worked around:
      #
      # https://github.com/golang/go/issues/54531
      import ycmd.completers.language_server.language_server_protocol as lsp
      capabilities[ 'semanticTokensProvider' ] = {
        'full': True,
        'legend': {
          'tokenTypes': lsp.TOKEN_TYPES,
          'tokenModifiers': lsp.TOKEN_MODIFIERS
        }
      }

    return super()._SetUpSemanticTokenAtlas( capabilities )


  def GetDoc( self, request_data ):
    assert self._settings[ 'ls' ][ 'hoverKind' ] == 'Structured'
    try:
      result = json.loads( self.GetHoverResponse( request_data )[ 'value' ] )
      docs = result[ 'signature' ] + '\n' + result[ 'fullDocumentation' ]
      return responses.BuildDetailedInfoResponse( docs.strip() )
    except language_server_completer.NoHoverInfoException:
      raise RuntimeError( 'No documentation available.' )


  def GetType( self, request_data ):
    try:
      result = json.loads(
          self.GetHoverResponse( request_data )[ 'value' ] )[ 'signature' ]
      return responses.BuildDisplayMessageResponse( result )
    except language_server_completer.NoHoverInfoException:
      raise RuntimeError( 'Unknown type.' )


  def DefaultSettings( self, request_data ):
    return {
      'hoverKind': 'Structured',
      'hints': {
        'assignVariableTypes': True,
        'compositeLiteralFields': True,
        'compositeLiteralTypes': True,
        'constantValues': True,
        'functionTypeParameters': True,
        'parameterNames': True,
        'rangeVariableTypes': True,
      },
      'semanticTokens': True
    }



  def ExtraCapabilities( self ):
    return {
      'workspace': { 'configuration': True }
    }


  def WorkspaceConfigurationResponse( self, request ):
    # Returns the same settings for each "section", since gopls requests
    # settings for each open project, but ycmd only has a single settings
    # object per LSP completer.
    return [ self._settings.get( 'ls', {} )
             for i in request[ 'params' ][ 'items' ] ]
