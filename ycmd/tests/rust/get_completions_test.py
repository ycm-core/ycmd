# Copyright (C) 2015-2020 ycmd contributors
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

from hamcrest import assert_that, contains_exactly

from ycmd.tests.rust import PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import BuildRequest, CompletionEntryMatcher
from ycmd.utils import ReadFile


@SharedYcmd
def GetCompletions_Basic_test( app ):
  filepath = PathToTestFile( 'common', 'src', 'main.rs' )
  contents = ReadFile( filepath )

  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'rust',
                                  contents = contents,
                                  line_num = 14,
                                  column_num = 19 )

  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]

  assert_that(
    results,
    contains_exactly(
      CompletionEntryMatcher(
        'build_rocket',
        'fn build_rocket(&self)',
        {
          'detailed_info': 'build_rocket\n\nDo not try at home',
          'menu_text':     'build_rocket',
          'kind':          'Function'
        }
      ),
      CompletionEntryMatcher(
        'build_shuttle',
        'fn build_shuttle(&self)',
        {
          'detailed_info': 'build_shuttle\n\n',
          'menu_text':     'build_shuttle',
          'kind':          'Function'
        }
      )
    )
  )
