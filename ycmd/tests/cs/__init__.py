# Copyright (C) 2016 ycmd contributors
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

from contextlib import contextmanager
import functools
import os
import time

from ycmd import handlers
from ycmd.tests.test_utils import BuildRequest, SetUpApp

shared_app = None
shared_filepaths = []


def PathToTestFile( *args ):
  dir_of_current_script = os.path.dirname( os.path.abspath( __file__ ) )
  return os.path.join( dir_of_current_script, 'testdata', *args )


def StartOmniSharpServer( app, filepath ):
  app.post_json( '/run_completer_command',
                 BuildRequest( completer_target = 'filetype_default',
                               command_arguments = [ "StartServer" ],
                               filepath = filepath,
                               filetype = 'cs' ) )


def StopOmniSharpServer( app, filepath ):
  app.post_json( '/run_completer_command',
                 BuildRequest( completer_target = 'filetype_default',
                               command_arguments = [ 'StopServer' ],
                               filepath = filepath,
                               filetype = 'cs' ) )


def WaitUntilOmniSharpServerReady( app, filepath ):
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
                            command_arguments = [ 'ServerIsRunning' ],
                            filepath = filepath,
                            filetype = 'cs' )
    result = app.post_json( '/run_completer_command', request ).json
    if not result:
      raise RuntimeError( "OmniSharp failed during startup." )
    time.sleep( 0.2 )
    retries = retries - 1

  if not success:
    raise RuntimeError( "Timeout waiting for OmniSharpServer" )


def setUpPackage():
  """Initializes the ycmd server as a WebTest application that will be shared
  by all tests using the SharedYcmd decorator in this package. Additional
  configuration that is common to these tests, like starting a semantic
  subserver, should be done here."""
  global shared_app

  shared_app = SetUpApp()
  shared_app.post_json(
    '/ignore_extra_conf_file',
    { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )


def tearDownPackage():
  """Cleans up the tests using the SharedYcmd decorator in this package. It is
  executed once after running all the tests in the package."""
  global shared_app, shared_filepaths

  for filepath in shared_filepaths:
    StopOmniSharpServer( shared_app, filepath )


@contextmanager
def WrapOmniSharpServer( app, filepath ):
  global shared_filepaths

  if filepath not in shared_filepaths:
    StartOmniSharpServer( app, filepath )
    shared_filepaths.append( filepath )
  WaitUntilOmniSharpServerReady( app, filepath )
  yield


def SharedYcmd( test ):
  """Defines a decorator to be attached to tests of this package. This decorator
  passes the shared ycmd application as a parameter.

  Do NOT attach it to test generators but directly to the yielded tests."""
  global shared_app

  @functools.wraps( test )
  def Wrapper( *args, **kwargs ):
    return test( shared_app, *args, **kwargs )
  return Wrapper


def IsolatedYcmd( test ):
  """Defines a decorator to be attached to tests of this package. This decorator
  passes a unique ycmd application as a parameter. It should be used on tests
  that change the server state in a irreversible way (ex: a semantic subserver
  is stopped or restarted) or expect a clean state (ex: no semantic subserver
  started, no .ycm_extra_conf.py loaded, etc).

  Do NOT attach it to test generators but directly to the yielded tests."""
  @functools.wraps( test )
  def Wrapper( *args, **kwargs ):
    old_server_state = handlers._server_state

    try:
      app = SetUpApp()
      app.post_json(
        '/ignore_extra_conf_file',
        { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
      test( app, *args, **kwargs )
    finally:
      handlers._server_state = old_server_state
  return Wrapper
