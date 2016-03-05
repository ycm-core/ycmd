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

import functools
import os
import time

from ycmd import handlers
from ycmd.tests.test_utils import BuildRequest, SetUpApp

shared_app = None


def PathToTestFile( *args ):
  dir_of_current_script = os.path.dirname( os.path.abspath( __file__ ) )
  return os.path.join( dir_of_current_script, 'testdata', *args )


def WaitUntilJediHTTPServerReady( app ):
  retries = 100

  while retries > 0:
    result = app.get( '/ready', { 'subserver': 'python' } ).json
    if result:
      return

    time.sleep( 0.2 )
    retries = retries - 1

  raise RuntimeError( "Timeout waiting for JediHTTP" )


def StopJediHTTPServer( app ):
  # We don't actually start a JediHTTP server on every test, so we just
  # ignore errors when stopping the server
  app.post_json( '/run_completer_command',
                 BuildRequest( completer_target = 'filetype_default',
                               command_arguments = [ 'StopServer' ],
                               filetype = 'python' ),
                 expect_errors = True )


def setUpPackage():
  global shared_app

  shared_app = SetUpApp()

  WaitUntilJediHTTPServerReady( shared_app )


def tearDownPackage():
  global shared_app

  StopJediHTTPServer( shared_app )


def Shared( function ):
  global shared_app

  @functools.wraps( function )
  def Wrapper( *args, **kwargs ):
    return function( shared_app, *args, **kwargs )
  return Wrapper


def Isolated( function ):
  @functools.wraps( function )
  def Wrapper( *args, **kwargs ):
    old_server_state = handlers._server_state

    try:
      function( SetUpApp(), *args, **kwargs )
    finally:
      handlers._server_state = old_server_state
  return Wrapper
