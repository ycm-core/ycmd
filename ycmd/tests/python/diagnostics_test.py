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

from ycmd.tests.python import IsolatedYcmd, PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import ( BuildRequest,
                                    ErrorMatcher,
                                    LocationMatcher,
                                    RangeMatcher )
from ycmd.utils import ReadFile


@SharedYcmd
def Diagnostics_FileReadyToParse_test( app ):
  filepath = PathToTestFile( 'basic.py' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'python',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  assert_that(
    app.post_json( '/event_notification', event_data ).json,
    contains_inanyorder(
      has_entries( {
        'kind': 'ERROR',
        'text': 'SyntaxError: invalid syntax',
        'location': LocationMatcher( filepath, 9, 14 ),
        'location_extent': RangeMatcher( filepath, ( 9, 14 ), ( 9, 18 ) ),
        'ranges': contains_exactly(
          RangeMatcher( filepath, ( 9, 14 ), ( 9, 18 ) ) ),
        'fixit_available': False
      } ),
      has_entries( {
        'kind': 'ERROR',
        'text': 'IndentationError: unexpected indent',
        'location': LocationMatcher( filepath, 10, 1 ),
        'location_extent': RangeMatcher( filepath, ( 10, 1 ), ( 10, 1 ) ),
        'ranges': contains_exactly(
          RangeMatcher( filepath, ( 10, 1 ), ( 10, 1 ) ) ),
        'fixit_available': False
      } ),
    )
  )


@SharedYcmd
def Diagnostics_DetailedDiagnostics_DiagnosticNotFound_test( app ):
  filepath = PathToTestFile( 'basic.py' )
  contents = ReadFile( filepath )

  diagnostic_data = BuildRequest( filepath = filepath,
                                  filetype = 'python',
                                  contents = contents,
                                  line_num = 4,
                                  column_num = 1 )

  assert_that(
    app.post_json( '/detailed_diagnostic',
                   diagnostic_data,
                   expect_errors = True ).json,
    ErrorMatcher( ValueError, 'No diagnostic for current line!' )
  )


@SharedYcmd
def Diagnostics_DetailedDiagnostics_test( app ):
  filepath = PathToTestFile( 'basic.py' )
  contents = ReadFile( filepath )

  diagnostic_data = BuildRequest( filepath = filepath,
                                  filetype = 'python',
                                  contents = contents,
                                  line_num = 9,
                                  column_num = 14 )

  assert_that(
    app.post_json( '/detailed_diagnostic', diagnostic_data ).json,
    has_entry(
      'message', 'SyntaxError: invalid syntax'
    )
  )


@IsolatedYcmd( { 'max_diagnostics_to_display': 1 } )
def Diagnostics_MaximumDiagnosticsNumberExceeded_test( app ):
  filepath = PathToTestFile( 'basic.py' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'python',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  assert_that(
    app.post_json( '/event_notification', event_data ).json,
    contains_inanyorder(
      has_entries( {
        'kind': 'ERROR',
        'text': 'SyntaxError: invalid syntax',
        'location': LocationMatcher( filepath, 9, 14 ),
        'location_extent': RangeMatcher( filepath, ( 9, 14 ), ( 9, 18 ) ),
        'ranges': contains_exactly(
          RangeMatcher( filepath, ( 9, 14 ), ( 9, 18 ) ) ),
        'fixit_available': False
      } ),
      has_entries( {
        'kind': 'ERROR',
        'text': 'Maximum number of diagnostics exceeded.',
        'location': LocationMatcher( filepath, 1, 1 ),
        'location_extent': RangeMatcher( filepath, ( 1, 1 ), ( 1, 1 ) ),
        'ranges': contains_exactly(
          RangeMatcher( filepath, ( 1, 1 ), ( 1, 1 ) ) ),
        'fixit_available': False
      } ),
    )
  )


def Dummy_test():
  # Workaround for https://github.com/pytest-dev/pytest-rerunfailures/issues/51
  assert True
