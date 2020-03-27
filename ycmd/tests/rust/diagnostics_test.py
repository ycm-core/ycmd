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
import os

from ycmd.tests.rust import ( PathToTestFile,
                              SharedYcmd,
                              IsolatedYcmd,
                              StartRustCompleterServerInDirectory )
from ycmd.tests.test_utils import ( BuildRequest,
                                    LocationMatcher,
                                    PollForMessages,
                                    PollForMessagesTimeoutException,
                                    RangeMatcher,
                                    WaitForDiagnosticsToBeReady,
                                    WithRetry )
from ycmd.utils import ReadFile


MAIN_FILEPATH = PathToTestFile( 'common', 'src', 'main.rs' )
DIAG_MATCHERS_PER_FILE = {
  MAIN_FILEPATH: contains_inanyorder(
    has_entries( {
      'kind': 'ERROR',
      'text':
          'no field `build_` on type `test::Builder`\n\nunknown field [E0609]',
      'location': LocationMatcher( MAIN_FILEPATH, 14, 13 ),
      'location_extent': RangeMatcher( MAIN_FILEPATH, ( 14, 13 ), ( 14, 19 ) ),
      'ranges': contains_exactly( RangeMatcher( MAIN_FILEPATH,
                                        ( 14, 13 ),
                                        ( 14, 19 ) ) ),
      'fixit_available': False
    } )
  )
}


@WithRetry
@SharedYcmd
def Diagnostics_DetailedDiags_test( app ):
  filepath = PathToTestFile( 'common', 'src', 'main.rs' )
  contents = ReadFile( filepath )
  WaitForDiagnosticsToBeReady( app, filepath, contents, 'rust' )
  request_data = BuildRequest( contents = contents,
                               filepath = filepath,
                               filetype = 'rust',
                               line_num = 14,
                               column_num = 13 )

  results = app.post_json( '/detailed_diagnostic', request_data ).json
  assert_that( results, has_entry(
      'message',
      'no field `build_` on type `test::Builder`\n\nunknown field' ) )


@WithRetry
@SharedYcmd
def Diagnostics_FileReadyToParse_test( app ):
  filepath = PathToTestFile( 'common', 'src', 'main.rs' )
  contents = ReadFile( filepath )

  # It can take a while for the diagnostics to be ready.
  results = WaitForDiagnosticsToBeReady( app, filepath, contents, 'rust' )
  print( 'completer response: {}'.format( pformat( results ) ) )

  assert_that( results, DIAG_MATCHERS_PER_FILE[ filepath ] )


@IsolatedYcmd
def Diagnostics_Poll_test( app ):
  project_dir = PathToTestFile( 'common' )
  filepath = os.path.join( project_dir, 'src', 'main.rs' )
  contents = ReadFile( filepath )
  StartRustCompleterServerInDirectory( app, project_dir )

  # Poll until we receive _all_ the diags asynchronously.
  to_see = sorted( DIAG_MATCHERS_PER_FILE.keys() )
  seen = {}

  try:
    for message in PollForMessages( app,
                                    { 'filepath': filepath,
                                      'contents': contents,
                                      'filetype': 'rust' } ):
      print( 'Message {}'.format( pformat( message ) ) )
      if 'diagnostics' in message:
        seen[ message[ 'filepath' ] ] = True
        if message[ 'filepath' ] not in DIAG_MATCHERS_PER_FILE:
          raise AssertionError(
            'Received diagnostics for unexpected file {}. '
            'Only expected {}'.format( message[ 'filepath' ], to_see ) )
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
      'Expected to see diags for {}, but only saw {}.'.format(
        json.dumps( to_see, indent=2 ),
        json.dumps( sorted( seen.keys() ), indent=2 ) ) )
