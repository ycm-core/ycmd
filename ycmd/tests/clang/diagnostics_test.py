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
from hamcrest import ( assert_that, contains, contains_string, has_entries,
                       has_entry, has_items, empty, equal_to )
from clang_handlers_test import Clang_Handlers_test
from pprint import pprint


class Clang_Diagnostics_test( Clang_Handlers_test ):

  def ZeroBasedLineAndColumn_test( self ):
    contents = """
void foo() {
  double baz = "foo";
}
// Padding to 5 lines
// Padding to 5 lines
"""

    event_data = self._BuildRequest( compilation_flags = ['-x', 'c++'],
                                     event_name = 'FileReadyToParse',
                                     contents = contents,
                                     filetype = 'cpp' )

    results = self._app.post_json( '/event_notification', event_data ).json
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


  def SimpleLocationExtent_test( self ):
    contents = """
void foo() {
  baz = 5;
}
// Padding to 5 lines
// Padding to 5 lines
"""

    event_data = self._BuildRequest( compilation_flags = ['-x', 'c++'],
                                     event_name = 'FileReadyToParse',
                                     contents = contents,
                                     filetype = 'cpp' )

    results = self._app.post_json( '/event_notification', event_data ).json
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


  def PragmaOnceWarningIgnored_test( self ):
    contents = """
#pragma once

struct Foo {
  int x;
  int y;
  int c;
  int d;
};
"""

    event_data = self._BuildRequest( compilation_flags = ['-x', 'c++'],
                                     event_name = 'FileReadyToParse',
                                     contents = contents,
                                     filepath = '/foo.h',
                                     filetype = 'cpp' )

    response = self._app.post_json( '/event_notification', event_data ).json
    assert_that( response, empty() )


  def Works_test( self ):
    contents = """
struct Foo {
  int x  // semicolon missing here!
  int y;
  int c;
  int d;
};
"""

    diag_data = self._BuildRequest( compilation_flags = ['-x', 'c++'],
                                    line_num = 3,
                                    contents = contents,
                                    filetype = 'cpp' )

    event_data = diag_data.copy()
    event_data.update( {
      'event_name': 'FileReadyToParse',
    } )

    self._app.post_json( '/event_notification', event_data )
    results = self._app.post_json( '/detailed_diagnostic', diag_data ).json
    assert_that( results,
                 has_entry( 'message', contains_string( "expected ';'" ) ) )


  def Multiline_test( self ):
    contents = """
struct Foo {
  Foo(int z) {}
};

int main() {
  Foo foo("goo");
}
"""

    diag_data = self._BuildRequest( compilation_flags = [ '-x', 'c++' ],
                                    line_num = 7,
                                    contents = contents,
                                    filetype = 'cpp' )

    event_data = diag_data.copy()
    event_data.update( {
      'event_name': 'FileReadyToParse',
    } )

    self._app.post_json( '/event_notification', event_data )
    results = self._app.post_json( '/detailed_diagnostic', diag_data ).json
    assert_that( results,
                 has_entry( 'message', contains_string( "\n" ) ) )


  def FixIt_Available_test( self ):
    contents = open( self._PathToTestFile( 'FixIt_Clang_cpp11.cpp' ) ).read()

    event_data = self._BuildRequest( contents = contents,
                                     event_name = 'FileReadyToParse',
                                     filetype = 'cpp',
                                     compilation_flags = [ '-x', 'c++',
                                                           '-std=c++03',
                                                           '-Wall',
                                                           '-Wextra',
                                                           '-pedantic' ] )

    response = self._app.post_json( '/event_notification', event_data ).json

    pprint( response )

    assert_that( response, has_items(
      has_entries( {
        'location': has_entries( { 'line_num': 16, 'column_num': 3 } ),
        'text': equal_to( 'switch condition type \'A\' '
                          'requires explicit conversion to \'int\''),
        'fixit_available': True
      } ),
      has_entries( {
        'location': has_entries( { 'line_num': 11, 'column_num': 3 } ),
        'text': equal_to(
           'explicit conversion functions are a C++11 extension' ),
        'fixit_available': False
      } ),
    ) )
