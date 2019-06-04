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

import logging
import os

from ycmd import responses
from ycmd import utils
from ycmd.completers.language_server import ( simple_language_server_completer,
                                              language_server_completer )


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


  def GetProjectDirectory( self, request_data, extra_conf_dir ):
    # Without LSP workspaces support, GOPLS relies on the rootUri to detect a
    # project.
    # TODO: add support for LSP workspaces to allow users to change project
    # without having to restart GOPLS.
    for folder in utils.PathsToAllParentFolders( request_data[ 'filepath' ] ):
      if os.path.isfile( os.path.join( folder, 'go.mod' ) ):
        return folder
    return super( GoCompleter, self ).GetProjectDirectory( request_data,
                                                           extra_conf_dir )


  def GetCommandLine( self ):
    cmdline = [ PATH_TO_GOPLS, '-logfile', self._stderr_file ]
    if utils.LOGGER.isEnabledFor( logging.DEBUG ):
      cmdline.append( '-rpc.trace' )
    return cmdline


  def SupportedFiletypes( self ):
    return [ 'go' ]


  def GetType( self, request_data ):
    try:
      result = self.GetHoverResponse( request_data )[ 'value' ]
      return responses.BuildDisplayMessageResponse( result )
    except language_server_completer.ResponseFailedException:
      raise RuntimeError( 'Unknown type.' )


  def GetCustomSubcommands( self ):
    return {
      'RestartServer': (
        lambda self, request_data, args: self._RestartServer( request_data )
      ),
      'FixIt': (
        lambda self, request_data, args: self.GetCodeActions( request_data,
                                                              args )
      ),
      'GetType': (
        # In addition to type information we show declaration.
        lambda self, request_data, args: self.GetType( request_data )
      ),
    }


  def HandleServerCommand( self, request_data, command ):
    return language_server_completer.WorkspaceEditToFixIt(
      request_data,
      command[ 'edit' ],
      text = command[ 'title' ] )
