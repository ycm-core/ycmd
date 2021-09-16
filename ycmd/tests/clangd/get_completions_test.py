# Copyright (C) 2015-2021 ycmd contributors
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

from time import sleep
import json
import requests
from hamcrest import ( assert_that,
                       contains_exactly,
                       contains_inanyorder,
                       empty,
                       equal_to,
                       has_item,
                       has_items,
                       has_entries )
from unittest import TestCase

from ycmd import handlers
from ycmd.tests.clangd import setUpModule, tearDownModule # noqa
from ycmd.tests.clangd import IsolatedYcmd, PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import ( BuildRequest,
                                    CombineRequest,
                                    CompletionEntryMatcher,
                                    WaitUntilCompleterServerReady,
                                    WindowsOnly,
                                    WithRetry )
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

  for i in range( 10 ):
    try:
      # We also ignore errors here, but then we check the response code ourself.
      # This is to allow testing of requests returning errors.
      response = app.post_json( '/completions', BuildRequest( **request ),
                                expect_errors = True )

      assert_that( response.status_code,
                   equal_to( test[ 'expect' ][ 'response' ] ) )

      print( 'Completer response: '
             f'{ json.dumps( response.json, indent = 2 ) }' )

      assert_that( response.json, test[ 'expect' ][ 'data' ] )
      break
    except Exception:
      if i == 9:
        raise
      else:
        completer = handlers._server_state.GetFiletypeCompleter( [ 'cpp' ] )
        completer._completions_cache.Invalidate()
        sleep( 0.1 )
        pass


class GetCompletionsTest( TestCase ):
  @IsolatedYcmd( { 'clangd_uses_ycmd_caching': 0 } )
  def test_GetCompletions_ForcedWithNoTrigger_NoYcmdCaching( self, app ):
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
          'completions': contains_exactly(
            CompletionEntryMatcher( 'do_something', 'void' ),
            CompletionEntryMatcher( 'DO_SOMETHING_TO', 'void' ),
            CompletionEntryMatcher( 'DO_SOMETHING_WITH', 'void' ),
          ),
          'errors': empty(),
        } )
      },
    } )


  @IsolatedYcmd( { 'clangd_uses_ycmd_caching': 0 } )
  def test_GetCompletions_NotForced_NoYcmdCaching( self, app ):
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
          'completions': contains_exactly(
            CompletionEntryMatcher( 'do_something', 'void' ),
            CompletionEntryMatcher( 'DO_SOMETHING_TO', 'void' ),
            CompletionEntryMatcher( 'DO_SOMETHING_WITH', 'void' ),
          ),
          'errors': empty(),
        } )
      },
    } )



  @WithRetry()
  @SharedYcmd
  def test_GetCompletions_ForcedWithNoTrigger( self, app ):
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
          'completions': contains_exactly(
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
  def test_GetCompletions_Fallback_NoSuggestions( self, app ):
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


  @WithRetry()
  @SharedYcmd
  def test_GetCompletions_Fallback_NoSuggestions_MinimumCharaceters(
      self, app ):
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


  @WithRetry()
  @SharedYcmd
  def test_GetCompletions_Fallback_Suggestions( self, app ):
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


  @WithRetry()
  @SharedYcmd
  def test_GetCompletions_Fallback_Exception( self, app ):
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
          'completions': contains_exactly(
            CompletionEntryMatcher( 'a_parameter', 'int' ),
            CompletionEntryMatcher( 'another_parameter', 'int' ),
          ),
          'errors': empty()
        } )
      },
    } )


  @WithRetry()
  @SharedYcmd
  def test_GetCompletions_Forced_NoFallback( self, app ):
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


  @WithRetry()
  @SharedYcmd
  def test_GetCompletions_FilteredNoResults_Fallback( self, app ):
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
  def test_GetCompletions_NoCompletionsWhenAutoTriggerOff( self, app ):
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


  @WithRetry()
  @SharedYcmd
  def test_GetCompletions_ForceSemantic_YcmdCache( self, app ):
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
          'completions': contains_exactly( CompletionEntryMatcher( 'foobar' ),
                                   CompletionEntryMatcher( 'floozar' ) ),
          'errors': empty()
        } )
      },
    } )


  @IsolatedYcmd( { 'clangd_uses_ycmd_caching': 0 } )
  def test_GetCompletions_ForceSemantic_NoYcmdCache( self, app ):
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


  @WindowsOnly
  @WithRetry()
  @SharedYcmd
  def test_GetCompletions_ClangCLDriverFlag_SimpleCompletion( self, app ):
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


  @WindowsOnly
  @WithRetry()
  @IsolatedYcmd()
  def test_GetCompletions_ClangCLDriverExec_SimpleCompletion( self, app ):
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


  @WindowsOnly
  @WithRetry()
  @SharedYcmd
  def test_GetCompletions_ClangCLDriverFlag_IncludeStatementCandidate(
      self, app ):
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


  @WindowsOnly
  @WithRetry()
  @SharedYcmd
  def test_GetCompletions_ClangCLDriverExec_IncludeStatementCandidate(
      self, app ):
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


  @WithRetry()
  @SharedYcmd
  def test_GetCompletions_UnicodeInLine( self, app ):
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
          'completions': contains_exactly(
            CompletionEntryMatcher( 'member_with_å_unicøde', 'int' ),
          ),
          'errors': empty(),
        } )
      },
    } )


  @WithRetry()
  @SharedYcmd
  def test_GetCompletions_UnicodeInLineFilter( self, app ):
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


  @WithRetry()
  @SharedYcmd
  def test_GetCompletions_QuotedInclude( self, app ):
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
          'completions': contains_exactly(
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


  @WithRetry()
  @SharedYcmd
  def test_GetCompletions_QuotedInclude_AfterDirectorySeparator( self, app ):
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
          'completions': contains_exactly(
            CompletionEntryMatcher( 'd.hpp"' ),
          ),
          'errors': empty(),
        } )
      },
    } )


  @WithRetry()
  @SharedYcmd
  def test_GetCompletions_QuotedInclude_AfterDot( self, app ):
    RunTest( app, {
      'description': 'completion of #include "quote/b.',
      'request': {
        'filetype'  : 'cpp',
        'filepath'  : PathToTestFile( 'test-include', 'main.cpp' ),
        'line_num'  : 9,
        'column_num': 28,
        'compilation_flags': [ '-x', 'c++' ]
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'completion_start_column': 27,
          'completions': contains_exactly(
            CompletionEntryMatcher( 'd.hpp"' ),
          ),
          'errors': empty(),
        } )
      },
    } )


  @WithRetry()
  @SharedYcmd
  def test_GetCompletions_QuotedInclude_AfterSpace( self, app ):
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
          'completions': contains_exactly(
            CompletionEntryMatcher( 'dir with spaces/' ),
          ),
          'errors': empty(),
        } )
      },
    } )


  @WithRetry()
  @SharedYcmd
  def test_GetCompletions_QuotedInclude_Invalid( self, app ):
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


  @WithRetry()
  @SharedYcmd
  def test_GetCompletions_BracketInclude( self, app ):
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


  @WithRetry()
  @SharedYcmd
  def test_GetCompletions_BracketInclude_AtDirectorySeparator( self, app ):
    RunTest( app, {
      'description': 'completion of #include <system/',
      'request': {
        'filetype'  : 'cpp',
        'filepath'  : PathToTestFile( 'test-include', 'main.cpp' ),
        'line_num'  : 10,
        'column_num': 18,
        'compilation_flags': [ '-x', 'c++' ],
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


  @WithRetry()
  @IsolatedYcmd()
  def test_GetCompletions_cuda( self, app ):
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
          'completions': contains_exactly(
            CompletionEntryMatcher( 'do_something', 'void',
                { 'menu_text': 'do_something(float *a)' } ),
          ),
          'errors': empty(),
        } )
      }
    } )


  @IsolatedYcmd( { 'clangd_args': [ '-header-insertion-decorators=1' ] } )
  def test_GetCompletions_WithHeaderInsertionDecorators( self, app ):
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
          'completions': contains_exactly(
            CompletionEntryMatcher( 'do_something', 'void',
                { 'menu_text': ' do_something(float *a)' } ),
          ),
          'errors': empty(),
        } )
      }
    } )


  @WithRetry()
  @SharedYcmd
  def test_GetCompletions_ServerTriggers_Ignored( self, app ):
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


  @IsolatedYcmd( { 'extra_conf_globlist': [
    PathToTestFile( 'extra_conf', '.ycm_extra_conf.py' ) ] } )
  def test_GetCompletions_SupportExtraConf( self, app ):
    RunTest( app, {
      'description': 'Flags for foo.cpp from extra conf file are used',
      'request': {
        'filetype'  : 'cpp',
        'filepath'  : PathToTestFile( 'extra_conf', 'foo.cpp' ),
        'line_num'  : 5,
        'column_num': 15
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'completion_start_column': 15,
          'completions': contains_exactly(
            CompletionEntryMatcher( 'member_foo' ) ),
          'errors': empty(),
        } )
      }
    } )

    RunTest( app, {
      'description': 'Same flags are used again for foo.cpp',
      'request': {
        'filetype'  : 'cpp',
        'filepath'  : PathToTestFile( 'extra_conf', 'foo.cpp' ),
        'line_num'  : 5,
        'column_num': 15
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'completion_start_column': 15,
          'completions': contains_exactly(
            CompletionEntryMatcher( 'member_foo' ) ),
          'errors': empty(),
        } )
      }
    } )

    RunTest( app, {
      'description': 'Flags for bar.cpp from extra conf file are used',
      'request': {
        'filetype'  : 'cpp',
        'filepath'  : PathToTestFile( 'extra_conf', 'bar.cpp' ),
        'line_num'  : 5,
        'column_num': 15
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'completion_start_column': 15,
          'completions': contains_exactly(
            CompletionEntryMatcher( 'member_bar' ) ),
          'errors': empty(),
        } )
      }
    } )
