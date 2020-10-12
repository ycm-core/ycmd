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

from hamcrest import assert_that, contains_exactly, equal_to, has_entry
from unittest.mock import patch

from ycmd.completers.language_server.language_server_completer import (
    LanguageServerConnectionTimeout )
from ycmd.tests.rust import ( PathToTestFile,
                              IsolatedYcmd,
                              StartRustCompleterServerInDirectory )
from ycmd.tests.test_utils import ( BuildRequest,
                                    MockProcessTerminationTimingOut,
                                    WaitUntilCompleterServerReady )


def AssertRustCompleterServerIsRunning( app, is_running ):
  request_data = BuildRequest( filetype = 'rust' )
  assert_that( app.post_json( '/debug_info', request_data ).json,
               has_entry(
                 'completer',
                 has_entry( 'servers', contains_exactly(
                   has_entry( 'is_running', is_running )
                 ) )
               ) )


@IsolatedYcmd
def ServerManagement_RestartServer_test( app ):
  filepath = PathToTestFile( 'common', 'src', 'main.rs' )
  StartRustCompleterServerInDirectory( app, filepath )

  AssertRustCompleterServerIsRunning( app, True )

  app.post_json(
    '/run_completer_command',
    BuildRequest(
      filepath = filepath,
      filetype = 'rust',
      command_arguments = [ 'RestartServer' ],
    ),
  )

  WaitUntilCompleterServerReady( app, 'rust' )

  AssertRustCompleterServerIsRunning( app, True )


@IsolatedYcmd
@patch( 'shutil.rmtree', side_effect = OSError )
@patch( 'ycmd.utils.WaitUntilProcessIsTerminated',
        MockProcessTerminationTimingOut )
def ServerManagement_CloseServer_Unclean_test( wait_until, app ):
  StartRustCompleterServerInDirectory( app, PathToTestFile( 'common', 'src' ) )

  app.post_json(
    '/run_completer_command',
    BuildRequest(
      filetype = 'rust',
      command_arguments = [ 'StopServer' ]
    )
  )

  request_data = BuildRequest( filetype = 'rust' )
  assert_that( app.post_json( '/debug_info', request_data ).json,
               has_entry(
                 'completer',
                 has_entry( 'servers', contains_exactly(
                   has_entry( 'is_running', False )
                 ) )
               ) )


@IsolatedYcmd
def ServerManagement_StopServerTwice_test( app ):
  StartRustCompleterServerInDirectory( app, PathToTestFile( 'common', 'src' ) )

  app.post_json(
    '/run_completer_command',
    BuildRequest(
      filetype = 'rust',
      command_arguments = [ 'StopServer' ],
    ),
  )

  AssertRustCompleterServerIsRunning( app, False )

  # Stopping a stopped server is a no-op
  app.post_json(
    '/run_completer_command',
    BuildRequest(
      filetype = 'rust',
      command_arguments = [ 'StopServer' ],
    ),
  )

  AssertRustCompleterServerIsRunning( app, False )


@IsolatedYcmd
def ServerManagement_StartServer_Fails_test( app ):
  with patch( 'ycmd.completers.language_server.language_server_completer.'
              'LanguageServerConnection.AwaitServerConnection',
              side_effect = LanguageServerConnectionTimeout ):
    resp = app.post_json( '/event_notification',
                   BuildRequest(
                     event_name = 'FileReadyToParse',
                     filetype = 'rust',
                     filepath = PathToTestFile( 'common', 'src', 'main.rs' ),
                     contents = ""
                   ) )

    assert_that( resp.status_code, equal_to( 200 ) )

    request_data = BuildRequest( filetype = 'rust' )
    assert_that( app.post_json( '/debug_info', request_data ).json,
                 has_entry(
                   'completer',
                   has_entry( 'servers', contains_exactly(
                     has_entry( 'is_running', False )
                   ) )
                 ) )


def Dummy_test():
  # Workaround for https://github.com/pytest-dev/pytest-rerunfailures/issues/51
  assert True
