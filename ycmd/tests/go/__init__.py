# Copyright (C) 2021 ycmd contributors
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

import functools
import os
from ycmd.tests.test_utils import ( BuildRequest,
                                    ClearCompletionsCache,
                                    IgnoreExtraConfOutsideTestsFolder,
                                    IsolatedApp,
                                    SetUpApp,
                                    StopCompleterServer,
                                    WaitUntilCompleterServerReady ) # noqa

shared_app = None


def setUpModule():
  global shared_app
  shared_app = SetUpApp()
  with IgnoreExtraConfOutsideTestsFolder():
    StartGoCompleterServerInDirectory( shared_app, PathToTestFile() )


def tearDownModule():
  StopCompleterServer( shared_app, 'go' )


def StartGoCompleterServerInDirectory( app, directory ):
  app.post_json( '/event_notification',
                 BuildRequest(
                   filepath = os.path.join( directory, 'goto.go' ),
                   event_name = 'FileReadyToParse',
                   filetype = 'go' ) )
  WaitUntilCompleterServerReady( app, 'go' )


def SharedYcmd( test ):
  @functools.wraps( test )
  def Wrapper( test_case_instance, *args, **kwargs ):
    ClearCompletionsCache()
    with IgnoreExtraConfOutsideTestsFolder():
      return test( test_case_instance, shared_app, *args, **kwargs )
  return Wrapper


def IsolatedYcmd( custom_options = {} ):
  def Decorator( test ):
    @functools.wraps( test )
    def Wrapper( test_case_instance, *args, **kwargs ):
      with IsolatedApp( custom_options ) as app:
        try:
          test( test_case_instance, app, *args, **kwargs )
        finally:
          StopCompleterServer( app, 'go' )
    return Wrapper
  return Decorator


def PathToTestFile( *args, module_dir = 'go_module' ):
  dir_of_current_script = os.path.dirname( os.path.abspath( __file__ ) )
  # GOPLS doesn't work if any parent directory is named "testdata"
  return os.path.join( dir_of_current_script, module_dir, *args )
