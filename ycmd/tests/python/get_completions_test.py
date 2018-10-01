# coding: utf-8
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

from nose.tools import eq_
from hamcrest import ( all_of,
                       assert_that,
                       contains,
                       contains_string,
                       empty,
                       has_item,
                       has_items,
                       has_entry,
                       has_entries,
                       is_not )
import requests

from ycmd.utils import ReadFile
from ycmd.tests.python import IsolatedYcmd, PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import ( BuildRequest,
                                    CombineRequest,
                                    CompletionEntryMatcher,
                                    ErrorMatcher )


def RunTest( app, test ):
  """
  Method to run a simple completion test and verify the result

  test is a dictionary containing:
    'request': kwargs for BuildRequest
    'expect': {
       'response': server response code (e.g. httplib.OK)
       'data': matcher for the server response json
    }
  """
  contents = ReadFile( test[ 'request' ][ 'filepath' ] )

  app.post_json( '/event_notification',
                 CombineRequest( test[ 'request' ], {
                                 'event_name': 'FileReadyToParse',
                                 'contents': contents,
                                 } ),
                 expect_errors = True )

  # We ignore errors here and we check the response code ourself.
  # This is to allow testing of requests returning errors.
  response = app.post_json( '/completions',
                            CombineRequest( test[ 'request' ], {
                              'contents': contents
                            } ),
                            expect_errors = True )

  eq_( response.status_code, test[ 'expect' ][ 'response' ] )

  assert_that( response.json, test[ 'expect' ][ 'data' ] )


@SharedYcmd
def GetCompletions_Basic_test( app ):
  filepath = PathToTestFile( 'basic.py' )
  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'python',
                                  contents = ReadFile( filepath ),
                                  line_num = 7,
                                  column_num = 3 )

  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]
  assert_that( results,
               has_items(
                 CompletionEntryMatcher( 'a',
                                         'self.a = 1',
                                         {
                                           'extra_data': has_entry(
                                             'location', has_entries( {
                                               'line_num': 3,
                                               'column_num': 10,
                                               'filepath': filepath
                                             } )
                                           )
                                         } ),
                 CompletionEntryMatcher( 'b',
                                         'self.b = 2',
                                         {
                                           'extra_data': has_entry(
                                             'location', has_entries( {
                                               'line_num': 4,
                                               'column_num': 10,
                                               'filepath': filepath
                                             } )
                                           )
                                         } )
               ) )

  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'python',
                                  contents = ReadFile( filepath ),
                                  line_num = 7,
                                  column_num = 4 )

  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]
  assert_that( results,
               all_of(
                 has_item(
                   CompletionEntryMatcher( 'a',
                                           'self.a = 1',
                                           {
                                             'extra_data': has_entry(
                                               'location', has_entries( {
                                                 'line_num': 3,
                                                 'column_num': 10,
                                                 'filepath': filepath
                                               } )
                                             )
                                           } ) ),
                 is_not( has_item( CompletionEntryMatcher( 'b' ) ) )
               ) )


@SharedYcmd
def GetCompletions_UnicodeDescription_test( app ):
  filepath = PathToTestFile( 'unicode.py' )
  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'python',
                                  contents = ReadFile( filepath ),
                                  force_semantic = True,
                                  line_num = 5,
                                  column_num = 3 )

  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]
  assert_that( results, has_item(
    has_entry( 'detailed_info', contains_string( u'aafäö' ) ) ) )


@SharedYcmd
def GetCompletions_NoSuggestions_Fallback_test( app ):
  # Python completer doesn't raise NO_COMPLETIONS_MESSAGE, so this is a
  # different code path to the Clang completer cases

  # TESTCASE2 (general_fallback/lang_python.py)
  RunTest( app, {
    'description': 'param jedi does not know about (id). query="a_p"',
    'request': {
      'filetype'  : 'python',
      'filepath'  : PathToTestFile( 'general_fallback',
                                    'lang_python.py' ),
      'line_num'  : 28,
      'column_num': 20,
      'force_semantic': False,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': contains(
          CompletionEntryMatcher( 'a_parameter', '[ID]' ),
          CompletionEntryMatcher( 'another_parameter', '[ID]' ),
        ),
        'errors': empty()
      } )
    }
  } )


@SharedYcmd
def GetCompletions_Unicode_InLine_test( app ):
  RunTest( app, {
    'description': 'return completions for strings with multi-byte chars',
    'request': {
      'filetype'  : 'python',
      'filepath'  : PathToTestFile( 'unicode.py' ),
      'line_num'  : 7,
      'column_num': 14
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': contains(
          CompletionEntryMatcher( 'center', 'def center(width, fillchar)' )
        ),
        'errors': empty()
      } )
    }
  } )


@IsolatedYcmd( { 'global_ycm_extra_conf':
                 PathToTestFile( 'project', 'empty_extra_conf.py' ) } )
def GetCompletions_SysPath_EmptyExtraConf_test( app ):
  RunTest( app, {
    'description': 'Module is not added to sys.path through extra conf file',
    'request': {
      'filetype'  : 'python',
      'filepath'  : PathToTestFile( 'project', '__main__.py' ),
      'line_num'  : 3,
      'column_num': 8
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': empty(),
        'errors': empty()
      } )
    }
  } )


@IsolatedYcmd( { 'global_ycm_extra_conf':
                 PathToTestFile( 'project', 'settings_extra_conf.py' ) } )
def GetCompletions_SysPath_SettingsFunctionInExtraConf_test( app ):
  RunTest( app, {
    'description': 'Module is added to sys.path through the Settings '
                   'function in extra conf file',
    'request': {
      'filetype'  : 'python',
      'filepath'  : PathToTestFile( 'project', '__main__.py' ),
      'line_num'  : 3,
      'column_num': 8
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': has_item(
          CompletionEntryMatcher( 'SOME_CONSTANT', 'SOME_CONSTANT = 1' )
        ),
        'errors': empty()
      } )
    }
  } )


@IsolatedYcmd( { 'global_ycm_extra_conf':
                 PathToTestFile( 'project', 'settings_empty_extra_conf.py' ) } )
def GetCompletions_SysPath_SettingsEmptyInExtraConf_test( app ):
  RunTest( app, {
    'description': 'The Settings function returns an empty dictionary '
                   'in extra conf file',
    'request': {
      'filetype'  : 'python',
      'filepath'  : PathToTestFile( 'project', '__main__.py' ),
      'line_num'  : 3,
      'column_num': 8
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': empty(),
        'errors': empty()
      } )
    }
  } )


@IsolatedYcmd( { 'global_ycm_extra_conf':
                 PathToTestFile( 'project', 'settings_none_extra_conf.py' ) } )
def GetCompletions_SysPath_SettingsNoneInExtraConf_test( app ):
  RunTest( app, {
    'description': 'The Settings function returns None in extra conf file',
    'request': {
      'filetype'  : 'python',
      'filepath'  : PathToTestFile( 'project', '__main__.py' ),
      'line_num'  : 3,
      'column_num': 8
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': empty(),
        'errors': empty()
      } )
    }
  } )


@IsolatedYcmd( { 'global_ycm_extra_conf':
                 PathToTestFile( 'project', 'sys_path_extra_conf.py' ) } )
def GetCompletions_SysPath_PythonSysPathInExtraConf_test( app ):
  RunTest( app, {
    'description': 'Module is added to sys.path through the PythonSysPath '
                   'function in extra conf file',
    'request': {
      'filetype'  : 'python',
      'filepath'  : PathToTestFile( 'project', '__main__.py' ),
      'line_num'  : 3,
      'column_num': 8
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': has_item(
          CompletionEntryMatcher( 'SOME_CONSTANT', 'SOME_CONSTANT = 1' )
        ),
        'errors': empty()
      } )
    }
  } )


@IsolatedYcmd( { 'global_ycm_extra_conf':
                 PathToTestFile( 'project', 'invalid_python_extra_conf.py' ) } )
def GetCompletions_PythonInterpreter_InvalidPythonInExtraConf_test( app ):
  RunTest( app, {
    'description': 'Python interpreter path specified in extra conf file '
                   'does not exist',
    'request': {
      'filetype'  : 'python',
      'filepath'  : PathToTestFile( 'project', '__main__.py' ),
      'line_num'  : 3,
      'column_num': 8
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': empty(),
        'errors': contains(
          ErrorMatcher( RuntimeError,
                        'Cannot find Python interpreter path '
                        '/non/existing/python.' )
        )
      } )
    }
  } )


@IsolatedYcmd( { 'global_ycm_extra_conf':
                 PathToTestFile( 'project', 'client_data_extra_conf.py' ) } )
def GetCompletions_PythonInterpreter_ExtraConfData_test( app ):
  filepath = PathToTestFile( 'project', '__main__.py' )
  contents = ReadFile( filepath )
  request = {
    'filetype'  : 'python',
    'filepath'  : filepath,
    'contents'  : contents,
    'line_num'  : 3,
    'column_num': 8
  }

  # Complete with a sys.path specified by the client that contains the path to a
  # third-party module.
  completion_request = CombineRequest( request, {
    'extra_conf_data': {
      'sys_path': [ PathToTestFile( 'project', 'third_party' ) ]
    }
  } )

  assert_that(
    app.post_json( '/completions', completion_request ).json,
    has_entries( {
      'completions': has_item(
        CompletionEntryMatcher( 'SOME_CONSTANT', 'SOME_CONSTANT = 1' )
      ),
      'errors': empty()
    } )
  )

  # Complete at the same position but no sys.path from the client.
  completion_request = CombineRequest( request, {} )

  assert_that(
    app.post_json( '/completions', completion_request ).json,
    has_entries( {
      'completions': empty(),
      'errors': empty()
    } )
  )
