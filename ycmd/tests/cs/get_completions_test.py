# Copyright (C) 2015-2021 ycmd contributors
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

from hamcrest import ( assert_that,
                       empty,
                       has_entries,
                       has_items )
from unittest import TestCase

from ycmd.tests.cs import setUpModule, tearDownModule # noqa
from ycmd.tests.cs import PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import ( BuildRequest,
                                    CompletionEntryMatcher,
                                    WithRetry )
from ycmd.utils import ReadFile


class GetCompletionsTest( TestCase ):
  @WithRetry
  @SharedYcmd
  def test_GetCompletions_Basic( self, app ):
    filepath = PathToTestFile( 'testy', 'Program.cs' )
    contents = ReadFile( filepath )

    completion_data = BuildRequest( filepath = filepath,
                                    filetype = 'cs',
                                    contents = contents,
                                    line_num = 10,
                                    column_num = 12 )
    response_data = app.post_json( '/completions', completion_data ).json
    print( 'Response: ', response_data )
    assert_that(
      response_data,
      has_entries( {
        'completion_start_column': 12,
        'completions': has_items(
          CompletionEntryMatcher( 'CursorLeft',
                                  None,
                                  { 'kind': 'Property' } ),
          CompletionEntryMatcher( 'CursorSize',
                                  None,
                                  { 'kind': 'Property' } ),
        ),
        'errors': empty(),
      } ) )
