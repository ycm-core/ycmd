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

from hamcrest import ( all_of,
                       assert_that,
                       has_items,
                       has_key,
                       is_not )
from unittest import TestCase

from ycmd.tests.go import setUpModule, tearDownModule # noqa
from ycmd.tests.go import PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import ( BuildRequest,
                                    CompletionEntryMatcher,
                                    WithRetry )
from ycmd.utils import ReadFile


class GetCompletionsTest( TestCase ):
  @WithRetry( reruns = 100 )
  @SharedYcmd
  def test_GetCompletions_Basic( self, app ):
    filepath = PathToTestFile( 'td', 'test.go' )
    completion_data = BuildRequest( filepath = filepath,
                                    filetype = 'go',
                                    contents = ReadFile( filepath ),
                                    force_semantic = True,
                                    line_num = 10,
                                    column_num = 9 )

    results = app.post_json( '/completions',
                             completion_data ).json[ 'completions' ]
    assert_that( results,
                 all_of(
                   has_items(
                     CompletionEntryMatcher(
                       'Llongfile',
                       'int',
                       {
                         'detailed_info': 'Llongfile\n\n'
                                          'These flags define which text to'
                                          ' prefix to each log entry generated'
                                          ' by the Logger.',
                         'menu_text': 'Llongfile',
                         'kind': 'Constant',
                       }
                     ),
                     CompletionEntryMatcher(
                       'Logger',
                       'struct{...}',
                       {
                         'detailed_info': 'Logger\n\n'
                                          'A Logger represents an active '
                                          'logging object that generates lines '
                                          'of output to an io.Writer.',
                         'menu_text': 'Logger',
                         'kind': 'Struct',
                       }
                     ) ) ) )


    # This completer does not require or support resolve
    assert_that( results[ 0 ], is_not( has_key( 'resolve' ) ) )
    assert_that( results[ 0 ], is_not( has_key( 'item' ) ) )
