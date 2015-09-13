#!/usr/bin/env python
#
# Copyright (C) 2013  Google Inc.
#
# This file is part of YouCompleteMe.
#
# YouCompleteMe is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# YouCompleteMe is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with YouCompleteMe.  If not, see <http://www.gnu.org/licenses/>.

from ..server_utils import SetUpPythonPath
SetUpPythonPath()
from .test_utils import ( Setup,
                          BuildRequest,
                          PathToTestFile,
                          StopOmniSharpServer,
                          WaitUntilOmniSharpServerReady )
from webtest import TestApp
from nose.tools import with_setup, eq_
from hamcrest import ( assert_that,
                       contains,
                       contains_string,
                       has_entries,
                       has_entry,
                       has_items,
                       empty,
                       equal_to )
from ..responses import NoDiagnosticSupport
from .. import handlers
import bottle
import httplib
from pprint import pprint

bottle.debug( True )

@with_setup( Setup )
def Diagnostics_ClangCompleter_ZeroBasedLineAndColumn_test():
  app = TestApp( handlers.app )
  contents = """
void foo() {
  double baz = "foo";
}
// Padding to 5 lines
// Padding to 5 lines
"""

  event_data = BuildRequest( compilation_flags = ['-x', 'c++'],
                             event_name = 'FileReadyToParse',
                             contents = contents,
                             filetype = 'cpp' )

  results = app.post_json( '/event_notification', event_data ).json
  assert_that( results,
               contains(
                  has_entries( {
                    'kind': equal_to( 'ERROR' ),
                    'text': contains_string( 'cannot initialize' ),
                    'ranges': contains( has_entries( {
                      'start': has_entries( {
                        'line_num': 3,
                        'column_num': 16,
                      } ),
                      'end': has_entries( {
                        'line_num': 3,
                        'column_num': 21,
                      } ),
                    } ) ),
                    'location': has_entries( {
                      'line_num': 3,
                      'column_num': 10
                    } ),
                    'location_extent': has_entries( {
                      'start': has_entries( {
                        'line_num': 3,
                        'column_num': 10,
                      } ),
                      'end': has_entries( {
                        'line_num': 3,
                        'column_num': 13,
                      } ),
                    } )
                  } ) ) )


@with_setup( Setup )
def Diagnostics_ClangCompleter_SimpleLocationExtent_test():
  app = TestApp( handlers.app )
  contents = """
void foo() {
  baz = 5;
}
// Padding to 5 lines
// Padding to 5 lines
"""

  event_data = BuildRequest( compilation_flags = ['-x', 'c++'],
                             event_name = 'FileReadyToParse',
                             contents = contents,
                             filetype = 'cpp' )

  results = app.post_json( '/event_notification', event_data ).json
  assert_that( results,
               contains(
                  has_entries( {
                    'location_extent': has_entries( {
                      'start': has_entries( {
                        'line_num': 3,
                        'column_num': 3,
                      } ),
                      'end': has_entries( {
                        'line_num': 3,
                        'column_num': 6,
                      } ),
                    } )
                  } ) ) )


@with_setup( Setup )
def Diagnostics_ClangCompleter_PragmaOnceWarningIgnored_test():
  app = TestApp( handlers.app )
  contents = """
#pragma once

struct Foo {
  int x;
  int y;
  int c;
  int d;
};
"""

  event_data = BuildRequest( compilation_flags = ['-x', 'c++'],
                             event_name = 'FileReadyToParse',
                             contents = contents,
                             filepath = '/foo.h',
                             filetype = 'cpp' )

  response = app.post_json( '/event_notification', event_data ).json
  assert_that( response, empty() )

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
def GetDetailedDiagnostic_ClangCompleter_Works_test():
  app = TestApp( handlers.app )
  contents = """
struct Foo {
  int x  // semicolon missing here!
  int y;
  int c;
  int d;
};
"""

  diag_data = BuildRequest( compilation_flags = ['-x', 'c++'],
                            line_num = 3,
                            contents = contents,
                            filetype = 'cpp' )

  event_data = diag_data.copy()
  event_data.update( {
    'event_name': 'FileReadyToParse',
  } )

  app.post_json( '/event_notification', event_data )
  results = app.post_json( '/detailed_diagnostic', diag_data ).json
  assert_that( results,
               has_entry( 'message', contains_string( "expected ';'" ) ) )


@with_setup( Setup )
def GetDetailedDiagnostic_ClangCompleter_Multiline_test():
  app = TestApp( handlers.app )
  contents = """
struct Foo {
  Foo(int z) {}
};

int main() {
  Foo foo("goo");
}
"""

  diag_data = BuildRequest( compilation_flags = ['-x', 'c++'],
                            line_num = 7,
                            contents = contents,
                            filetype = 'cpp' )

  event_data = diag_data.copy()
  event_data.update( {
    'event_name': 'FileReadyToParse',
  } )

  app.post_json( '/event_notification', event_data )
  results = app.post_json( '/detailed_diagnostic', diag_data ).json
  assert_that( results,
               has_entry( 'message', contains_string( "\n" ) ) )


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


@with_setup( Setup )
def GetDetailedDiagnostic_JediCompleter_DoesntWork_test():
  app = TestApp( handlers.app )
  diag_data = BuildRequest( contents = "foo = 5",
                            line_num = 2,
                            filetype = 'python' )
  response = app.post_json( '/detailed_diagnostic',
                            diag_data,
                            expect_errors = True )

  eq_( response.status_code, httplib.INTERNAL_SERVER_ERROR )
  assert_that( response.json,
               has_entry( 'exception',
                          has_entry( 'TYPE', NoDiagnosticSupport.__name__ ) ) )



@with_setup( Setup )
def Diagnostics_ClangCompleter_FixIt_Available_test():
  app = TestApp( handlers.app )
  contents = open( PathToTestFile( 'FixIt_Clang_cpp11.cpp' ) ).read()

  event_data = BuildRequest( contents = contents,
                             event_name = 'FileReadyToParse',
                             filetype = 'cpp',
                             compilation_flags = [ '-x', 'c++',
                                                   '-std=c++03',
                                                   '-Wall',
                                                   '-Wextra',
                                                   '-pedantic' ] )

  response = app.post_json( '/event_notification', event_data ).json

  pprint( response )

  assert_that( response, has_items (
    has_entries( {
      'location' : has_entries( { 'line_num': 16, 'column_num': 3 } ),
      'text': equal_to( 'switch condition type \'A\' '
                        'requires explicit conversion to \'int\''),
      'fixit_available' : True
    } ),
    has_entries( {
      'location' : has_entries( { 'line_num': 11, 'column_num': 3 } ),
      'text': equal_to('explicit conversion functions are a C++11 extension'),
      'fixit_available' : False
    } ),
  ) )
