# Copyright (C) 2015 ycmd contributors
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

from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa

from hamcrest import assert_that, empty, has_entry, has_items
from mock import patch

from ycmd.completers.rust.rust_completer import (
  ERROR_FROM_RACERD_MESSAGE, NON_EXISTING_RUST_SOURCES_PATH_MESSAGE )
from ycmd.tests.rust import IsolatedYcmd, PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import ( BuildRequest, CompletionEntryMatcher,
                                    ErrorMatcher,
                                    WaitUntilCompleterServerReady )
from ycmd.utils import ReadFile


@SharedYcmd
def GetCompletions_Basic_test( app ):
  filepath = PathToTestFile( 'test.rs' )
  contents = ReadFile( filepath )

  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'rust',
                                  contents = contents,
                                  force_semantic = True,
                                  line_num = 9,
                                  column_num = 11 )

  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]

  assert_that( results,
               has_items( CompletionEntryMatcher( 'build_rocket' ),
                          CompletionEntryMatcher( 'build_shuttle' ) ) )


@IsolatedYcmd()
@patch( 'ycmd.completers.rust.rust_completer._GetRustSysroot',
        return_value = '/non/existing/rust/src/path' )
def GetCompletions_WhenStandardLibraryCompletionFails_MentionRustSrcPath_test(
  app, *args ):
  WaitUntilCompleterServerReady( app, 'rust' )
  filepath = PathToTestFile( 'std_completions.rs' )
  contents = ReadFile( filepath )

  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'rust',
                                  contents = contents,
                                  force_semantic = True,
                                  line_num = 5,
                                  column_num = 11 )

  response = app.post_json( '/completions',
                            completion_data,
                            expect_errors = True ).json
  assert_that( response,
               ErrorMatcher( RuntimeError, ERROR_FROM_RACERD_MESSAGE ) )


@IsolatedYcmd()
@patch( 'ycmd.completers.rust.rust_completer._GetRustSysroot',
        return_value = '/non/existing/rust/src/path' )
def GetCompletions_WhenNoCompletionsFound_MentionRustSrcPath_test( app, *args ):
  WaitUntilCompleterServerReady( app, 'rust' )
  filepath = PathToTestFile( 'test.rs' )
  contents = ReadFile( filepath )

  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'rust',
                                  contents = contents,
                                  force_semantic = True,
                                  line_num = 4,
                                  column_num = 1 )

  response = app.post_json( '/completions',
                            completion_data,
                            expect_errors = True ).json
  assert_that( response,
               ErrorMatcher( RuntimeError, ERROR_FROM_RACERD_MESSAGE ) )


# Set the rust_src_path option to a dummy folder.
@IsolatedYcmd( { 'rust_src_path': PathToTestFile() } )
def GetCompletions_NoCompletionsFound_ExistingRustSrcPath_test( app ):
  WaitUntilCompleterServerReady( app, 'rust' )

  filepath = PathToTestFile( 'test.rs' )
  contents = ReadFile( filepath )

  # Try to complete the pub keyword.
  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'rust',
                                  contents = contents,
                                  force_semantic = True,
                                  line_num = 1,
                                  column_num = 2 )

  response = app.post_json( '/completions', completion_data )
  assert_that( response.json, has_entry( 'completions', empty() ) )


@IsolatedYcmd( { 'rust_src_path': '/non/existing/rust/src/path' } )
def GetCompletions_NonExistingRustSrcPathFromUserOption_test( app ):
  response = app.get( '/ready',
                      { 'subserver': 'rust' },
                      expect_errors = True ).json
  assert_that( response,
               ErrorMatcher( RuntimeError,
                             NON_EXISTING_RUST_SOURCES_PATH_MESSAGE ) )


@IsolatedYcmd()
@patch.dict( 'os.environ', { 'RUST_SRC_PATH': '/non/existing/rust/src/path' } )
def GetCompletions_NonExistingRustSrcPathFromEnvironmentVariable_test( app ):
  response = app.get( '/ready',
                      { 'subserver': 'rust' },
                      expect_errors = True ).json
  assert_that( response,
               ErrorMatcher( RuntimeError,
                             NON_EXISTING_RUST_SOURCES_PATH_MESSAGE ) )


@IsolatedYcmd()
@patch( 'ycmd.completers.rust.rust_completer.FindExecutable',
        return_value = None )
def GetCompletions_WhenRustcNotFound_MentionRustSrcPath_test( app, *args ):
  WaitUntilCompleterServerReady( app, 'rust' )
  filepath = PathToTestFile( 'test.rs' )
  contents = ReadFile( filepath )

  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'rust',
                                  contents = contents,
                                  force_semantic = True,
                                  line_num = 1,
                                  column_num = 1 )

  response = app.post_json( '/completions',
                            completion_data,
                            expect_errors = True ).json
  assert_that( response,
               ErrorMatcher( RuntimeError, ERROR_FROM_RACERD_MESSAGE ) )


@IsolatedYcmd()
@patch( 'ycmd.completers.rust.rust_completer._GetRustSysroot',
        return_value = PathToTestFile( 'rustup-toolchain' ) )
def GetCompletions_RustupPathHeuristics_test( app, *args ):
  request_data = BuildRequest( filetype = 'rust' )

  assert_that( app.post_json( '/debug_info', request_data ).json,
               has_entry( 'completer', has_entry( 'items', has_items(
                 has_entry( 'value', PathToTestFile( 'rustup-toolchain',
                                                     'lib',
                                                     'rustlib',
                                                     'src',
                                                     'rust',
                                                     'src' ) ) ) ) ) )
