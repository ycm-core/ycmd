# Copyright (C) 2017 ycmd contributors
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

import functools
import os
import time
from pprint import pformat

from ycmd.tests.test_utils import ( BuildRequest,
                                    ClearCompletionsCache,
                                    IgnoreExtraConfOutsideTestsFolder,
                                    IsolatedApp,
                                    SetUpApp,
                                    StopCompleterServer,
                                    WaitUntilCompleterServerReady )

shared_app = None
DEFAULT_PROJECT_DIR = 'simple_eclipse_project'
SERVER_STARTUP_TIMEOUT = 120 # seconds


def PathToTestFile( *args ):
  dir_of_current_script = os.path.dirname( os.path.abspath( __file__ ) )
  return os.path.join( dir_of_current_script, 'testdata', *args )


def setUpPackage():
  """Initializes the ycmd server as a WebTest application that will be shared
  by all tests using the SharedYcmd decorator in this package. Additional
  configuration that is common to these tests, like starting a semantic
  subserver, should be done here."""
  global shared_app

  shared_app = SetUpApp()
  # By default, we use the eclipse project for convenience. This means we don't
  # have to @IsolatedYcmdInDirectory( DEFAULT_PROJECT_DIR ) for every test
  with IgnoreExtraConfOutsideTestsFolder():
    StartJavaCompleterServerInDirectory( shared_app,
                                         PathToTestFile( DEFAULT_PROJECT_DIR ) )


def tearDownPackage():
  """Cleans up the tests using the SharedYcmd decorator in this package. It is
  executed once after running all the tests in the package."""
  global shared_app

  StopCompleterServer( shared_app, 'java' )


def StartJavaCompleterServerInDirectory( app, directory ):
  app.post_json( '/event_notification',
                 BuildRequest(
                   filepath = os.path.join( directory, 'test.java' ),
                   event_name = 'FileReadyToParse',
                   filetype = 'java' ) )
  WaitUntilCompleterServerReady( shared_app, 'java', SERVER_STARTUP_TIMEOUT )


def SharedYcmd( test ):
  """Defines a decorator to be attached to tests of this package. This decorator
  passes the shared ycmd application as a parameter.

  Do NOT attach it to test generators but directly to the yielded tests."""
  global shared_app

  @functools.wraps( test )
  def Wrapper( *args, **kwargs ):
    ClearCompletionsCache()
    with IgnoreExtraConfOutsideTestsFolder():
      return test( shared_app, *args, **kwargs )
  return Wrapper


def IsolatedYcmd( custom_options = {} ):
  """Defines a decorator to be attached to tests of this package. This decorator
  passes a unique ycmd application as a parameter. It should be used on tests
  that change the server state in a irreversible way (ex: a semantic subserver
  is stopped or restarted) or expect a clean state (ex: no semantic subserver
  started, no .ycm_extra_conf.py loaded, etc).

  Do NOT attach it to test generators but directly to the yielded tests."""
  def Decorator( test ):
    @functools.wraps( test )
    def Wrapper( *args, **kwargs ):
      with IsolatedApp( custom_options ) as app:
        try:
          test( app, *args, **kwargs )
        finally:
          StopCompleterServer( app, 'java' )
    return Wrapper
  return Decorator


class PollForMessagesTimeoutException( Exception ):
  pass


def PollForMessages( app, request_data, timeout = 30 ):
  expiration = time.time() + timeout
  while True:
    if time.time() > expiration:
      raise PollForMessagesTimeoutException(
        'Waited for diagnostics to be ready for {0} seconds, aborting.'.format(
          timeout ) )

    default_args = {
      'filetype'  : 'java',
      'line_num'  : 1,
      'column_num': 1,
    }
    args = dict( default_args )
    args.update( request_data )

    response = app.post_json( '/receive_messages', BuildRequest( **args ) ).json

    print( 'poll response: {0}'.format( pformat( response ) ) )

    if isinstance( response, bool ):
      if not response:
        raise RuntimeError( 'The message poll was aborted by the server' )
    elif isinstance( response, list ):
      for message in response:
        yield message
    else:
      raise AssertionError( 'Message poll response was wrong type: {0}'.format(
        type( response ).__name__ ) )

    time.sleep( 0.25 )
