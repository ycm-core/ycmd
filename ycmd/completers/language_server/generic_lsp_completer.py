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

from ycmd import responses, utils
from ycmd.completers.language_server.simple_language_server_completer import (
    SimpleLSPCompleter )


class GenericLSPCompleter( SimpleLSPCompleter ):
  def __init__( self, user_options, server_settings ):
    self._name = server_settings[ 'name' ]
    self._supported_filetypes = server_settings[ 'filetypes' ]
    super( GenericLSPCompleter, self ).__init__( user_options )
    self._command_line = server_settings[ 'cmdline' ]
    self._command_line[ 0 ] = utils.FindExecutable( self._command_line[ 0 ] )


  def Language( self ):
    return self._name


  def GetServerName( self ):
    return self._name + 'Completer'


  def GetCommandLine( self ):
    return self._command_line


  def GetCustomSubcommands( self ):
    return { 'GetHover': lambda self, request_data, args:
      responses.BuildDisplayMessageResponse(
        self.GetHoverResponse( request_data ) ) }


  def SupportedFiletypes( self ):
    return self._supported_filetypes
