# Copyright (C) 2015 ycmd contributors
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
from future import standard_library
standard_library.install_aliases()
from builtins import *  # noqa

from ..handlers_test import Handlers_test

import time


class Rust_Handlers_test( Handlers_test ):


  def __init__( self ):
    self._file = __file__


  def tearDown( self ):
    self._StopServer()


  def _StopServer( self ):
    try:
      self._app.post_json(
        '/run_completer_command',
        self._BuildRequest( command_arguments = [ 'StopServer' ],
                            filetype = 'rust',
                            completer_target = 'filetype_default' )
      )
    except:
      pass


  def _WaitUntilServerReady( self ):
    retries = 100

    while retries > 0:
      result = self._app.get( '/ready', { 'subserver': 'rust' } ).json
      if result:
        return
      time.sleep( 0.2 )
      retries = retries - 1

    raise RuntimeError( "Timeout waiting for racerd" )
