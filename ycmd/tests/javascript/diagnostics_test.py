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
from unittest import TestCase

from ycmd.tests.javascript import setUpModule, tearDownModule # noqa
from ycmd.tests.javascript import PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import BuildRequest, LocationMatcher, RangeMatcher
from ycmd.utils import ReadFile


class DiagnosticsTest( TestCase ):
  @SharedYcmd
  def test_Diagnostics_FileReadyToParse( self, app ):
    filepath = PathToTestFile( 'test.js' )
    contents = ReadFile( filepath )

    event_data = BuildRequest( filepath = filepath,
                               filetype = 'javascript',
                               contents = contents,
                               event_name = 'BufferVisit' )
    app.post_json( '/event_notification', event_data )

    event_data = BuildRequest( filepath = filepath,
                               filetype = 'javascript',
                               contents = contents,
                               event_name = 'FileReadyToParse' )

    assert_that(
      app.post_json( '/event_notification', event_data ).json,
      contains_inanyorder(
        has_entries( {
          'kind': 'ERROR',
          'text': "Property 'm' does not exist on type 'Foo'.",
          'location': LocationMatcher( filepath, 14, 5 ),
          'location_extent': RangeMatcher( filepath, ( 14, 5 ), ( 14, 6 ) ),
          'ranges': contains_exactly(
            RangeMatcher( filepath, ( 14, 5 ), ( 14, 6 ) ) ),
          'fixit_available': False
        } ),
        has_entries( {
          'kind': 'ERROR',
          'text': "Property 'nonExistingMethod' does not exist on type 'Bar'.",
          'location': LocationMatcher( filepath, 32, 5 ),
          'location_extent': RangeMatcher( filepath, ( 32, 5 ), ( 32, 22 ) ),
          'ranges': contains_exactly(
            RangeMatcher( filepath, ( 32, 5 ), ( 32, 22 ) ) ),
          'fixit_available': True
        } ),
        has_entries( {
          'kind': 'ERROR',
          'text': "Cannot find name 'Bår'.",
          'location': LocationMatcher( filepath, 36, 1 ),
          'location_extent': RangeMatcher( filepath, ( 36, 1 ), ( 36, 5 ) ),
          'ranges': contains_exactly(
            RangeMatcher( filepath, ( 36, 1 ), ( 36, 5 ) ) ),
          'fixit_available': True
        } ),
      )
    )


  @SharedYcmd
  def test_Diagnostics_DetailedDiagnostics( self, app ):
    filepath = PathToTestFile( 'test.js' )
    contents = ReadFile( filepath )

    event_data = BuildRequest( filepath = filepath,
                               filetype = 'javascript',
                               contents = contents,
                               event_name = 'BufferVisit' )
    app.post_json( '/event_notification', event_data )

    diagnostic_data = BuildRequest( filepath = filepath,
                                    filetype = 'javascript',
                                    contents = contents,
                                    line_num = 32,
                                    column_num = 13 )

    assert_that(
      app.post_json( '/detailed_diagnostic', diagnostic_data ).json,
      has_entry(
        'message', "Property 'nonExistingMethod' does not exist on type 'Bar'."
      )
    )
