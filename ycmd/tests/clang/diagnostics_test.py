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
from ycmd.tests.test_utils import BuildRequest, LocationMatcher, RangeMatcher
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

  event_data = BuildRequest( compilation_flags = [ '-x', 'c++' ],
                             event_name = 'FileReadyToParse',
                             contents = contents,
                             filepath = 'foo',
                             filetype = 'cpp' )

  results = app.post_json( '/event_notification', event_data ).json
  assert_that( results, contains(
    has_entries( {
      'kind': equal_to( 'ERROR' ),
      'text': contains_string( 'cannot initialize' ),
      'ranges': contains( RangeMatcher( 'foo', ( 3, 16 ), ( 3, 21 ) ) ),
      'location': LocationMatcher( 'foo', 3, 10 ),
      'location_extent': RangeMatcher( 'foo', ( 3, 10 ), ( 3, 13 ) )
    } )
  ) )


@IsolatedYcmd()
def Diagnostics_SimpleLocationExtent_test( app ):
  contents = """
void foo() {
  baz = 5;
}
// Padding to 5 lines
// Padding to 5 lines
"""

  event_data = BuildRequest( compilation_flags = [ '-x', 'c++' ],
                             event_name = 'FileReadyToParse',
                             contents = contents,
                             filepath = 'foo',
                             filetype = 'cpp' )

  results = app.post_json( '/event_notification', event_data ).json
  assert_that( results, contains(
    has_entries( {
      'location_extent': RangeMatcher( 'foo', ( 3, 3 ), ( 3, 6 ) )
    } )
  ) )


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

  event_data = BuildRequest( compilation_flags = [ '-x', 'c++' ],
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

  diag_data = BuildRequest( compilation_flags = [ '-x', 'c++' ],
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
  filepath = PathToTestFile( 'FixIt_Clang_cpp11.cpp' )

  event_data = BuildRequest( contents = ReadFile( filepath ),
                             event_name = 'FileReadyToParse',
                             filepath = filepath,
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
      'location': LocationMatcher( filepath, 16, 3 ),
      'text': equal_to( 'switch condition type \'A\' '
                        'requires explicit conversion to \'int\'' ),
      'fixit_available': True
    } ),
    has_entries( {
      'location': LocationMatcher( filepath, 11, 3 ),
      'text': equal_to(
         'explicit conversion functions are a C++11 extension' ),
      'fixit_available': False
    } ),
  ) )


@IsolatedYcmd()
def Diagnostics_MultipleMissingIncludes_test( app ):
  filepath = PathToTestFile( 'multiple_missing_includes.cc' )

  event_data = BuildRequest( contents = ReadFile( filepath ),
                             event_name = 'FileReadyToParse',
                             filepath = filepath,
                             filetype = 'cpp',
                             compilation_flags = [ '-x', 'c++' ] )

  response = app.post_json( '/event_notification', event_data ).json

  pprint( response )

  assert_that( response, has_items(
    has_entries( {
      'kind': equal_to( 'ERROR' ),
      'location': LocationMatcher( filepath, 1, 10 ),
      'text': equal_to( "'first_missing_include' file not found" ),
      'fixit_available': False
    } ),
    has_entries( {
      'kind': equal_to( 'ERROR' ),
      'location': LocationMatcher( filepath, 2, 10 ),
      'text': equal_to( "'second_missing_include' file not found" ),
      'fixit_available': False
    } ),
  ) )


@IsolatedYcmd()
def Diagnostics_LocationExtent_MissingSemicolon_test( app ):
  filepath = PathToTestFile( 'location_extent.cc' )

  event_data = BuildRequest( contents = ReadFile( filepath ),
                             event_name = 'FileReadyToParse',
                             filepath = filepath,
                             filetype = 'cpp',
                             compilation_flags = [ '-x', 'c++' ] )

  response = app.post_json( '/event_notification', event_data ).json

  pprint( response )

  assert_that( response, contains(
    has_entries( {
      'kind': equal_to( 'ERROR' ),
      'location': LocationMatcher( filepath, 2, 9 ),
      'location_extent': RangeMatcher( filepath, ( 2, 9 ), ( 2, 9 ) ),
      'ranges': empty(),
      'text': equal_to( "expected ';' at end of declaration list" ),
      'fixit_available': True
    } ),
    has_entries( {
      'kind': equal_to( 'ERROR' ),
      'location': LocationMatcher( filepath, 5, 1 ),
      'location_extent': RangeMatcher( filepath, ( 5, 1 ), ( 6, 11 ) ),
      'ranges': empty(),
      'text': equal_to( "unknown type name 'multiline_identifier'" ),
      'fixit_available': False
    } ),
    has_entries( {
      'kind': equal_to( 'ERROR' ),
      'location': LocationMatcher( filepath, 8, 7 ),
      'location_extent': RangeMatcher( filepath, ( 8, 7 ), ( 8, 11 ) ),
      'ranges': contains(
        # FIXME: empty ranges from libclang should be ignored.
        RangeMatcher( '', ( 0, 0 ), ( 0, 0 ) ),
        RangeMatcher( filepath, ( 8, 7 ), ( 8, 11 ) )
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
        'location': LocationMatcher( PathToTestFile( 'unity.h' ), 4, 3 ),
        'location_extent': RangeMatcher( PathToTestFile( 'unity.h' ),
                                         ( 4, 3 ),
                                         ( 4, 14 ) ),
        'ranges': empty(),
        'text': equal_to( "use of undeclared identifier 'fake_method'" ),
        'fixit_available': False
      } ),
      has_entries( {
        'kind': equal_to( 'ERROR' ),
        'location': LocationMatcher( PathToTestFile( 'unitya.cc' ), 11, 18 ),
        'location_extent': RangeMatcher( PathToTestFile( 'unitya.cc' ),
                                         ( 11, 18 ),
                                         ( 11, 18 ) ),
        'ranges': empty(),
        'text': equal_to( "expected ';' after expression" ),
        'fixit_available': True
      } ),
    ) )


@SharedYcmd
def Diagnostics_CUDA_Kernel_test( app ):
  filepath = PathToTestFile( 'cuda', 'kernel_call.cu' )

  event_data = BuildRequest( filepath = filepath,
                             contents = ReadFile( filepath ),
                             event_name = 'FileReadyToParse',
                             filetype = 'cuda',
                             compilation_flags = [ '-x', 'cuda', '-nocudainc',
                                                   '-nocudalib' ] )

  response = app.post_json( '/event_notification', event_data ).json

  pprint( response )

  assert_that( response, contains_inanyorder(
    has_entries( {
      'kind': equal_to( 'ERROR' ),
      'location': LocationMatcher( filepath, 59, 5 ),
      'location_extent': RangeMatcher( filepath, ( 59, 5 ), ( 59, 6 ) ),
      'ranges': contains( RangeMatcher( filepath, ( 59, 3 ), ( 59, 5 ) ) ),
      'text': equal_to( "call to global function 'g1' not configured" ),
      'fixit_available': False
    } ),
    has_entries( {
      'kind': equal_to( 'ERROR' ),
      'location': LocationMatcher( filepath, 60, 9 ),
      'location_extent': RangeMatcher( filepath, ( 60, 9 ), ( 60, 12 ) ),
      'ranges': contains( RangeMatcher( filepath, ( 60, 5 ), ( 60, 8 ) ) ),
      'text': equal_to(
        'too few execution configuration arguments to kernel function call, '
        'expected at least 2, have 1'
      ),
      'fixit_available': False
    } ),
    has_entries( {
      'kind': equal_to( 'ERROR' ),
      'location': LocationMatcher( filepath, 61, 20 ),
      'location_extent': RangeMatcher( filepath, ( 61, 20 ), ( 61, 21 ) ),
      'ranges': contains(
        RangeMatcher( filepath, ( 61, 5 ), ( 61, 8 ) ),
        RangeMatcher( filepath, ( 61, 20 ), ( 61, 21 ) )
      ),
      'text': equal_to( 'too many execution configuration arguments to kernel '
                        'function call, expected at most 4, have 5' ),
      'fixit_available': False
    } ),
    has_entries( {
      'kind': equal_to( 'ERROR' ),
      'location': LocationMatcher( filepath, 65, 15 ),
      'location_extent': RangeMatcher( filepath, ( 65, 15 ), ( 65, 16 ) ),
      'ranges': contains( RangeMatcher( filepath, ( 65, 3 ), ( 65, 5 ) ) ),
      'text': equal_to( "kernel call to non-global function 'h1'" ),
      'fixit_available': False
    } ),
    has_entries( {
      'kind': equal_to( 'ERROR' ),
      'location': LocationMatcher( filepath, 68, 15 ),
      'location_extent': RangeMatcher( filepath, ( 68, 15 ), ( 68, 16 ) ),
      'ranges': contains( RangeMatcher( filepath, ( 68, 3 ), ( 68, 5 ) ) ),
      'text': equal_to( "kernel function type 'int (*)(int)' must have "
                        "void return type" ),
      'fixit_available': False
    } ),
    has_entries( {
      'kind': equal_to( 'ERROR' ),
      'location': LocationMatcher( filepath, 70, 8 ),
      'location_extent': RangeMatcher( filepath, ( 70, 8 ), ( 70, 18 ) ),
      'ranges': empty(),
      'text': equal_to( "use of undeclared identifier 'undeclared'" ),
      'fixit_available': False
    } ),
  ) )


@IsolatedYcmd( { 'max_diagnostics_to_display': 1 } )
def Diagnostics_MaximumDiagnosticsNumberExceeded_test( app ):
  filepath = PathToTestFile( 'max_diagnostics.cc' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( contents = contents,
                             event_name = 'FileReadyToParse',
                             filetype = 'cpp',
                             filepath = filepath,
                             compilation_flags = [ '-x', 'c++' ] )

  response = app.post_json( '/event_notification', event_data ).json

  pprint( response )

  assert_that( response, contains(
    has_entries( {
      'kind': equal_to( 'ERROR' ),
      'location': LocationMatcher( filepath, 3, 9 ),
      'location_extent': RangeMatcher( filepath, ( 3, 9 ), ( 3, 13 ) ),
      'ranges': empty(),
      'text': equal_to( "redefinition of 'test'" ),
      'fixit_available': False
    } ),
    has_entries( {
      'kind': equal_to( 'ERROR' ),
      'location': LocationMatcher( filepath, 1, 1 ),
      'location_extent': RangeMatcher( filepath, ( 1, 1 ), ( 1, 1 ) ),
      'ranges': contains( RangeMatcher( filepath, ( 1, 1 ), ( 1, 1 ) ) ),
      'text': equal_to( 'Maximum number of diagnostics exceeded.' ),
      'fixit_available': False
    } )
  ) )


@IsolatedYcmd( { 'max_diagnostics_to_display': 0 } )
def Diagnostics_NoLimitToNumberOfDiagnostics_test( app ):
  filepath = PathToTestFile( 'max_diagnostics.cc' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( contents = contents,
                             event_name = 'FileReadyToParse',
                             filetype = 'cpp',
                             filepath = filepath,
                             compilation_flags = [ '-x', 'c++' ] )

  response = app.post_json( '/event_notification', event_data ).json

  pprint( response )

  assert_that( response, contains(
    has_entries( {
      'kind': equal_to( 'ERROR' ),
      'location': LocationMatcher( filepath, 3, 9 ),
      'location_extent': RangeMatcher( filepath, ( 3, 9 ), ( 3, 13 ) ),
      'ranges': empty(),
      'text': equal_to( "redefinition of 'test'" ),
      'fixit_available': False
    } ),
    has_entries( {
      'kind': equal_to( 'ERROR' ),
      'location': LocationMatcher( filepath, 4, 9 ),
      'location_extent': RangeMatcher( filepath, ( 4, 9 ), ( 4, 13 ) ),
      'ranges': empty(),
      'text': equal_to( "redefinition of 'test'" ),
      'fixit_available': False
    } )
  ) )
