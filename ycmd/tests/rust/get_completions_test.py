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
from future import standard_library
standard_library.install_aliases()
from builtins import *  # noqa

from hamcrest import assert_that, empty, has_entry, has_items, contains_string
from nose.tools import eq_

from ycmd.tests.rust import IsolatedYcmd, PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import BuildRequest, CompletionEntryMatcher
from ycmd.utils import ReadFile
import http.client


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


# This test is isolated because it affects the GoTo tests, although it
# shouldn't.
@IsolatedYcmd
def GetCompletions_WhenStandardLibraryCompletionFails_MentionRustSrcPath_test(
  app ):
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
               has_entry( 'message',
                          contains_string( 'rust_src_path' ) ) )


@SharedYcmd
def GetCompletions_NoCompletionsFound_test( app ):
  filepath = PathToTestFile( 'test.rs' )
  contents = ReadFile( filepath )

  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'rust',
                                  contents = contents,
                                  force_semantic = True,
                                  line_num = 4,
                                  column_num = 1 )

  response = app.post_json( '/completions', completion_data )

  eq_( response.status_code, http.client.OK )
  assert_that( response.json, has_entry( 'completions', empty() ) )
