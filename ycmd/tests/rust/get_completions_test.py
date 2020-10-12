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

from hamcrest import ( assert_that,
                       contains_exactly,
                       empty,
                       has_key,
                       is_not )
from pprint import pformat


from ycmd.tests.rust import PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import ( BuildRequest,
                                    CompletionEntryMatcher,
                                    WithRetry )
from ycmd.utils import ReadFile


@WithRetry
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
        'pub fn build_rocket(&self)',
        {
          'detailed_info': 'build_rocket\n\nDo not try at home',
          'menu_text':     'build_rocket',
          'kind':          'Method'
        }
      ),
      CompletionEntryMatcher(
        'build_shuttle',
        'pub fn build_shuttle(&self)',
        {
          'detailed_info': 'build_shuttle\n\n',
          'menu_text':     'build_shuttle',
          'kind':          'Method'
        }
      )
    )
  )

  # This completer does not require or support resolve
  assert_that( results[ 0 ], is_not( has_key( 'resolve' ) ) )
  assert_that( results[ 0 ], is_not( has_key( 'item' ) ) )

  # So (erroneously) resolving an item returns the item
  completion_data[ 'resolve' ] = 0
  response = app.post_json( '/resolve_completion', completion_data ).json
  print( f"Resolve resolve: { pformat( response ) }" )

  # We can't actually check the result because we don't know what completion
  # resolve ID 0 actually is (could be anything), so we just check that we get 1
  # result, and that there are no errors.
  assert_that( response[ 'completion' ], is_not( None ) )
  assert_that( response[ 'errors' ], empty() )


def Dummy_test():
  # Workaround for https://github.com/pytest-dev/pytest-rerunfailures/issues/51
  assert True
