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

import time
from hamcrest import ( assert_that,
                       has_item,
                       empty,
                       equal_to,
                       has_key,
                       has_entry )
from pprint import pformat
from unittest import TestCase


from ycmd.tests.rust import setUpModule, tearDownModule # noqa
from ycmd.tests.rust import ( IsolatedYcmd,
                              PathToTestFile,
                              StartRustCompleterServerInDirectory )
from ycmd.tests.test_utils import ( BuildRequest,
                                    CompletionEntryMatcher,
                                    WithRetry )
from ycmd.utils import ReadFile


class GetCompletionsProcMacroTest( TestCase ):
  @WithRetry()
  @IsolatedYcmd( { 'max_num_candidates_to_detail': 0 } )
  def test_GetCompletions_ProcMacro( self, app ):
    StartRustCompleterServerInDirectory( app, PathToTestFile( 'macro' ) )

    filepath = PathToTestFile( 'macro', 'src', 'main.rs' )
    contents = ReadFile( filepath )

    completion_data = BuildRequest( filepath = filepath,
                                    filetype = 'rust',
                                    contents = contents,
                                    line_num = 33,
                                    column_num = 14 )

    results = []
    expiration = time.time() + 60
    while time.time() < expiration:
      results = app.post_json( '/completions',
                             completion_data ).json[ 'completions' ]
      if len( results ) > 0:
        break
      time.sleep( 0.25 )

    assert_that(
      results,
      has_item(
        CompletionEntryMatcher(
          'checkpoint'
        )
      )
    )

    checked_candidate = None
    for candidate in results:
      if candidate[ 'insertion_text' ] == 'checkpoint':
        checked_candidate = candidate

    unresolved_item = checked_candidate[ 'extra_data' ]
    assert_that( unresolved_item, has_key( 'resolve' ) )
    assert_that( unresolved_item, has_key( 'item' ) )
    assert_that( checked_candidate, has_entry( 'detailed_info',
                                               'checkpoint\n\n' ) )

    completion_data[ 'resolve' ] = unresolved_item[ 'resolve' ]
    response = app.post_json( '/resolve_completion', completion_data ).json
    print( f"Resolve resolve: { pformat( response ) }" )

    assert_that( response[ 'errors' ], empty() )
    assert_that( response[ 'completion' ][ 'detailed_info' ],
                 equal_to(
                   "checkpoint\n"
                   "\n"
                   "Validate that all current expectations for "
                   "all methods have\n"
                   "been satisfied, and discard them." ) )
