# Copyright (C) 2016-2021 ycmd contributors
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
import time
from pprint import pformat

from ycmd.tests.test_utils import ( BuildRequest,
                                    ClearCompletionsCache,
                                    IgnoreExtraConfOutsideTestsFolder,
                                    IsolatedApp,
                                    PollForMessagesTimeoutException,
                                    SetUpApp,
                                    StopCompleterServer,
                                    WaitUntilCompleterServerReady )

shared_app = None


def setUpModule():
  global shared_app
  shared_app = SetUpApp()
  with IgnoreExtraConfOutsideTestsFolder():
    StartRustCompleterServerInDirectory( shared_app,
                                         PathToTestFile( 'common' ) )


def tearDownModule():
  StopCompleterServer( shared_app, 'rust' )


def StartRustCompleterServerInDirectory( app, directory ):
  app.post_json( '/event_notification',
                 BuildRequest( filepath = os.path.join( directory,
                                                        'src',
                                                        'main.rs' ),
                               event_name = 'FileReadyToParse',
                               filetype = 'rust' ) )
  WaitUntilCompleterServerReady( app, 'rust' )


def PollForMessages( app, request_data, timeout = 60 ):
  expiration = time.time() + timeout
  while True:
    if time.time() > expiration:
      raise PollForMessagesTimeoutException( 'Waited for diagnostics to be '
        f'ready for { timeout } seconds, aborting.' )

    default_args = {
      'line_num'  : 1,
      'column_num': 1,
    }
    args = dict( default_args )
    args.update( request_data )

    response = app.post_json( '/receive_messages', BuildRequest( **args ) ).json

    print( f'poll response: { pformat( response ) }' )

    if isinstance( response, bool ):
      if not response:
        raise RuntimeError( 'The message poll was aborted by the server' )
    elif isinstance( response, list ):
      return response
    else:
      raise AssertionError(
        f'Message poll response was wrong type: { type( response ).__name__ }' )

    time.sleep( 0.25 )


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
          StopCompleterServer( app, 'rust' )
    return Wrapper
  return Decorator


def PathToTestFile( *args ):
  dir_of_current_script = os.path.dirname( os.path.abspath( __file__ ) )
  return os.path.join( dir_of_current_script, 'testdata', *args )
