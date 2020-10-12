# Copyright (C) 2015-2020 ycmd contributors
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

from hamcrest import ( assert_that,
                       calling,
                       contains_exactly,
                       contains_inanyorder,
                       equal_to,
                       has_entries,
                       has_item,
                       matches_regexp,
                       raises )
from webtest import AppError
import pprint
import requests

from ycmd.tests.typescript import IsolatedYcmd, PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import ( BuildRequest,
                                    ChunkMatcher,
                                    CombineRequest,
                                    CompletionEntryMatcher,
                                    LocationMatcher,
                                    StopCompleterServer )
from ycmd.utils import ReadFile


def RunTest( app, test ):
  contents = ReadFile( test[ 'request' ][ 'filepath' ] )
  filetype = test[ 'request' ].get( 'filetype', 'typescript' )
  app.post_json(
    '/event_notification',
    CombineRequest( test[ 'request' ], {
      'contents': contents,
      'filetype': filetype,
      'event_name': 'BufferVisit'
    } )
  )

  response = app.post_json(
    '/completions',
    CombineRequest( test[ 'request' ], {
      'contents': contents,
      'filetype': 'typescript',
      'force_semantic': True
    } )
  )

  print( f'completer response: { pprint.pformat( response.json ) }' )

  assert_that( response.status_code,
               equal_to( test[ 'expect' ][ 'response' ] ) )

  assert_that( response.json, test[ 'expect' ][ 'data' ] )


@SharedYcmd
def GetCompletions_Basic_test( app ):
  RunTest( app, {
    'description': 'Extra and detailed info when completions are methods',
    'request': {
      'line_num': 17,
      'column_num': 6,
      'filepath': PathToTestFile( 'test.ts' )
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': contains_inanyorder(
          CompletionEntryMatcher(
            'methodA',
            '(method) Foo.methodA(): void',
            extra_params = {
              'kind': 'method',
              'detailed_info': '(method) Foo.methodA(): void\n\n'
                               'Unicode string: 说话'
            }
          ),
          CompletionEntryMatcher(
            'methodB',
            '(method) Foo.methodB(): void',
            extra_params = {
              'kind': 'method',
              'detailed_info': '(method) Foo.methodB(): void'
            }
          ),
          CompletionEntryMatcher(
            'methodC',
            '(method) Foo.methodC(a: { foo: string; bar: number; }): void',
            extra_params = {
              'kind': 'method',
              'detailed_info': '(method) Foo.methodC(a: {\n'
                               '    foo: string;\n'
                               '    bar: number;\n'
                               '}): void'
            }
          )
        )
      } )
    }
  } )

  RunTest( app, {
    'description': 'Filtering works',
    'request': {
      'line_num': 17,
      'column_num': 7,
      'filepath': PathToTestFile( 'test.ts' )
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': contains_inanyorder(
          CompletionEntryMatcher(
            'methodA',
            '(method) Foo.methodA(): void',
            extra_params = {
              'kind': 'method',
              'detailed_info': '(method) Foo.methodA(): void\n\n'
                               'Unicode string: 说话'
            }
          )
        )
      } )
    }
  } )


@IsolatedYcmd( { 'disable_signature_help': True } )
def GetCompletions_Basic_NoSigHelp_test( app ):
  RunTest( app, {
    'description': 'Extra and detailed info when completions are methods',
    'request': {
      'line_num': 17,
      'column_num': 6,
      'filepath': PathToTestFile( 'test.ts' )
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': contains_inanyorder(
          CompletionEntryMatcher(
            'methodA',
            '(method) Foo.methodA(): void',
            extra_params = {
              'kind': 'method',
              'detailed_info': '(method) Foo.methodA(): void\n\n'
                               'Unicode string: 说话'
            }
          ),
          CompletionEntryMatcher(
            'methodB',
            '(method) Foo.methodB(): void',
            extra_params = {
              'kind': 'method',
              'detailed_info': '(method) Foo.methodB(): void'
            }
          ),
          CompletionEntryMatcher(
            'methodC',
            '(method) Foo.methodC(a: { foo: string; bar: number; }): void',
            extra_params = {
              'kind': 'method',
              'detailed_info': '(method) Foo.methodC(a: {\n'
                               '    foo: string;\n'
                               '    bar: number;\n'
                               '}): void'
            }
          )
        )
      } )
    }
  } )


@SharedYcmd
def GetCompletions_Keyword_test( app ):
  RunTest( app, {
    'description': 'No extra and detailed info when completion is a keyword',
    'request': {
      'line_num': 2,
      'column_num': 5,
      'filepath': PathToTestFile( 'test.ts' ),
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': has_item( {
          'insertion_text': 'class',
          'kind':           'keyword',
          'extra_data':     {}
        } )
      } )
    }
  } )


@SharedYcmd
def GetCompletions_AfterRestart_test( app ):
  filepath = PathToTestFile( 'test.ts' )

  app.post_json( '/run_completer_command',
                BuildRequest( completer_target = 'filetype_default',
                              command_arguments = [ 'RestartServer' ],
                              filetype = 'typescript',
                              filepath = filepath ) )

  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'typescript',
                                  contents = ReadFile( filepath ),
                                  force_semantic = True,
                                  line_num = 17,
                                  column_num = 6 )

  assert_that(
    app.post_json( '/completions', completion_data ).json,
    has_entries( {
      'completions': contains_inanyorder(
        CompletionEntryMatcher(
          'methodA',
          '(method) Foo.methodA(): void',
          extra_params = { 'kind': 'method' }
        ),
        CompletionEntryMatcher(
          'methodB',
          '(method) Foo.methodB(): void',
          extra_params = {
            'kind': 'method',
            'detailed_info': '(method) Foo.methodB(): void'
          }
        ),
        CompletionEntryMatcher(
          'methodC',
          '(method) Foo.methodC(a: { foo: string; bar: number; }): void',
          extra_params = {
            'kind': 'method',
            'detailed_info': '(method) Foo.methodC(a: {\n'
                             '    foo: string;\n'
                             '    bar: number;\n'
                             '}): void'
          }
        )
      )
    } )
  )


@IsolatedYcmd()
def GetCompletions_ServerIsNotRunning_test( app ):
  StopCompleterServer( app, filetype = 'typescript' )

  filepath = PathToTestFile( 'test.ts' )
  contents = ReadFile( filepath )

  # Check that sending a request to TSServer (the response is ignored) raises
  # the proper exception.
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'typescript',
                             contents = contents,
                             event_name = 'BufferVisit' )

  assert_that(
    calling( app.post_json ).with_args( '/event_notification', event_data ),
    raises( AppError, 'TSServer is not running.' ) )

  # Check that sending a command to TSServer (the response is processed) raises
  # the proper exception.
  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'typescript',
                                  contents = contents,
                                  force_semantic = True,
                                  line_num = 17,
                                  column_num = 6 )

  assert_that(
    calling( app.post_json ).with_args( '/completions', completion_data ),
    raises( AppError, 'TSServer is not running.' ) )


@SharedYcmd
def GetCompletions_AutoImport_test( app ):
  filepath = PathToTestFile( 'test.ts' )
  RunTest( app, {
    'description': 'Symbol from external module can be completed and '
                   'its completion contains fixits to automatically import it',
    'request': {
      'line_num': 39,
      'column_num': 5,
      'filepath': filepath,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': has_item( has_entries( {
          'insertion_text':  'Bår',
          'extra_menu_info': 'class Bår',
          'detailed_info':   'class Bår',
          'kind':            'class',
          'extra_data': has_entries( {
            'fixits': contains_inanyorder(
              has_entries( {
                'text': 'Import \'Bår\' from module "./unicode"',
                'chunks': contains_exactly(
                  ChunkMatcher(
                    matches_regexp( '^import { Bår } from "./unicode";\r?\n' ),
                    LocationMatcher( filepath, 1, 1 ),
                    LocationMatcher( filepath, 1, 1 )
                  )
                ),
                'location': LocationMatcher( filepath, 39, 5 )
              } )
            )
          } )
        } ) )
      } )
    }
  } )


@SharedYcmd
def GetCompletions_TypeScriptReact_DefaultTriggers_test( app ):
  filepath = PathToTestFile( 'test.tsx' )
  RunTest( app, {
    'description': 'No need to force after a semantic trigger',
    'request': {
      'line_num': 17,
      'column_num': 3,
      'filepath': filepath,
      'filetype': 'typescriptreact'
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': has_item( has_entries( {
          'insertion_text':  'foo',
          'extra_menu_info': "(property) 'foo': number",
          'detailed_info':   "(property) 'foo': number",
          'kind':            'property',
        } ) )
      } )
    }
  } )


def Dummy_test():
  # Workaround for https://github.com/pytest-dev/pytest-rerunfailures/issues/51
  assert True
