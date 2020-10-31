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

import os
from pprint import pformat
from hamcrest import ( assert_that,
                       contains_exactly,
                       contains_string,
                       empty,
                       equal_to,
                       has_entries,
                       has_entry,
                       has_items )
from unittest.mock import patch
from pprint import pprint

from ycmd.tests.clangd import ( IsolatedYcmd,
                                PathToTestFile,
                                RunAfterInitialized )
from ycmd.tests.test_utils import ( BuildRequest,
                                    LocationMatcher,
                                    RangeMatcher,
                                    PollForMessages,
                                    TemporaryTestDir,
                                    UnixOnly )
from ycmd.utils import ReadFile
from ycmd import handlers


@IsolatedYcmd()
def Diagnostics_ZeroBasedLineAndColumn_test( app ):
  contents = """
void foo() {
  double baz = "foo";
}
// Padding to 5 lines
// Padding to 5 lines
"""

  filepath = PathToTestFile( 'foo.cc' )
  request = { 'contents': contents,
              'filepath': filepath,
              'filetype': 'cpp' }

  test = { 'request': request, 'route': '/receive_messages' }
  results = RunAfterInitialized( app, test )
  assert_that( results, contains_exactly(
    has_entries( { 'diagnostics': contains_exactly(
      has_entries( {
        'kind': equal_to( 'ERROR' ),
        'text': contains_string( 'Cannot initialize' ),
        'ranges': contains_exactly(
          RangeMatcher( filepath, ( 3, 10 ), ( 3, 13 ) ) ),
        'location': LocationMatcher( filepath, 3, 10 ),
        'location_extent': RangeMatcher( filepath, ( 3, 10 ), ( 3, 13 ) )
      } )
    ) } )
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

  filepath = PathToTestFile( 'foo.cc' )
  request = { 'contents': contents,
              'filepath': filepath,
              'filetype': 'cpp' }
  test = { 'request': request, 'route': '/receive_messages' }
  results = RunAfterInitialized( app, test )
  assert_that( results, contains_exactly(
    has_entries( { 'diagnostics': contains_exactly(
      has_entries( {
        'location_extent': RangeMatcher( filepath, ( 3, 3 ), ( 3, 6 ) )
      } )
    ) } ) ) )


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

  request = { 'contents': contents,
              'filepath': PathToTestFile( 'foo.h' ),
              'filetype': 'cpp' }
  test = { 'request': request, 'route': '/receive_messages' }
  response = RunAfterInitialized( app, test )
  assert_that( response, contains_exactly(
      has_entries( { 'diagnostics': empty() } ) ) )


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

  filepath = PathToTestFile( 'foo.cc' )
  request = { 'contents': contents,
              'filepath': filepath,
              'filetype': 'cpp' }

  test = { 'request': request, 'route': '/receive_messages' }
  RunAfterInitialized( app, test )
  diag_data = BuildRequest( line_num = 3,
                            contents = contents,
                            filepath = filepath,
                            filetype = 'cpp' )

  results = app.post_json( '/detailed_diagnostic', diag_data ).json
  assert_that( results,
               has_entry( 'message', contains_string( "Expected ';'" ) ) )


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

  filepath = PathToTestFile( 'foo.cc' )
  request = { 'contents': contents,
              'filepath': filepath,
              'filetype': 'cpp' }

  test = { 'request': request, 'route': '/receive_messages' }
  RunAfterInitialized( app, test )
  diag_data = BuildRequest( line_num = 7,
                            contents = contents,
                            filepath = filepath,
                            filetype = 'cpp' )

  results = app.post_json( '/detailed_diagnostic', diag_data ).json
  assert_that( results,
               has_entry( 'message', contains_string( "\n" ) ) )


@IsolatedYcmd()
def Diagnostics_FixIt_Available_test( app ):
  filepath = PathToTestFile( 'FixIt_Clang_cpp11.cpp' )
  contents = ReadFile( filepath )
  request = { 'contents': contents,
              'filepath': filepath,
              'filetype': 'cpp' }

  test = { 'request': request, 'route': '/receive_messages' }
  response = RunAfterInitialized( app, test )

  pprint( response )

  assert_that( response, has_items(
    has_entries( { 'diagnostics': has_items(
      has_entries( {
        'location': LocationMatcher( filepath, 16, 3 ),
        'text': contains_string( 'Switch condition type \'A\' '
                                 'requires explicit conversion to \'int\'' ),
        'fixit_available': False
      } )
    ) } )
  ) )


@IsolatedYcmd()
def Diagnostics_MultipleMissingIncludes_test( app ):
  filepath = PathToTestFile( 'multiple_missing_includes.cc' )
  contents = ReadFile( filepath )
  request = { 'contents': contents,
              'filepath': filepath,
              'filetype': 'cpp' }

  test = { 'request': request, 'route': '/receive_messages' }
  response = RunAfterInitialized( app, test )

  pprint( response )

  assert_that( response, has_items(
    has_entries( { 'diagnostics': has_items(
      has_entries( {
        'kind': equal_to( 'ERROR' ),
        'location': LocationMatcher( filepath, 1, 10 ),
        'text': equal_to( "'first_missing_include' file not found"
                          " [pp_file_not_found]" ),
        'fixit_available': False
      } )
    ) } )
  ) )


@IsolatedYcmd()
def Diagnostics_LocationExtent_MissingSemicolon_test( app ):
  filepath = PathToTestFile( 'location_extent.cc' )
  contents = ReadFile( filepath )
  request = { 'contents': contents,
              'filepath': filepath,
              'filetype': 'cpp' }

  test = { 'request': request, 'route': '/receive_messages' }
  response = RunAfterInitialized( app, test )

  pprint( response )

  assert_that( response, contains_exactly(
    has_entries( { 'diagnostics': has_items(
      has_entries( {
        'kind': equal_to( 'ERROR' ),
        'location': LocationMatcher( filepath, 2, 9 ),
        'location_extent': RangeMatcher( filepath, ( 2, 9 ), ( 2, 9 ) ),
        'ranges': contains_exactly(
          RangeMatcher( filepath, ( 2, 9 ), ( 2, 9 ) ) ),
        'text': equal_to( "Expected ';' at end of declaration list (fix "
                          "available) [expected_semi_decl_list]" ),
        'fixit_available': False
      } ),
      has_entries( {
        'kind': equal_to( 'ERROR' ),
        'location': LocationMatcher( filepath, 5, 1 ),
        'location_extent': RangeMatcher( filepath, ( 5, 1 ), ( 6, 11 ) ),
        'ranges': contains_exactly(
          RangeMatcher( filepath, ( 5, 1 ), ( 6, 11 ) ) ),
        'text': equal_to( "Unknown type name 'multiline_identifier'"
                          " [unknown_typename]" ),
        'fixit_available': False
      } ),
      has_entries( {
        'kind': equal_to( 'ERROR' ),
        'location': LocationMatcher( filepath, 8, 7 ),
        'location_extent': RangeMatcher( filepath, ( 8, 7 ), ( 8, 11 ) ),
        'ranges': contains_exactly(
          RangeMatcher( filepath, ( 8, 7 ), ( 8, 11 ) ) ),
        'text': equal_to( 'Constructor cannot have a return type'
                          ' [constructor_return_type]' ),
        'fixit_available': False
      } )
    ) } )
  ) )


@IsolatedYcmd()
def Diagnostics_CUDA_Kernel_test( app ):
  filepath = PathToTestFile( 'cuda', 'kernel_call.cu' )
  contents = ReadFile( filepath )
  request = { 'contents': contents,
              'filepath': filepath,
              'filetype': 'cuda' }

  test = { 'request': request, 'route': '/receive_messages' }
  response = RunAfterInitialized( app, test )

  pprint( response )

  assert_that( response, contains_exactly(
    has_entries( { 'diagnostics': has_items(
      has_entries( {
        'kind': equal_to( 'ERROR' ),
        'location': LocationMatcher( filepath, 59, 5 ),
        'location_extent': RangeMatcher( filepath, ( 59, 5 ), ( 59, 6 ) ),
        'ranges': contains_exactly(
          RangeMatcher( filepath, ( 59, 5 ), ( 59, 6 ) ) ),
        'text': equal_to( 'Call to global function \'g1\' not configured'
                          ' [global_call_not_config]' ),
        'fixit_available': False
      } ),
      has_entries( {
        'kind': equal_to( 'ERROR' ),
        'location': LocationMatcher( filepath, 60, 9 ),
        'location_extent': RangeMatcher( filepath, ( 60, 9 ), ( 60, 12 ) ),
        'ranges': contains_exactly(
          RangeMatcher( filepath, ( 60, 9 ), ( 60, 12 ) ) ),
        'text': equal_to( 'Too few execution configuration arguments to kernel '
                          'function call, expected at least 2, have 1'
                          ' [typecheck_call_too_few_args_at_least]' ),
        'fixit_available': False
      } ),
      has_entries( {
        'kind': equal_to( 'ERROR' ),
        'location': LocationMatcher( filepath, 61, 20 ),
        'location_extent': RangeMatcher( filepath, ( 61, 20 ), ( 61, 21 ) ),
        'ranges': contains_exactly(
          RangeMatcher( filepath, ( 61, 20 ), ( 61, 21 ) )
        ),
        'text': equal_to( 'Too many execution configuration arguments to '
                          'kernel function call, expected at most 4, have 5'
                          ' [typecheck_call_too_many_args_at_most]' ),
        'fixit_available': False
      } ),
      has_entries( {
        'kind': equal_to( 'ERROR' ),
        'location': LocationMatcher( filepath, 65, 15 ),
        'location_extent': RangeMatcher( filepath, ( 65, 15 ), ( 65, 16 ) ),
        'ranges': contains_exactly(
          RangeMatcher( filepath, ( 65, 15 ), ( 65, 16 ) ) ),
        'text': equal_to( 'Kernel call to non-global function \'h1\''
                          ' [kern_call_not_global_function]' ),
        'fixit_available': False
      } ),
      has_entries( {
        'kind': equal_to( 'ERROR' ),
        'location': LocationMatcher( filepath, 68, 15 ),
        'location_extent': RangeMatcher( filepath, ( 68, 15 ), ( 68, 16 ) ),
        'ranges': contains_exactly(
          RangeMatcher( filepath, ( 68, 15 ), ( 68, 16 ) ) ),
        'text': equal_to( "Kernel function type 'int (*)(int)' must have "
                          "void return type [kern_type_not_void_return]" ),
        'fixit_available': False
      } ),
      has_entries( {
        'kind': equal_to( 'ERROR' ),
        'location': LocationMatcher( filepath, 70, 8 ),
        'location_extent': RangeMatcher( filepath, ( 70, 8 ), ( 70, 18 ) ),
        'ranges': contains_exactly(
          RangeMatcher( filepath, ( 70, 8 ), ( 70, 18 ) ) ),
        'text': equal_to( "Use of undeclared identifier 'undeclared'"
                           ' [undeclared_var_use]' ),
        'fixit_available': False
      } ),
    ) } )
  ) )


@IsolatedYcmd( { 'max_diagnostics_to_display': 1 } )
def Diagnostics_MaximumDiagnosticsNumberExceeded_test( app ):
  filepath = PathToTestFile( 'max_diagnostics.cc' )
  contents = ReadFile( filepath )
  request = { 'contents': contents,
              'filepath': filepath,
              'filetype': 'cpp' }

  test = { 'request': request, 'route': '/receive_messages' }
  response = RunAfterInitialized( app, test )

  pprint( response )

  assert_that( response, contains_exactly(
    has_entries( { 'diagnostics': has_items(
      has_entries( {
        'kind': equal_to( 'ERROR' ),
        'location': LocationMatcher( filepath, 3, 9 ),
        'location_extent': RangeMatcher( filepath, ( 3, 9 ), ( 3, 13 ) ),
        'ranges': contains_exactly(
          RangeMatcher( filepath, ( 3, 9 ), ( 3, 13 ) ) ),
        'text': contains_string( "Redefinition of 'test'" ),
        'fixit_available': False
      } ),
      has_entries( {
        'kind': equal_to( 'ERROR' ),
        'location': LocationMatcher( filepath, 1, 1 ),
        'location_extent': RangeMatcher( filepath, ( 1, 1 ), ( 1, 1 ) ),
        'ranges': contains_exactly(
          RangeMatcher( filepath, ( 1, 1 ), ( 1, 1 ) ) ),
        'text': equal_to( 'Maximum number of diagnostics exceeded.' ),
        'fixit_available': False
      } )
    ) } )
  ) )


@IsolatedYcmd( { 'max_diagnostics_to_display': 0 } )
def Diagnostics_NoLimitToNumberOfDiagnostics_test( app ):
  filepath = PathToTestFile( 'max_diagnostics.cc' )
  contents = ReadFile( filepath )
  request = { 'contents': contents,
              'filepath': filepath,
              'filetype': 'cpp' }

  test = { 'request': request, 'route': '/receive_messages' }
  response = RunAfterInitialized( app, test )

  pprint( response )

  assert_that( response, contains_exactly(
    has_entries( { 'diagnostics': has_items(
      has_entries( {
        'kind': equal_to( 'ERROR' ),
        'location': LocationMatcher( filepath, 3, 9 ),
        'location_extent': RangeMatcher( filepath, ( 3, 9 ), ( 3, 13 ) ),
        'ranges': contains_exactly(
          RangeMatcher( filepath, ( 3, 9 ), ( 3, 13 ) ) ),
        'text': contains_string( "Redefinition of 'test'" ),
        'fixit_available': False
      } ),
      has_entries( {
        'kind': equal_to( 'ERROR' ),
        'location': LocationMatcher( filepath, 4, 9 ),
        'location_extent': RangeMatcher( filepath, ( 4, 9 ), ( 4, 13 ) ),
        'ranges': contains_exactly(
          RangeMatcher( filepath, ( 4, 9 ), ( 4, 13 ) ) ),
        'text': contains_string( "Redefinition of 'test'" ),
        'fixit_available': False
      } )
    ) } )
  ) )


@IsolatedYcmd()
def Diagnostics_DiagsNotReady_test( app ):
  completer = handlers._server_state.GetFiletypeCompleter( [ 'cpp' ] )
  contents = """
struct Foo {
  int x  // semicolon missing here!
  int y;
  int c;
  int d;
};
"""

  filepath = PathToTestFile( 'foo.cc' )
  request = { 'contents': contents,
              'filepath': filepath,
              'filetype': 'cpp' }

  test = { 'request': request, 'route': '/receive_messages' }
  RunAfterInitialized( app, test )
  diag_data = BuildRequest( line_num = 3,
                            contents = contents,
                            filepath = filepath,
                            filetype = 'cpp' )

  with patch.object( completer, '_latest_diagnostics', None ):
    results = app.post_json( '/detailed_diagnostic', diag_data ).json
    assert_that( results,
               has_entry( 'message', contains_string( "are not ready yet" ) ) )


@UnixOnly
@IsolatedYcmd()
def Diagnostics_UpdatedOnBufferVisit_test( app ):
  with TemporaryTestDir() as tmp_dir:
    source_file = os.path.join( tmp_dir, 'source.cpp' )
    source_contents = """#include "header.h"
int main() {return S::h();}
"""
    with open( source_file, 'w' ) as sf:
      sf.write( source_contents )

    header_file = os.path.join( tmp_dir, 'header.h' )
    old_header_content = """#pragma once
struct S{static int h();};
"""
    with open( header_file, 'w' ) as hf:
      hf.write( old_header_content )

    flags_file = os.path.join( tmp_dir, 'compile_flags.txt' )
    flags_content = """-xc++"""
    with open( flags_file, 'w' ) as ff:
      ff.write( flags_content )

    messages_request = { 'contents': source_contents,
                         'filepath': source_file,
                         'filetype': 'cpp' }

    test = { 'request': messages_request, 'route': '/receive_messages' }
    response = RunAfterInitialized( app, test )
    assert_that( response, contains_exactly(
      has_entries( { 'diagnostics': empty() } ) ) )

    # Overwrite header.cpp
    new_header_content = """#pragma once
  static int h();
  """
    with open( header_file, 'w' ) as f:
      f.write( new_header_content )

    # Send BufferSaved notification for the header
    file_save_request = { "event_name": "FileSave",
                          "filepath": header_file,
                          "filetype": 'cpp' }
    app.post_json( '/event_notification',
                   BuildRequest( **file_save_request ) )

    # Send BufferVisit notification
    buffer_visit_request = { "event_name": "BufferVisit",
                             "filepath": source_file,
                             "filetype": 'cpp' }
    app.post_json( '/event_notification',
                   BuildRequest( **buffer_visit_request ) )
    # Assert diagnostics
    for message in PollForMessages( app, messages_request ):
      if 'diagnostics' in message:
        assert_that( message,
          has_entries( { 'diagnostics': contains_exactly(
            has_entries( {
              'kind': equal_to( 'ERROR' ),
              'text': "Use of undeclared identifier 'S' [undeclared_var_use]",
              'ranges': contains_exactly( RangeMatcher(
                contains_string( source_file ), ( 2, 20 ), ( 2, 21 ) ) ),
              'location': LocationMatcher(
                contains_string( source_file ), 2, 20 ),
              'location_extent': RangeMatcher(
                contains_string( source_file ), ( 2, 20 ), ( 2, 21 ) )
            } )
          ) } ) )
        break

    # Restore original content
    with open( header_file, 'w' ) as f:
      f.write( old_header_content )

    # Send BufferSaved notification for the header
    file_save_request = { "event_name": "FileSave",
                          "filepath": header_file,
                          "filetype": 'cpp' }
    app.post_json( '/event_notification',
                   BuildRequest( **file_save_request ) )

    # Send BufferVisit notification
    app.post_json( '/event_notification',
                   BuildRequest( **buffer_visit_request ) )

    # Assert no diagnostics
    for message in PollForMessages( app, messages_request ):
      print( f'Message { pformat( message ) }' )
      if 'diagnostics' in message:
        assert_that( message,
          has_entries( { 'diagnostics': empty() } ) )
        break

    # Assert no dirty files
    with open( header_file, 'r' ) as f:
      assert_that( f.read(), equal_to( old_header_content ) )


def Dummy_test():
  # Workaround for https://github.com/pytest-dev/pytest-rerunfailures/issues/51
  assert True
