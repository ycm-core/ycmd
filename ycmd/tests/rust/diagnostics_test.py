# Copyright (C) 2021 ycmd contributors
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
from unittest import TestCase
import json
import os

from ycmd.tests.rust import setUpModule, tearDownModule # noqa
from ycmd.tests.rust import PathToTestFile, SharedYcmd
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
          'no field `build_` on type `test::Builder`\nunknown field [E0609]',
      'location': LocationMatcher( MAIN_FILEPATH, 14, 13 ),
      'location_extent': RangeMatcher( MAIN_FILEPATH, ( 14, 13 ), ( 14, 19 ) ),
      'ranges': contains_exactly( RangeMatcher( MAIN_FILEPATH,
                                        ( 14, 13 ),
                                        ( 14, 19 ) ) ),
      'fixit_available': False
    } )
  )
}


class DiagnosticsTest( TestCase ):
  @WithRetry()
  @SharedYcmd
  def test_Diagnostics_DetailedDiags( self, app ):
    filepath = PathToTestFile( 'common', 'src', 'main.rs' )
    contents = ReadFile( filepath )
    with open( filepath, 'w' ) as f:
      f.write( contents )
    event_data = BuildRequest( event_name = 'FileSave',
                               contents = contents,
                               filepath = filepath,
                               filetype = 'rust' )
    app.post_json( '/event_notification', event_data )

    WaitForDiagnosticsToBeReady( app, filepath, contents, 'rust' )
    request_data = BuildRequest( contents = contents,
                                 filepath = filepath,
                                 filetype = 'rust',
                                 line_num = 14,
                                 column_num = 13 )

    results = app.post_json( '/detailed_diagnostic', request_data ).json
    assert_that( results, has_entry(
        'message',
        'no field `build_` on type `test::Builder`\nunknown field' ) )


  @WithRetry()
  @SharedYcmd
  def test_Diagnostics_FileReadyToParse( self, app ):
    filepath = PathToTestFile( 'common', 'src', 'main.rs' )
    contents = ReadFile( filepath )
    with open( filepath, 'w' ) as f:
      f.write( contents )
    event_data = BuildRequest( event_name = 'FileSave',
                               contents = contents,
                               filepath = filepath,
                               filetype = 'rust' )
    app.post_json( '/event_notification', event_data )

    # It can take a while for the diagnostics to be ready.
    results = WaitForDiagnosticsToBeReady( app, filepath, contents, 'rust' )
    print( f'completer response: { pformat( results ) }' )

    assert_that( results, DIAG_MATCHERS_PER_FILE[ filepath ] )


  @SharedYcmd
  def test_Diagnostics_Poll( self, app ):
    project_dir = PathToTestFile( 'common' )
    filepath = os.path.join( project_dir, 'src', 'main.rs' )
    contents = ReadFile( filepath )
    with open( filepath, 'w' ) as f:
      f.write( contents )
    event_data = BuildRequest( event_name = 'FileSave',
                               contents = contents,
                               filepath = filepath,
                               filetype = 'rust' )
    app.post_json( '/event_notification', event_data )

    # Poll until we receive _all_ the diags asynchronously.
    to_see = sorted( DIAG_MATCHERS_PER_FILE.keys() )
    seen = {}

    try:
      for message in PollForMessages( app,
                                      { 'filepath': filepath,
                                        'contents': contents,
                                        'filetype': 'rust' } ):
        print( f'Message { pformat( message ) }' )
        if 'diagnostics' in message:
          if message[ 'diagnostics' ] == []:
            # Sometimes we get empty diagnostics before the real ones.
            continue
          seen[ message[ 'filepath' ] ] = True
          if message[ 'filepath' ] not in DIAG_MATCHERS_PER_FILE:
            raise AssertionError( 'Received diagnostics for unexpected file '
              f'{ message[ "filepath" ] }. Only expected { to_see }' )
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
