# encoding: utf-8
#
# Copyright (C) 2015-2018 ycmd contributors
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
from nose.tools import eq_
from hamcrest import ( assert_that, contains, contains_inanyorder, empty,
                       has_item, has_items, has_entries )

from ycmd.tests.clangd import IsolatedYcmd, PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import ( BuildRequest,
                                    CombineRequest,
                                    CompletionEntryMatcher,
                                    WaitUntilCompleterServerReady,
                                    WindowsOnly )
from ycmd.utils import ReadFile


def RunTest( app, test ):
  """
  Method to run a simple completion test and verify the result

  Note: Compile commands are extracted from a compile_flags.txt file by clangd
  by iteratively looking at the directory containing the source file and its
  ancestors.

  test is a dictionary containing:
    'request': kwargs for BuildRequest
    'expect': {
       'response': server response code (e.g. requests.codes.ok)
       'data': matcher for the server response json
    }
  """

  request = test[ 'request' ]
  filetype = request.get( 'filetype', 'cpp' )
  if 'contents' not in request:
    contents = ReadFile( request[ 'filepath' ] )
    request[ 'contents' ] = contents
    request[ 'filetype' ] = filetype

  # Because we aren't testing this command, we *always* ignore errors. This
  # is mainly because we (may) want to test scenarios where the completer
  # throws an exception and the easiest way to do that is to throw from
  # within the Settings function.
  app.post_json( '/event_notification',
                 CombineRequest( request, {
                   'event_name': 'FileReadyToParse',
                   'filetype': filetype
                 } ),
                 expect_errors = True )
  WaitUntilCompleterServerReady( app, filetype )

  # We also ignore errors here, but then we check the response code ourself.
  # This is to allow testing of requests returning errors.
  response = app.post_json( '/completions', BuildRequest( **request ),
                            expect_errors = True )

  eq_( response.status_code, test[ 'expect' ][ 'response' ] )

  print( 'Completer response: {}'.format( json.dumps(
    response.json, indent = 2 ) ) )

  assert_that( response.json, test[ 'expect' ][ 'data' ] )


@IsolatedYcmd( { 'clangd_uses_ycmd_caching': 0 } )
def GetCompletions_ForcedWithNoTrigger_NoYcmdCaching_test( app ):
  RunTest( app, {
    'description': 'semantic completion with force query=DO_SO',
    'request': {
      'filetype'  : 'cpp',
      'filepath'  : PathToTestFile( 'general_fallback',
                                    'lang_cpp.cc' ),
      'line_num'  : 54,
      'column_num': 8,
      'force_semantic': True,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': contains(
          CompletionEntryMatcher( 'DO_SOMETHING_TO', 'void' ),
          CompletionEntryMatcher( 'DO_SOMETHING_WITH', 'void' ),
          CompletionEntryMatcher( 'do_something', 'void' ),
        ),
        'errors': empty(),
      } )
    },
  } )


@IsolatedYcmd( { 'clangd_uses_ycmd_caching': 0 } )
def GetCompletions_NotForced_NoYcmdCaching_test( app ):
  RunTest( app, {
    'description': 'semantic completion with force query=DO_SO',
    'request': {
      'filetype'  : 'cpp',
      'filepath'  : PathToTestFile( 'general_fallback',
                                    'lang_cpp.cc' ),
      'line_num'  : 54,
      'column_num': 8,
      'force_semantic': False,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': contains(
          CompletionEntryMatcher( 'DO_SOMETHING_TO', 'void' ),
          CompletionEntryMatcher( 'DO_SOMETHING_WITH', 'void' ),
          CompletionEntryMatcher( 'do_something', 'void' ),
        ),
        'errors': empty(),
      } )
    },
  } )



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
      'force_semantic': False,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': empty(),
        'errors': empty(),
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
      'force_semantic': False,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': empty(),
        'errors': empty(),
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
      'force_semantic': False,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': has_item( CompletionEntryMatcher( 'a_parameter',
                                                         '[ID]' ) ),
        'errors': empty(),
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
      'force_semantic': False,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': contains(
          CompletionEntryMatcher( 'a_parameter', 'int' ),
          CompletionEntryMatcher( 'another_parameter', 'int' ),
        ),
        'errors': empty()
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
      'force_semantic': True,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( { 'completions': empty() } ),
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


@IsolatedYcmd( { 'auto_trigger': 0 } )
def GetCompletions_NoCompletionsWhenAutoTriggerOff_test( app ):
  RunTest( app, {
    'description': 'no completions on . when auto trigger is off',
    'request': {
      'filetype': 'cpp',
      'filepath': PathToTestFile( 'foo.cc' ),
      'contents': """
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
""",
      'line_num': 11,
      'column_num': 7
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': empty(),
        'errors': empty()
      } )
    },
  } )


@SharedYcmd
def GetCompletions_ForceSemantic_YcmdCache_test( app ):
  RunTest( app, {
    'description': 'completions are returned when using ycmd filtering',
    'request': {
      'filetype': 'cpp',
      'filepath': PathToTestFile( 'foo.cc' ),
      'contents': """
int main()
{
  int foobar;
  int floozar;
  int gooboo;
  int bleble;

  fooar
}
""",
      'line_num': 9,
      'column_num': 8,
      'force_semantic': True
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': contains( CompletionEntryMatcher( 'foobar' ),
                                 CompletionEntryMatcher( 'floozar' ) ),
        'errors': empty()
      } )
    },
  } )


@IsolatedYcmd( { 'clangd_uses_ycmd_caching': 0 } )
def GetCompletions_ForceSemantic_NoYcmdCache_test( app ):
  RunTest( app, {
    'description': 'no completions are returned when using Clangd filtering',
    'request': {
      'filetype': 'cpp',
      'filepath': PathToTestFile( 'foo.cc' ),
      'contents': """
int main()
{
  int foobar;
  int floozar;
  int gooboo;
  int bleble;

  fooar
}
""",
      'line_num': 9,
      'column_num': 8,
      'force_semantic': True
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': empty(),
        'errors': empty()
      } )
    },
  } )


@SharedYcmd
@WindowsOnly
def GetCompletions_ClangCLDriverFlag_SimpleCompletion_test( app ):
  RunTest( app, {
    'description': 'basic completion with --driver-mode=cl',
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
          CompletionEntryMatcher( 'driver_mode_cl_include.h\"' ),
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
          CompletionEntryMatcher( 'driver_mode_cl_include.h\"' ),
        ),
        'errors': empty(),
      } )
    }
  } )


@SharedYcmd
def GetCompletions_UnicodeInLine_test( app ):
  RunTest( app, {
    'description': 'member completion with a unicode identifier',
    'request': {
      'filetype'  : 'cpp',
      'filepath'  : PathToTestFile( 'unicode.cc' ),
      'line_num'  : 9,
      'column_num': 8,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 8,
        'completions': contains(
          CompletionEntryMatcher( 'member_with_å_unicøde', 'int' ),
        ),
        'errors': empty(),
      } )
    },
  } )


@SharedYcmd
def GetCompletions_UnicodeInLineFilter_test( app ):
  RunTest( app, {
    'description': 'member completion with a unicode identifier',
    'request': {
      'filetype'  : 'cpp',
      'filepath'  : PathToTestFile( 'unicode.cc' ),
      'line_num'  : 9,
      'column_num': 10,
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
def GetCompletions_QuotedInclude_test( app ):
  RunTest( app, {
    'description': 'completion of #include "',
    'request': {
      'filetype'  : 'cpp',
      'filepath'  : PathToTestFile( 'test-include', 'main.cpp' ),
      'line_num'  : 9,
      'column_num': 11,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 11,
        'completions': contains(
          CompletionEntryMatcher( 'a.hpp"' ),
          CompletionEntryMatcher( 'b.hpp"' ),
          CompletionEntryMatcher( 'c.hpp"' ),
          CompletionEntryMatcher( 'dir with spaces/' ),
          CompletionEntryMatcher( 'quote/' ),
          CompletionEntryMatcher( 'system/' ),
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
      'line_num'  : 9,
      'column_num': 27,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 27,
        'completions': contains(
          CompletionEntryMatcher( 'd.hpp"' ),
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
      'line_num'  : 9,
      'column_num': 28,
      'compilation_flags': [ '-x', 'cpp' ]
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 27,
        'completions': contains(
          CompletionEntryMatcher( 'd.hpp"' ),
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
      'line_num'  : 9,
      'column_num': 20,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 11,
        'completions': contains(
          CompletionEntryMatcher( 'dir with spaces/' ),
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
      'line_num'  : 11,
      'column_num': 12,
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
def GetCompletions_BracketInclude_test( app ):
  RunTest( app, {
    'description': 'completion of #include <',
    'request': {
      'filetype'  : 'cpp',
      'filepath'  : PathToTestFile( 'test-include', 'main.cpp' ),
      'line_num'  : 10,
      'column_num': 11,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 11,
        'completions': has_items(
          CompletionEntryMatcher( 'a.hpp>' ),
          CompletionEntryMatcher( 'c.hpp>' )
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
      'line_num'  : 10,
      'column_num': 18,
      'compilation_flags': [ '-x', 'cpp' ],
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
def GetCompletions_cuda_test( app ):
  RunTest( app, {
    'description': 'Completion of CUDA files',
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
          CompletionEntryMatcher( 'do_something', 'void',
              { 'menu_text': 'do_something(float *a)' } ),
        ),
        'errors': empty(),
      } )
    }
  } )


@IsolatedYcmd( { 'clangd_args': [ '-header-insertion-decorators=1' ] } )
def GetCompletions_WithHeaderInsertionDecorators_test( app ):
  RunTest( app, {
    'description': 'Completion of CUDA files',
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
          CompletionEntryMatcher( 'do_something', 'void',
              { 'menu_text': ' do_something(float *a)' } ),
        ),
        'errors': empty(),
      } )
    }
  } )


@SharedYcmd
def GetCompletions_ServerTriggers_Ignored_test( app ):
  RunTest( app, {
    'description': "We don't trigger completion on things like map< int >|",
    'request': {
      'filetype'  : 'cpp',
      'filepath'  : PathToTestFile( 'template.cc' ),
      'line_num'  : 1,
      'column_num': 25
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 25,
        'completions': empty(),
        'errors': empty(),
      } )
    }
  } )
