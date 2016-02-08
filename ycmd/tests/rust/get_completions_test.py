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

from ycmd.utils import ReadFile
from hamcrest import assert_that, has_entry, has_items, contains_string
from .rust_handlers_test import Rust_Handlers_test


class Rust_GetCompletions_test( Rust_Handlers_test ):


  def Basic_test( self ):
    filepath = self._PathToTestFile( 'test.rs' )
    contents = ReadFile( filepath )

    self._WaitUntilServerReady()

    completion_data = self._BuildRequest( filepath = filepath,
                                          filetype = 'rust',
                                          contents = contents,
                                          force_semantic = True,
                                          line_num = 9,
                                          column_num = 11 )

    results = self._app.post_json( '/completions',
                                   completion_data ).json[ 'completions' ]

    assert_that( results,
                 has_items( self._CompletionEntryMatcher( 'build_rocket' ),
                            self._CompletionEntryMatcher( 'build_shuttle' ) ) )


  def WhenStandardLibraryCompletionFails_MentionRustSrcPath_test( self ):
    filepath = self._PathToTestFile( 'std_completions.rs' )
    contents = ReadFile( filepath )

    self._WaitUntilServerReady()

    completion_data = self._BuildRequest( filepath = filepath,
                                          filetype = 'rust',
                                          contents = contents,
                                          force_semantic = True,
                                          line_num = 5,
                                          column_num = 11 )

    response = self._app.post_json( '/completions',
                                    completion_data,
                                    expect_errors = True ).json
    assert_that( response,
                 has_entry( 'message',
                            contains_string( 'rust_src_path' ) ) )
