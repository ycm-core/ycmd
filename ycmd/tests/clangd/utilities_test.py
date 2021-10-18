# Copyright (C) 2021      ycmd contributors
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

"""This test is for utilities used in clangd."""

from unittest.mock import patch
from unittest import TestCase
from hamcrest import assert_that, equal_to
from ycmd import handlers
from ycmd.completers.cpp import clangd_completer
from ycmd.completers.language_server.language_server_completer import (
    LanguageServerConnectionTimeout )
from ycmd.tests.clangd import IsolatedYcmd, PathToTestFile
from ycmd.tests.test_utils import BuildRequest
from ycmd.user_options_store import DefaultOptions


class MockPopen:
  stdin = None
  stdout = None
  pid = 0

  def communicate( self ):
    return ( bytes(), None )


class UtilitiesTest( TestCase ):
  def test_ClangdCompleter_GetClangdCommand_NoCustomBinary( self ):
    user_options = DefaultOptions()

    # Supported binary in third_party.
    THIRD_PARTY = '/third_party/clangd'
    clangd_completer.CLANGD_COMMAND = clangd_completer.NOT_CACHED
    with patch( 'ycmd.completers.cpp.clangd_completer.GetThirdPartyClangd',
                return_value = THIRD_PARTY ):
      assert_that( clangd_completer.GetClangdCommand( user_options )[ 0 ],
                   equal_to( THIRD_PARTY ) )
      # With args
      clangd_completer.CLANGD_COMMAND = clangd_completer.NOT_CACHED
      CLANGD_ARGS = [ "1", "2", "3" ]
      user_options[ 'clangd_args' ] = CLANGD_ARGS
      assert_that( clangd_completer.GetClangdCommand( user_options )[ 1:4 ],
                   equal_to( CLANGD_ARGS ) )

    # No supported binary in third_party.
    clangd_completer.CLANGD_COMMAND = clangd_completer.NOT_CACHED
    with patch( 'ycmd.completers.cpp.clangd_completer.GetThirdPartyClangd',
                return_value = None ):
      assert_that( clangd_completer.GetClangdCommand( user_options ),
                   equal_to( None ) )

    clangd_completer.CLANGD_COMMAND = clangd_completer.NOT_CACHED


  @patch( 'ycmd.completers.cpp.clangd_completer.FindExecutable',
          lambda exe: exe )
  def test_ClangdCompleter_GetClangdCommand_CustomBinary( self ):
    CLANGD_PATH = '/test/clangd'
    user_options = DefaultOptions()
    user_options[ 'clangd_binary_path' ] = CLANGD_PATH
    # Supported version.
    with patch( 'ycmd.completers.cpp.clangd_completer.CheckClangdVersion',
                return_value = True ):
      clangd_completer.CLANGD_COMMAND = clangd_completer.NOT_CACHED
      assert_that( clangd_completer.GetClangdCommand( user_options )[ 0 ],
                   equal_to( CLANGD_PATH ) )

      # No Clangd binary in the given path.
      with patch( 'ycmd.completers.cpp.clangd_completer.FindExecutable',
                  return_value = None ):
        clangd_completer.CLANGD_COMMAND = clangd_completer.NOT_CACHED
        assert_that( clangd_completer.GetClangdCommand( user_options ),
                     equal_to( None ) )

    # Unsupported version.
    with patch( 'ycmd.completers.cpp.clangd_completer.CheckClangdVersion',
                return_value = False ):
      # Never fall back to the third-party Clangd.
      clangd_completer.CLANGD_COMMAND = clangd_completer.NOT_CACHED
      assert_that( clangd_completer.GetClangdCommand( user_options ),
                   equal_to( None ) )

    clangd_completer.CLANGD_COMMAND = clangd_completer.NOT_CACHED


  @patch( 'ycmd.completers.cpp.clangd_completer.GetVersion',
          side_effect = [ None,
                          ( 5, 0, 0 ),
                          clangd_completer.MIN_SUPPORTED_VERSION,
                          ( 13, 0, 0 ),
                          ( 13, 10, 10 ),
                          ( 100, 100, 100 ) ] )
  def test_ClangdCompleter_CheckClangdVersion( *args ):
    assert_that( clangd_completer.CheckClangdVersion( 'clangd' ),
                  equal_to( True ) )
    assert_that( clangd_completer.CheckClangdVersion( 'clangd' ),
                 equal_to( False ) )
    assert_that( clangd_completer.CheckClangdVersion( 'clangd' ),
                 equal_to( True ) )
    assert_that( clangd_completer.CheckClangdVersion( 'clangd' ),
                 equal_to( True ) )
    assert_that( clangd_completer.CheckClangdVersion( 'clangd' ),
                 equal_to( True ) )
    assert_that( clangd_completer.CheckClangdVersion( 'clangd' ),
                 equal_to( True ) )


  def test_ClangdCompleter_ShouldEnableClangdCompleter( self ):
    user_options = DefaultOptions()

    # Clangd not in third_party (or an old version).
    with patch( 'ycmd.completers.cpp.clangd_completer.GetThirdPartyClangd',
                return_value = None ):
      # Default.
      clangd_completer.CLANGD_COMMAND = clangd_completer.NOT_CACHED
      assert_that( clangd_completer.ShouldEnableClangdCompleter( user_options ),
                   equal_to( False ) )

      # Found supported binary.
      with patch( 'ycmd.completers.cpp.clangd_completer.GetClangdCommand',
                  return_value = [ 'clangd' ] ):
        assert_that(
            clangd_completer.ShouldEnableClangdCompleter( user_options ),
            equal_to( True ) )
      # No supported binary found.
      with patch( 'ycmd.completers.cpp.clangd_completer.GetClangdCommand',
                  return_value = None ):
        assert_that(
            clangd_completer.ShouldEnableClangdCompleter( user_options ),
            equal_to( False ) )

      # Clangd is disabled.
      user_options[ 'use_clangd' ] = 0
      assert_that(
          clangd_completer.ShouldEnableClangdCompleter( user_options ),
          equal_to( False ) )

    user_options = DefaultOptions()

    # Clangd in third_party with a supported version.
    with patch( 'ycmd.completers.cpp.clangd_completer.GetThirdPartyClangd',
                return_value = 'third_party_clangd' ):
      # Default.
      clangd_completer.CLANGD_COMMAND = clangd_completer.NOT_CACHED
      assert_that( clangd_completer.ShouldEnableClangdCompleter( user_options ),
                   equal_to( True ) )

      # Enabled.
      user_options[ 'use_clangd' ] = 1
      # Found supported binary.
      with patch( 'ycmd.completers.cpp.clangd_completer.GetClangdCommand',
                  return_value = [ 'clangd' ] ):
        assert_that(
            clangd_completer.ShouldEnableClangdCompleter( user_options ),
            equal_to( True ) )
      # No supported binary found.
      with patch( 'ycmd.completers.cpp.clangd_completer.GetClangdCommand',
                  return_value = None ):
        assert_that(
            clangd_completer.ShouldEnableClangdCompleter( user_options ),
            equal_to( False ) )

      # Disabled.
      user_options[ 'use_clangd' ] = 0
      assert_that( clangd_completer.ShouldEnableClangdCompleter( user_options ),
                   equal_to( False ) )


  @patch( 'subprocess.Popen', return_value = MockPopen() )
  def test_ClangdCompleter_GetVersion( self, mock_popen ):
    assert_that( clangd_completer.GetVersion( '' ),
                 equal_to( None ) )
    mock_popen.assert_called()


  def test_ClangdCompleter_ParseClangdVersion( self ):
    cases = [
      ( 'clangd version 10.0.0 (https://github.com/llvm/llvm-project.git '
        '45be5e477e9216363191a8ac9123bea4585cf14f)', ( 10, 0, 0 ) ),
      ( 'clangd version 8.0.0-3 (tags/RELEASE_800/final)', ( 8, 0, 0 ) ),
      ( 'LLVM (http://llvm.org/):\nLLVM version 6.0.0\n'
        'Optimized build.\nDefault target: x86_64-unknown-linux-gnu\n'
        'Host CPU: haswell', ( 6, 0, 0 ) ),
    ]

    for version_str, expected in cases:
      assert_that( clangd_completer.ParseClangdVersion( version_str ),
                   equal_to( expected ) )


  @IsolatedYcmd()
  def test_ClangdCompleter_ShutdownFail( self, app ):
    completer = handlers._server_state.GetFiletypeCompleter( [ 'cpp' ] )
    with patch.object( completer, 'ShutdownServer',
                       side_effect = Exception ) as shutdown_server:
      completer._server_handle = MockPopen()
      with patch.object( completer, 'ServerIsHealthy', return_value = True ):
        completer.Shutdown()
        shutdown_server.assert_called()


  def test_ClangdCompleter_GetThirdParty( self ):
    with patch( 'ycmd.completers.cpp.clangd_completer.GetExecutable',
                return_value = None ):
      assert_that( clangd_completer.GetThirdPartyClangd(),
                   equal_to( None ) )

    with patch( 'ycmd.completers.cpp.clangd_completer.GetExecutable',
                return_value = '/third_party/clangd' ):
      with patch( 'ycmd.completers.cpp.clangd_completer.CheckClangdVersion',
                  return_value = True ):
        assert_that( clangd_completer.GetThirdPartyClangd(),
                     equal_to( '/third_party/clangd' ) )

      with patch( 'ycmd.completers.cpp.clangd_completer.CheckClangdVersion',
                  return_value = False ):
        assert_that( clangd_completer.GetThirdPartyClangd(),
                     equal_to( None ) )


  @IsolatedYcmd()
  def test_ClangdCompleter_StartServer_Fails( self, app ):
    with patch( 'ycmd.completers.language_server.language_server_completer.'
                'LanguageServerConnection.AwaitServerConnection',
                side_effect = LanguageServerConnectionTimeout ):
      with patch( 'ycmd.completers.cpp.clangd_completer.ClangdCompleter.'
                  'ShutdownServer' ) as shutdown:
        resp = app.post_json( '/event_notification',
                       BuildRequest(
                         event_name = 'FileReadyToParse',
                         filetype = 'cpp',
                         filepath = PathToTestFile( 'foo.cc' ),
                         contents = ""
                       ) )
        assert_that( resp.status_code, equal_to( 200 ) )
        shutdown.assert_called()
