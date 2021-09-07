# Copyright (C) 2014-2021 ycmd contributors
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

import os
from hamcrest import assert_that, contains_inanyorder, empty, is_not
from unittest.mock import patch
from unittest import TestCase

from ycmd.tests import IsolatedYcmd
from ycmd.tests.test_utils import ( BuildRequest,
                                    CurrentWorkingDirectory,
                                    CompletionEntryMatcher,
                                    WindowsOnly )
from ycmd.utils import GetCurrentDirectory, ToBytes

TEST_DIR = os.path.dirname( os.path.abspath( __file__ ) )
DATA_DIR = os.path.join( TEST_DIR,
                         'testdata',
                         'filename_completer',
                         'inner_dir' )
ROOT_FOLDER_COMPLETIONS = tuple(
  ( path, '[Dir]' if os.path.isdir( os.path.sep + path ) else '[File]' )
  for path in os.listdir( os.path.sep ) )
DRIVE = os.path.splitdrive( TEST_DIR )[ 0 ]
PATH_TO_TEST_FILE = os.path.join( DATA_DIR, 'test.cpp' )


def FilenameCompleter_Completion( app,
                                  contents,
                                  environ,
                                  filetype,
                                  completions ):
  completion_data = BuildRequest( contents = contents,
                                  filepath = PATH_TO_TEST_FILE,
                                  filetype = filetype,
                                  column_num = len( ToBytes( contents ) ) + 1 )
  if completions:
    completion_matchers = [ CompletionEntryMatcher( *completion )
                            for completion in completions ]
    expected_results = contains_inanyorder( *completion_matchers )
  else:
    expected_results = empty()

  with patch.dict( 'os.environ', environ ):
    results = app.post_json( '/completions',
                             completion_data ).json[ 'completions' ]

  assert_that( results, expected_results )


class FilenameCompleterTest( TestCase ):
  # A series of tests represented by tuples whose elements are:
  #  - the line to complete;
  #  - the environment variables;
  #  - the expected completions.
  @IsolatedYcmd( { 'max_num_candidates': 0 } )
  def test_FilenameCompleter_Completion( self, app ):
    test_cases = [
      ( '/',
        {},
        ROOT_FOLDER_COMPLETIONS ),
      ( '//',
        {},
        () ),
      ( 'const char* c = "/',
        {},
        ROOT_FOLDER_COMPLETIONS ),
      ( 'const char* c = "./',
        {},
        ( ( 'dir with spaces (x64)', '[Dir]' ),
          ( 'foo漢字.txt',           '[File]' ),
          ( 'test.cpp',              '[File]' ),
          ( 'test.hpp',              '[File]' ) ) ),
      ( 'const char* c = "./漢',
        {},
        ( ( 'foo漢字.txt', '[File]' ), ) ),
      ( 'const char* c = "./dir with spaces (x64)/',
        {},
        ( ( 'Qt',    '[Dir]' ),
          ( 'QtGui', '[Dir]' ) ) ),
      ( 'const char* c = "./dir with spaces (x64)//',
        {},
        ( ( 'Qt',    '[Dir]' ),
          ( 'QtGui', '[Dir]' ) ) ),
      ( 'const char* c = "../',
        {},
        ( ( 'inner_dir', '[Dir]' ),
          ( '∂†∫',       '[Dir]' ) ) ),
      ( 'const char* c = "../inner_dir/',
        {},
        ( ( 'dir with spaces (x64)', '[Dir]' ),
          ( 'foo漢字.txt',           '[File]' ),
          ( 'test.cpp',              '[File]' ),
          ( 'test.hpp',              '[File]' ) ) ),
      ( 'const char* c = "../inner_dir/dir with spaces (x64)/',
        {},
        ( ( 'Qt',    '[Dir]' ),
          ( 'QtGui', '[Dir]' ) ) ),
      ( 'const char* c = "~/',
        { 'HOME': DATA_DIR , 'USERPROFILE': DATA_DIR },
        ( ( 'dir with spaces (x64)', '[Dir]' ),
          ( 'foo漢字.txt',           '[File]' ),
          ( 'test.cpp',              '[File]' ),
          ( 'test.hpp',              '[File]' ) ) ),
      ( 'const char* c = "~/dir with spaces (x64)/',
        { 'HOME': DATA_DIR, 'USERPROFILE': DATA_DIR },
        ( ( 'Qt',    '[Dir]' ),
          ( 'QtGui', '[Dir]' ) ) ),
      ( 'const char* c = "~/dir with spaces (x64)/Qt/',
        { 'HOME': DATA_DIR, 'USERPROFILE': DATA_DIR },
        ( ( 'QtGui', '[File]' ), ) ),
      ( 'const char* c = "dir with spaces (x64)/',
        {},
        ( ( 'Qt',    '[Dir]' ),
          ( 'QtGui', '[Dir]' ) ) ),
      ( 'const char* c = "dir with spaces (x64)/Qt/',
        {},
        ( ( 'QtGui', '[File]' ), ) ),
      ( 'const char* c = "dir with spaces (x64)/Qt/QtGui '
        'dir with spaces (x64)/',
        {},
        ( ( 'Qt',    '[Dir]' ),
          ( 'QtGui', '[Dir]' ) ) ),
      ( 'const char* c = "dir with spaces (x64)/Qt/QtGui/',
        {},
        () ),
      ( 'const char* c = "dir with spaces (x64)/Qt/QtGui /',
        {},
        () ),
      ( 'set x = $YCM_TEST_DATA_DIR/dir with spaces (x64)/QtGui/',
        { 'YCM_TEST_DATA_DIR': DATA_DIR },
        ( ( 'QDialog', '[File]' ),
          ( 'QWidget', '[File]' ) ) ),
      ( 'set x = $YCM_TEST_DIR/testdata/filename_completer/inner_dir/test',
        { 'YCM_TEST_DIR': TEST_DIR },
        ( ( 'test.cpp', '[File]' ),
          ( 'test.hpp', '[File]' ) ) ),
      ( 'set x = $YCMTESTDIR/testdata/filename_completer/',
        { 'YCMTESTDIR': TEST_DIR },
        ( ( 'inner_dir', '[Dir]' ),
          ( '∂†∫',       '[Dir]' ) ) ),
      ( 'set x = $test_ycm_dir/testdata/filename_completer/inn',
        { 'test_ycm_dir': TEST_DIR },
        ( ( 'inner_dir', '[Dir]' ), ) ),
      ( 'set x = ' + TEST_DIR +
        '/testdata/filename_completer/$YCM_TEST_filename_completer/',
        { 'YCM_TEST_filename_completer': 'inner_dir' },
        ( ( 'dir with spaces (x64)', '[Dir]' ),
          ( 'foo漢字.txt',           '[File]' ),
          ( 'test.cpp',              '[File]' ),
          ( 'test.hpp',              '[File]' ) ) ),
      ( 'set x = ' + TEST_DIR +
        '/testdata/filename_completer/$YCM_TEST_filename_c0mpleter/test',
        { 'YCM_TEST_filename_c0mpleter': 'inner_dir' },
        ( ( 'test.cpp', '[File]' ),
          ( 'test.hpp', '[File]' ) ) ),
      ( 'set x = ' + TEST_DIR + '/${YCM_TEST_td}ata/filename_completer/',
        { 'YCM_TEST_td': 'testd' },
        ( ( 'inner_dir', '[Dir]' ),
          ( '∂†∫',       '[Dir]' ) ) ),
      ( 'set x = ' + TEST_DIR + '/tes${YCM_TEST_td}/filename_completer/',
        { 'YCM_TEST_td': 'tdata' },
        ( ( 'inner_dir', '[Dir]' ),
          ( '∂†∫',       '[Dir]' ) ) ),
      ( 'set x = ' + TEST_DIR + '/testdata/filename_completer${YCM_TEST_td}/',
        {},
        () ),
      ( 'set x = ' + TEST_DIR + '/testdata/filename_completer${YCM_empty_var}/',
        { 'YCM_empty_var': '' },
        ( ( 'inner_dir', '[Dir]' ),
          ( '∂†∫',       '[Dir]' ) ) ),
      ( 'set x = ' + TEST_DIR + '/$YCM_TEST_td}/',
        { 'YCM_TEST_td': 'testdata/filename_completer' },
        () ),
      ( 'set x = ' + TEST_DIR + '/${YCM_TEST_td/',
        { 'YCM_TEST_td': 'testdata/filename_completer' },
        () ),
      ( 'set x = ' + TEST_DIR + '/$ YCM_TEST_td/',
        { 'YCM_TEST_td': 'testdata/filename_completer' },
        () ),
      ( 'test ' + DATA_DIR + '/../∂',
        {},
        ( ( '∂†∫', '[Dir]' ), ) ),
    ]
    for contents, env, expected in test_cases:
      with self.subTest( contents = contents, env = env, expected = expected ):
        FilenameCompleter_Completion( app, contents, env, 'foo', expected )


  @WindowsOnly
  @IsolatedYcmd( { 'max_num_candidates': 0 } )
  def test_FilenameCompleter_Completion_Windows( self, app ):
    test_cases = [
      ( '\\',
        {},
        ROOT_FOLDER_COMPLETIONS ),
      ( '/\\',
        {},
        () ),
      ( '\\\\',
        {},
        () ),
      ( '\\/',
        {},
        () ),
      ( 'const char* c = "\\',
        {},
        ROOT_FOLDER_COMPLETIONS ),
      ( 'const char* c = "' + DRIVE + '/',
        {},
        ROOT_FOLDER_COMPLETIONS ),
      ( 'const char* c = "' + DRIVE + '\\',
        {},
        ROOT_FOLDER_COMPLETIONS ),
      ( 'const char* c = ".\\',
        {},
        ( ( 'dir with spaces (x64)', '[Dir]' ),
          ( 'foo漢字.txt',           '[File]' ),
          ( 'test.cpp',              '[File]' ),
          ( 'test.hpp',              '[File]' ) ) ),
      ( 'const char* c = ".\\dir with spaces (x64)\\',
        {},
        ( ( 'Qt',    '[Dir]' ),
          ( 'QtGui', '[Dir]' ) ) ),
      ( 'const char* c = ".\\dir with spaces (x64)\\\\',
        {},
        ( ( 'Qt',    '[Dir]' ),
          ( 'QtGui', '[Dir]' ) ) ),
      ( 'const char* c = ".\\dir with spaces (x64)/\\',
        {},
        ( ( 'Qt',    '[Dir]' ),
          ( 'QtGui', '[Dir]' ) ) ),
      ( 'const char* c = ".\\dir with spaces (x64)\\/',
        {},
        ( ( 'Qt',    '[Dir]' ),
          ( 'QtGui', '[Dir]' ) ) ),
      ( 'const char* c = ".\\dir with spaces (x64)/Qt\\',
        {},
        ( ( 'QtGui', '[File]' ), ) ),
      ( 'const char* c = "dir with spaces (x64)\\Qt\\',
        {},
        ( ( 'QtGui', '[File]' ), ) ),
      ( 'dir with spaces (x64)\\Qt/QtGui dir with spaces (x64)\\',
        {},
        ( ( 'Qt',    '[Dir]' ),
          ( 'QtGui', '[Dir]' ) ) ),
      ( 'set x = %YCM_TEST_DIR%\\testdata/filename_completer\\inner_dir/test',
        { 'YCM_TEST_DIR': TEST_DIR },
        ( ( 'test.cpp', '[File]' ),
          ( 'test.hpp', '[File]' ) ) ),
      ( 'set x = YCM_TEST_DIR%\\testdata/filename_completer\\inner_dir/test',
        { 'YCM_TEST_DIR': TEST_DIR },
        () ),
      ( 'set x = %YCM_TEST_DIR\\testdata/filename_completer\\inner_dir/test',
        { 'YCM_TEST_DIR': TEST_DIR },
        () ),
    ]
    for contents, env, expected in test_cases:
      with self.subTest( contents = contents, env = env, expected = expected ):
        FilenameCompleter_Completion( app, contents, env, 'foo', expected )


  @IsolatedYcmd( { 'filepath_completion_use_working_dir': 0 } )
  def test_WorkingDir_UseFilePath( self, app ):
    assert_that( GetCurrentDirectory() != DATA_DIR,
                 'Please run this test from a different directory' )

    completion_data = BuildRequest( contents = 'ls ./dir with spaces (x64)/',
                                    filepath = PATH_TO_TEST_FILE,
                                    column_num = 28 )
    results = app.post_json( '/completions',
                             completion_data ).json[ 'completions' ]
    assert_that( results, contains_inanyorder(
      CompletionEntryMatcher( 'Qt',    '[Dir]' ),
      CompletionEntryMatcher( 'QtGui', '[Dir]' )
    ) )


  @IsolatedYcmd( { 'filepath_completion_use_working_dir': 1 } )
  def test_WorkingDir_UseServerWorkingDirectory( self, app ):
    test_dir = os.path.join( DATA_DIR, 'dir with spaces (x64)' )
    with CurrentWorkingDirectory( test_dir ) as old_current_dir:
      assert_that( old_current_dir != test_dir,
                   'Please run this test from a different directory' )

      completion_data = BuildRequest( contents = 'ls ./',
                                      filepath = PATH_TO_TEST_FILE,
                                      column_num = 6 )
      results = app.post_json( '/completions',
                               completion_data ).json[ 'completions' ]
      assert_that( results, contains_inanyorder(
        CompletionEntryMatcher( 'Qt',    '[Dir]' ),
        CompletionEntryMatcher( 'QtGui', '[Dir]' )
      ) )


  @IsolatedYcmd( { 'filepath_completion_use_working_dir': 1 } )
  def test_WorkingDir_UseServerWorkingDirectory_Unicode( self, app ):
    test_dir = os.path.join( TEST_DIR, 'testdata', 'filename_completer', '∂†∫' )
    with CurrentWorkingDirectory( test_dir ) as old_current_dir:
      assert_that( old_current_dir != test_dir,
                   'Please run this test from a different directory' )

      # We don't supply working_dir in the request, so the current working
      # directory is used.
      completion_data = BuildRequest( contents = 'ls ./',
                                      filepath = PATH_TO_TEST_FILE,
                                      column_num = 6 )
      results = app.post_json( '/completions',
                               completion_data ).json[ 'completions' ]
      assert_that( results, contains_inanyorder(
        CompletionEntryMatcher( '†es†.txt', '[File]' )
      ) )


  @IsolatedYcmd( { 'filepath_completion_use_working_dir': 1 } )
  def test_WorkingDir_UseClientWorkingDirectory( self, app ):
    test_dir = os.path.join( DATA_DIR, 'dir with spaces (x64)' )
    assert_that( GetCurrentDirectory() != test_dir,
                 'Please run this test from a different directory' )

    # We supply working_dir in the request, so we expect results to be
    # relative to the supplied path.
    completion_data = BuildRequest( contents = 'ls ./',
                                    filepath = PATH_TO_TEST_FILE,
                                    column_num = 6,
                                    working_dir = test_dir )
    results = app.post_json( '/completions',
                             completion_data ).json[ 'completions' ]
    assert_that( results, contains_inanyorder(
      CompletionEntryMatcher( 'Qt',    '[Dir]' ),
      CompletionEntryMatcher( 'QtGui', '[Dir]' )
    ) )


  @IsolatedYcmd( { 'filepath_blacklist': {} } )
  def test_FilenameCompleter_NoFiletypeBlacklisted( self, app ):
    completion_data = BuildRequest( filetypes = [ 'foo', 'bar' ],
                                    contents = './',
                                    column_num = 3 )
    results = app.post_json( '/completions',
                             completion_data ).json[ 'completions' ]
    assert_that( results, is_not( empty() ) )


  @IsolatedYcmd( { 'filepath_blacklist': { 'foo': 1 } } )
  def test_FilenameCompleter_FirstFiletypeBlacklisted( self, app ):
    completion_data = BuildRequest( filetypes = [ 'foo', 'bar' ],
                                    contents = './',
                                    column_num = 3 )
    results = app.post_json( '/completions',
                             completion_data ).json[ 'completions' ]
    assert_that( results, empty() )


  @IsolatedYcmd( { 'filepath_blacklist': { 'bar': 1 } } )
  def test_FilenameCompleter_SecondFiletypeBlacklisted( self, app ):
    completion_data = BuildRequest( filetypes = [ 'foo', 'bar' ],
                                    contents = './',
                                    column_num = 3 )
    results = app.post_json( '/completions',
                             completion_data ).json[ 'completions' ]
    assert_that( results, empty() )


  @IsolatedYcmd( { 'filepath_blacklist': { '*': 1 } } )
  def test_FilenameCompleter_AllFiletypesBlacklisted( self, app ):
    completion_data = BuildRequest( filetypes = [ 'foo', 'bar' ],
                                    contents = './',
                                    column_num = 3 )
    results = app.post_json( '/completions',
                             completion_data ).json[ 'completions' ]
    assert_that( results, empty() )
