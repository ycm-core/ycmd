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

from hamcrest import ( all_of,
                       assert_that,
                       contains_exactly,
                       contains_string,
                       empty,
                       equal_to,
                       has_item,
                       has_items,
                       has_entry,
                       has_entries,
                       is_not )
from unittest import TestCase
import requests

from ycmd.utils import ReadFile
from ycmd.tests.python import setUpModule # noqa
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

  assert_that( response.status_code,
               equal_to( test[ 'expect' ][ 'response' ] ) )

  assert_that( response.json, test[ 'expect' ][ 'data' ] )


class GetCompletionsTest( TestCase ):
  @SharedYcmd
  def test_GetCompletions_Basic( self, app ):
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
                                             'detailed_info': '',
                                             'kind': 'statement'
                                           } ),
                   CompletionEntryMatcher( 'b',
                                           'self.b = 2',
                                           {
                                             'detailed_info': '',
                                             'kind': 'statement'
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
                                               'detailed_info': '',
                                               'kind': 'statement'
                                             } ) ),
                   is_not( has_item( CompletionEntryMatcher( 'b' ) ) )
                 ) )


  @SharedYcmd
  def test_GetCompletions_UnicodeDescription( self, app ):
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
  def test_GetCompletions_NoSuggestions_Fallback( self, app ):
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
          'completions': contains_exactly(
            CompletionEntryMatcher( 'a_parameter', '[ID]' ),
            CompletionEntryMatcher( 'another_parameter', '[ID]' ),
          ),
          'errors': empty()
        } )
      }
    } )


  @SharedYcmd
  def test_GetCompletions_Unicode_InLine( self, app ):
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
          'completions': contains_exactly(
            CompletionEntryMatcher(
              'center', 'def center(width: int, fillchar: str=...)' )
          ),
          'errors': empty()
        } )
      }
    } )


  @IsolatedYcmd( { 'global_ycm_extra_conf':
                   PathToTestFile( 'project', 'empty_extra_conf.py' ) } )
  def test_GetCompletions_SysPath_EmptyExtraConf( self, app ):
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
  def test_GetCompletions_SysPath_SettingsFunctionInExtraConf( self, app ):
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


  @IsolatedYcmd( {
    'global_ycm_extra_conf': PathToTestFile( 'project',
                                             'settings_extra_conf.py' ),
    'disable_signature_help': True
  } )
  def test_GetCompletions_SysPath_SettingsFunctionInExtraConf_DisableSig(
      self, app ):
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
                   PathToTestFile( 'project',
                                   'settings_empty_extra_conf.py' ) } )
  def test_GetCompletions_SysPath_SettingsEmptyInExtraConf( self, app ):
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
                   PathToTestFile( 'project',
                                   'settings_none_extra_conf.py' ) } )
  def test_GetCompletions_SysPath_SettingsNoneInExtraConf( self, app ):
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
  def test_GetCompletions_SysPath_PythonSysPathInExtraConf( self, app ):
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
                   PathToTestFile( 'project',
                                   'invalid_python_extra_conf.py' ) } )
  def test_GetCompletions_PythonInterpreter_InvalidPythonInExtraConf(
      self, app ):
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
          'errors': contains_exactly(
            ErrorMatcher( RuntimeError,
                          'Cannot find Python interpreter path '
                          '/non/existing/python.' )
          )
        } )
      }
    } )


  @IsolatedYcmd( { 'global_ycm_extra_conf':
                   PathToTestFile( 'project', 'client_data_extra_conf.py' ) } )
  def test_GetCompletions_PythonInterpreter_ExtraConfData( self, app ):
    filepath = PathToTestFile( 'project', '__main__.py' )
    contents = ReadFile( filepath )
    request = {
      'filetype'  : 'python',
      'filepath'  : filepath,
      'contents'  : contents,
      'line_num'  : 3,
      'column_num': 8
    }

    # Complete with a sys.path specified by the client that contains the path
    # to a third-party module.
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


  @SharedYcmd
  def test_GetCompletions_NumpyDoc( self, app ):
    RunTest( app, {
      'description': 'Type hinting is working with docstrings '
                     'in the Numpy format',
      'request': {
        'filetype'  : 'python',
        'filepath'  : PathToTestFile( 'numpy_docstring.py' ),
        'line_num'  : 11,
        'column_num': 18
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'completions': contains_exactly(
            CompletionEntryMatcher( 'SomeMethod', 'def SomeMethod()' ),
          ),
          'errors': empty()
        } )
      }
    } )
