# Copyright (C) 2018 ycmd contributors
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
import json
import os

from hamcrest import assert_that
from nose.tools import eq_


from ycmd.tests.test_utils import ( ClearCompletionsCache,
                                    CombineRequest,
                                    IgnoreExtraConfOutsideTestsFolder,
                                    IsolatedApp,
                                    SetUpApp,
                                    StopCompleterServer,
                                    WaitUntilCompleterServerReady )
from ycmd.utils import ReadFile
from ycmd.completers.cpp import clangd_completer

shared_app = None


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


def tearDownPackage():
  global shared_app

  StopCompleterServer( shared_app, 'cpp' )


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
  started, no .ycm_extra_conf.py loaded, etc). Use the optional parameter
  |custom_options| to give additional options and/or override the default ones.

  Do NOT attach it to test generators but directly to the yielded tests.

  Example usage:

    from ycmd.tests.clang import IsolatedYcmd

    @IsolatedYcmd( { 'auto_trigger': 0 } )
    def CustomAutoTrigger_test( app ):
      ...
  """
  def Decorator( test ):
    @functools.wraps( test )
    def Wrapper( *args, **kwargs ):
      with IgnoreExtraConfOutsideTestsFolder():
        with IsolatedApp( custom_options ) as app:
          clangd_completer.CLANGD_COMMAND = clangd_completer.NOT_CACHED
          try:
            test( app, *args, **kwargs )
          finally:
            StopCompleterServer( app, 'cpp' )
    return Wrapper
  return Decorator


def RunAfterInitialized( app, test ):
  """Performs initialization of clangd server for the file contents specified in
  the |test| and optionally can run a test and check for its response.
  Since LSP servers do not start until initialization we need to send a
  FileReadyToParse request prior to any other request we will make.

  |test| consists of two parts a 'request' to be made and an optional 'expect'
  to perform a check on server's response.
  Request part must contain either a 'content' or 'filepath' element which
  either contains or points to the source code that will be sent to the server.
  In addition to that, if |test| also contain a 'route' element, then a
  follow-up request will be made to the server, with the same file contents and
  response of that request will be returned.
  Expect part, if specified, must contain two elements named 'response' and
  'data' which are used to check status code and data of the result received
  from server before returning them to the caller.

  Example usage:
    filepath = PathToTestFile( 'foo.cc' )
    request = { 'filepath': filepath,
                'filetype': 'cpp' }

    test = { 'request': request }
    RunAfterInitialized( app, test )
    ...
  """
  request = test[ 'request' ]
  contents = ( request[ 'contents' ] if 'contents' in request else
               ReadFile( request[ 'filepath' ] ) )
  response = app.post_json( '/event_notification',
                 CombineRequest( request, {
                   'event_name': 'FileReadyToParse',
                   'contents': contents,
                 } ),
                 expect_errors = True )
  WaitUntilCompleterServerReady( app, 'cpp' )

  if 'route' in test:
    expect_errors = 'expect' in test
    response = app.post_json( test[ 'route' ],
                              CombineRequest( request, {
                                'contents': contents
                              } ),
                              expect_errors = expect_errors )

  if 'expect' in test:
    print( "Completer response: {}".format( json.dumps( response.json,
                                                        indent = 2 ) ) )
    eq_( response.status_code, test[ 'expect' ][ 'response' ] )
    assert_that( response.json, test[ 'expect' ][ 'data' ] )
  return response.json
