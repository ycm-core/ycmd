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
                       has_key,
                       is_not )
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
  @IsolatedYcmd()
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

    # This completer does not require or support resolve
    assert_that( results[ 0 ], is_not( has_key( 'resolve' ) ) )
    assert_that( results[ 0 ], is_not( has_key( 'item' ) ) )

    # So (erroneously) resolving an item returns the item
    completion_data[ 'resolve' ] = 0
    response = app.post_json( '/resolve_completion', completion_data ).json
    print( f"Resolve resolve: { pformat( response ) }" )

    # We can't actually check the result because we don't know what completion
    # resolve ID 0 actually is (could be anything), so we just check that we
    # get 1 result, and that there are no errors.
    assert_that( response[ 'completion' ], is_not( None ) )
    assert_that( response[ 'errors' ], empty() )
