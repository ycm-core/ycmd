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

from hamcrest import ( assert_that, contains_exactly, contains_string, equal_to,
                       has_entries, has_entry, has_items )
from unittest import TestCase

from ycmd.tests.cs import setUpModule, tearDownModule # noqa
from ycmd.tests.cs import ( IsolatedYcmd,
                            PathToTestFile,
                            SharedYcmd,
                            WrapOmniSharpServer )
from ycmd.tests.test_utils import ( BuildRequest,
                                    LocationMatcher,
                                    RangeMatcher,
                                    WithRetry )
from ycmd.utils import ReadFile


class DiagnosticsTest( TestCase ):
  @WithRetry()
  @SharedYcmd
  def test_Diagnostics_Basic( self, app ):
    filepath = PathToTestFile( 'testy', 'Program.cs' )
    with WrapOmniSharpServer( app, filepath ):
      contents = ReadFile( filepath )

      event_data = BuildRequest( filepath = filepath,
                                 event_name = 'FileReadyToParse',
                                 filetype = 'cs',
                                 contents = contents )
      app.post_json( '/event_notification', event_data )

      diag_data = BuildRequest( filepath = filepath,
                                filetype = 'cs',
                                contents = contents,
                                line_num = 10,
                                column_num = 2 )

      results = app.post_json( '/detailed_diagnostic', diag_data ).json
      assert_that( results,
                   has_entry(
                       'message',
                       contains_string(
                         "Identifier expected" ) ) )


  @SharedYcmd
  def test_Diagnostics_ZeroBasedLineAndColumn( self, app ):
    filepath = PathToTestFile( 'testy', 'Program.cs' )
    with WrapOmniSharpServer( app, filepath ):
      contents = ReadFile( filepath )

      event_data = BuildRequest( filepath = filepath,
                                 event_name = 'FileReadyToParse',
                                 filetype = 'cs',
                                 contents = contents )

      results = app.post_json( '/event_notification', event_data ).json

      assert_that( results, has_items(
        has_entries( {
          'kind': equal_to( 'ERROR' ),
          'text': contains_string( "Identifier expected" ),
          'location': LocationMatcher( filepath, 10, 12 ),
          'location_extent': RangeMatcher( filepath, ( 10, 12 ), ( 10, 12 ) ),
        } )
      ) )


  @WithRetry()
  @SharedYcmd
  def test_Diagnostics_WithRange( self, app ):
    filepath = PathToTestFile( 'testy', 'DiagnosticRange.cs' )
    with WrapOmniSharpServer( app, filepath ):
      contents = ReadFile( filepath )

      event_data = BuildRequest( filepath = filepath,
                                 event_name = 'FileReadyToParse',
                                 filetype = 'cs',
                                 contents = contents )

      results = app.post_json( '/event_notification', event_data ).json

      assert_that( results, contains_exactly(
        has_entries( {
          'kind': equal_to( 'WARNING' ),
          'text': contains_string(
            "The variable '\u4e5d' is assigned but its value is never used" ),
          'location': LocationMatcher( filepath, 6, 13 ),
          'location_extent': RangeMatcher( filepath, ( 6, 13 ), ( 6, 16 ) )
        } )
      ) )


  @IsolatedYcmd()
  def test_Diagnostics_MultipleSolution( self, app ):
    filepaths = [ PathToTestFile( 'testy', 'Program.cs' ),
                  PathToTestFile( 'testy-multiple-solutions',
                                  'solution-named-like-folder',
                                  'testy', 'Program.cs' ) ]
    for filepath in filepaths:
      with WrapOmniSharpServer( app, filepath ):
        contents = ReadFile( filepath )
        event_data = BuildRequest( filepath = filepath,
                                   event_name = 'FileReadyToParse',
                                   filetype = 'cs',
                                   contents = contents )

        results = app.post_json( '/event_notification', event_data ).json
        assert_that( results, has_items(
          has_entries( {
            'kind': equal_to( 'ERROR' ),
            'text': contains_string( "Identifier expected" ),
            'location': LocationMatcher( filepath, 10, 12 ),
            'location_extent': RangeMatcher(
                filepath, ( 10, 12 ), ( 10, 12 ) )
          } )
        ) )


  @IsolatedYcmd( { 'max_diagnostics_to_display': 1 } )
  def test_Diagnostics_MaximumDiagnosticsNumberExceeded( self, app ):
    filepath = PathToTestFile( 'testy', 'MaxDiagnostics.cs' )
    with WrapOmniSharpServer( app, filepath ):
      contents = ReadFile( filepath )

      event_data = BuildRequest( filepath = filepath,
                                 event_name = 'FileReadyToParse',
                                 filetype = 'cs',
                                 contents = contents )

      results = app.post_json( '/event_notification', event_data ).json

      assert_that( results, contains_exactly(
        has_entries( {
          'kind': equal_to( 'ERROR' ),
          'text': contains_string( "The type 'MaxDiagnostics' already contains "
                                   "a definition for 'test'" ),
          'location': LocationMatcher( filepath, 4, 16 ),
          'location_extent': RangeMatcher( filepath, ( 4, 16 ), ( 4, 20 ) )
        } ),
        has_entries( {
          'kind': equal_to( 'ERROR' ),
          'text': contains_string( 'Maximum number of diagnostics exceeded.' ),
          'location': LocationMatcher( filepath, 1, 1 ),
          'location_extent': RangeMatcher( filepath, ( 1, 1 ), ( 1, 1 ) ),
          'ranges': contains_exactly(
            RangeMatcher( filepath, ( 1, 1 ), ( 1, 1 ) )
          )
        } )
      ) )
