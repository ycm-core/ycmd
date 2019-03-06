# Copyright (C) 2011-2019 ycmd contributors
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

from mock import patch
import psutil

from hamcrest import ( assert_that,
                       contains,
                       empty,
                       has_entries,
                       has_entry,
                       has_item )

from ycmd import handlers, utils
from ycmd.tests.clangd import ( IsolatedYcmd, PathToTestFile,
                                RunAfterInitialized )
from ycmd.tests.test_utils import ( BuildRequest,
                                    CompleterProjectDirectoryMatcher,
                                    MockProcessTerminationTimingOut,
                                    StopCompleterServer,
                                    WaitUntilCompleterServerReady )


def GetDebugInfo( app ):
  request_data = BuildRequest( filetype = 'cpp' )
  return app.post_json( '/debug_info', request_data ).json


def GetPid( app ):
  return GetDebugInfo( app )[ 'completer' ][ 'servers' ][ 0 ][ 'pid' ]


def StartClangd( app, filepath = PathToTestFile( 'basic.cpp' ) ):
  request_data = BuildRequest( filepath = filepath,
                               filetype = 'cpp' )
  test = { 'request': request_data }
  RunAfterInitialized( app, test )


def CheckStopped( app ):
  assert_that(
    GetDebugInfo( app ),
    has_entry( 'completer', has_entries( {
      'name': 'clangd',
      'servers': contains( has_entries( {
        'name': 'clangd',
        'pid': None,
        'is_running': False
      } ) ),
      'items': empty()
    } ) )
  )


@IsolatedYcmd()
def ServerManagement_StopServer_Clean_test( app ):
  StartClangd( app )
  StopCompleterServer( app, 'cpp', '' )
  CheckStopped( app )


@IsolatedYcmd()
@patch( 'os.remove', side_effect = OSError )
@patch( 'ycmd.utils.WaitUntilProcessIsTerminated',
        MockProcessTerminationTimingOut )
def ServerManagement_StopServer_Unclean_test( app, *args ):
  StartClangd( app )
  StopCompleterServer( app, 'cpp', '' )
  CheckStopped( app )


@IsolatedYcmd()
def ServerManagement_StopServer_Twice_test( app ):
  StartClangd( app )
  StopCompleterServer( app, 'cpp', '' )
  CheckStopped( app )
  StopCompleterServer( app, 'cpp', '' )
  CheckStopped( app )


@IsolatedYcmd()
def ServerManagement_StopServer_Killed_test( app ):
  StartClangd( app )
  process = psutil.Process( GetPid( app ) )
  process.terminate()
  process.wait( timeout = 5 )
  StopCompleterServer( app, 'cpp', '' )
  CheckStopped( app )


@IsolatedYcmd()
def ServerManagement_ServerDiesWhileShuttingDown_test( app ):
  StartClangd( app )
  process = psutil.Process( GetPid( app ) )
  completer = handlers._server_state.GetFiletypeCompleter( [ 'cpp' ] )

  # We issue a shutdown but make sure it never reaches server by mocking
  # WriteData in Connection. Then we kill the server and check shutdown still
  # succeeds.
  with patch.object( completer.GetConnection(), 'WriteData' ):
    stop_server_task = utils.StartThread( StopCompleterServer, app, 'cpp', '' )
    process.terminate()
    stop_server_task.join()

  CheckStopped( app )


@IsolatedYcmd()
def ServerManagement_ConnectionRaisesWhileShuttingDown_test( app ):
  StartClangd( app )
  process = psutil.Process( GetPid( app ) )
  completer = handlers._server_state.GetFiletypeCompleter( [ 'cpp' ] )

  # We issue a shutdown but make sure it never reaches server by mocking
  # WriteData in Connection. Then we kill the server and check shutdown still
  # succeeds.
  with patch.object( completer.GetConnection(), 'GetResponse',
                     side_effect = RuntimeError ):
    StopCompleterServer( app, 'cpp', '' )

  CheckStopped( app )
  if process.is_running():
    process.terminate()
    raise AssertionError( 'Termination failed' )


@IsolatedYcmd()
def ServerManagement_RestartServer_test( app ):
  StartClangd( app, PathToTestFile( 'basic.cpp' ) )

  assert_that(
    GetDebugInfo( app ),
    CompleterProjectDirectoryMatcher( PathToTestFile() ) )

  app.post_json(
    '/run_completer_command',
    BuildRequest(
      filepath = PathToTestFile( 'test-include', 'main.cpp' ),
      filetype = 'cpp',
      command_arguments = [ 'RestartServer' ],
    ),
  )

  WaitUntilCompleterServerReady( app, 'cpp' )

  assert_that(
    GetDebugInfo( app ),
    has_entry( 'completer', has_entries( {
      'name': 'clangd',
      'servers': contains( has_entries( {
        'name': 'clangd',
        'is_running': True,
        'extras': has_item( has_entries( {
          'key': 'Project Directory',
          'value': PathToTestFile( 'test-include' ),
        } ) )
      } ) )
    } ) )
  )
