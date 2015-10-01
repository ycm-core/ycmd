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

import os
import time
from ycmd.utils import OnTravis
from ..test_utils import BuildRequest


def PathToTestDataDir():
  dir_of_current_script = os.path.dirname( os.path.abspath( __file__ ) )
  return os.path.join( dir_of_current_script, 'testdata' )


def PathToTestFile( *args ):
  return os.path.join( PathToTestDataDir(), *args )


def StopOmniSharpServer( app, filename ):
  app.post_json( '/run_completer_command',
                 BuildRequest( completer_target = 'filetype_default',
                               command_arguments = ['StopServer'],
                               filepath = filename,
                               filetype = 'cs' ) )


def WaitUntilOmniSharpServerReady( app, filename ):
  retries = 100
  success = False

  # If running on Travis CI, keep trying forever. Travis will kill the worker
  # after 10 mins if nothing happens.
  while retries > 0 or OnTravis():
    result = app.get( '/ready', { 'subserver': 'cs' } ).json
    if result:
      success = True
      break
    request = BuildRequest( completer_target = 'filetype_default',
                            command_arguments = [ 'ServerTerminated' ],
                            filepath = filename,
                            filetype = 'cs' )
    result = app.post_json( '/run_completer_command', request ).json
    if result:
      raise RuntimeError( "OmniSharp failed during startup." )
    time.sleep( 0.2 )
    retries = retries - 1

  if not success:
    raise RuntimeError( "Timeout waiting for OmniSharpServer" )
