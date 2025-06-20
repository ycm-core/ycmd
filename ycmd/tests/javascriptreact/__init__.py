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
from unittest.mock import patch
from ycmd.tests.test_utils import ( ClearCompletionsCache,
                                    IgnoreExtraConfOutsideTestsFolder,
                                    IsolatedApp,
                                    SetUpApp,
                                    StopCompleterServer,
                                    WaitUntilCompleterServerReady )

shared_app = None


def setUpModule():
  global shared_app
  with patch( 'ycmd.completers.javascript.hook.'
      'ShouldEnableTernCompleter', return_value = False ):
    shared_app = SetUpApp()
    WaitUntilCompleterServerReady( shared_app, 'javascriptreact' )


def tearDownModule():
  StopCompleterServer( shared_app, 'javascriptreact' )


def PathToTestFile( *args ):
  dir_of_current_script = os.path.dirname( os.path.abspath( __file__ ) )
  return os.path.join( dir_of_current_script, 'testdata', *args )


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
      with patch( 'ycmd.completers.javascript.hook.'
                  'ShouldEnableTernCompleter', return_value = False ):
        with IsolatedApp( custom_options ) as app:
          try:
            test( test_case_instance, app, *args, **kwargs )
          finally:
            StopCompleterServer( app, 'javascriptreact' )
    return Wrapper
  return Decorator
