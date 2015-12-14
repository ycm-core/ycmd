#!/usr/bin/env python
#
# Copyright (C) 2015 ycmd contributors.
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

from ..handlers_test import Handlers_test
import os
import time


class Javascript_Handlers_test( Handlers_test ):

  def __init__( self ):
    self._file = __file__


  def setUp( self ):
    super( Javascript_Handlers_test, self ).setUp()

    self._prev_current_dir = os.getcwd()
    os.chdir( self._PathToTestFile() )

    self._WaitUntilTernServerReady()


  def tearDown( self ):
    self._StopTernServer()

    os.chdir( self._prev_current_dir )


  def _StopTernServer( self ):
    try:
      self._app.post_json(
        '/run_completer_command',
        self._BuildRequest( command_arguments = [ 'StopServer' ],
                            filetype = 'javascript',
                            completer_target = 'filetype_default' )
      )
    except:
      pass


  def _WaitUntilTernServerReady( self ):
    self._app.post_json( '/run_completer_command', self._BuildRequest(
      command_arguments = [ 'StartServer' ],
      completer_target = 'filetype_default',
      filetype = 'javascript',
      filepath = '/foo.js',
      contents = '',
      line_num = '1'
    ) )

    retries = 100
    while retries > 0:
      result = self._app.get( '/ready', { 'subserver': 'javascript' } ).json
      if result:
        return

      time.sleep( 0.2 )
      retries = retries - 1

    raise RuntimeError( 'Timeout waiting for Tern.js server to be ready' )
