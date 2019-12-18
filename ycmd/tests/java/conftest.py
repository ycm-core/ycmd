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

import contextlib
import os
import pytest
from ycmd.tests.test_utils import ( BuildRequest,
                                    ClearCompletionsCache,
                                    IgnoreExtraConfOutsideTestsFolder,
                                    IsolatedApp,
                                    SetUpApp,
                                    StopCompleterServer,
                                    WaitUntilCompleterServerReady )
shared_app = None
SERVER_STARTUP_TIMEOUT = 120 # seconds


DEFAULT_PROJECT_DIR = 'simple_eclipse_project'


def setup_module():
  """Initializes the ycmd server as a WebTest application that will be shared
  by all tests using the SharedYcmd decorator in this package. Additional
  configuration that is common to these tests, like starting a semantic
  subserver, should be done here."""
  global shared_app
  shared_app = SetUpApp()
  with IgnoreExtraConfOutsideTestsFolder():
    StartJavaCompleterServerInDirectory( shared_app,
                                         PathToTestFile( DEFAULT_PROJECT_DIR ) )


def teardown_module():
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


@pytest.fixture
def isolated_app():
  """Defines a pytest fixture to be used in cases where it is easier to
  specify user options of the isolated ycmdat some point inside the function.

  Example usage:

    def some_test( isolated_app ):
      with TemporaryTestDir() as tmp_dir:
        with isolated_app( user_options ) as app:

  """
  @contextlib.contextmanager
  def manager( custom_options ):
    with IsolatedApp( custom_options ) as app:
      try:
        yield app
      finally:
        StopCompleterServer( app, 'java' )

  return manager


@pytest.fixture
def app( request ):
  which = request.param[ 0 ]
  assert which == 'isolated' or which == 'shared'
  if which == 'isolated':
    with IsolatedApp( request.param[ 1 ] ) as app:
      try:
        yield app
      finally:
        StopCompleterServer( app, 'java' )
  else:
    global shared_app
    ClearCompletionsCache()
    with IgnoreExtraConfOutsideTestsFolder():
      yield shared_app


"""Defines a decorator to be attached to tests of this package. This decorator
passes the shared ycmd application as a parameter."""
SharedYcmd = pytest.mark.parametrize(
    # Name of the fixture/function argument
    'app',
    # Fixture parameters, passed to app() as request.param
    [ ( 'shared', ) ],
    # Non-empty ids makes fixture parameters visible in pytest verbose output
    ids = [ '' ],
    # Execute the fixture, instead of passing parameters directly to the
    # function argument
    indirect = True )


def IsolatedYcmd( custom_options = {} ):
  """Defines a decorator to be attached to tests of this package. This decorator
  passes a unique ycmd application as a parameter. It should be used on tests
  that change the server state in a irreversible way (ex: a semantic subserver
  is stopped or restarted) or expect a clean state (ex: no semantic subserver
  started, no .ycm_extra_conf.py loaded, etc). Use the optional parameter
  |custom_options| to give additional options and/or override the default ones.

  Example usage:

    from ycmd.tests.python import IsolatedYcmd

    @IsolatedYcmd( { 'python_binary_path': '/some/path' } )
    def CustomPythonBinaryPath_test( app ):
      ...
  """
  return pytest.mark.parametrize(
      # Name of the fixture/function argument
      'app',
      # Fixture parameters, passed to app() as request.param
      [ ( 'isolated', custom_options ) ],
      # Non-empty ids makes fixture parameters visible in pytest verbose output
      ids = [ '' ],
      # Execute the fixture, instead of passing parameters directly to the
      # function argument
      indirect = True )


def PathToTestFile( *args ):
  dir_of_current_script = os.path.dirname( os.path.abspath( __file__ ) )
  return os.path.join( dir_of_current_script, 'testdata', *args )
