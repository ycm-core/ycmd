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

from hamcrest import assert_that, contains_exactly, equal_to, has_entry
from unittest.mock import patch
from unittest import TestCase
import contextlib
from pathlib import Path

from ycmd.completers.language_server.language_server_completer import (
    LanguageServerConnectionTimeout )
from ycmd.tests.rust import ( PathToTestFile,
                              IsolatedYcmd,
                              StartRustCompleterServerInDirectory )
from ycmd.tests.test_utils import ( BuildRequest,
                                    MockProcessTerminationTimingOut,
                                    WaitUntilCompleterServerReady,
                                    TemporaryTestDir )

from ycmd import handlers


def AssertRustCompleterServerIsRunning( app, is_running ):
  request_data = BuildRequest( filetype = 'rust' )
  assert_that( app.post_json( '/debug_info', request_data ).json,
               has_entry(
                 'completer',
                 has_entry( 'servers', contains_exactly(
                   has_entry( 'is_running', is_running )
                 ) )
               ) )


class ServerManagementTest( TestCase ):
  @IsolatedYcmd()
  def test_ServerManagement_RestartServer( self, app ):
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


  @IsolatedYcmd()
  @patch( 'shutil.rmtree', side_effect = OSError )
  @patch( 'ycmd.utils.WaitUntilProcessIsTerminated',
          MockProcessTerminationTimingOut )
  def test_ServerManagement_CloseServer_Unclean( self, app, *args ):
    StartRustCompleterServerInDirectory( app,
                                         PathToTestFile( 'common', 'src' ) )

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


  @IsolatedYcmd()
  def test_ServerManagement_StopServerTwice( self, app ):
    StartRustCompleterServerInDirectory( app,
                                         PathToTestFile( 'common', 'src' ) )

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


  @IsolatedYcmd()
  def test_ServerManagement_StartServer_Fails( self, app ):
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


@contextlib.contextmanager
def TemporaryProjectLayout( project_files ):
  import os
  with TemporaryTestDir() as project_dir:
    project_dir_path = Path( project_dir )
    for file, contents in project_files.items():
      file = project_dir_path / file
      os.makedirs( file.parent, exist_ok = True )
      file.write_text( contents )
    yield project_dir_path


class ProjectDetectionTest( TestCase ):
  @IsolatedYcmd()
  def test_ProjectDetection_CargoTomlFiles_None( self, app ):
    with TemporaryProjectLayout( {
      'src/main.rs': '',
      'src/foo/main.rs': '',
      'foo/main.rs': '',
    } ) as project_dir:
      StartRustCompleterServerInDirectory( app, project_dir )
      completer = handlers._server_state.GetFiletypeCompleter( [ 'rust' ] )
      assert_that(
        completer.GetWorkspaceForFilepath( project_dir / 'src/main.rs',
                                           strict=True ),
        equal_to( None )
      )
      assert_that(
        completer.GetWorkspaceForFilepath( project_dir / 'src/foo/main.rs',
                                           strict=True ),
        equal_to( None )
      )
      assert_that(
        completer.GetWorkspaceForFilepath( project_dir / 'foo/main.rs',
                                           strict=True ),
        equal_to( None )
      )
      assert_that(
        completer.GetWorkspaceForFilepath( project_dir / 'src/main.rs',
                                           strict=False ),
        equal_to( str( project_dir / 'src' ) )
      )
      assert_that(
        completer.GetWorkspaceForFilepath( project_dir / 'src/foo/main.rs',
                                           strict=False ),
        equal_to( str( project_dir / 'src' ) )
      )
      assert_that(
        completer.GetWorkspaceForFilepath( project_dir / 'foo/main.rs',
                                           strict=False ),
        equal_to( str( project_dir / 'src' ) )
      )

  @IsolatedYcmd()
  def test_ProjectDetection_CargoTomlFiles_Justone( self, app ):
    with TemporaryProjectLayout( {
      'Cargo.toml': '',
      'src/main.rs': '',
      'src/foo/main.rs': '',
      'foo/main.rs': '',
    } ) as project_dir:
      StartRustCompleterServerInDirectory( app, project_dir )
      completer = handlers._server_state.GetFiletypeCompleter( [ 'rust' ] )
      assert_that(
        completer.GetWorkspaceForFilepath( project_dir / 'src/main.rs' ),
        equal_to( str( project_dir ) )
      )
      assert_that(
        completer.GetWorkspaceForFilepath( project_dir / 'src/foo/main.rs' ),
        equal_to( str( project_dir ) )
      )
      assert_that(
        completer.GetWorkspaceForFilepath( project_dir / 'foo/main.rs' ),
        equal_to( str( project_dir ) )
      )

  @IsolatedYcmd()
  def test_ProjectDetection_CargoTomlFiles_Nogaps( self, app ):
    with TemporaryProjectLayout( {
      'Cargo.toml': '',
      'src/main.rs': '',
      'src/Cargo.toml': '',
      'src/foo/main.rs': '',
      'src/foo/Cargo.toml': '',
    } ) as project_dir:
      StartRustCompleterServerInDirectory( app, project_dir )
      completer = handlers._server_state.GetFiletypeCompleter( [ 'rust' ] )
      assert_that(
        completer.GetWorkspaceForFilepath( project_dir / 'src/main.rs' ),
        equal_to( str( project_dir ) )
      )
      assert_that(
        completer.GetWorkspaceForFilepath( project_dir / 'src/foo/main.rs' ),
        equal_to( str( project_dir ) )
      )

  @IsolatedYcmd()
  def test_ProjectDetection_CargoTomlFiles_Gaps( self, app ):
    # This result is not ideal, but better in other tests/cases below
    # This is the "historical" behaviour
    with TemporaryProjectLayout( {
      'Cargo.toml': '',
      'src/foo/main.rs': '',
      'src/foo/Cargo.toml': '',
      'src/bar/main.rs': '',
      'src/bar/Cargo.toml': '',
    } ) as project_dir:
      StartRustCompleterServerInDirectory( app, project_dir )
      completer = handlers._server_state.GetFiletypeCompleter( [ 'rust' ] )
      assert_that(
        completer.GetWorkspaceForFilepath( project_dir / 'src/foo/main.rs' ),
        equal_to( str( project_dir / 'src' / 'foo' ) )
      )
      assert_that(
        completer.GetWorkspaceForFilepath( project_dir / 'src/bar/main.rs' ),
        equal_to( str( project_dir / 'src' / 'bar' ) )
      )


  @IsolatedYcmd()
  def test_ProjectDetection_CargoLockFiles( self, app ):
    with self.subTest( 'justone' ):
      with TemporaryProjectLayout( {
        'Cargo.lock': '',
        'src/main.rs': '',
        'src/Cargo.toml': '',
        'src/foo/main.rs': '',
        'src/foo/Cargo.toml': '',
      } ) as project_dir:
        StartRustCompleterServerInDirectory( app, project_dir )
        completer = handlers._server_state.GetFiletypeCompleter( [ 'rust' ] )
        assert_that(
          completer.GetWorkspaceForFilepath( project_dir / 'src/main.rs' ),
          equal_to( str( project_dir ) )
        )
        assert_that(
          completer.GetWorkspaceForFilepath( project_dir / 'src/foo/main.rs' ),
          equal_to( str( project_dir ) )
        )


  @IsolatedYcmd()
  def test_ProjectDetection_LockPrecidenceOverToml( self, app ):
    pass

  @IsolatedYcmd()
  def test_ProjectDetection_ManualProjectOverrideWithinPath( self, app ):
    pass

  @IsolatedYcmd()
  def test_ProjectDetection_ManualProjectIgnoredOutside( self, app ):
    pass
