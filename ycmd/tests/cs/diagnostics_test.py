#!/usr/bin/env python
#
# Copyright (C) 2015 ycmd contributors.
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

from hamcrest import ( assert_that, contains, contains_string, equal_to,
                       has_entries, has_entry )
from .cs_handlers_test import Cs_Handlers_test


class Cs_Diagnostics_test( Cs_Handlers_test ):

  def ZeroBasedLineAndColumn_test( self ):
    filepath = self._PathToTestFile( 'testy', 'Program.cs' )
    contents = open( filepath ).read()
    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'cs',
                                     contents = contents,
                                     event_name = 'FileReadyToParse' )

    results = self._app.post_json( '/event_notification', event_data )
    self._WaitUntilOmniSharpServerReady( filepath )

    event_data = self._BuildRequest( filepath = filepath,
                                     event_name = 'FileReadyToParse',
                                     filetype = 'cs',
                                     contents = contents )

    results = self._app.post_json( '/event_notification', event_data ).json

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

    self._StopOmniSharpServer( filepath )


  def MultipleSolution_test( self ):
    filepaths = [ self._PathToTestFile( 'testy', 'Program.cs' ),
                  self._PathToTestFile( 'testy-multiple-solutions',
                                        'solution-named-like-folder',
                                        'testy',
                                        'Program.cs' ) ]
    lines = [ 11, 10 ]
    for filepath, line in zip( filepaths, lines ):
      contents = open( filepath ).read()
      event_data = self._BuildRequest( filepath = filepath,
                                       filetype = 'cs',
                                       contents = contents,
                                       event_name = 'FileReadyToParse' )

      results = self._app.post_json( '/event_notification', event_data )
      self._WaitUntilOmniSharpServerReady( filepath )

      event_data = self._BuildRequest( filepath = filepath,
                                       event_name = 'FileReadyToParse',
                                       filetype = 'cs',
                                       contents = contents )

      results = self._app.post_json( '/event_notification', event_data ).json

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

      self._StopOmniSharpServer( filepath )


  # This test seems identical to ZeroBasedLineAndColumn one
  def Basic_test( self ):
    filepath = self._PathToTestFile( 'testy', 'Program.cs' )
    contents = open( filepath ).read()
    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'cs',
                                     contents = contents,
                                     event_name = 'FileReadyToParse' )

    self._app.post_json( '/event_notification', event_data )
    self._WaitUntilOmniSharpServerReady( filepath )
    self._app.post_json( '/event_notification', event_data )

    diag_data = self._BuildRequest( filepath = filepath,
                                    filetype = 'cs',
                                    contents = contents,
                                    line_num = 11,
                                    column_num = 2 )

    results = self._app.post_json( '/detailed_diagnostic', diag_data ).json
    assert_that( results,
                 has_entry(
                    'message',
                    contains_string(
                       "Unexpected symbol `}'', expecting identifier" ) ) )

    self._StopOmniSharpServer( filepath )
