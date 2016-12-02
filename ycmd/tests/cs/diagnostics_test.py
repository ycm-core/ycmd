# Copyright (C) 2015 ycmd contributors
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

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa

from hamcrest import ( assert_that, contains, contains_string, equal_to,
                       has_entries )

from ycmd.tests.cs import PathToTestFile, SharedYcmd, WrapOmniSharpServer
from ycmd.tests.test_utils import BuildRequest
from ycmd.utils import ReadFile


def Diagnostics_ZeroBasedLineAndColumn_test():
  yield _Diagnostics_ZeroBasedLineAndColumn_test, False
  yield _Diagnostics_ZeroBasedLineAndColumn_test, True


@SharedYcmd
def _Diagnostics_ZeroBasedLineAndColumn_test( app, use_roslyn ):
  filepath = PathToTestFile( 'testy', 'Program.cs' )
  with WrapOmniSharpServer( app, filepath, use_roslyn ):
    contents = ReadFile( filepath )

    event_data = BuildRequest( filepath = filepath,
                                event_name = 'FileReadyToParse',
                                filetype = 'cs',
                                contents = contents )

    results = app.post_json( '/event_notification', event_data ).json

    assert_that( results,
      _Diagnostics_CsCompleter_ExpectedResult( use_roslyn, True ) )


def Diagnostics_WithRange_test():
  yield _Diagnostics_WithRange_test, False
  yield _Diagnostics_WithRange_test, True


@SharedYcmd
def _Diagnostics_WithRange_test( app, use_roslyn ):
  filepath = PathToTestFile( 'testy', 'DiagnosticRange.cs' )
  with WrapOmniSharpServer( app, filepath, use_roslyn ):
    contents = ReadFile( filepath )

    results = {}
    for _ in ( 0, 1 ):  # First call always returns blank for some reason
      event_data = BuildRequest( filepath = filepath,
                                 event_name = 'FileReadyToParse',
                                 filetype = 'cs',
                                 contents = contents )

      results = app.post_json( '/event_notification', event_data ).json

    assert_that( results,
                 contains(
                     has_entries( {
                       'kind': equal_to( 'WARNING' ),
                       'text': contains_string(
                           "Name should have prefix '_'" ),
                       'location': has_entries( {
                         'line_num': 3,
                         'column_num': 16
                       } ),
                       'location_extent': has_entries( {
                         'start': has_entries( {
                           'line_num': 3,
                           'column_num': 16,
                         } ),
                         'end': has_entries( {
                           'line_num': 3,
                           'column_num': 25,
                         } ),
                       } )
                     } ) ) )


def Diagnostics_MultipleSolution_test():
  yield _Diagnostics_MultipleSolution_test, False
  yield _Diagnostics_MultipleSolution_test, True


@SharedYcmd
def _Diagnostics_MultipleSolution_test( app, use_roslyn ):
  filepaths = [ PathToTestFile( 'testy', 'Program.cs' ),
                PathToTestFile( 'testy-multiple-solutions',
                                'solution-named-like-folder',
                                'testy', 'Program.cs' ) ]
  main_errors = [ True, False ]
  for filepath, main_error in zip( filepaths, main_errors ):
    with WrapOmniSharpServer( app, filepath, use_roslyn ):
      contents = ReadFile( filepath )

      event_data = BuildRequest( filepath = filepath,
                                  event_name = 'FileReadyToParse',
                                  filetype = 'cs',
                                  contents = contents )

      results = app.post_json( '/event_notification', event_data ).json

      assert_that( results,
        _Diagnostics_CsCompleter_ExpectedResult( use_roslyn, main_error ) )


def _Diagnostics_CsCompleter_ExpectedResult( use_roslyn, flag ):
  def build_matcher( kind, message, line, column ):
    return has_entries( {
      'kind': equal_to( kind ),
      'text': contains_string( message ),
      'location': has_entries( {
        'line_num': line,
        'column_num': column
      } ),
      'location_extent': has_entries( {
        'start': has_entries( {
          'line_num': line,
          'column_num': column
        } ),
        'end': has_entries( {
          'line_num': line,
          'column_num': column
        } ),
      } )
    } )
  entries = []
  if use_roslyn:
    entries.append(
      build_matcher( 'ERROR', "Identifier expected", 10, 12 )
    )
    entries.append(
      build_matcher( 'ERROR', "; expected", 10, 12 ),
    )
    entries.append(
      build_matcher( 'ERROR',
        "'Console' does not contain a definition for ''", 11, 1 ),
    )
    entries.append(
      build_matcher( 'WARNING',
        "is assigned but its value is never used", 9, 8 ),
    )
    if flag:
      entries.append(
        build_matcher( 'ERROR',
          "Program has more than one entry point defined. Compile with /main"
          + " to specify the type that contains the entry point.", 7, 22 ),
      )
  else:
    entries.append(
      build_matcher( 'ERROR', "Unexpected symbol `}'', expecting identifier",
                      11, 2 )
    )
  return contains( *entries )
