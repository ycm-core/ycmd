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

import os

from ycmd.completers.language_server import language_server_completer as lsc
from ycmd.tests.language_server.conftest import * # noqa


def PathToTestFile( *args ):
  dir_of_current_script = os.path.dirname( os.path.abspath( __file__ ) )
  return os.path.join( dir_of_current_script, 'testdata', *args )


class MockConnection( lsc.LanguageServerConnection ):
  def __init__( self, workspace_config_handler = None ):
    super().__init__( None, None, workspace_config_handler )

  def TryServerConnectionBlocking( self ):
    return True


  def Shutdown( self ):
    pass


  def WriteData( self, data ):
    pass


  def ReadData( self, size = -1 ):
    return bytes( b'' )
