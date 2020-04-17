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
      'fuzzyMatching': False,
    }


  def CodeActionLiteralToFixIt( self, request_data, code_action_literal ):
    document_changes = code_action_literal[ 'edit' ][ 'documentChanges' ]
    for text_document_edit in document_changes:
      for text_edit in text_document_edit[ 'edits' ]:
        end_line = text_edit[ 'range' ][ 'end' ][ 'line' ]
        # LSP offsets are zero based, plus `request_data[ 'lines' ]` contains
        # a trailing empty line.
        if end_line >= len( request_data[ 'lines' ] ) - 1:
          return None

    return super().CodeActionLiteralToFixIt( request_data, code_action_literal )
