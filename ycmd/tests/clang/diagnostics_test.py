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

from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from future import standard_library
standard_library.install_aliases()
from builtins import *  # noqa

from hamcrest import ( assert_that, contains, contains_string, has_entries,
                       has_entry, has_items, empty, equal_to )
from pprint import pprint

from ycmd.tests.clang import IsolatedYcmd, PathToTestFile
from ycmd.tests.test_utils import BuildRequest
from ycmd.utils import ReadFile


@IsolatedYcmd
def Diagnostics_ZeroBasedLineAndColumn_test( app ):
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


@IsolatedYcmd
def Diagnostics_SimpleLocationExtent_test( app ):
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


@IsolatedYcmd
def Diagnostics_PragmaOnceWarningIgnored_test( app ):
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


@IsolatedYcmd
def Diagnostics_Works_test( app ):
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


@IsolatedYcmd
def Diagnostics_Multiline_test( app ):
  contents = """
struct Foo {
  Foo(int z) {}
};

int main() {
  Foo foo("goo");
}
"""

  diag_data = BuildRequest( compilation_flags = [ '-x', 'c++' ],
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


@IsolatedYcmd
def Diagnostics_FixIt_Available_test( app ):
  contents = ReadFile( PathToTestFile( 'FixIt_Clang_cpp11.cpp' ) )

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
