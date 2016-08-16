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
from future import standard_library
standard_library.install_aliases()
from builtins import *  # noqa

from hamcrest import ( assert_that, contains, contains_string, equal_to,
                       has_entries, has_entry )

from ycmd.tests.cs import PathToTestFile, SharedYcmd, WrapOmniSharpServer
from ycmd.tests.test_utils import BuildRequest
from ycmd.utils import ReadFile


@SharedYcmd
def Diagnostics_Basic_test( app ):
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
                              line_num = 11,
                              column_num = 2 )

    results = app.post_json( '/detailed_diagnostic', diag_data ).json
    assert_that( results,
                 has_entry(
                     'message',
                     contains_string(
                       "Unexpected symbol `}'', expecting identifier" ) ) )


@SharedYcmd
def Diagnostics_ZeroBasedLineAndColumn_test( app ):
  filepath = PathToTestFile( 'testy', 'Program.cs' )
  with WrapOmniSharpServer( app, filepath ):
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
                       'kind': equal_to( 'ERROR' ),
                       'text': contains_string(
                           "Unexpected symbol `}'', expecting identifier" ),
                       'location': has_entries( {
                         'line_num': 11,
                         'column_num': 2
                       } ),
                       'location_extent': has_entries( {
                         'start': has_entries( {
                           'line_num': 11,
                           'column_num': 2,
                         } ),
                         'end': has_entries( {
                           'line_num': 11,
                           'column_num': 2,
                         } ),
                       } )
                     } ) ) )


@SharedYcmd
def Diagnostics_WithRange_test( app ):
  filepath = PathToTestFile( 'testy', 'DiagnosticRange.cs' )
  with WrapOmniSharpServer( app, filepath ):
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


@SharedYcmd
def Diagnostics_MultipleSolution_test( app ):
  filepaths = [ PathToTestFile( 'testy', 'Program.cs' ),
                PathToTestFile( 'testy-multiple-solutions',
                                'solution-named-like-folder',
                                'testy', 'Program.cs' ) ]
  lines = [ 11, 10 ]
  for filepath, line in zip( filepaths, lines ):
    with WrapOmniSharpServer( app, filepath ):
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
                           'kind': equal_to( 'ERROR' ),
                           'text': contains_string( "Unexpected symbol `}'', "
                                                    "expecting identifier" ),
                           'location': has_entries( {
                             'line_num': line,
                             'column_num': 2
                           } ),
                           'location_extent': has_entries( {
                             'start': has_entries( {
                               'line_num': line,
                               'column_num': 2,
                             } ),
                             'end': has_entries( {
                               'line_num': line,
                               'column_num': 2,
                             } ),
                           } )
                       } ) ) )
