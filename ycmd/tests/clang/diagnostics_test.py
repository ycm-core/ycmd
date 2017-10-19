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
# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa

from hamcrest import ( assert_that,
                       contains,
                       contains_inanyorder,
                       contains_string,
                       has_entries,
                       has_entry,
                       has_items,
                       empty,
                       equal_to )
from pprint import pprint

from ycmd.tests.clang import SharedYcmd, IsolatedYcmd, PathToTestFile
from ycmd.tests.test_utils import BuildRequest
from ycmd.utils import ReadFile


@IsolatedYcmd()
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


@IsolatedYcmd()
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


@IsolatedYcmd()
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


@IsolatedYcmd()
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


@IsolatedYcmd()
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


@IsolatedYcmd()
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


@IsolatedYcmd()
def Diagnostics_MultipleMissingIncludes_test( app ):
  contents = ReadFile( PathToTestFile( 'multiple_missing_includes.cc' ) )

  event_data = BuildRequest( contents = contents,
                             event_name = 'FileReadyToParse',
                             filetype = 'cpp',
                             compilation_flags = [ '-x', 'c++' ] )

  response = app.post_json( '/event_notification', event_data ).json

  pprint( response )

  assert_that( response, has_items(
    has_entries( {
      'kind': equal_to( 'ERROR' ),
      'location': has_entries( { 'line_num': 1, 'column_num': 10 } ),
      'text': equal_to( "'first_missing_include' file not found" ),
      'fixit_available': False
    } ),
    has_entries( {
      'kind': equal_to( 'ERROR' ),
      'location': has_entries( { 'line_num': 2, 'column_num': 10 } ),
      'text': equal_to( "'second_missing_include' file not found" ),
      'fixit_available': False
    } ),
  ) )


@IsolatedYcmd()
def Diagnostics_LocationExtent_MissingSemicolon_test( app ):
  contents = ReadFile( PathToTestFile( 'location_extent.cc' ) )

  event_data = BuildRequest( contents = contents,
                             event_name = 'FileReadyToParse',
                             filetype = 'cpp',
                             filepath = 'foo',
                             compilation_flags = [ '-x', 'c++' ] )

  response = app.post_json( '/event_notification', event_data ).json

  pprint( response )

  assert_that( response, contains(
    has_entries( {
      'kind': equal_to( 'ERROR' ),
      'location': has_entries( {
        'line_num': 2,
        'column_num': 9,
        'filepath': 'foo'
      } ),
      'location_extent': has_entries( {
        'start': has_entries( {
          'line_num': 2,
          'column_num': 9,
          'filepath': 'foo'
        } ),
        'end': has_entries( {
          'line_num': 2,
          'column_num': 9,
          'filepath': 'foo'
        } )
      } ),
      'ranges': empty(),
      'text': equal_to( "expected ';' at end of declaration list" ),
      'fixit_available': True
    } ),
    has_entries( {
      'kind': equal_to( 'ERROR' ),
      'location': has_entries( {
        'line_num': 5,
        'column_num': 1,
        'filepath': 'foo'
      } ),
      'location_extent': has_entries( {
        'start': has_entries( {
          'line_num': 5,
          'column_num': 1,
          'filepath': 'foo'
        } ),
        'end': has_entries( {
          'line_num': 6,
          'column_num': 11,
          'filepath': 'foo'
        } )
      } ),
      'ranges': empty(),
      'text': equal_to( "unknown type name 'multiline_identifier'" ),
      'fixit_available': False
    } ),
    has_entries( {
      'kind': equal_to( 'ERROR' ),
      'location': has_entries( {
        'line_num': 8,
        'column_num': 7,
        'filepath': 'foo'
      } ),
      'location_extent': has_entries( {
        'start': has_entries( {
          'line_num': 8,
          'column_num': 7,
          'filepath': 'foo'
        } ),
        'end': has_entries( {
          'line_num': 8,
          'column_num': 11,
          'filepath': 'foo'
        } )
      } ),
      'ranges': contains(
        # FIXME: empty ranges from libclang should be ignored.
        has_entries( {
          'start': has_entries( {
            'line_num': 0,
            'column_num': 0,
            'filepath': ''
          } ),
          'end': has_entries( {
            'line_num': 0,
            'column_num': 0,
            'filepath': ''
          } )
        } ),
        has_entries( {
          'start': has_entries( {
            'line_num': 8,
            'column_num': 7,
            'filepath': 'foo'
          } ),
          'end': has_entries( {
            'line_num': 8,
            'column_num': 11,
            'filepath': 'foo'
          } )
        } )
      ),
      'text': equal_to( 'constructor cannot have a return type' ),
      'fixit_available': False
    } )
  ) )


@SharedYcmd
def Diagnostics_Unity_test( app ):
  app.post_json( '/load_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )

  for filename in [ 'unity.cc', 'unity.h', 'unitya.cc' ]:
    contents = ReadFile( PathToTestFile( filename ) )

    event_data = BuildRequest( filepath = PathToTestFile( filename ),
                               contents = contents,
                               event_name = 'FileReadyToParse',
                               filetype = 'cpp' )

    response = app.post_json( '/event_notification', event_data ).json

    pprint( response )

    assert_that( response, contains_inanyorder(
      has_entries( {
        'kind': equal_to( 'ERROR' ),
        'location': has_entries( {
          'line_num': 4,
          'column_num': 3,
          'filepath': PathToTestFile( 'unity.h' )
        } ),
        'location_extent': has_entries( {
          'start': has_entries( {
            'line_num': 4,
            'column_num': 3,
            'filepath': PathToTestFile( 'unity.h' )
          } ),
          'end': has_entries( {
            'line_num': 4,
            'column_num': 14,
            'filepath': PathToTestFile( 'unity.h' )
          } ),
        } ),
        'ranges': empty(),
        'text': equal_to( "use of undeclared identifier 'fake_method'" ),
        'fixit_available': False
      } ),
      has_entries( {
        'kind': equal_to( 'ERROR' ),
        'location': has_entries( {
          'line_num': 11,
          'column_num': 18,
          'filepath': PathToTestFile( 'unitya.cc' )
        } ),
        'location_extent': has_entries( {
          'start': has_entries( {
            'line_num': 11,
            'column_num': 18,
            'filepath': PathToTestFile( 'unitya.cc' )
          } ),
          'end': has_entries( {
            'line_num': 11,
            'column_num': 18,
            'filepath': PathToTestFile( 'unitya.cc' )
          } ),
        } ),
        'ranges': empty(),
        'text': equal_to( "expected ';' after expression" ),
        'fixit_available': True
      } ),
    ) )
