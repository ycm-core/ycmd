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

from ...server_utils import SetUpPythonPath
SetUpPythonPath()
from ..test_utils import ( Setup,
                           BuildRequest )
from .utils import ( PathToTestFile, StopOmniSharpServer,
                     WaitUntilOmniSharpServerReady )
from webtest import TestApp
from nose.tools import with_setup
from hamcrest import ( assert_that,
                       contains,
                       contains_string,
                       has_entries,
                       has_entry,
                       equal_to )
from ... import handlers
import bottle

bottle.debug( True )


@with_setup( Setup )
def Diagnostics_CsCompleter_ZeroBasedLineAndColumn_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy', 'Program.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  results = app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app, filepath )

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

  StopOmniSharpServer( app, filepath )


@with_setup( Setup )
def Diagnostics_CsCompleter_MultipleSolution_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepaths = [ PathToTestFile( 'testy', 'Program.cs' ),
                PathToTestFile( 'testy-multiple-solutions',
                                'solution-named-like-folder',
                                'testy',
                                'Program.cs' ) ]
  lines = [ 11, 10 ]
  for filepath, line in zip( filepaths, lines ):
    contents = open( filepath ).read()
    event_data = BuildRequest( filepath = filepath,
                               filetype = 'cs',
                               contents = contents,
                               event_name = 'FileReadyToParse' )

    results = app.post_json( '/event_notification', event_data )
    WaitUntilOmniSharpServerReady( app, filepath )

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

    StopOmniSharpServer( app, filepath )


@with_setup( Setup )
def GetDetailedDiagnostic_CsCompleter_Works_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy', 'Program.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app, filepath )
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

  StopOmniSharpServer( app, filepath )
