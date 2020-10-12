# Copyright (C) 2020 ycmd contributors
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
                       contains_inanyorder,
                       has_entries,
                       has_entry )
from pprint import pformat
import json

from ycmd.tests.go import PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import ( BuildRequest,
                                    LocationMatcher,
                                    PollForMessages,
                                    PollForMessagesTimeoutException,
                                    RangeMatcher,
                                    WaitForDiagnosticsToBeReady,
                                    WithRetry )
from ycmd.utils import ReadFile


MAIN_FILEPATH = PathToTestFile( 'goto.go' )
DIAG_MATCHERS_PER_FILE = {
  MAIN_FILEPATH: contains_inanyorder(
    has_entries( {
      'kind': 'ERROR',
      'text': 'undeclared name: diagnostics_test',
      'location': LocationMatcher( MAIN_FILEPATH, 12, 5 ),
      'location_extent': RangeMatcher( MAIN_FILEPATH, ( 12, 5 ), ( 12, 21 ) ),
      'ranges': contains_exactly( RangeMatcher( MAIN_FILEPATH,
                                        ( 12, 5 ),
                                        ( 12, 21 ) ) ),
      'fixit_available': False
    } )
  )
}


@WithRetry
@SharedYcmd
def Diagnostics_DetailedDiags_test( app ):
  filepath = PathToTestFile( 'goto.go' )
  contents = ReadFile( filepath )
  WaitForDiagnosticsToBeReady( app, filepath, contents, 'go' )
  request_data = BuildRequest( contents = contents,
                               filepath = filepath,
                               filetype = 'go',
                               line_num = 12,
                               column_num = 5 )

  results = app.post_json( '/detailed_diagnostic', request_data ).json
  assert_that( results,
               has_entry( 'message', 'undeclared name: diagnostics_test' ) )


@WithRetry
@SharedYcmd
def Diagnostics_FileReadyToParse_test( app ):
  filepath = PathToTestFile( 'goto.go' )
  contents = ReadFile( filepath )

  # It can take a while for the diagnostics to be ready.
  results = WaitForDiagnosticsToBeReady( app, filepath, contents, 'go' )
  print( f'completer response: { pformat( results ) }' )

  assert_that( results, DIAG_MATCHERS_PER_FILE[ filepath ] )


@WithRetry
@SharedYcmd
def Diagnostics_Poll_test( app ):
  filepath = PathToTestFile( 'goto.go' )
  contents = ReadFile( filepath )

  # Poll until we receive _all_ the diags asynchronously.
  to_see = sorted( DIAG_MATCHERS_PER_FILE.keys() )
  seen = {}

  try:
    for message in PollForMessages( app,
                                    { 'filepath': filepath,
                                      'contents': contents,
                                      'filetype': 'go' } ):
      if 'diagnostics' in message:
        if message[ 'filepath' ] not in DIAG_MATCHERS_PER_FILE:
          continue
        seen[ message[ 'filepath' ] ] = True
        assert_that( message, has_entries( {
          'diagnostics': DIAG_MATCHERS_PER_FILE[ message[ 'filepath' ] ],
          'filepath': message[ 'filepath' ]
        } ) )

      if sorted( seen.keys() ) == to_see:
        break

      # Eventually PollForMessages will throw a timeout exception and we'll fail
      # if we don't see all of the expected diags.
  except PollForMessagesTimeoutException as e:
    raise AssertionError(
      str( e ) +
      'Timed out waiting for full set of diagnostics. '
      f'Expected to see diags for { json.dumps( to_see, indent = 2 ) }, '
      f'but only saw { json.dumps( sorted( seen.keys() ), indent = 2 ) }.' )


def Dummy_test():
  # Workaround for https://github.com/pytest-dev/pytest-rerunfailures/issues/51
  assert True
