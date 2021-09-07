# Copyright (C) 2017-2021 ycmd contributors
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

import contextlib
import os
from ycmd.tests.test_utils import ( BuildRequest,
                                    ClearCompletionsCache,
                                    IgnoreExtraConfOutsideTestsFolder,
                                    IsolatedApp,
                                    SetUpApp,
                                    StopCompleterServer,
                                    WaitUntilCompleterServerReady )
import functools

shared_app = None
SERVER_STARTUP_TIMEOUT = 120 # seconds


DEFAULT_PROJECT_DIR = 'simple_eclipse_project'


def PathToTestFile( *args ):
  dir_of_current_script = os.path.dirname( os.path.abspath( __file__ ) )
  return os.path.join( dir_of_current_script, 'testdata', *args )


def setUpModule():
  global shared_app
  shared_app = SetUpApp()
  with IgnoreExtraConfOutsideTestsFolder():
    StartJavaCompleterServerInDirectory( shared_app,
                                         PathToTestFile( DEFAULT_PROJECT_DIR ) )


def tearDownModule():
  global shared_app
  StopCompleterServer( shared_app, 'java' )


def StartJavaCompleterServerInDirectory( app, directory ):
  StartJavaCompleterServerWithFile( app,
                                    os.path.join( directory, 'test.java' ) )


def StartJavaCompleterServerWithFile( app, file_path ):
  app.post_json( '/event_notification',
                 BuildRequest(
                   event_name = 'FileReadyToParse',
                   filepath = file_path,
                   filetype = 'java' ) )
  WaitUntilCompleterServerReady( app, 'java', SERVER_STARTUP_TIMEOUT )


@contextlib.contextmanager
def isolated_app( custom_options = {} ):
  """Defines a context manager to be used in cases where it is easier to
  specify user options of the isolated ycmdat some point inside the function.

  Example usage:

    def some_test( isolated_app ):
      with TemporaryTestDir() as tmp_dir:
        with isolated_app( user_options ) as app:

  """
  with IsolatedApp( custom_options ) as app:
    try:
      yield app
    finally:
      StopCompleterServer( app, 'java' )


def SharedYcmd( test ):
  global shared_app

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
          StopCompleterServer( app, 'java' )
    return Wrapper
  return Decorator
