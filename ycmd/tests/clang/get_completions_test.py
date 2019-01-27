# encoding: utf-8
#
# Copyright (C) 2015-2019 ycmd contributors
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

import json
import requests
import ycm_core
from mock import patch
from nose.tools import eq_
from hamcrest import ( all_of,
                       assert_that,
                       contains,
                       contains_inanyorder,
                       empty,
                       has_item,
                       has_items,
                       has_entry,
                       has_entries,
                       is_not,
                       matches_regexp )

from ycmd import handlers
from ycmd.completers.cpp.clang_completer import ( NO_COMPLETIONS_MESSAGE,
                                                  NO_COMPILE_FLAGS_MESSAGE,
                                                  PARSING_FILE_MESSAGE )
from ycmd.responses import UnknownExtraConf, NoExtraConfDetected
from ycmd.tests.clang import ( IsolatedYcmd,
                               MockCoreClangCompleter,
                               PathToTestFile,
                               SharedYcmd )
from ycmd.tests.test_utils import ( BuildRequest,
                                    ChunkMatcher,
                                    CombineRequest,
                                    CompletionEntryMatcher,
                                    ErrorMatcher,
                                    ExpectedFailure,
                                    LocationMatcher,
                                    WindowsOnly )
from ycmd.utils import ReadFile

NO_COMPLETIONS_ERROR = ErrorMatcher( RuntimeError, NO_COMPLETIONS_MESSAGE )


def RunTest( app, test ):
  """
  Method to run a simple completion test and verify the result

  Note: by default uses the .ycm_extra_conf from general_fallback/ which:
   - supports cpp, c and objc
   - requires extra_conf_data containing 'filetype&' = the filetype

  This should be sufficient for many standard test cases. If not, specify
  a path (as a list of path items) in 'extra_conf' member of |test|.

  test is a dictionary containing:
    'request': kwargs for BuildRequest
    'expect': {
       'response': server response code (e.g. requests.codes.ok)
       'data': matcher for the server response json
    }
    'extra_conf': [ optional list of path items to extra conf file ]
  """

  extra_conf = ( test[ 'extra_conf' ] if 'extra_conf' in test
                                      else [ 'general_fallback',
                                             '.ycm_extra_conf.py' ] )

  app.post_json( '/load_extra_conf_file', {
    'filepath': PathToTestFile( *extra_conf ) } )


  request = test[ 'request' ]
  contents = ( request[ 'contents' ] if 'contents' in request else
               ReadFile( request[ 'filepath' ] ) )

  # Because we aren't testing this command, we *always* ignore errors. This
  # is mainly because we (may) want to test scenarios where the completer
  # throws an exception and the easiest way to do that is to throw from
  # within the Settings function.
  app.post_json( '/event_notification',
                 CombineRequest( request, {
                   'event_name': 'FileReadyToParse',
                   'contents': contents,
                 } ),
                 expect_errors = True )

  # We also ignore errors here, but then we check the response code ourself.
  # This is to allow testing of requests returning errors.
  response = app.post_json( '/completions',
                            CombineRequest( request, {
                              'contents': contents
                            } ),
                            expect_errors = True )

  eq_( response.status_code, test[ 'expect' ][ 'response' ] )

  print( 'Completer response: {0}'.format( json.dumps(
    response.json, indent = 2 ) ) )

  assert_that( response.json, test[ 'expect' ][ 'data' ] )


@SharedYcmd
def GetCompletions_ForcedWithNoTrigger_test( app ):
  RunTest( app, {
    'description': 'semantic completion with force query=DO_SO',
    'request': {
      'filetype'  : 'cpp',
      'filepath'  : PathToTestFile( 'general_fallback',
                                    'lang_cpp.cc' ),
      'line_num'  : 54,
      'column_num': 8,
      'extra_conf_data': { '&filetype': 'cpp' },
      'force_semantic': True,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': contains(
          CompletionEntryMatcher( 'DO_SOMETHING_TO', 'void' ),
          CompletionEntryMatcher( 'DO_SOMETHING_WITH', 'void' ),
        ),
        'errors': empty(),
      } )
    },
  } )


# This test is isolated to make sure we trigger c hook for clangd, instead of
# fetching completer from cache.
@IsolatedYcmd()
def GetCompletions_Fallback_NoSuggestions_test( app ):
  # TESTCASE1 (general_fallback/lang_c.c)
  RunTest( app, {
    'description': 'Triggered, fallback but no query so no completions',
    'request': {
      'filetype'  : 'c',
      'filepath'  : PathToTestFile( 'general_fallback', 'lang_c.c' ),
      'line_num'  : 29,
      'column_num': 21,
      'extra_conf_data': { '&filetype': 'c' },
      'force_semantic': False,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': empty(),
        'errors': has_item( NO_COMPLETIONS_ERROR ),
      } )
    },
  } )


@SharedYcmd
def GetCompletions_Fallback_NoSuggestions_MinimumCharaceters_test( app ):
  # TESTCASE1 (general_fallback/lang_cpp.cc)
  RunTest( app, {
    'description': 'fallback general completion obeys min chars setting '
                   ' (query="a")',
    'request': {
      'filetype'  : 'cpp',
      'filepath'  : PathToTestFile( 'general_fallback',
                                    'lang_cpp.cc' ),
      'line_num'  : 21,
      'column_num': 22,
      'extra_conf_data': { '&filetype': 'cpp' },
      'force_semantic': False,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': empty(),
        'errors': has_item( NO_COMPLETIONS_ERROR ),
      } )
    },
  } )


@SharedYcmd
def GetCompletions_Fallback_Suggestions_test( app ):
  # TESTCASE1 (general_fallback/lang_c.c)
  RunTest( app, {
    'description': '. after macro with some query text (.a_)',
    'request': {
      'filetype'  : 'c',
      'filepath'  : PathToTestFile( 'general_fallback', 'lang_c.c' ),
      'line_num'  : 29,
      'column_num': 23,
      'extra_conf_data': { '&filetype': 'c' },
      'force_semantic': False,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': has_item( CompletionEntryMatcher( 'a_parameter',
                                                         '[ID]' ) ),
        'errors': has_item( NO_COMPLETIONS_ERROR ),
      } )
    },
  } )


@SharedYcmd
def GetCompletions_Fallback_Exception_test( app ):
  # TESTCASE4 (general_fallback/lang_c.c)
  # extra conf throws exception
  RunTest( app, {
    'description': '. on struct returns identifier because of error',
    'request': {
      'filetype'  : 'c',
      'filepath'  : PathToTestFile( 'general_fallback', 'lang_c.c' ),
      'line_num'  : 62,
      'column_num': 20,
      'extra_conf_data': { '&filetype': 'c', 'throw': 'testy' },
      'force_semantic': False,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': contains(
          CompletionEntryMatcher( 'a_parameter', '[ID]' ),
          CompletionEntryMatcher( 'another_parameter', '[ID]' ),
        ),
        'errors': has_item( ErrorMatcher( ValueError, 'testy' ) )
      } )
    },
  } )


@SharedYcmd
def GetCompletions_Forced_NoFallback_test( app ):
  # TESTCASE2 (general_fallback/lang_c.c)
  RunTest( app, {
    'description': '-> after macro with forced semantic',
    'request': {
      'filetype'  : 'c',
      'filepath'  : PathToTestFile( 'general_fallback', 'lang_c.c' ),
      'line_num'  : 41,
      'column_num': 30,
      'extra_conf_data': { '&filetype': 'c' },
      'force_semantic': True,
    },
    'expect': {
      'response': requests.codes.internal_server_error,
      'data': NO_COMPLETIONS_ERROR,
    },
  } )


@SharedYcmd
def GetCompletions_FilteredNoResults_Fallback_test( app ):
  # no errors because the semantic completer returned results, but they
  # were filtered out by the query, so this is considered working OK
  # (whereas no completions from the semantic engine is considered an
  # error)

  # TESTCASE5 (general_fallback/lang_cpp.cc)
  RunTest( app, {
    'description': '. on struct returns IDs after query=do_',
    'request': {
      'filetype':   'c',
      'filepath':   PathToTestFile( 'general_fallback', 'lang_c.c' ),
      'line_num':   71,
      'column_num': 18,
      'extra_conf_data': { '&filetype': 'c' },
      'force_semantic': False,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': contains_inanyorder(
          # do_ is an identifier because it is already in the file when we
          # load it
          CompletionEntryMatcher( 'do_', '[ID]' ),
          CompletionEntryMatcher( 'do_something', '[ID]' ),
          CompletionEntryMatcher( 'do_another_thing', '[ID]' ),
          CompletionEntryMatcher( 'DO_SOMETHING_TO', '[ID]' ),
          CompletionEntryMatcher( 'DO_SOMETHING_VIA', '[ID]' )
        ),
        'errors': empty()
      } )
    },
  } )


@IsolatedYcmd()
def GetCompletions_WorksWithExplicitFlags_test( app ):
  app.post_json(
    '/ignore_extra_conf_file',
    { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  contents = """
struct Foo {
  int x;
  int y;
  char c;
};

int main()
{
  Foo foo;
  foo.
}
"""

  completion_data = BuildRequest( filepath = '/foo.cpp',
                                  filetype = 'cpp',
                                  contents = contents,
                                  line_num = 11,
                                  column_num = 7,
                                  compilation_flags = [ '-x', 'c++' ] )

  response_data = app.post_json( '/completions', completion_data ).json
  assert_that( response_data[ 'completions' ],
               has_items( CompletionEntryMatcher( 'c' ),
                          CompletionEntryMatcher( 'x' ),
                          CompletionEntryMatcher( 'y' ) ) )
  eq_( 7, response_data[ 'completion_start_column' ] )


@IsolatedYcmd( { 'auto_trigger': 0 } )
def GetCompletions_NoCompletionsWhenAutoTriggerOff_test( app ):
  app.post_json(
    '/ignore_extra_conf_file',
    { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  contents = """
struct Foo {
  int x;
  int y;
  char c;
};

int main()
{
  Foo foo;
  foo.
}
"""

  completion_data = BuildRequest( filepath = '/foo.cpp',
                                  filetype = 'cpp',
                                  contents = contents,
                                  line_num = 11,
                                  column_num = 7,
                                  compilation_flags = [ '-x', 'c++' ] )

  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]
  assert_that( results, empty() )


@IsolatedYcmd()
def GetCompletions_UnknownExtraConfException_test( app ):
  filepath = PathToTestFile( 'basic.cpp' )
  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'cpp',
                                  contents = ReadFile( filepath ),
                                  line_num = 11,
                                  column_num = 7,
                                  force_semantic = True )

  response = app.post_json( '/completions',
                            completion_data,
                            expect_errors = True )

  eq_( response.status_code, requests.codes.internal_server_error )
  assert_that( response.json,
               has_entry( 'exception',
                          has_entry( 'TYPE', UnknownExtraConf.__name__ ) ) )

  app.post_json(
    '/ignore_extra_conf_file',
    { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )

  response = app.post_json( '/completions',
                            completion_data,
                            expect_errors = True )

  eq_( response.status_code, requests.codes.internal_server_error )
  assert_that( response.json,
               has_entry( 'exception',
                          has_entry( 'TYPE',
                                     NoExtraConfDetected.__name__ ) ) )


@IsolatedYcmd()
def GetCompletions_WorksWhenExtraConfExplicitlyAllowed_test( app ):
  app.post_json(
    '/load_extra_conf_file',
    { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )

  filepath = PathToTestFile( 'basic.cpp' )
  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'cpp',
                                  contents = ReadFile( filepath ),
                                  line_num = 11,
                                  column_num = 7 )

  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]
  assert_that( results, has_items( CompletionEntryMatcher( 'c' ),
                                   CompletionEntryMatcher( 'x' ),
                                   CompletionEntryMatcher( 'y' ) ) )


@SharedYcmd
def GetCompletions_ExceptionWhenNoFlagsFromExtraConf_test( app ):
  app.post_json(
    '/load_extra_conf_file',
    { 'filepath': PathToTestFile( 'noflags',
                                  '.ycm_extra_conf.py' ) } )

  filepath = PathToTestFile( 'noflags', 'basic.cpp' )

  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'cpp',
                                  contents = ReadFile( filepath ),
                                  line_num = 11,
                                  column_num = 7,
                                  force_semantic = True )

  response = app.post_json( '/completions',
                            completion_data,
                            expect_errors = True )
  eq_( response.status_code, requests.codes.internal_server_error )

  assert_that( response.json,
               has_entry( 'exception',
                          has_entry( 'TYPE', RuntimeError.__name__ ) ) )


@SharedYcmd
def GetCompletions_ForceSemantic_OnlyFilteredCompletions_test( app ):
  contents = """
int main()
{
  int foobar;
  int floozar;
  int gooboo;
  int bleble;

  fooar
}
"""

  completion_data = BuildRequest( filepath = '/foo.cpp',
                                  filetype = 'cpp',
                                  force_semantic = True,
                                  contents = contents,
                                  line_num = 9,
                                  column_num = 8,
                                  compilation_flags = [ '-x', 'c++' ] )

  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]
  assert_that(
    results,
    contains_inanyorder( CompletionEntryMatcher( 'foobar' ),
                         CompletionEntryMatcher( 'floozar' ) )
  )


@SharedYcmd
def GetCompletions_DocStringsAreIncluded_test( app ):
  filepath = PathToTestFile( 'completion_docstring.cc' )
  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'cpp',
                                  contents = ReadFile( filepath ),
                                  line_num = 5,
                                  column_num = 7,
                                  compilation_flags = [ '-x', 'c++' ],
                                  force_semantic = True )

  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]
  assert_that( results, has_item(
    has_entries( {
      'insertion_text': 'func',
      'extra_data': has_entry( 'doc_string', 'This is a docstring.' )
    } )
  ) )


@ExpectedFailure(
  'libclang wrongly marks protected members from base class in derived class '
  'as inaccessible. See https://bugs.llvm.org/show_bug.cgi?id=24329',
  all_of( matches_regexp( "was .*public_member" ),
          is_not( matches_regexp( "was .*protected_member" ) ),
          is_not( matches_regexp( "was .*private_member" ) ) ) )
@SharedYcmd
def GetCompletions_PublicAndProtectedMembersAvailableInDerivedClass_test( app ):
  filepath = PathToTestFile( 'completion_availability.cc' )
  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'cpp',
                                  contents = ReadFile( filepath ),
                                  line_num = 14,
                                  column_num = 5,
                                  compilation_flags = [ '-x', 'c++' ],
                                  force_semantic = True )

  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]
  assert_that(
    results,
    all_of(
      has_items( CompletionEntryMatcher( 'public_member' ),
                 CompletionEntryMatcher( 'protected_member' ) ),
      is_not( has_item( CompletionEntryMatcher( 'private_member' ) ) )
    ) )


@SharedYcmd
def GetCompletions_ClientDataGivenToExtraConf_test( app ):
  app.post_json(
    '/load_extra_conf_file',
    { 'filepath': PathToTestFile( 'client_data',
                                  '.ycm_extra_conf.py' ) } )

  filepath = PathToTestFile( 'client_data', 'main.cpp' )
  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'cpp',
                                  contents = ReadFile( filepath ),
                                  line_num = 9,
                                  column_num = 7,
                                  extra_conf_data = {
                                    'flags': [ '-x', 'c++' ]
                                  } )

  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]
  assert_that( results, has_item( CompletionEntryMatcher( 'x' ) ) )


@IsolatedYcmd( { 'max_num_candidates': 0 } )
def GetCompletions_ClientDataGivenToExtraConf_Include_test( app ):
  app.post_json(
    '/load_extra_conf_file',
    { 'filepath': PathToTestFile( 'client_data',
                                  '.ycm_extra_conf.py' ) } )

  filepath = PathToTestFile( 'client_data', 'include.cpp' )
  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'cpp',
                                  contents = ReadFile( filepath ),
                                  line_num = 1,
                                  column_num = 11,
                                  extra_conf_data = {
                                    'flags': [ '-x', 'c++' ]
                                  } )

  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]
  assert_that(
    results,
    has_item( CompletionEntryMatcher( 'include.hpp',
              extra_menu_info = '[File]' ) )
  )


@IsolatedYcmd()
def GetCompletions_ClientDataGivenToExtraConf_Cache_test( app ):
  app.post_json(
    '/load_extra_conf_file',
    { 'filepath': PathToTestFile( 'client_data', '.ycm_extra_conf.py' ) } )

  filepath = PathToTestFile( 'client_data', 'macro.cpp' )
  contents = ReadFile( filepath )
  request = {
    'filetype'  : 'cpp',
    'filepath'  : filepath,
    'contents'  : contents,
    'line_num'  : 11,
    'column_num': 8
  }

  # Complete with flags from the client.
  completion_request = CombineRequest( request, {
    'extra_conf_data': {
      'flags': [ '-DSOME_MACRO' ]
    }
  } )

  assert_that(
    app.post_json( '/completions', completion_request ).json,
    has_entries( {
      'completions': has_item(
        CompletionEntryMatcher( 'macro_defined' )
      ),
      'errors': empty()
    } )
  )

  # Complete at the same position but for a different set of flags from the
  # client.
  completion_request = CombineRequest( request, {
    'extra_conf_data': {
      'flags': [ '-Wall' ]
    }
  } )

  assert_that(
    app.post_json( '/completions', completion_request ).json,
    has_entries( {
      'completions': has_item(
        CompletionEntryMatcher( 'macro_not_defined' )
      ),
      'errors': empty()
    } )
  )

  # Finally, complete once again at the same position but no flags are given by
  # the client. An empty list of flags is returned by the extra conf file in
  # that case.
  completion_request = CombineRequest( request, {} )

  assert_that(
    app.post_json( '/completions', completion_request ).json,
    has_entries( {
      'completions': empty(),
      'errors': contains(
        ErrorMatcher( RuntimeError, NO_COMPILE_FLAGS_MESSAGE )
      )
    } )
  )


@SharedYcmd
@WindowsOnly
def GetCompletions_ClangCLDriverFlag_SimpleCompletion_test( app ):
  RunTest( app, {
    'description': 'basic completion with --driver-mode=cl',
    'extra_conf': [ 'driver_mode_cl', 'flag', '.ycm_extra_conf.py' ],
    'request': {
      'filetype': 'cpp',
      'filepath': PathToTestFile( 'driver_mode_cl',
                                  'flag',
                                  'driver_mode_cl.cpp' ),
      'line_num': 8,
      'column_num': 18,
      'force_semantic': True,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 3,
        'completions': contains_inanyorder(
          CompletionEntryMatcher( 'driver_mode_cl_include_func', 'void' ),
          CompletionEntryMatcher( 'driver_mode_cl_include_int', 'int' ),
        ),
        'errors': empty(),
      } )
    }
  } )


@SharedYcmd
@WindowsOnly
def GetCompletions_ClangCLDriverExec_SimpleCompletion_test( app ):
  RunTest( app, {
    'description': 'basic completion with --driver-mode=cl',
    'extra_conf': [ 'driver_mode_cl', 'executable', '.ycm_extra_conf.py' ],
    'request': {
      'filetype': 'cpp',
      'filepath': PathToTestFile( 'driver_mode_cl',
                                  'executable',
                                  'driver_mode_cl.cpp' ),
      'line_num': 8,
      'column_num': 18,
      'force_semantic': True,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 3,
        'completions': contains_inanyorder(
          CompletionEntryMatcher( 'driver_mode_cl_include_func', 'void' ),
          CompletionEntryMatcher( 'driver_mode_cl_include_int', 'int' ),
        ),
        'errors': empty(),
      } )
    }
  } )


@SharedYcmd
@WindowsOnly
def GetCompletions_ClangCLDriverFlag_IncludeStatementCandidate_test( app ):
  RunTest( app, {
    'description': 'Completion inside include statement with CL driver',
    'extra_conf': [ 'driver_mode_cl', 'flag', '.ycm_extra_conf.py' ],
    'request': {
      'filetype': 'cpp',
      'filepath': PathToTestFile( 'driver_mode_cl',
                                  'flag',
                                  'driver_mode_cl.cpp' ),
      'line_num': 1,
      'column_num': 34,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 11,
        'completions': contains_inanyorder(
          CompletionEntryMatcher( 'driver_mode_cl_include.h', '[File]' ),
        ),
        'errors': empty(),
      } )
    }
  } )


@SharedYcmd
@WindowsOnly
def GetCompletions_ClangCLDriverExec_IncludeStatementCandidate_test( app ):
  RunTest( app, {
    'description': 'Completion inside include statement with CL driver',
    'extra_conf': [ 'driver_mode_cl', 'executable', '.ycm_extra_conf.py' ],
    'request': {
      'filetype': 'cpp',
      'filepath': PathToTestFile( 'driver_mode_cl',
                                  'executable',
                                  'driver_mode_cl.cpp' ),
      'line_num': 1,
      'column_num': 34,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 11,
        'completions': contains_inanyorder(
          CompletionEntryMatcher( 'driver_mode_cl_include.h', '[File]' ),
        ),
        'errors': empty(),
      } )
    }
  } )


@SharedYcmd
def GetCompletions_UnicodeInLine_test( app ):
  RunTest( app, {
    'description': 'member completion with a unicode identifier',
    'extra_conf': [ '.ycm_extra_conf.py' ],
    'request': {
      'filetype'  : 'cpp',
      'filepath'  : PathToTestFile( 'unicode.cc' ),
      'line_num'  : 9,
      'column_num': 8,
      'extra_conf_data': { '&filetype': 'cpp' },
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 8,
        'completions': contains_inanyorder(
          CompletionEntryMatcher( 'member_with_å_unicøde', 'int' ),
          CompletionEntryMatcher( '~MyStruct', 'void' ),
          CompletionEntryMatcher( 'operator=', 'MyStruct &' ),
          CompletionEntryMatcher( 'MyStruct::', '' ),
        ),
        'errors': empty(),
      } )
    },
  } )


@SharedYcmd
def GetCompletions_UnicodeInLineFilter_test( app ):
  RunTest( app, {
    'description': 'member completion with a unicode identifier',
    'extra_conf': [ '.ycm_extra_conf.py' ],
    'request': {
      'filetype'  : 'cpp',
      'filepath'  : PathToTestFile( 'unicode.cc' ),
      'line_num'  : 9,
      'column_num': 10,
      'extra_conf_data': { '&filetype': 'cpp' },
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 8,
        'completions': contains_inanyorder(
          CompletionEntryMatcher( 'member_with_å_unicøde', 'int' ),
        ),
        'errors': empty(),
      } )
    },
  } )


@SharedYcmd
def GetCompletions_QuotedInclude_AtStart_test( app ):
  RunTest( app, {
    'description': 'completion of #include "',
    'request': {
      'filetype'  : 'cpp',
      'filepath'  : PathToTestFile( 'test-include', 'main.cpp' ),
      'line_num'  : 11,
      'column_num': 11,
      'compilation_flags': [ '-x', 'cpp', '-nostdinc', '-nobuiltininc' ]
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 11,
        'completions': contains(
          CompletionEntryMatcher( '.ycm_extra_conf.py', '[File]' ),
          CompletionEntryMatcher( 'a.hpp',              '[File]' ),
          CompletionEntryMatcher( 'dir with spaces',    '[Dir]' ),
          CompletionEntryMatcher( 'main.cpp',           '[File]' ),
          CompletionEntryMatcher( 'quote',              '[Dir]' ),
          CompletionEntryMatcher( 'system',             '[Dir]' ),
          CompletionEntryMatcher( 'Frameworks',         '[Dir]' )
        ),
        'errors': empty(),
      } )
    },
  } )


@SharedYcmd
def GetCompletions_QuotedInclude_UserIncludeFlag_test( app ):
  RunTest( app, {
    'description': 'completion of #include " with a -I flag',
    'request': {
      'filetype'  : 'cpp',
      'filepath'  : PathToTestFile( 'test-include', 'main.cpp' ),
      'line_num'  : 11,
      'column_num': 11,
      'compilation_flags': [
        '-x', 'cpp', '-nostdinc', '-nobuiltininc',
        '-I', PathToTestFile( 'test-include', 'system' )
      ]
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 11,
        'completions': contains(
          CompletionEntryMatcher( '.ycm_extra_conf.py', '[File]' ),
          CompletionEntryMatcher( 'a.hpp',              '[File]' ),
          CompletionEntryMatcher( 'c.hpp',              '[File]' ),
          CompletionEntryMatcher( 'common',             '[Dir]' ),
          CompletionEntryMatcher( 'dir with spaces',    '[Dir]' ),
          CompletionEntryMatcher( 'main.cpp',           '[File]' ),
          CompletionEntryMatcher( 'quote',              '[Dir]' ),
          CompletionEntryMatcher( 'system',             '[Dir]' ),
          CompletionEntryMatcher( 'Frameworks',         '[Dir]' )
        ),
        'errors': empty(),
      } )
    },
  } )


@SharedYcmd
def GetCompletions_QuotedInclude_SystemIncludeFlag_test( app ):
  RunTest( app, {
    'description': 'completion of #include " with a -isystem flag',
    'request': {
      'filetype'  : 'cpp',
      'filepath'  : PathToTestFile( 'test-include', 'main.cpp' ),
      'line_num'  : 11,
      'column_num': 11,
      'compilation_flags': [
        '-x', 'cpp', '-nostdinc', '-nobuiltininc',
        '-isystem', PathToTestFile( 'test-include', 'system' )
      ]
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 11,
        'completions': contains(
          CompletionEntryMatcher( '.ycm_extra_conf.py', '[File]' ),
          CompletionEntryMatcher( 'a.hpp',              '[File]' ),
          CompletionEntryMatcher( 'c.hpp',              '[File]' ),
          CompletionEntryMatcher( 'common',             '[Dir]' ),
          CompletionEntryMatcher( 'dir with spaces',    '[Dir]' ),
          CompletionEntryMatcher( 'main.cpp',           '[File]' ),
          CompletionEntryMatcher( 'quote',              '[Dir]' ),
          CompletionEntryMatcher( 'system',             '[Dir]' ),
          CompletionEntryMatcher( 'Frameworks',         '[Dir]' )
        ),
        'errors': empty(),
      } )
    },
  } )


@SharedYcmd
def GetCompletions_QuotedInclude_QuoteIncludeFlag_test( app ):
  RunTest( app, {
    'description': 'completion of #include " with a -iquote flag',
    'request': {
      'filetype'  : 'cpp',
      'filepath'  : PathToTestFile( 'test-include', 'main.cpp' ),
      'line_num'  : 11,
      'column_num': 11,
      'compilation_flags': [
        '-x', 'cpp', '-nostdinc', '-nobuiltininc',
        '-iquote', PathToTestFile( 'test-include', 'quote' )
      ]
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 11,
        'completions': contains(
          CompletionEntryMatcher( '.ycm_extra_conf.py', '[File]' ),
          CompletionEntryMatcher( 'a.hpp',              '[File]' ),
          CompletionEntryMatcher( 'b.hpp',              '[File]' ),
          CompletionEntryMatcher( 'dir with spaces',    '[Dir]' ),
          CompletionEntryMatcher( 'main.cpp',           '[File]' ),
          CompletionEntryMatcher( 'quote',              '[Dir]' ),
          CompletionEntryMatcher( 'system',             '[Dir]' ),
          CompletionEntryMatcher( 'Frameworks',         '[Dir]' )
        ),
        'errors': empty(),
      } )
    },
  } )


@SharedYcmd
def GetCompletions_QuotedInclude_MultipleIncludeFlags_test( app ):
  RunTest( app, {
    'description': 'completion of #include " with multiple -I flags',
    'request': {
      'filetype'  : 'cpp',
      'filepath'  : PathToTestFile( 'test-include', 'main.cpp' ),
      'line_num'  : 11,
      'column_num': 11,
      'compilation_flags': [
        '-x', 'cpp', '-nostdinc', '-nobuiltininc',
        '-I', PathToTestFile( 'test-include', 'dir with spaces' ),
        '-I', PathToTestFile( 'test-include', 'quote' ),
        '-I', PathToTestFile( 'test-include', 'system' )
      ]
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 11,
        'completions': contains(
          CompletionEntryMatcher( '.ycm_extra_conf.py', '[File]' ),
          CompletionEntryMatcher( 'a.hpp',              '[File]' ),
          CompletionEntryMatcher( 'b.hpp',              '[File]' ),
          CompletionEntryMatcher( 'c.hpp',              '[File]' ),
          CompletionEntryMatcher( 'common',             '[Dir]' ),
          CompletionEntryMatcher( 'd.hpp',              '[File]' ),
          CompletionEntryMatcher( 'dir with spaces',    '[Dir]' ),
          CompletionEntryMatcher( 'main.cpp',           '[File]' ),
          CompletionEntryMatcher( 'quote',              '[Dir]' ),
          CompletionEntryMatcher( 'system',             '[Dir]' ),
          CompletionEntryMatcher( 'Frameworks',         '[Dir]' )
        ),
        'errors': empty(),
      } )
    },
  } )


@SharedYcmd
def GetCompletions_QuotedInclude_AfterDirectorySeparator_test( app ):
  RunTest( app, {
    'description': 'completion of #include "quote/',
    'request': {
      'filetype'  : 'cpp',
      'filepath'  : PathToTestFile( 'test-include', 'main.cpp' ),
      'line_num'  : 11,
      'column_num': 27,
      'compilation_flags': [ '-x', 'cpp', '-nostdinc', '-nobuiltininc' ]
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 27,
        'completions': contains(
          CompletionEntryMatcher( 'd.hpp', '[File]' )
        ),
        'errors': empty(),
      } )
    },
  } )


@SharedYcmd
def GetCompletions_QuotedInclude_AfterDot_test( app ):
  RunTest( app, {
    'description': 'completion of #include "quote/b.',
    'request': {
      'filetype'  : 'cpp',
      'filepath'  : PathToTestFile( 'test-include', 'main.cpp' ),
      'line_num'  : 11,
      'column_num': 28,
      'compilation_flags': [ '-x', 'cpp', '-nostdinc', '-nobuiltininc' ]
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 27,
        'completions': contains(
          CompletionEntryMatcher( 'd.hpp', '[File]' )
        ),
        'errors': empty(),
      } )
    },
  } )


@SharedYcmd
def GetCompletions_QuotedInclude_AfterSpace_test( app ):
  RunTest( app, {
    'description': 'completion of #include "dir with ',
    'request': {
      'filetype'  : 'cpp',
      'filepath'  : PathToTestFile( 'test-include', 'main.cpp' ),
      'line_num'  : 11,
      'column_num': 20,
      'compilation_flags': [ '-x', 'cpp', '-nostdinc', '-nobuiltininc' ]
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 11,
        'completions': contains(
          CompletionEntryMatcher( 'dir with spaces', '[Dir]' )
        ),
        'errors': empty(),
      } )
    },
  } )


@SharedYcmd
def GetCompletions_QuotedInclude_Invalid_test( app ):
  RunTest( app, {
    'description': 'completion of an invalid include statement',
    'request': {
      'filetype'  : 'cpp',
      'filepath'  : PathToTestFile( 'test-include', 'main.cpp' ),
      'line_num'  : 13,
      'column_num': 12,
      'compilation_flags': [ '-x', 'cpp', '-nostdinc', '-nobuiltininc' ]
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 12,
        'completions': empty(),
        'errors': empty(),
      } )
    },
  } )


@SharedYcmd
def GetCompletions_QuotedInclude_FrameworkHeader_test( app ):
  RunTest( app, {
    'description': 'completion of #include "OpenGL/',
    'request': {
      'filetype'  : 'cpp',
      'filepath'  : PathToTestFile( 'test-include', 'main.cpp' ),
      'line_num'  : 14,
      'column_num': 18,
      'compilation_flags': [
        '-x', 'cpp', '-nostdinc', '-nobuiltininc',
        '-iframework', PathToTestFile( 'test-include', 'Frameworks' )
      ]
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 18,
        'completions': contains(
          CompletionEntryMatcher( 'gl.h', '[File]' )
        ),
        'errors': empty()
      } )
    },
  } )


@SharedYcmd
def GetCompletions_BracketInclude_AtStart_test( app ):
  RunTest( app, {
    'description': 'completion of #include <',
    'request': {
      'filetype'  : 'cpp',
      'filepath'  : PathToTestFile( 'test-include', 'main.cpp' ),
      'line_num'  : 12,
      'column_num': 11,
      'compilation_flags': [ '-x', 'cpp', '-nostdinc', '-nobuiltininc' ]
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 11,
        'completions': empty(),
        'errors': empty(),
      } )
    },
  } )


@SharedYcmd
def GetCompletions_BracketInclude_UserIncludeFlag_test( app ):
  RunTest( app, {
    'description': 'completion of #include < with a -I flag',
    'request': {
      'filetype'  : 'cpp',
      'filepath'  : PathToTestFile( 'test-include', 'main.cpp' ),
      'line_num'  : 12,
      'column_num': 11,
      'compilation_flags': [
        '-x', 'cpp', '-nostdinc', '-nobuiltininc',
        '-I', PathToTestFile( 'test-include', 'system' )
      ]
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 11,
        'completions': contains(
          CompletionEntryMatcher( 'a.hpp',  '[File]' ),
          CompletionEntryMatcher( 'c.hpp',  '[File]' ),
          CompletionEntryMatcher( 'common', '[Dir]' )
        ),
        'errors': empty(),
      } )
    },
  } )


@SharedYcmd
def GetCompletions_BracketInclude_SystemIncludeFlag_test( app ):
  RunTest( app, {
    'description': 'completion of #include < with a -isystem flag',
    'request': {
      'filetype'  : 'cpp',
      'filepath'  : PathToTestFile( 'test-include', 'main.cpp' ),
      'line_num'  : 12,
      'column_num': 11,
      'compilation_flags': [
        '-x', 'cpp', '-nostdinc', '-nobuiltininc',
        '-isystem', PathToTestFile( 'test-include', 'system' )
      ]
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 11,
        'completions': contains(
          CompletionEntryMatcher( 'a.hpp',  '[File]' ),
          CompletionEntryMatcher( 'c.hpp',  '[File]' ),
          CompletionEntryMatcher( 'common', '[Dir]' )
        ),
        'errors': empty(),
      } )
    },
  } )


@SharedYcmd
def GetCompletions_BracketInclude_QuoteIncludeFlag_test( app ):
  RunTest( app, {
    'description': 'completion of #include < with a -iquote flag',
    'request': {
      'filetype'  : 'cpp',
      'filepath'  : PathToTestFile( 'test-include', 'main.cpp' ),
      'line_num'  : 12,
      'column_num': 11,
      'compilation_flags': [
        '-x', 'cpp', '-nostdinc', '-nobuiltininc',
        '-iquote', PathToTestFile( 'test-include', 'quote' )
      ]
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 11,
        'completions': empty(),
        'errors': empty(),
      } )
    },
  } )


@SharedYcmd
def GetCompletions_BracketInclude_MultipleIncludeFlags_test( app ):
  RunTest( app, {
    'description': 'completion of #include < with multiple -I flags',
    'request': {
      'filetype'  : 'cpp',
      'filepath'  : PathToTestFile( 'test-include', 'main.cpp' ),
      'line_num'  : 12,
      'column_num': 11,
      'compilation_flags': [
        '-x', 'cpp', '-nostdinc', '-nobuiltininc',
        '-I', PathToTestFile( 'test-include', 'dir with spaces' ),
        '-I', PathToTestFile( 'test-include', 'quote' ),
        '-I', PathToTestFile( 'test-include', 'system' )
      ]
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 11,
        'completions': contains(
          CompletionEntryMatcher( 'a.hpp',  '[File]' ),
          CompletionEntryMatcher( 'b.hpp',  '[File]' ),
          CompletionEntryMatcher( 'c.hpp',  '[File]' ),
          CompletionEntryMatcher( 'common', '[Dir]' ),
          CompletionEntryMatcher( 'd.hpp',  '[File]' )
        ),
        'errors': empty(),
      } )
    },
  } )


@SharedYcmd
def GetCompletions_BracketInclude_AtDirectorySeparator_test( app ):
  RunTest( app, {
    'description': 'completion of #include <system/',
    'request': {
      'filetype'  : 'cpp',
      'filepath'  : PathToTestFile( 'test-include', 'main.cpp' ),
      'line_num'  : 12,
      'column_num': 18,
      'compilation_flags': [ '-x', 'cpp', '-nostdinc', '-nobuiltininc' ],
      # NOTE: when not forcing semantic, it falls back to the filename
      # completer and returns the root folder entries.
      'force_semantic': True
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 18,
        'completions': empty(),
        'errors': empty(),
      } )
    },
  } )


@SharedYcmd
def GetCompletions_BracketInclude_FrameworkHeader_test( app ):
  RunTest( app, {
    'description': 'completion of #include <OpenGL/',
    'request': {
      'filetype'  : 'cpp',
      'filepath'  : PathToTestFile( 'test-include', 'main.cpp' ),
      'line_num'  : 15,
      'column_num': 18,
      'compilation_flags': [
        '-x', 'cpp', '-nostdinc', '-nobuiltininc',
        '-iframework', PathToTestFile( 'test-include', 'Frameworks' )
      ]
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 18,
        'completions': contains(
          CompletionEntryMatcher( 'gl.h', '[File]' )
        ),
        'errors': empty()
      } )
    },
  } )


@SharedYcmd
def GetCompletions_BracketInclude_FileAndDirectory_test( app ):
  RunTest( app, {
    'description': 'suggestion can simultaneously be a file '
                   'and a directory',
    'request': {
      'filetype'  : 'cpp',
      'filepath'  : PathToTestFile( 'test-include', 'main.cpp' ),
      'line_num'  : 12,
      'column_num': 11,
      'compilation_flags': [
        '-x', 'cpp', '-nostdinc', '-nobuiltininc',
        '-isystem', PathToTestFile( 'test-include', 'system' ),
        '-isystem', PathToTestFile( 'test-include', 'system', 'common' )
      ]
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 11,
        'completions': contains(
          CompletionEntryMatcher( 'a.hpp',  '[File]' ),
          CompletionEntryMatcher( 'c.hpp',  '[File]' ),
          CompletionEntryMatcher( 'common', '[File&Dir]' )
        ),
        'errors': empty()
      } )
    },
  } )


@SharedYcmd
def GetCompletions_BracketInclude_FileAndFramework_test( app ):
  RunTest( app, {
    'description': 'suggestion can simultaneously be a file and a framework',
    'request': {
      'filetype'  : 'cpp',
      'filepath'  : PathToTestFile( 'test-include', 'main.cpp' ),
      'line_num'  : 12,
      'column_num': 11,
      'compilation_flags': [
        '-x', 'cpp', '-nostdinc', '-nobuiltininc',
        '-iframework', PathToTestFile( 'test-include', 'Frameworks' ),
        '-isystem', PathToTestFile( 'test-include', 'system', 'common' )
      ]
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 11,
        'completions': contains(
          CompletionEntryMatcher( 'common', '[File&Framework]' ),
          CompletionEntryMatcher( 'OpenGL', '[Framework]' )
        ),
        'errors': empty()
      } )
    },
  } )


@SharedYcmd
def GetCompletions_BracketInclude_DirectoryAndFramework_test( app ):
  RunTest( app, {
    'description': 'suggestion can simultaneously be a directory '
                   'and a framework',
    'request': {
      'filetype'  : 'cpp',
      'filepath'  : PathToTestFile( 'test-include', 'main.cpp' ),
      'line_num'  : 12,
      'column_num': 11,
      'compilation_flags': [
        '-x', 'cpp', '-nostdinc', '-nobuiltininc',
        '-iframework', PathToTestFile( 'test-include', 'Frameworks' ),
        '-isystem', PathToTestFile( 'test-include', 'system' )
      ]
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 11,
        'completions': contains(
          CompletionEntryMatcher( 'a.hpp',  '[File]' ),
          CompletionEntryMatcher( 'c.hpp',  '[File]' ),
          CompletionEntryMatcher( 'common', '[Dir&Framework]' ),
          CompletionEntryMatcher( 'OpenGL', '[Framework]' )
        ),
        'errors': empty()
      } )
    },
  } )


@SharedYcmd
def GetCompletions_BracketInclude_FileAndDirectoryAndFramework_test( app ):
  RunTest( app, {
    'description': 'suggestion can simultaneously be a file, a directory, '
                   'and a framework',
    'request': {
      'filetype'  : 'cpp',
      'filepath'  : PathToTestFile( 'test-include', 'main.cpp' ),
      'line_num'  : 12,
      'column_num': 11,
      'compilation_flags': [
        '-x', 'cpp', '-nostdinc', '-nobuiltininc',
        '-iframework', PathToTestFile( 'test-include', 'Frameworks' ),
        '-isystem', PathToTestFile( 'test-include', 'system' ),
        '-isystem', PathToTestFile( 'test-include', 'system', 'common' )
      ]
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 11,
        'completions': contains(
          CompletionEntryMatcher( 'a.hpp',  '[File]' ),
          CompletionEntryMatcher( 'c.hpp',  '[File]' ),
          CompletionEntryMatcher( 'common', '[File&Dir&Framework]' ),
          CompletionEntryMatcher( 'OpenGL', '[Framework]' )
        ),
        'errors': empty()
      } )
    },
  } )


@SharedYcmd
def GetCompletions_TranslateClangExceptionToPython_test( app ):
  RunTest( app, {
    'description': 'The ClangParseError C++ exception is properly translated '
                   'to a Python exception',
    'extra_conf': [ '.ycm_extra_conf.py' ],
    'request': {
      'filetype'  : 'cpp',
      # libclang fails to parse a file that doesn't exist.
      'filepath'  : PathToTestFile( 'non_existing_file' ),
      'contents'  : '',
      'force_semantic': True
    },
    'expect': {
      'response': requests.codes.internal_server_error,
      'data': ErrorMatcher( ycm_core.ClangParseError,
                            "Failed to parse the translation unit." )
    },
  } )


@SharedYcmd
def GetCompletions_Unity_test( app ):
  RunTest( app, {
    'description': 'Completion returns from file included in TU, but not in '
                   'opened file',
    'extra_conf': [ '.ycm_extra_conf.py' ],
    'request': {
      'filetype'  : 'cpp',
      'filepath'  : PathToTestFile( 'unitya.cc' ),
      'line_num'  : 10,
      'column_num': 24,
      'force_semantic': True,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 20,
        'completions': contains(
          CompletionEntryMatcher( 'this_is_an_it', 'int' ),
        ),
        'errors': empty(),
      } )
    }
  } )


@SharedYcmd
def GetCompletions_UnityInclude_test( app ):
  RunTest( app, {
    'description': 'Completion returns for includes in unity setup',
    'extra_conf': [ '.ycm_extra_conf.py' ],
    'request': {
      'filetype'  : 'cpp',
      'filepath'  : PathToTestFile( 'unitya.cc' ),
      'line_num'  : 1,
      'column_num': 17,
      'force_semantic': True,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 11,
        'completions': has_items(
          CompletionEntryMatcher( 'unity.h', '[File]' ),
          CompletionEntryMatcher( 'unity.cc', '[File]' ),
          CompletionEntryMatcher( 'unitya.cc', '[File]' ),
        ),
        'errors': empty(),
      } )
    }
  } )


# This test is isolated to make sure we trigger c hook for clangd, instead of
# fetching completer from cache.
@IsolatedYcmd()
def GetCompletions_cuda_test( app ):
  RunTest( app, {
    'description': 'Completion of CUDA files',
    'extra_conf': [ '.ycm_extra_conf.py' ],
    'request': {
      'filetype'  : 'cuda',
      'filepath'  : PathToTestFile( 'cuda', 'completion_test.cu' ),
      'line_num'  : 16,
      'column_num': 29,
      'force_semantic': True,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 29,
        'completions': contains(
          CompletionEntryMatcher( 'do_something', 'void' ),
        ),
        'errors': empty(),
      } )
    }
  } )


@SharedYcmd
def GetCompletions_StillParsingError_test( app ):
  completer = handlers._server_state.GetFiletypeCompleter( [ 'cpp' ] )
  with patch.object( completer, '_completer', MockCoreClangCompleter() ):
    RunTest( app, {
      'description': 'raise an appropriate error if translation unit is still '
                     'being parsed.',
      'request': {
        'filetype'         : 'cpp',
        'filepath'         : PathToTestFile( 'test.cpp' ),
        'contents'         : '',
        'compilation_flags': [ '-x', 'c++' ],
        'force_semantic'   : True
      },
      'expect': {
        'response': requests.codes.internal_server_error,
        'data': ErrorMatcher( RuntimeError, PARSING_FILE_MESSAGE )
      },
    } )


@SharedYcmd
def GetCompletions_FixIt_test( app ):
  filepath = PathToTestFile( 'completion_fixit.cc' )
  RunTest( app, {
    'description': 'member completion has a fixit that change "." into "->"',
    'extra_conf': [ '.ycm_extra_conf.py' ],
    'request': {
      'filetype': 'cpp',
      'filepath': filepath,
      'line_num': 7,
      'column_num': 8,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': has_item( has_entries( {
          'insertion_text':  'bar',
          'extra_menu_info': 'int',
          'menu_text':       'bar',
          'detailed_info':   'int bar\n',
          'kind':            'MEMBER',
          'extra_data': has_entries( {
            'fixits': contains_inanyorder(
              has_entries( {
                'text': '',
                'chunks': contains(
                  ChunkMatcher(
                    '->',
                    LocationMatcher( filepath, 7, 6 ),
                    LocationMatcher( filepath, 7, 7 )
                  )
                ),
                'location': LocationMatcher( '', 0, 0 )
              } )
            )
          } )
        } ) )
      } )
    }
  } )
