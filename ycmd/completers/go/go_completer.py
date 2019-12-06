# Copyright (C) 2019 ycmd contributors
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

import json
import logging
import os

from ycmd import responses
from ycmd import utils
from ycmd.completers.language_server import simple_language_server_completer
from ycmd.completers.language_server import language_server_completer


PATH_TO_GOPLS = os.path.abspath( os.path.join( os.path.dirname( __file__ ),
  '..',
  '..',
  '..',
  'third_party',
  'go',
  'src',
  'golang.org',
  'x',
  'tools',
  'cmd',
  'gopls',
  utils.ExecutableName( 'gopls' ) ) )


def ShouldEnableGoCompleter( user_options ):
  server_exists = os.path.isfile( PATH_TO_GOPLS )
  if server_exists:
    return True
  utils.LOGGER.info( 'No gopls executable at %s.', PATH_TO_GOPLS )
  return False


class GoCompleter( simple_language_server_completer.SimpleLSPCompleter ):
  def __init__( self, user_options ):
    super( GoCompleter, self ).__init__( user_options )


  def GetServerName( self ):
    return 'gopls'


  def GetProjectRootFiles( self ):
    # Without LSP workspaces support, GOPLS relies on the rootUri to detect a
    # project.
    # TODO: add support for LSP workspaces to allow users to change project
    # without having to restart GOPLS.
    return [ 'go.mod' ]


  def GetCommandLine( self ):
    cmdline = [ PATH_TO_GOPLS, '-logfile', self._stderr_file ]
    if utils.LOGGER.isEnabledFor( logging.DEBUG ):
      cmdline.append( '-rpc.trace' )
    return cmdline


  def SupportedFiletypes( self ):
    return [ 'go' ]


  def GetDoc( self, request_data ):
    assert self._settings[ 'hoverKind' ] == 'Structured'
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
    return { 'hoverKind': 'Structured',
             'fuzzyMatching': False }
