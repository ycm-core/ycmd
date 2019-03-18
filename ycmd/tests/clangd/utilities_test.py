# Copyright (C) 2011-2012 Google Inc.
#               2018      ycmd contributors
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

"""This test is for utilites used in clangd."""

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import

from nose.tools import eq_
from mock import patch
from ycmd import handlers
from ycmd.completers.cpp import clangd_completer
from ycmd.completers.language_server.language_server_completer import (
    LanguageServerConnectionTimeout )
from ycmd.tests.clangd import IsolatedYcmd, PathToTestFile
from ycmd.tests.test_utils import BuildRequest
from ycmd.user_options_store import DefaultOptions


def _TupleToLSPRange( tuple ):
  return { 'line': tuple[ 0 ], 'character': tuple[ 1 ] }


def _Check_Distance( point, start, end, expected ):
  point = _TupleToLSPRange( point )
  start = _TupleToLSPRange( start )
  end = _TupleToLSPRange( end )
  range = { 'start': start, 'end': end }
  result = clangd_completer.DistanceOfPointToRange( point, range )
  eq_( result, expected )


def ClangdCompleter_DistanceOfPointToRange_SingleLineRange_test():
  # Point to the left of range.
  _Check_Distance( ( 0, 0 ), ( 0, 2 ), ( 0, 5 ) , 2 )
  # Point inside range.
  _Check_Distance( ( 0, 4 ), ( 0, 2 ), ( 0, 5 ) , 0 )
  # Point to the right of range.
  _Check_Distance( ( 0, 8 ), ( 0, 2 ), ( 0, 5 ) , 3 )


def ClangdCompleter_DistanceOfPointToRange_MultiLineRange_test():
  # Point to the left of range.
  _Check_Distance( ( 0, 0 ), ( 0, 2 ), ( 3, 5 ) , 2 )
  # Point inside range.
  _Check_Distance( ( 1, 4 ), ( 0, 2 ), ( 3, 5 ) , 0 )
  # Point to the right of range.
  _Check_Distance( ( 3, 8 ), ( 0, 2 ), ( 3, 5 ) , 3 )


def ClangdCompleter_GetClangdCommand_NoCustomBinary_test():
  user_options = DefaultOptions()

  # Supported binary in third_party.
  THIRD_PARTY = '/third_party/clangd'
  clangd_completer.CLANGD_COMMAND = clangd_completer.NOT_CACHED
  with patch( 'ycmd.completers.cpp.clangd_completer.GetThirdPartyClangd',
              return_value = THIRD_PARTY ):
    eq_( clangd_completer.GetClangdCommand( user_options )[ 0 ],
         THIRD_PARTY )
    # With args
    clangd_completer.CLANGD_COMMAND = clangd_completer.NOT_CACHED
    CLANGD_ARGS = [ "1", "2", "3" ]
    user_options[ 'clangd_args' ] = CLANGD_ARGS
    eq_( clangd_completer.GetClangdCommand( user_options )[ 1:4 ],
         CLANGD_ARGS )

  # No supported binary in third_party.
  clangd_completer.CLANGD_COMMAND = clangd_completer.NOT_CACHED
  with patch( 'ycmd.completers.cpp.clangd_completer.GetThirdPartyClangd',
              return_value = None ):
    eq_( clangd_completer.GetClangdCommand( user_options ), None )

  clangd_completer.CLANGD_COMMAND = clangd_completer.NOT_CACHED


@patch( 'ycmd.completers.cpp.clangd_completer.FindExecutable', lambda exe: exe )
def ClangdCompleter_GetClangdCommand_CustomBinary_test():
  CLANGD_PATH = '/test/clangd'
  user_options = DefaultOptions()
  user_options[ 'clangd_binary_path' ] = CLANGD_PATH
  # Supported version.
  with patch( 'ycmd.completers.cpp.clangd_completer.CheckClangdVersion',
              return_value = True ):
    clangd_completer.CLANGD_COMMAND = clangd_completer.NOT_CACHED
    eq_( clangd_completer.GetClangdCommand( user_options )[ 0 ],
         CLANGD_PATH )

    # No Clangd binary in the given path.
    with patch( 'ycmd.completers.cpp.clangd_completer.FindExecutable',
                return_value = None ):
      clangd_completer.CLANGD_COMMAND = clangd_completer.NOT_CACHED
      eq_( clangd_completer.GetClangdCommand( user_options ), None )

  # Unsupported version.
  with patch( 'ycmd.completers.cpp.clangd_completer.CheckClangdVersion',
              return_value = False ):
    # Never fall back to the third-party Clangd.
    clangd_completer.CLANGD_COMMAND = clangd_completer.NOT_CACHED
    eq_( clangd_completer.GetClangdCommand( user_options ), None )

  clangd_completer.CLANGD_COMMAND = clangd_completer.NOT_CACHED


@patch( 'ycmd.completers.cpp.clangd_completer.GetVersion',
        side_effect = [ None,
                        '5.0.0',
                        clangd_completer.MIN_SUPPORTED_VERSION ] )
def ClangdCompleter_CheckClangdVersion_test( *args ):
  eq_( clangd_completer.CheckClangdVersion( 'clangd' ), True )
  eq_( clangd_completer.CheckClangdVersion( 'clangd' ), False )
  eq_( clangd_completer.CheckClangdVersion( 'clangd' ), True )


def ClangdCompleter_ShouldEnableClangdCompleter_test():
  user_options = DefaultOptions()

  # Clangd not in third_party (or an old version).
  with patch( 'ycmd.completers.cpp.clangd_completer.GetThirdPartyClangd',
              return_value = None ):
    # Default.
    clangd_completer.CLANGD_COMMAND = clangd_completer.NOT_CACHED
    eq_( clangd_completer.ShouldEnableClangdCompleter( user_options ), False )

    # Found supported binary.
    with patch( 'ycmd.completers.cpp.clangd_completer.GetClangdCommand',
                return_value = [ 'clangd' ] ):
      eq_( clangd_completer.ShouldEnableClangdCompleter( user_options ), True )
    # No supported binary found.
    with patch( 'ycmd.completers.cpp.clangd_completer.GetClangdCommand',
                return_value = None ):
      eq_( clangd_completer.ShouldEnableClangdCompleter( user_options ), False )

    # Clangd is disabled.
    user_options[ 'use_clangd' ] = 0
    eq_( clangd_completer.ShouldEnableClangdCompleter( user_options ), False )

  user_options = DefaultOptions()

  # Clangd in third_party with a supported version.
  with patch( 'ycmd.completers.cpp.clangd_completer.GetThirdPartyClangd',
              return_value = 'third_party_clangd' ):
    # Default.
    clangd_completer.CLANGD_COMMAND = clangd_completer.NOT_CACHED
    eq_( clangd_completer.ShouldEnableClangdCompleter( user_options ), True )

    # Enabled.
    user_options[ 'use_clangd' ] = 1
    # Found supported binary.
    with patch( 'ycmd.completers.cpp.clangd_completer.GetClangdCommand',
                return_value = [ 'clangd' ] ):
      eq_( clangd_completer.ShouldEnableClangdCompleter( user_options ), True )
    # No supported binary found.
    with patch( 'ycmd.completers.cpp.clangd_completer.GetClangdCommand',
                return_value = None ):
      eq_( clangd_completer.ShouldEnableClangdCompleter( user_options ), False )

    # Disabled.
    user_options[ 'use_clangd' ] = 0
    eq_( clangd_completer.ShouldEnableClangdCompleter( user_options ), False )


class MockPopen:
  stdin = None
  stdout = None
  pid = 0

  def communicate( self ):
    return ( bytes(), None )


@patch( 'subprocess.Popen', return_value = MockPopen() )
def ClangdCompleter_GetVersion_test( mock_popen ):
  eq_( clangd_completer.GetVersion( '' ), None )
  mock_popen.assert_called()


@IsolatedYcmd()
def ClangdCompleter_ShutdownFail_test( app ):
  completer = handlers._server_state.GetFiletypeCompleter( [ 'cpp' ] )
  with patch.object( completer, 'ShutdownServer',
                     side_effect = Exception ) as shutdown_server:
    completer._server_handle = MockPopen()
    with patch.object( completer, 'ServerIsHealthy', return_value = True ):
      completer.Shutdown()
      shutdown_server.assert_called()


def ClangdCompleter_GetThirdParty_test():
  with patch( 'ycmd.completers.cpp.clangd_completer.GetExecutable',
              return_value = None ):
    eq_( clangd_completer.GetThirdPartyClangd(), None )

  with patch( 'ycmd.completers.cpp.clangd_completer.GetExecutable',
              return_value = '/third_party/clangd' ):
    with patch( 'ycmd.completers.cpp.clangd_completer.CheckClangdVersion',
                return_value = True ):
      eq_( clangd_completer.GetThirdPartyClangd(), '/third_party/clangd' )

    with patch( 'ycmd.completers.cpp.clangd_completer.CheckClangdVersion',
                return_value = False ):
      eq_( clangd_completer.GetThirdPartyClangd(), None )


@IsolatedYcmd()
def ClangdCompleter_StartServer_Fails_test( app ):
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
      eq_( resp.status_code, 200 )
      shutdown.assert_called()
