#!/usr/bin/env python
# -*- coding: utf-8 -*-
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
import httplib
from .test_utils import ( Setup, BuildRequest, PathToTestFile,
                          ChangeSpecificOptions, StopOmniSharpServer,
                          WaitUntilOmniSharpServerReady, StopGoCodeServer,
                          ErrorMatcher )
from webtest import TestApp, AppError
from nose.tools import eq_, with_setup
from hamcrest import ( assert_that, has_item, has_items, has_entry, has_entries,
                       contains, contains_inanyorder, empty, greater_than,
                       contains_string )
from ..responses import  UnknownExtraConf, NoExtraConfDetected
from .. import handlers
from ..completers.cpp.clang_completer import NO_COMPLETIONS_MESSAGE
import bottle
import pprint

bottle.debug( True )

def CompletionEntryMatcher( insertion_text, extra_menu_info = None ):
  match = { 'insertion_text': insertion_text }
  if extra_menu_info:
    match.update( { 'extra_menu_info': extra_menu_info } )
  return has_entries( match )


def CompletionLocationMatcher( location_type, value ):
  return has_entry( 'extra_data',
                    has_entry( 'location',
                               has_entry( location_type, value ) ) )

NO_COMPLETIONS_ERROR = ErrorMatcher( RuntimeError, NO_COMPLETIONS_MESSAGE )


@with_setup( Setup )
def GetCompletions_RunTest( test ):
  """
  Method to run a simple completion test and verify the result

  Note: uses the .ycm_extra_conf from general_fallback/ which:
   - supports cpp, c and objc
   - requires extra_conf_data containing 'filetype&' = the filetype

  this should be sufficient for many standard test cases

  test is a dictionary containing:
    'request': kwargs for BuildRequest
    'expect': {
       'response': server response code (e.g. httplib.OK)
       'data': matcher for the server response json
    }
  """
  app = TestApp( handlers.app )
  app.post_json( '/load_extra_conf_file',
                 { 'filepath': PathToTestFile( 'general_fallback',
                                               '.ycm_extra_conf.py' ) } )

  contents = open( test[ 'request' ][ 'filepath' ] ).read()

  def CombineRequest( request, data ):
    kw = request
    request.update( data )
    return BuildRequest( **kw )

  # Because we aren't testing this command, we *always* ignore errors. This is
  # mainly because we (may) want to test scenarios where the completer throws
  # an exception and the easiest way to do that is to throw from within the
  # FlagsForFile function.
  app.post_json( '/event_notification',
                 CombineRequest( test[ 'request' ], {
                                   'event_name': 'FileReadyToParse',
                                   'contents': contents,
                                 } ),
                 expect_errors = True )

  # We also ignore errors here, but then we check the response code ourself.
  # This is to allow testing of requests returning errors.
  response = app.post_json( '/completions',
                            CombineRequest( test[ 'request' ], {
                              'contents': contents
                            } ),
                            expect_errors = True )

  print 'completer response: ' + pprint.pformat( response.json )

  eq_( response.status_code, test[ 'expect' ][ 'response' ] )

  assert_that( response.json, test[ 'expect' ][ 'data' ] )

@with_setup( Setup )
def GetCompletions_RequestValidation_NoLineNumException_test():
  app = TestApp( handlers.app )
  response = app.post_json( '/semantic_completion_available', {
    'column_num': 0,
    'filepath': '/foo',
    'file_data': {
      '/foo': {
        'filetypes': [ 'text' ],
        'contents': 'zoo'
      }
    }
  }, status = '5*', expect_errors = True )
  response.mustcontain( 'missing', 'line_num' )


@with_setup( Setup )
def GetCompletions_IdentifierCompleter_Works_test():
  app = TestApp( handlers.app )
  event_data = BuildRequest( contents = 'foo foogoo ba',
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )

  # query is 'oo'
  completion_data = BuildRequest( contents = 'oo foo foogoo ba',
                                  column_num = 3 )
  response_data = app.post_json( '/completions', completion_data ).json

  eq_( 1, response_data[ 'completion_start_column' ] )
  assert_that( response_data[ 'completions' ],
               has_items( CompletionEntryMatcher( 'foo', '[ID]' ),
                          CompletionEntryMatcher( 'foogoo', '[ID]' ) ) )


@with_setup( Setup )
def GetCompletions_IdentifierCompleter_StartColumn_AfterWord_test():
  app = TestApp( handlers.app )
  completion_data = BuildRequest( contents = 'oo foo foogoo ba',
                                  column_num = 11 )
  response_data = app.post_json( '/completions', completion_data ).json
  eq_( 8, response_data[ 'completion_start_column' ] )


@with_setup( Setup )
def GetCompletions_IdentifierCompleter_WorksForSpecialIdentifierChars_test():
  app = TestApp( handlers.app )
  contents = """
    textarea {
      font-family: sans-serif;
      font-size: 12px;
    }"""
  event_data = BuildRequest( contents = contents,
                             filetype = 'css',
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )

  # query is 'fo'
  completion_data = BuildRequest( contents = 'fo ' + contents,
                                  filetype = 'css',
                                  column_num = 3 )
  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]

  assert_that( results,
               has_items( CompletionEntryMatcher( 'font-size', '[ID]' ),
                          CompletionEntryMatcher( 'font-family', '[ID]' ) ) )

@with_setup( Setup )
def GetCompletions_ClangCompleter_Forced_With_No_Trigger_test():
  GetCompletions_RunTest( {
    'description': 'semantic completion with force query=DO_SO',
    'request': {
      'filetype':   'cpp',
      'filepath':   PathToTestFile( 'general_fallback', 'lang_cpp.cc' ),
      'line_num':   54,
      'column_num': 8,
      'extra_conf_data': { '&filetype': 'cpp' },
      'force_semantic': True,
    },
    'expect': {
      'response': httplib.OK,
      'data': has_entries( {
        'completions': contains(
          CompletionEntryMatcher( 'DO_SOMETHING_TO', 'void' ),
          CompletionEntryMatcher( 'DO_SOMETHING_WITH', 'void' ),
        ),
        'errors': empty(),
      } )
    },
  } )  

@with_setup( Setup )
def GetCompletions_ClangCompleter_Fallback_NoSuggestions_test():
  # TESTCASE1 (general_fallback/lang_c.c)
  GetCompletions_RunTest( {
    'description': 'Triggered, fallback but no query so no completions',
    'request': {
      'filetype':   'c',
      'filepath':   PathToTestFile( 'general_fallback', 'lang_c.c' ),
      'line_num':   29,
      'column_num': 21,
      'extra_conf_data': { '&filetype': 'c' },
      'force_semantic': False,
    },
    'expect': {
      'response': httplib.OK,
      'data': has_entries( {
        'completions': empty(),
        'errors': has_item( NO_COMPLETIONS_ERROR ),
      } )
    },
  } )

@with_setup( Setup)
def GetCompletions_ClangCompleter_Fallback_NoSuggestions_MinCh_test():
  # TESTCASE1 (general_fallback/lang_cpp.cc)
  GetCompletions_RunTest( {
    'description': 'fallback general completion obeys min chars setting '
                   ' (query="a")',
    'request': {
      'filetype':   'cpp',
      'filepath':   PathToTestFile( 'general_fallback', 'lang_cpp.cc' ),
      'line_num':   21,
      'column_num': 22,
      'extra_conf_data': { '&filetype': 'cpp' },
      'force_semantic': False,
    },
    'expect': {
      'response': httplib.OK,
      'data': has_entries( {
        'completions': empty(),
        'errors': has_item( NO_COMPLETIONS_ERROR ),
      } )
    },
  } )

@with_setup( Setup)
def GetCompletions_ClangCompleter_Fallback_Suggestions_test():
  # TESTCASE1 (general_fallback/lang_c.c)
  GetCompletions_RunTest( {
    'description': '. after macro with some query text (.a_)',
    'request': {
      'filetype':   'c',
      'filepath':   PathToTestFile( 'general_fallback', 'lang_c.c' ),
      'line_num':   29,
      'column_num': 23,
      'extra_conf_data': { '&filetype': 'c' },
      'force_semantic': False,
    },
    'expect': {
      'response': httplib.OK,
      'data': has_entries( {
        'completions': has_item( CompletionEntryMatcher( 'a_parameter',
                                                         '[ID]' ) ),
        'errors': has_item( NO_COMPLETIONS_ERROR ),
      } )
    },
  } )

@with_setup( Setup )
def GetCompletions_ClangCompleter_Fallback_Exception_test():
  # TESTCASE4 (general_fallback/lang_c.c)
  # extra conf throws exception
  GetCompletions_RunTest( {
    'description': '. on struct returns identifier because of error',
    'request': {
      'filetype':   'c',
      'filepath':   PathToTestFile( 'general_fallback', 'lang_c.c' ),
      'line_num':   62,
      'column_num': 20,
      'extra_conf_data': { '&filetype': 'c', 'throw': 'testy' },
      'force_semantic': False,
    },
    'expect': {
      'response': httplib.OK,
      'data': has_entries( {
        'completions': contains(
          CompletionEntryMatcher( 'a_parameter', '[ID]' ),
          CompletionEntryMatcher( 'another_parameter', '[ID]' ),
        ),
        'errors': has_item( ErrorMatcher( ValueError, 'testy' ) )
      } )
    },
  } )

@with_setup( Setup )
def GetCompletions_ClangCompleter_Forced_NoFallback_test():
  # TESTCASE2 (general_fallback/lang_c.c)
  GetCompletions_RunTest( {
    'description': '-> after macro with forced semantic',
    'request': {
      'filetype':   'c',
      'filepath':   PathToTestFile( 'general_fallback', 'lang_c.c' ),
      'line_num':   41,
      'column_num': 30,
      'extra_conf_data': { '&filetype': 'c' },
      'force_semantic': True,
    },
    'expect': {
      'response': httplib.INTERNAL_SERVER_ERROR,
      'data': NO_COMPLETIONS_ERROR,
    },
  } )

@with_setup( Setup )
def GetCompletions_JediCompleter_NoSuggestions_Fallback_test():
  # jedi completer doesn't raise NO_COMPLETIONS_MESSAGE, so this is a different
  # code path to the ClangCompleter cases

  # TESTCASE2 (general_fallback/lang_python.py)
  GetCompletions_RunTest( {
    'description': 'param jedi does not know about (id). query="a_p"',
    'request': {
      'filetype':   'python',
      'filepath':   PathToTestFile( 'general_fallback', 'lang_python.py' ),
      'line_num':   28,
      'column_num': 20,
      'extra_conf_data': { '&filetype': 'python' },
      'force_semantic': False,
    },
    'expect': {
      'response': httplib.OK,
      'data': has_entries( {
        'completions': contains(
          CompletionEntryMatcher( 'a_parameter', '[ID]' ),
          CompletionEntryMatcher( 'another_parameter', '[ID]' ),
        ),
        'errors': empty(),
      } )
    },
  } )

@with_setup( Setup )
def GetCompletions_ClangCompleter_Filtered_No_Results_Fallback_test():
  # no errors because the semantic completer returned results, but they
  # were filtered out by the query, so this is considered working OK
  # (whereas no completions from the semantic engine is considered an
  # error)

  # TESTCASE5 (general_fallback/lang_cpp.cc)
  GetCompletions_RunTest( {
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
      'response': httplib.OK,
      'data': has_entries( {
        'completions': contains_inanyorder(
          # do_ is an identifier because it is already in the file when we
          # load it
          CompletionEntryMatcher( 'do_', '[ID]' ),
          CompletionEntryMatcher( 'do_something', '[ID]' ),
          CompletionEntryMatcher( 'do_another_thing', '[ID]' ),
        ),
        'errors': empty()
      } )
    },
  } )
  

@with_setup( Setup )
def GetCompletions_CsCompleter_Works_test():
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

  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'cs',
                                  contents = contents,
                                  line_num = 10,
                                  column_num = 12 )
  response_data = app.post_json( '/completions', completion_data ).json
  assert_that( response_data[ 'completions' ],
               has_items( CompletionEntryMatcher( 'CursorLeft' ),
                          CompletionEntryMatcher( 'CursorSize' ) ) )
  eq_( 12, response_data[ 'completion_start_column' ] )

  StopOmniSharpServer( app, filepath )


@with_setup( Setup )
def GetCompletions_CsCompleter_MultipleSolution_Works_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepaths = [ PathToTestFile( 'testy', 'Program.cs' ),
                PathToTestFile( 'testy-multiple-solutions',
                                'solution-named-like-folder',
                                'testy',
                                'Program.cs' ) ]
  lines = [ 10, 9 ]
  for filepath, line in zip( filepaths, lines ):
    contents = open( filepath ).read()
    event_data = BuildRequest( filepath = filepath,
                               filetype = 'cs',
                               contents = contents,
                               event_name = 'FileReadyToParse' )

    app.post_json( '/event_notification', event_data )
    WaitUntilOmniSharpServerReady( app, filepath )

    completion_data = BuildRequest( filepath = filepath,
                                    filetype = 'cs',
                                    contents = contents,
                                    line_num = line,
                                    column_num = 12 )
    response_data = app.post_json( '/completions', completion_data ).json
    assert_that( response_data[ 'completions' ],
                  has_items( CompletionEntryMatcher( 'CursorLeft' ),
                             CompletionEntryMatcher( 'CursorSize' ) ) )
    eq_( 12, response_data[ 'completion_start_column' ] )

    StopOmniSharpServer( app, filepath )


@with_setup( Setup )
def GetCompletions_CsCompleter_PathWithSpace_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( u'неприличное слово', 'Program.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app, filepath )

  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'cs',
                                  contents = contents,
                                  line_num = 9,
                                  column_num = 12 )
  response_data = app.post_json( '/completions', completion_data ).json
  assert_that( response_data[ 'completions' ],
               has_items( CompletionEntryMatcher( 'CursorLeft' ),
                          CompletionEntryMatcher( 'CursorSize' ) ) )
  eq_( 12, response_data[ 'completion_start_column' ] )

  StopOmniSharpServer( app, filepath )


@with_setup( Setup )
def GetCompletions_CsCompleter_HasBothImportsAndNonImport_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy', 'ImportTest.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app, filepath )

  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'cs',
                                  contents = contents,
                                  line_num = 9,
                                  column_num = 12,
                                  force_semantic = True,
                                  query = 'Date' )
  response_data = app.post_json( '/completions', completion_data ).json

  assert_that( response_data[ 'completions' ],
               has_items( CompletionEntryMatcher( 'DateTime' ),
                          CompletionEntryMatcher( 'DateTimeStyles' ) ) )

  StopOmniSharpServer( app, filepath )


@with_setup( Setup )
def GetCompletions_CsCompleter_ImportsOrderedAfter_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy', 'ImportTest.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app, filepath )

  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'cs',
                                  contents = contents,
                                  line_num = 9,
                                  column_num = 12,
                                  force_semantic = True,
                                  query = 'Date' )
  response_data = app.post_json( '/completions', completion_data ).json

  min_import_index = min( loc for loc, val
                          in enumerate( response_data[ 'completions' ] )
                          if val[ 'extra_data' ][ 'required_namespace_import' ] )
  max_nonimport_index = max( loc for loc, val
                            in enumerate( response_data[ 'completions' ] )
                            if not val[ 'extra_data' ][ 'required_namespace_import' ] )

  assert_that( min_import_index, greater_than( max_nonimport_index ) ),
  StopOmniSharpServer( app, filepath )


@with_setup( Setup )
def GetCompletions_CsCompleter_ForcedReturnsResults_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy', 'ContinuousTest.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app, filepath )

  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'cs',
                                  contents = contents,
                                  line_num = 9,
                                  column_num = 21,
                                  force_semantic = True,
                                  query = 'Date' )
  response_data = app.post_json( '/completions', completion_data ).json

  assert_that( response_data[ 'completions' ],
               has_items( CompletionEntryMatcher( 'String' ),
                          CompletionEntryMatcher( 'StringBuilder' ) ) )
  StopOmniSharpServer( app, filepath )


@with_setup( Setup )
def GetCompletions_CsCompleter_NonForcedReturnsNoResults_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy', 'ContinuousTest.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app, filepath )

  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'cs',
                                  contents = contents,
                                  line_num = 9,
                                  column_num = 21,
                                  force_semantic = False,
                                  query = 'Date' )
  results = app.post_json( '/completions', completion_data ).json

  # there are no semantic completions. However, we fall back to identifier
  # completer in this case.
  assert_that( results, has_entries( {
    'completions' : has_item( has_entries( {
      'insertion_text' : 'String',
      'extra_menu_info': '[ID]',
    } ) ),
    'errors' : empty(),
  } ) )
  StopOmniSharpServer( app, filepath )


@with_setup( Setup )
def GetCompletions_CsCompleter_ForcedDividesCache_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy', 'ContinuousTest.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app, filepath )

  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'cs',
                                  contents = contents,
                                  line_num = 9,
                                  column_num = 21,
                                  force_semantic = True,
                                  query = 'Date' )
  results = app.post_json( '/completions', completion_data ).json

  assert_that( results[ 'completions' ], not( empty() ) )
  assert_that( results[ 'errors' ], empty() )

  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'cs',
                                  contents = contents,
                                  line_num = 9,
                                  column_num = 21,
                                  force_semantic = False,
                                  query = 'Date' )
  results = app.post_json( '/completions', completion_data ).json

  # there are no semantic completions. However, we fall back to identifier
  # completer in this case.
  assert_that( results, has_entries( {
    'completions' : has_item( has_entries( {
      'insertion_text' : 'String',
      'extra_menu_info': '[ID]',
    } ) ),
    'errors' : empty(),
  } ) )
  StopOmniSharpServer( app, filepath )


@with_setup( Setup )
def GetCompletions_CsCompleter_ReloadSolutionWorks_test():
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
  result = app.post_json( '/run_completer_command',
                          BuildRequest( completer_target = 'filetype_default',
                                        command_arguments = [ 'ReloadSolution' ],
                                        filepath = filepath,
                                        filetype = 'cs' ) ).json

  StopOmniSharpServer( app, filepath )
  eq_( result, True )


@with_setup( Setup )
def GetCompletions_CsCompleter_ReloadSolution_MultipleSolution_Works_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepaths = [ PathToTestFile( 'testy', 'Program.cs' ),
                PathToTestFile( 'testy-multiple-solutions',
                                'solution-named-like-folder',
                                'testy',
                                'Program.cs' ) ]
  for filepath in filepaths:
    contents = open( filepath ).read()
    event_data = BuildRequest( filepath = filepath,
                               filetype = 'cs',
                               contents = contents,
                               event_name = 'FileReadyToParse' )

    app.post_json( '/event_notification', event_data )
    WaitUntilOmniSharpServerReady( app, filepath )
    result = app.post_json( '/run_completer_command',
                            BuildRequest( completer_target = 'filetype_default',
                                          command_arguments = [ 'ReloadSolution' ],
                                          filepath = filepath,
                                          filetype = 'cs' ) ).json

    StopOmniSharpServer( app, filepath )
    eq_( result, True )


def _CsCompleter_SolutionSelectCheck( app, sourcefile, reference_solution,
                                      extra_conf_store = None ):
  # reusable test: verify that the correct solution (reference_solution) is
  #   detected for a given source file (and optionally a given extra_conf)
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  if extra_conf_store:
    app.post_json( '/load_extra_conf_file', { 'filepath': extra_conf_store } )

  result = app.post_json( '/run_completer_command',
                          BuildRequest( completer_target = 'filetype_default',
                                        command_arguments = [ 'SolutionFile' ],
                                        filepath = sourcefile,
                                        filetype = 'cs' ) ).json
  # Now that cleanup is done, verify solution file
  eq_( reference_solution , result)

@with_setup( Setup )
def GetCompletions_CsCompleter_UsesSubfolderHint_test():
  app = TestApp( handlers.app )
  _CsCompleter_SolutionSelectCheck( app,
                                    PathToTestFile(
                                      'testy-multiple-solutions',
                                      'solution-named-like-folder',
                                      'testy',
                                      'Program.cs' ),
                                    PathToTestFile(
                                      'testy-multiple-solutions',
                                      'solution-named-like-folder',
                                      'testy.sln' ) )

@with_setup( Setup )
def GetCompletions_CsCompleter_UsesSuperfolderHint_test():
  app = TestApp( handlers.app )
  _CsCompleter_SolutionSelectCheck( app,
                                    PathToTestFile(
                                      'testy-multiple-solutions',
                                      'solution-named-like-folder',
                                      'not-testy',
                                      'Program.cs' ),
                                    PathToTestFile(
                                      'testy-multiple-solutions',
                                      'solution-named-like-folder',
                                      'solution-named-like-folder.sln' ) )

@with_setup( Setup )
def GetCompletions_CsCompleter_ExtraConfStoreAbsolute_test():
  app = TestApp( handlers.app )
  _CsCompleter_SolutionSelectCheck( app,
                                    PathToTestFile(
                                      'testy-multiple-solutions',
                                      'solution-not-named-like-folder',
                                      'extra-conf-abs',
                                      'testy',
                                      'Program.cs' ),
                                    PathToTestFile(
                                      'testy-multiple-solutions',
                                      'solution-not-named-like-folder',
                                      'testy2.sln' ),
                                    PathToTestFile(
                                      'testy-multiple-solutions',
                                      'solution-not-named-like-folder',
                                      'extra-conf-abs',
                                      '.ycm_extra_conf.py' ) )

@with_setup( Setup )
def GetCompletions_CsCompleter_ExtraConfStoreRelative_test():
  app = TestApp( handlers.app )
  _CsCompleter_SolutionSelectCheck( app,
                                    PathToTestFile(
                                      'testy-multiple-solutions',
                                      'solution-not-named-like-folder',
                                      'extra-conf-rel',
                                      'testy',
                                      'Program.cs' ),
                                    PathToTestFile(
                                      'testy-multiple-solutions',
                                      'solution-not-named-like-folder',
                                      'extra-conf-rel',
                                      'testy2.sln' ),
                                    PathToTestFile(
                                      'testy-multiple-solutions',
                                      'solution-not-named-like-folder',
                                      'extra-conf-rel',
                                      '.ycm_extra_conf.py' ) )

@with_setup( Setup )
def GetCompletions_CsCompleter_ExtraConfStoreNonexisting_test():
  app = TestApp( handlers.app )
  _CsCompleter_SolutionSelectCheck( app,
                                    PathToTestFile(
                                      'testy-multiple-solutions',
                                      'solution-not-named-like-folder',
                                      'extra-conf-bad',
                                      'testy',
                                      'Program.cs' ),
                                    PathToTestFile(
                                      'testy-multiple-solutions',
                                      'solution-not-named-like-folder',
                                      'extra-conf-bad',
                                      'testy2.sln' ),
                                    PathToTestFile(
                                      'testy-multiple-solutions',
                                      'solution-not-named-like-folder',
                                      'extra-conf-bad',
                                      'testy',
                                      '.ycm_extra_conf.py' ) )

@with_setup( Setup )
def GetCompletions_CsCompleter_DoesntStartWithAmbiguousMultipleSolutions_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy-multiple-solutions',
                             'solution-not-named-like-folder',
                             'testy', 'Program.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  exception_caught = False
  try:
    app.post_json( '/event_notification', event_data )
  except AppError as e:
    if 'Autodetection of solution file failed' in str( e ):
      exception_caught = True

  # the test passes if we caught an exception when trying to start it,
  # so raise one if it managed to start
  if not exception_caught:
    WaitUntilOmniSharpServerReady( app, filepath )
    StopOmniSharpServer( app, filepath )
    raise Exception( ( 'The Omnisharp server started, despite us not being able '
                      'to find a suitable solution file to feed it. Did you '
                      'fiddle with the solution finding code in '
                      'cs_completer.py? Hopefully you\'ve enhanced it: you need'
                      'to update this test then :)' ) )

@with_setup( Setup )
def GetCompletions_ClangCompleter_WorksWithExplicitFlags_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
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
                                  compilation_flags = ['-x', 'c++'] )

  response_data = app.post_json( '/completions', completion_data ).json
  assert_that( response_data[ 'completions'],
               has_items( CompletionEntryMatcher( 'c' ),
                          CompletionEntryMatcher( 'x' ),
                          CompletionEntryMatcher( 'y' ) ) )
  eq_( 7, response_data[ 'completion_start_column' ] )

@with_setup( Setup )
def GetCompletions_ClangCompleter_NoCompletionsWhenAutoTriggerOff_test():
  ChangeSpecificOptions( { 'auto_trigger': False } )
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
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
                                  compilation_flags = ['-x', 'c++'] )

  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]
  assert_that( results, empty() )


@with_setup( Setup )
def GetCompletions_ClangCompleter_UnknownExtraConfException_test():
  app = TestApp( handlers.app )
  filepath = PathToTestFile( 'basic.cpp' )
  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'cpp',
                                  contents = open( filepath ).read(),
                                  line_num = 11,
                                  column_num = 7,
                                  force_semantic = True )

  response = app.post_json( '/completions',
                            completion_data,
                            expect_errors = True )

  eq_( response.status_code, httplib.INTERNAL_SERVER_ERROR )
  assert_that( response.json,
               has_entry( 'exception',
                          has_entry( 'TYPE', UnknownExtraConf.__name__ ) ) )

  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )

  response = app.post_json( '/completions',
                            completion_data,
                            expect_errors = True )

  eq_( response.status_code, httplib.INTERNAL_SERVER_ERROR )
  assert_that( response.json,
               has_entry( 'exception',
                          has_entry( 'TYPE', NoExtraConfDetected.__name__ ) ) )


@with_setup( Setup )
def GetCompletions_ClangCompleter_WorksWhenExtraConfExplicitlyAllowed_test():
  app = TestApp( handlers.app )
  app.post_json( '/load_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )

  filepath = PathToTestFile( 'basic.cpp' )
  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'cpp',
                                  contents = open( filepath ).read(),
                                  line_num = 11,
                                  column_num = 7 )

  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]
  assert_that( results, has_items( CompletionEntryMatcher( 'c' ),
                                   CompletionEntryMatcher( 'x' ),
                                   CompletionEntryMatcher( 'y' ) ) )


@with_setup( Setup )
def GetCompletions_ClangCompleter_ExceptionWhenNoFlagsFromExtraConf_test():
  app = TestApp( handlers.app )
  app.post_json( '/load_extra_conf_file',
                 { 'filepath': PathToTestFile( 'noflags',
                                               '.ycm_extra_conf.py' ) } )

  filepath = PathToTestFile( 'noflags', 'basic.cpp' )

  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'cpp',
                                  contents = open( filepath ).read(),
                                  line_num = 11,
                                  column_num = 7,
                                  force_semantic = True )

  response = app.post_json( '/completions',
                            completion_data,
                            expect_errors = True )
  eq_( response.status_code, httplib.INTERNAL_SERVER_ERROR )

  assert_that( response.json,
               has_entry( 'exception',
                          has_entry( 'TYPE', RuntimeError.__name__ ) ) )

@with_setup( Setup )
def GetCompletions_ClangCompleter_ForceSemantic_OnlyFileteredCompletions_test():
  app = TestApp( handlers.app )
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
                                  compilation_flags = ['-x', 'c++'] )

  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]
  assert_that( results,
               contains_inanyorder( CompletionEntryMatcher( 'foobar' ),
                                    CompletionEntryMatcher( 'floozar' ) ) )


@with_setup( Setup )
def GetCompletions_ForceSemantic_Works_test():
  app = TestApp( handlers.app )

  completion_data = BuildRequest( filetype = 'python',
                                  force_semantic = True )

  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]
  assert_that( results, has_items( CompletionEntryMatcher( 'abs' ),
                                   CompletionEntryMatcher( 'open' ),
                                   CompletionEntryMatcher( 'bool' ) ) )


@with_setup( Setup )
def GetCompletions_ClangCompleter_ClientDataGivenToExtraConf_test():
  app = TestApp( handlers.app )
  app.post_json( '/load_extra_conf_file',
                 { 'filepath': PathToTestFile( 'client_data',
                                               '.ycm_extra_conf.py' ) } )

  filepath = PathToTestFile( 'client_data', 'main.cpp' )
  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'cpp',
                                  contents = open( filepath ).read(),
                                  line_num = 9,
                                  column_num = 7,
                                  extra_conf_data = {
                                    'flags': ['-x', 'c++']
                                  })

  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]
  assert_that( results, has_item( CompletionEntryMatcher( 'x' ) ) )


@with_setup( Setup )
def GetCompletions_FilenameCompleter_ClientDataGivenToExtraConf_test():
  app = TestApp( handlers.app )
  app.post_json( '/load_extra_conf_file',
                 { 'filepath': PathToTestFile( 'client_data',
                                               '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'client_data', 'include.cpp' )
  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'cpp',
                                  contents = open( filepath ).read(),
                                  line_num = 1,
                                  column_num = 11,
                                  extra_conf_data = {
                                    'flags': ['-x', 'c++']
                                  })

  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]
  assert_that( results,
               has_item(
                 CompletionEntryMatcher( 'include.hpp',
                                         extra_menu_info = '[File]' ) ) )


@with_setup( Setup )
def GetCompletions_IdentifierCompleter_SyntaxKeywordsAdded_test():
  app = TestApp( handlers.app )
  event_data = BuildRequest( event_name = 'FileReadyToParse',
                             syntax_keywords = ['foo', 'bar', 'zoo'] )

  app.post_json( '/event_notification', event_data )

  completion_data = BuildRequest( contents =  'oo ',
                                  column_num = 3 )

  results = app.post_json( '/completions',
                                 completion_data ).json[ 'completions' ]
  assert_that( results,
               has_items( CompletionEntryMatcher( 'foo' ),
                          CompletionEntryMatcher( 'zoo' ) ) )


@with_setup( Setup )
def GetCompletions_UltiSnipsCompleter_Works_test():
  app = TestApp( handlers.app )
  event_data = BuildRequest(
    event_name = 'BufferVisit',
    ultisnips_snippets = [
        {'trigger': 'foo', 'description': 'bar'},
        {'trigger': 'zoo', 'description': 'goo'},
    ] )

  app.post_json( '/event_notification', event_data )

  completion_data = BuildRequest( contents =  'oo ',
                                  column_num = 3 )

  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]
  assert_that( results,
               has_items(
                 CompletionEntryMatcher( 'foo', extra_menu_info='<snip> bar' ),
                 CompletionEntryMatcher( 'zoo', extra_menu_info='<snip> goo' ) ) )


@with_setup( Setup )
def GetCompletions_UltiSnipsCompleter_UnusedWhenOffWithOption_test():
  ChangeSpecificOptions( { 'use_ultisnips_completer': False } )
  app = TestApp( handlers.app )

  event_data = BuildRequest(
    event_name = 'BufferVisit',
    ultisnips_snippets = [
        {'trigger': 'foo', 'description': 'bar'},
        {'trigger': 'zoo', 'description': 'goo'},
    ] )

  app.post_json( '/event_notification', event_data )

  completion_data = BuildRequest( contents = 'oo ',
                                  column_num = 3 )

  eq_( [],
       app.post_json( '/completions', completion_data ).json[ 'completions' ] )


@with_setup( Setup )
def GetCompletions_JediCompleter_Basic_test():
  app = TestApp( handlers.app )
  filepath = PathToTestFile( 'basic.py' )
  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'python',
                                  contents = open( filepath ).read(),
                                  line_num = 7,
                                  column_num = 3)

  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]

  assert_that( results,
               has_items(
                 CompletionEntryMatcher( 'a' ),
                 CompletionEntryMatcher( 'b' ),
                 CompletionLocationMatcher( 'line_num', 3 ),
                 CompletionLocationMatcher( 'line_num', 4 ),
                 CompletionLocationMatcher( 'column_num', 10 ),
                 CompletionLocationMatcher( 'filepath', filepath ) ) )


@with_setup( Setup )
def GetCompletions_JediCompleter_UnicodeDescription_test():
  app = TestApp( handlers.app )
  filepath = PathToTestFile( 'unicode.py' )
  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'python',
                                  contents = open( filepath ).read(),
                                  force_semantic = True,
                                  line_num = 5,
                                  column_num = 3)

  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]
  assert_that( results, has_item(
                          has_entry( 'detailed_info',
                            contains_string( u'aafäö' ) ) ) )


@with_setup( Setup )
def GetCompletions_GoCodeCompleter_test():
  app = TestApp( handlers.app )
  filepath = PathToTestFile( 'test.go' )
  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'go',
                                  contents = open( filepath ).read(),
                                  force_semantic = True,
                                  line_num = 9,
                                  column_num = 11)

  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]
  assert_that( results, has_item( CompletionEntryMatcher( u'Logger' ) ) )

  StopGoCodeServer( app )


@with_setup( Setup )
def GetCompletions_TypeScriptCompleter_test():
  app = TestApp( handlers.app )
  filepath = PathToTestFile( 'test.ts' )
  contents = open ( filepath ).read()

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'typescript',
                             contents = contents,
                             event_name = 'BufferVisit' )

  app.post_json( '/event_notification', event_data )

  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'typescript',
                                  contents = contents,
                                  force_semantic = True,
                                  line_num = 12,
                                  column_num = 6 )

  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]
  assert_that( results,
               has_items( CompletionEntryMatcher( 'methodA' ),
                          CompletionEntryMatcher( 'methodB' ),
                          CompletionEntryMatcher( 'methodC' ) ) )

