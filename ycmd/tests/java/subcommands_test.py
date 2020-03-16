# Copyright (C) 2017-2020 ycmd contributors
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

import time
from hamcrest import ( assert_that,
                       contains_exactly,
                       contains_inanyorder,
                       empty,
                       equal_to,
                       has_entries,
                       has_entry,
                       instance_of,
                       is_not,
                       matches_regexp )
from pprint import pformat
import requests
import pytest
import json

from ycmd.utils import ReadFile
from ycmd.completers.java.java_completer import NO_DOCUMENTATION_MESSAGE
from ycmd.tests.java import ( PathToTestFile,
                              SharedYcmd,
                              StartJavaCompleterServerWithFile,
                              IsolatedYcmd )
from ycmd.tests.test_utils import ( BuildRequest,
                                    ChunkMatcher,
                                    CombineRequest,
                                    ErrorMatcher,
                                    ExpectedFailure,
                                    LocationMatcher,
                                    WithRetry )
from unittest.mock import patch
from ycmd import handlers
from ycmd.completers.language_server import language_server_protocol as lsp
from ycmd.completers.language_server.language_server_completer import (
  ResponseTimeoutException,
  ResponseFailedException
)
from ycmd.responses import UnknownExtraConf

TESTLAUNCHER_JAVA = PathToTestFile( 'simple_eclipse_project',
                                    'src',
                                    'com',
                                    'test',
                                    'TestLauncher.java' )

TEST_JAVA = PathToTestFile( 'simple_eclipse_project',
                            'src',
                            'com',
                            'youcompleteme',
                            'Test.java' )

TSET_JAVA = PathToTestFile( 'simple_eclipse_project',
                            'src',
                            'com',
                            'youcompleteme',
                            'testing',
                            'Tset.java' )


@WithRetry
@SharedYcmd
def Subcommands_DefinedSubcommands_test( app ):
  subcommands_data = BuildRequest( completer_target = 'java' )

  assert_that( app.post_json( '/defined_subcommands', subcommands_data ).json,
               contains_inanyorder(
                 'FixIt',
                 'ExecuteCommand',
                 'Format',
                 'GoToDeclaration',
                 'GoToDefinition',
                 'GoTo',
                 'GetDoc',
                 'GetType',
                 'GoToImplementation',
                 'GoToReferences',
                 'GoToType',
                 'OpenProject',
                 'OrganizeImports',
                 'RefactorRename',
                 'RestartServer',
                 'WipeWorkspace' ) )


@pytest.mark.parametrize( 'cmd,arguments', [
  ( 'GoTo', [] ),
  ( 'GoToDeclaration', [] ),
  ( 'GoToDefinition', [] ),
  ( 'GoToReferences', [] ),
  ( 'GetType', [] ),
  ( 'GetDoc', [] ),
  ( 'FixIt', [] ),
  ( 'Format', [] ),
  ( 'OrganizeImports', [] ),
  ( 'RefactorRename', [ 'test' ] ),
] )
@SharedYcmd
def Subcommands_ServerNotInitialized_test( app, cmd, arguments ):
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'test',
                             'AbstractTestWidget.java' )

  completer = handlers._server_state.GetFiletypeCompleter( [ 'java' ] )

  @patch.object( completer, '_ServerIsInitialized', return_value = False )
  def Test( app, cmd, arguments, *args ):
    RunTest( app, {
      'description': 'Subcommand ' + cmd + ' handles server not ready',
      'request': {
        'command': cmd,
        'line_num': 1,
        'column_num': 1,
        'filepath': filepath,
        'arguments': arguments,
      },
      'expect': {
        'response': requests.codes.internal_server_error,
        'data': ErrorMatcher( RuntimeError,
                              'Server is initializing. Please wait.' ),
      }
    } )

  Test( app, cmd, arguments )


def RunTest( app, test, contents = None ):
  if not contents:
    contents = ReadFile( test[ 'request' ][ 'filepath' ] )

  # Because we aren't testing this command, we *always* ignore errors. This
  # is mainly because we (may) want to test scenarios where the completer
  # throws an exception.
  app.post_json( '/event_notification',
                 CombineRequest( test[ 'request' ], {
                                 'event_name': 'FileReadyToParse',
                                 'contents': contents,
                                 'filetype': 'java',
                                 } ),
                 expect_errors = True )

  # We also ignore errors here, but then we check the response code
  # ourself. This is to allow testing of requests returning errors.
  expiry = time.time() + 10
  while True:
    try:
      response = app.post_json(
        '/run_completer_command',
        CombineRequest( test[ 'request' ], {
          'completer_target': 'filetype_default',
          'contents': contents,
          'filetype': 'java',
          'command_arguments': ( [ test[ 'request' ][ 'command' ] ]
                                 + test[ 'request' ].get( 'arguments', [] ) )
        } ),
        expect_errors = True
      )

      print( 'completer response: {0}'.format( pformat( response.json ) ) )

      assert_that( response.status_code,
                   equal_to( test[ 'expect' ][ 'response' ] ) )

      assert_that( response.json, test[ 'expect' ][ 'data' ] )
      break
    except AssertionError:
      if time.time() > expiry:
        raise

      time.sleep( 0.25 )


@WithRetry
@SharedYcmd
def Subcommands_GetDoc_NoDoc_test( app ):
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'test',
                             'AbstractTestWidget.java' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'java',
                             line_num = 18,
                             column_num = 1,
                             contents = contents,
                             command_arguments = [ 'GetDoc' ],
                             completer_target = 'filetype_default' )

  response = app.post_json( '/run_completer_command',
                            event_data,
                            expect_errors = True )

  assert_that( response.status_code,
               equal_to( requests.codes.internal_server_error ) )

  assert_that( response.json,
               ErrorMatcher( RuntimeError, NO_DOCUMENTATION_MESSAGE ) )


@WithRetry
@SharedYcmd
def Subcommands_GetDoc_Method_test( app ):
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'test',
                             'AbstractTestWidget.java' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'java',
                             line_num = 17,
                             column_num = 17,
                             contents = contents,
                             command_arguments = [ 'GetDoc' ],
                             completer_target = 'filetype_default' )

  response = app.post_json( '/run_completer_command', event_data ).json

  assert_that( response, has_entry( 'detailed_info',
    'Return runtime debugging info. Useful for finding the '
    'actual code which is useful.' ) )


@WithRetry
@SharedYcmd
def Subcommands_GetDoc_Class_test( app ):
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'test',
                             'TestWidgetImpl.java' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'java',
                             line_num = 11,
                             column_num = 7,
                             contents = contents,
                             command_arguments = [ 'GetDoc' ],
                             completer_target = 'filetype_default' )

  response = app.post_json( '/run_completer_command', event_data ).json

  assert_that( response, has_entry( 'detailed_info',
    'This is the actual code that matters. This concrete '
    'implementation is the equivalent of the main function '
    'in other languages' ) )


@WithRetry
@SharedYcmd
def Subcommands_GetType_NoKnownType_test( app ):
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'test',
                             'TestWidgetImpl.java' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'java',
                             line_num = 28,
                             column_num = 1,
                             contents = contents,
                             command_arguments = [ 'GetType' ],
                             completer_target = 'filetype_default' )

  response = app.post_json( '/run_completer_command',
                            event_data,
                            expect_errors = True )

  assert_that( response.status_code,
               equal_to( requests.codes.internal_server_error ) )

  assert_that( response.json,
               ErrorMatcher( RuntimeError, 'Unknown type' ) )


@WithRetry
@SharedYcmd
def Subcommands_GetType_Class_test( app ):
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'test',
                             'TestWidgetImpl.java' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'java',
                             line_num = 11,
                             column_num = 7,
                             contents = contents,
                             command_arguments = [ 'GetType' ],
                             completer_target = 'filetype_default' )

  response = app.post_json( '/run_completer_command', event_data ).json

  assert_that( response, has_entry( 'message', 'com.test.TestWidgetImpl' ) )


@WithRetry
@SharedYcmd
def Subcommands_GetType_Constructor_test( app ):
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'test',
                             'TestWidgetImpl.java' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'java',
                             line_num = 14,
                             column_num = 3,
                             contents = contents,
                             command_arguments = [ 'GetType' ],
                             completer_target = 'filetype_default' )

  response = app.post_json( '/run_completer_command', event_data ).json

  assert_that( response, has_entry(
    'message', 'com.test.TestWidgetImpl.TestWidgetImpl(String info)' ) )


@WithRetry
@SharedYcmd
def Subcommands_GetType_ClassMemberVariable_test( app ):
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'test',
                             'TestWidgetImpl.java' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'java',
                             line_num = 12,
                             column_num = 18,
                             contents = contents,
                             command_arguments = [ 'GetType' ],
                             completer_target = 'filetype_default' )

  response = app.post_json( '/run_completer_command', event_data ).json

  assert_that( response, has_entry( 'message', 'String info' ) )


@WithRetry
@SharedYcmd
def Subcommands_GetType_MethodArgument_test( app ):
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'test',
                             'TestWidgetImpl.java' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'java',
                             line_num = 16,
                             column_num = 17,
                             contents = contents,
                             command_arguments = [ 'GetType' ],
                             completer_target = 'filetype_default' )

  response = app.post_json( '/run_completer_command', event_data ).json

  assert_that( response, has_entry(
    'message', 'String info - com.test.TestWidgetImpl.TestWidgetImpl(String)'
  ) )


@WithRetry
@SharedYcmd
def Subcommands_GetType_MethodVariable_test( app ):
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'test',
                             'TestWidgetImpl.java' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'java',
                             line_num = 15,
                             column_num = 9,
                             contents = contents,
                             command_arguments = [ 'GetType' ],
                             completer_target = 'filetype_default' )

  response = app.post_json( '/run_completer_command', event_data ).json

  assert_that( response, has_entry(
    'message', 'int a - com.test.TestWidgetImpl.TestWidgetImpl(String)' ) )


@WithRetry
@SharedYcmd
def Subcommands_GetType_Method_test( app ):
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'test',
                             'TestWidgetImpl.java' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'java',
                             line_num = 20,
                             column_num = 15,
                             contents = contents,
                             command_arguments = [ 'GetType' ],
                             completer_target = 'filetype_default' )

  response = app.post_json( '/run_completer_command', event_data ).json

  assert_that( response, has_entry(
    'message', 'void com.test.TestWidgetImpl.doSomethingVaguelyUseful()' ) )


@WithRetry
@SharedYcmd
def Subcommands_GetType_Unicode_test( app ):
  contents = ReadFile( TEST_JAVA )

  app.post_json( '/event_notification',
                 BuildRequest( filepath = TEST_JAVA,
                               filetype = 'java',
                               contents = contents,
                               event_name = 'FileReadyToParse' ) )

  event_data = BuildRequest( filepath = TEST_JAVA,
                             filetype = 'java',
                             line_num = 7,
                             column_num = 17,
                             contents = contents,
                             command_arguments = [ 'GetType' ],
                             completer_target = 'filetype_default' )

  response = app.post_json( '/run_completer_command', event_data ).json

  assert_that( response, has_entry(
    'message', 'String whåtawîdgé - com.youcompleteme.Test.doUnicødeTes()' ) )


@WithRetry
@SharedYcmd
def Subcommands_GetType_LiteralValue_test( app ):
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'test',
                             'TestWidgetImpl.java' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'java',
                             line_num = 15,
                             column_num = 13,
                             contents = contents,
                             command_arguments = [ 'GetType' ],
                             completer_target = 'filetype_default' )

  response = app.post_json( '/run_completer_command',
                            event_data,
                            expect_errors = True )

  assert_that( response.status_code,
               equal_to( requests.codes.internal_server_error ) )

  assert_that( response.json,
               ErrorMatcher( RuntimeError, 'Unknown type' ) )


@WithRetry
@SharedYcmd
def Subcommands_GoTo_NoLocation_test( app ):
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'test',
                             'AbstractTestWidget.java' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'java',
                             line_num = 18,
                             column_num = 1,
                             contents = contents,
                             command_arguments = [ 'GoTo' ],
                             completer_target = 'filetype_default' )

  response = app.post_json( '/run_completer_command',
                            event_data,
                            expect_errors = True )

  assert_that( response.status_code,
               equal_to( requests.codes.internal_server_error ) )

  assert_that( response.json,
               ErrorMatcher( RuntimeError, 'Cannot jump to location' ) )


@WithRetry
@SharedYcmd
def Subcommands_GoToReferences_NoReferences_test( app ):
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'test',
                             'AbstractTestWidget.java' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'java',
                             line_num = 18,
                             column_num = 1,
                             contents = contents,
                             command_arguments = [ 'GoToReferences' ],
                             completer_target = 'filetype_default' )

  response = app.post_json( '/run_completer_command',
                            event_data,
                            expect_errors = True )

  assert_that( response.status_code,
               equal_to( requests.codes.internal_server_error ) )

  assert_that( response.json,
               ErrorMatcher( RuntimeError,
                             'Cannot jump to location' ) )


@WithRetry
@IsolatedYcmd( {
  'extra_conf_globlist': PathToTestFile( 'multiple_projects', '*' )
} )
def Subcommands_GoToReferences_MultipleProjects_test( app ):
  filepath = PathToTestFile( 'multiple_projects',
                             'src',
                             'core',
                             'java',
                             'com',
                             'puremourning',
                             'widget',
                             'core',
                             'Utils.java' )
  StartJavaCompleterServerWithFile( app, filepath )


  RunTest( app, {
    'description': 'GoToReferences works across multiple projects',
    'request': {
      'command': 'GoToReferences',
      'filepath': filepath,
      'line_num': 5,
      'column_num': 22,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': contains_inanyorder(
        LocationMatcher( filepath, 8, 35 ),
        LocationMatcher( PathToTestFile( 'multiple_projects',
                                         'src',
                                         'input',
                                         'java',
                                         'com',
                                         'puremourning',
                                         'widget',
                                         'input',
                                         'InputApp.java' ),
                         8,
                         16 )
      )
    }
  } )



@WithRetry
@SharedYcmd
def Subcommands_GoToReferences_test( app ):
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'test',
                             'AbstractTestWidget.java' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'java',
                             line_num = 10,
                             column_num = 15,
                             contents = contents,
                             command_arguments = [ 'GoToReferences' ],
                             completer_target = 'filetype_default' )

  response = app.post_json( '/run_completer_command', event_data ).json

  assert_that( response, contains_exactly( has_entries( {
           'filepath': PathToTestFile( 'simple_eclipse_project',
                                       'src',
                                       'com',
                                       'test',
                                       'TestFactory.java' ),
           'column_num': 9,
           'description': "      w.doSomethingVaguelyUseful();",
           'line_num': 28
         } ),
         has_entries( {
           'filepath': PathToTestFile( 'simple_eclipse_project',
                                       'src',
                                       'com',
                                       'test',
                                       'TestLauncher.java' ),
           'column_num': 11,
           'description': "        w.doSomethingVaguelyUseful();",
           'line_num': 32
         } ) ) )


@WithRetry
@SharedYcmd
def Subcommands_RefactorRename_Simple_test( app ):
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'test',
                             'TestLauncher.java' )
  RunTest( app, {
    'description': 'RefactorRename works within a single scope/file',
    'request': {
      'command': 'RefactorRename',
      'arguments': [ 'renamed_l' ],
      'filepath': filepath,
      'line_num': 28,
      'column_num': 5,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'fixits': contains_exactly( has_entries( {
          'chunks': contains_exactly(
              ChunkMatcher( 'renamed_l = new TestLauncher( 10 );'
                            '\n    renamed_l',
                            LocationMatcher( filepath, 27, 18 ),
                            LocationMatcher( filepath, 28, 6 ) ),
          ),
          'location': LocationMatcher( filepath, 28, 5 )
        } ) )
      } )
    }
  } )


@ExpectedFailure( 'Renaming does not work on overridden methods '
                  'since jdt.ls 0.21.0',
                  matches_regexp( 'No item matched:.*TestWidgetImpl.java' ) )
@WithRetry
@SharedYcmd
def Subcommands_RefactorRename_MultipleFiles_test( app ):
  AbstractTestWidget = PathToTestFile( 'simple_eclipse_project',
                                       'src',
                                       'com',
                                       'test',
                                       'AbstractTestWidget.java' )
  TestFactory = PathToTestFile( 'simple_eclipse_project',
                                'src',
                                'com',
                                'test',
                                'TestFactory.java' )
  TestLauncher = PathToTestFile( 'simple_eclipse_project',
                                 'src',
                                 'com',
                                 'test',
                                 'TestLauncher.java' )
  TestWidgetImpl = PathToTestFile( 'simple_eclipse_project',
                                   'src',
                                   'com',
                                   'test',
                                   'TestWidgetImpl.java' )

  RunTest( app, {
    'description': 'RefactorRename works across files',
    'request': {
      'command': 'RefactorRename',
      'arguments': [ 'a_quite_long_string' ],
      'filepath': TestLauncher,
      'line_num': 32,
      'column_num': 13,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'fixits': contains_exactly( has_entries( {
          'chunks': contains_exactly(
            ChunkMatcher(
              'a_quite_long_string',
              LocationMatcher( AbstractTestWidget, 10, 15 ),
              LocationMatcher( AbstractTestWidget, 10, 39 ) ),
            ChunkMatcher(
              'a_quite_long_string',
              LocationMatcher( TestFactory, 28, 9 ),
              LocationMatcher( TestFactory, 28, 33 ) ),
            ChunkMatcher(
              'a_quite_long_string',
              LocationMatcher( TestLauncher, 32, 11 ),
              LocationMatcher( TestLauncher, 32, 35 ) ),
            ChunkMatcher(
              'a_quite_long_string',
              LocationMatcher( TestWidgetImpl, 20, 15 ),
              LocationMatcher( TestWidgetImpl, 20, 39 ) ),
          ),
          'location': LocationMatcher( TestLauncher, 32, 13 )
        } ) )
      } )
    }
  } )


@WithRetry
@SharedYcmd
def Subcommands_RefactorRename_Missing_New_Name_test( app ):
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'test',
                             'TestLauncher.java' )
  RunTest( app, {
    'description': 'RefactorRename raises an error without new name',
    'request': {
      'command': 'RefactorRename',
      'line_num': 15,
      'column_num': 5,
      'filepath': filepath,
    },
    'expect': {
      'response': requests.codes.internal_server_error,
      'data': ErrorMatcher( ValueError,
                            'Please specify a new name to rename it to.\n'
                            'Usage: RefactorRename <new name>' ),
    }
  } )


@WithRetry
@SharedYcmd
def Subcommands_RefactorRename_Unicode_test( app ):
  RunTest( app, {
    'description': 'Rename works for unicode identifier',
    'request': {
      'command': 'RefactorRename',
      'arguments': [ 'shorter' ],
      'line_num': 7,
      'column_num': 21,
      'filepath': TEST_JAVA,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'fixits': contains_exactly( has_entries( {
          'chunks': contains_exactly(
            ChunkMatcher(
              'shorter = "Test";\n    return shorter',
              LocationMatcher( TEST_JAVA, 7, 12 ),
              LocationMatcher( TEST_JAVA, 8, 25 )
            ),
          ),
        } ) ),
      } ),
    },
  } )



@WithRetry
def RunFixItTest( app, description, filepath, line, col, fixits_for_line ):
  RunTest( app, {
    'description': description,
    'request': {
      'command': 'FixIt',
      'line_num': line,
      'column_num': col,
      'filepath': filepath,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': fixits_for_line,
    }
  } )


@pytest.mark.parametrize( 'description,column', [
  ( 'FixIt works at the firtst char of the line', 1 ),
  ( 'FixIt works at the begin of the range of the diag.', 15 ),
  ( 'FixIt works at the end of the range of the diag.', 20 ),
  ( 'FixIt works at the end of the line', 34 ),
] )
@SharedYcmd
def Subcommands_FixIt_SingleDiag_MultipleOption_Insertion_test( app,
                                                                description,
                                                                column ):
  import os
  wibble_path = PathToTestFile( 'simple_eclipse_project',
                                'src',
                                'com',
                                'test',
                                'Wibble.java' )
  wibble_text = 'package com.test;{0}{0}public {1} Wibble {{{0}{0}}}{0}'
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'test',
                             'TestFactory.java' )

  # Note: The code actions for creating variables are really not very useful.
  # The import is, however, and the FixIt almost exactly matches the one
  # supplied when completing 'CUTHBERT' and auto-inserting.
  fixits_for_line = has_entries( {
    'fixits': contains_inanyorder(
      has_entries( {
        'text': "Import 'Wibble' (com.test.wobble)",
        'chunks': contains_exactly(
          ChunkMatcher( 'package com.test;\n\n'
                        'import com.test.wobble.Wibble;\n\n',
                        LocationMatcher( filepath, 1, 1 ),
                        LocationMatcher( filepath, 3, 1 ) ),
        ),
      } ),
      has_entries( {
        'text': "Create constant 'Wibble'",
        'chunks': contains_exactly(
          ChunkMatcher( '\n\nprivate static final String Wibble = null;',
                        LocationMatcher( filepath, 16, 4 ),
                        LocationMatcher( filepath, 16, 4 ) ),
        ),
      } ),
      has_entries( {
        'text': "Create class 'Wibble'",
        'chunks': contains_exactly(
          ChunkMatcher( wibble_text.format( os.linesep, 'class' ),
                        LocationMatcher( wibble_path, 1, 1 ),
                        LocationMatcher( wibble_path, 1, 1 ) ),
        ),
      } ),
      has_entries( {
        'text': "Create interface 'Wibble'",
        'chunks': contains_exactly(
          ChunkMatcher( wibble_text.format( os.linesep, 'interface' ),
                        LocationMatcher( wibble_path, 1, 1 ),
                        LocationMatcher( wibble_path, 1, 1 ) ),
        ),
      } ),
      has_entries( {
        'text': "Create enum 'Wibble'",
        'chunks': contains_exactly(
          ChunkMatcher( wibble_text.format( os.linesep, 'enum' ),
                        LocationMatcher( wibble_path, 1, 1 ),
                        LocationMatcher( wibble_path, 1, 1 ) ),
        ),
      } ),
      has_entries( {
        'text': "Create local variable 'Wibble'",
        'chunks': contains_exactly(
          ChunkMatcher( 'Object Wibble;\n\t',
                        LocationMatcher( filepath, 19, 5 ),
                        LocationMatcher( filepath, 19, 5 ) ),
        ),
      } ),
      has_entries( {
        'text': "Create field 'Wibble'",
        'chunks': contains_exactly(
          ChunkMatcher( '\n\nprivate Object Wibble;',
                        LocationMatcher( filepath, 16, 4 ),
                        LocationMatcher( filepath, 16, 4 ) ),
        ),
      } ),
      has_entries( {
        'text': "Create parameter 'Wibble'",
        'chunks': contains_exactly(
          ChunkMatcher( ', Object Wibble',
                        LocationMatcher( filepath, 18, 32 ),
                        LocationMatcher( filepath, 18, 32 ) ),
        ),
      } ),
      has_entries( {
        'text': 'Generate toString()...',
        'chunks': contains_exactly(
          ChunkMatcher( '\n\n@Override\npublic String toString() {'
                        '\n\treturn "TestFactory []";\n}',
                        LocationMatcher( filepath, 32, 4 ),
                        LocationMatcher( filepath, 32, 4 ) ),
        ),
      } ),
      has_entries( {
        'text': 'Organize imports',
        'chunks': contains_exactly(
          ChunkMatcher( '\n\nimport com.test.wobble.Wibble;\n\n',
                        LocationMatcher( filepath, 1, 18 ),
                        LocationMatcher( filepath, 3, 1 ) ),
        ),
      } ),
      has_entries( {
        'text': 'Change modifiers to final where possible',
        'chunks': contains_exactly(
          ChunkMatcher( 'final Wibble w ) {\n    if ( w == Wibble.CUTHBERT ) {'
                        '\n    }\n  }\n\n  public AbstractTestWidget getWidget'
                        '( final String info ) {\n    final AbstractTestWidget'
                        ' w = new TestWidgetImpl( info );\n    final ',
                        LocationMatcher( filepath, 18, 24 ),
                        LocationMatcher( filepath, 25, 5 ) ),
        ),
      } ),
    )
  } )

  RunFixItTest( app, description, filepath, 19, column, fixits_for_line )


@SharedYcmd
def Subcommands_FixIt_SingleDiag_SingleOption_Modify_test( app ):
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'test',
                             'TestFactory.java' )

  # TODO: As there is only one option, we automatically apply it.
  # In Java case this might not be the right thing. It's a code assist, not a
  # FixIt really. Perhaps we should change the client to always ask for
  # confirmation?
  fixits = has_entries( {
    'fixits': contains_inanyorder(
      has_entries( {
        'text': "Change type of 'test' to 'boolean'",
        'chunks': contains_exactly(
          ChunkMatcher( 'boolean',
                        LocationMatcher( filepath, 14, 12 ),
                        LocationMatcher( filepath, 14, 15 ) ),
        ),
      } ),
      has_entries( {
        'text': 'Generate toString()...',
        'chunks': contains_exactly(
          ChunkMatcher( '\n\n@Override\npublic String toString() {'
                        '\n\treturn "TestFactory []";\n}',
                        LocationMatcher( filepath, 32, 4 ),
                        LocationMatcher( filepath, 32, 4 ) ),
        ),
      } ),
      has_entries( {
        'text': 'Organize imports',
        'chunks': contains_exactly(
          ChunkMatcher( '\n\nimport com.test.wobble.Wibble;\n\n',
                        LocationMatcher( filepath, 1, 18 ),
                        LocationMatcher( filepath, 3, 1 ) ),
        ),
      } ),
      has_entries( {
        'text': 'Change modifiers to final where possible',
        'chunks': contains_exactly(
          ChunkMatcher( 'final Wibble w ) {\n    if ( w == Wibble.CUTHBERT ) {'
                        '\n    }\n  }\n\n  public AbstractTestWidget getWidget'
                        '( final String info ) {\n    final AbstractTestWidget'
                        ' w = new TestWidgetImpl( info );\n    final ',
                        LocationMatcher( filepath, 18, 24 ),
                        LocationMatcher( filepath, 25, 5 ) ),
        ),
      } ),
    )
  } )

  RunFixItTest( app, 'FixIts can change lines as well as add them',
                filepath, 27, 12, fixits )


@SharedYcmd
def Subcommands_FixIt_SingleDiag_MultiOption_Delete_test( app ):
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'test',
                             'TestFactory.java' )

  fixits = has_entries( {
    'fixits': contains_inanyorder(
      has_entries( {
        'text': "Remove 'testString', keep assignments with side effects",
        'chunks': contains_exactly(
          ChunkMatcher( '',
                        LocationMatcher( filepath, 14, 21 ),
                        LocationMatcher( filepath, 15, 30 ) ),
        ),
      } ),
      # The edit reported for this is juge and uninteresting really. Manual
      # testing can show that it works. This test is really about the previous
      # FixIt (and nonetheless, the previous tests ensure that we correctly
      # populate the chunks list; the contents all come from jdt.ls)
      has_entries( {
        'text': "Create getter and setter for 'testString'",
        'chunks': instance_of( list )
      } ),
      has_entries( {
        'text': "Organize imports",
        'chunks': instance_of( list )
      } ),
      has_entries( {
        'text': "Generate Getters and Setters",
        'chunks': instance_of( list )
      } ),
      has_entries( {
        'text': 'Change modifiers to final where possible',
        'chunks': instance_of( list )
      } ),
    )
  } )

  RunFixItTest( app, 'FixIts can change lines as well as add them',
                filepath, 15, 29, fixits )


@pytest.mark.parametrize( 'description,column', [
  ( 'diags are merged in FixIt options - start of line', 1 ),
  ( 'diags are merged in FixIt options - start of diag 1', 10 ),
  ( 'diags are merged in FixIt options - end of diag 1', 15 ),
  ( 'diags are merged in FixIt options - start of diag 2', 23 ),
  ( 'diags are merged in FixIt options - end of diag 2', 46 ),
  ( 'diags are merged in FixIt options - end of line', 55 ),
] )
@SharedYcmd
def Subcommands_FixIt_MultipleDiags_test( app, description, column ):
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'test',
                             'TestFactory.java' )

  fixits = has_entries( {
    'fixits': contains_inanyorder(
      has_entries( {
        'text': "Change type of 'test' to 'boolean'",
        'chunks': contains_exactly(
          ChunkMatcher( 'boolean',
                        LocationMatcher( filepath, 14, 12 ),
                        LocationMatcher( filepath, 14, 15 ) ),
        ),
      } ),
      has_entries( {
        'text': "Remove argument to match 'doSomethingVaguelyUseful()'",
        'chunks': contains_exactly(
          ChunkMatcher( '',
                        LocationMatcher( filepath, 30, 48 ),
                        LocationMatcher( filepath, 30, 50 ) ),
        ),
      } ),
      has_entries( {
        'text': "Change method 'doSomethingVaguelyUseful()': Add parameter "
                "'Bar'",
        'chunks': instance_of( list ),
      } ),
      has_entries( {
        'text': "Create method 'doSomethingVaguelyUseful(Bar)' in type "
                "'AbstractTestWidget'",
        'chunks': instance_of( list ),
      } ),
      has_entries( {
        'text': "Generate toString()...",
        'chunks': instance_of( list ),
      } ),
      has_entries( {
        'text': "Organize imports",
        'chunks': instance_of( list ),
      } ),
      has_entries( {
        'text': 'Change modifiers to final where possible',
        'chunks': instance_of( list ),
      } ),
    )
  } )

  RunFixItTest( app, description, filepath, 30, column, fixits )


@SharedYcmd
def Subcommands_FixIt_Range_test( app ):
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'test',
                             'TestLauncher.java' )
  RunTest( app, {
    'description': 'Formatting is applied on some part of the file '
                   'with tabs composed of 4 spaces',
    'request': {
      'command': 'FixIt',
      'filepath': filepath,
      'range': {
        'start': {
          'line_num': 34,
          'column_num': 28,
        },
        'end': {
          'line_num': 34,
          'column_num': 73
        }
      },
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'fixits': contains_inanyorder(
          has_entries( {
            'text': 'Extract to field',
            'chunks': contains_exactly(
              ChunkMatcher(
                matches_regexp(
                  'private String \\w+;\n'
                  '\n'
                  '\t@Override\n'
                  '      public void launch\\(\\) {\n'
                  '        AbstractTestWidget w = '
                  'factory.getWidget\\( "Test" \\);\n'
                  '        '
                  'w.doSomethingVaguelyUseful\\(\\);\n'
                  '\n'
                  '        \\w+ = "Did something '
                  'useful: " \\+ w.getWidgetInfo\\(\\);\n'
                  '\t\tSystem.out.println\\( \\w+' ),
                LocationMatcher( filepath, 29, 7 ),
                LocationMatcher( filepath, 34, 73 ) ),
            ),
          } ),
          has_entries( {
            'text': 'Extract to method',
            'chunks': contains_exactly(
              # This one is a wall of text that rewrites 35 lines
              ChunkMatcher( instance_of( str ),
                            LocationMatcher( filepath, 1, 1 ),
                            LocationMatcher( filepath, 35, 8 ) ),
            ),
          } ),
          has_entries( {
            'text': 'Extract to local variable (replace all occurrences)',
            'chunks': contains_exactly(
              ChunkMatcher(
                matches_regexp(
                  'String \\w+ = "Did something '
                  'useful: " \\+ w.getWidgetInfo\\(\\);\n'
                  '\t\tSystem.out.println\\( \\w+' ),
                LocationMatcher( filepath, 34, 9 ),
                LocationMatcher( filepath, 34, 73 ) ),
            ),
          } ),
          has_entries( {
            'text': 'Extract to local variable',
            'chunks': contains_exactly(
              ChunkMatcher(
                matches_regexp(
                  'String \\w+ = "Did something '
                  'useful: " \\+ w.getWidgetInfo\\(\\);\n'
                  '\t\tSystem.out.println\\( \\w+' ),
                LocationMatcher( filepath, 34, 9 ),
                LocationMatcher( filepath, 34, 73 ) ),
            ),
          } ),
          has_entries( {
            'text': 'Organize imports',
            'chunks': instance_of( list ),
          } ),
          has_entries( {
            'text': 'Change modifiers to final where possible',
            'chunks': instance_of( list ),
          } ),
        )
      } )
    }
  } )



@SharedYcmd
def Subcommands_FixIt_NoDiagnostics_test( app ):
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'test',
                             'TestFactory.java' )

  RunFixItTest( app, "no FixIts means you gotta code it yo' self",
                filepath, 1, 1, has_entries( {
                  'fixits': contains_inanyorder(
                    has_entries( {
                      'text': 'Change modifiers to final where possible',
                      'chunks': instance_of( list ) } ),
                    has_entries( { 'text': 'Organize imports',
                                   'chunks': instance_of( list ) } ),
                    has_entries( { 'text': 'Generate toString()...',
                                   'chunks': instance_of( list ) } ) ) } ) )


@SharedYcmd
def Subcommands_FixIt_Unicode_test( app ):
  fixits = has_entries( {
    'fixits': contains_inanyorder(
      has_entries( {
        'text': "Remove argument to match 'doUnicødeTes()'",
        'chunks': contains_exactly(
          ChunkMatcher( '',
                        LocationMatcher( TEST_JAVA, 13, 24 ),
                        LocationMatcher( TEST_JAVA, 13, 29 ) ),
        ),
      } ),
      has_entries( {
        'text': "Change method 'doUnicødeTes()': Add parameter 'String'",
        'chunks': contains_exactly(
          ChunkMatcher( 'String test2',
                        LocationMatcher( TEST_JAVA, 6, 31 ),
                        LocationMatcher( TEST_JAVA, 6, 31 ) ),
        ),
      } ),
      has_entries( {
        'text': "Create method 'doUnicødeTes(String)'",
        'chunks': contains_exactly(
          ChunkMatcher( 'private void doUnicødeTes(String test2) {\n}\n\n\n',
                        LocationMatcher( TEST_JAVA, 20, 3 ),
                        LocationMatcher( TEST_JAVA, 20, 3 ) ),
        ),
      } ),
      has_entries( {
        'text': 'Change modifiers to final where possible',
        'chunks': instance_of( list ),
      } ),
      has_entries( {
        'text': "Generate Getters and Setters",
        'chunks': instance_of( list ),
      } ),
    )
  } )

  RunFixItTest( app, 'FixIts and diagnostics work with unicode strings',
                TEST_JAVA, 13, 1, fixits )


@WithRetry
@IsolatedYcmd()
def Subcommands_FixIt_InvalidURI_test( app ):
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'test',
                             'TestFactory.java' )

  fixits = has_entries( {
    'fixits': contains_inanyorder(
      has_entries( {
        'text': "Change type of 'test' to 'boolean'",
        'chunks': contains_exactly(
          ChunkMatcher( 'boolean',
                        LocationMatcher( '', 14, 12 ),
                        LocationMatcher( '', 14, 15 ) ),
        ),
      } ),
      has_entries( {
        'text': 'Organize imports',
        'chunks': contains_exactly(
          ChunkMatcher( '\n\nimport com.test.wobble.Wibble;\n\n',
                        LocationMatcher( '', 1, 1 ),
                        LocationMatcher( '', 3, 1 ) ),
        ),
      } ),
      has_entries( {
        'text': 'Change modifiers to final where possible',
        'chunks': contains_exactly(
          ChunkMatcher( "final Wibble w ) {\n    if ( w == Wibble.CUTHBERT ) {"
                        "\n    }\n  }\n\n  public AbstractTestWidget getWidget"
                        "( final String info ) {\n    final AbstractTestWidget"
                        " w = new TestWidgetImpl( info );\n    final ",
                        LocationMatcher( '', 18, 24 ),
                        LocationMatcher( '', 25, 5 ) ),
        ),
      } ),
      has_entries( {
        'text': 'Generate toString()...',
        'chunks': contains_exactly(
          ChunkMatcher( '\n\n@Override\npublic String toString() {'
                        '\n\treturn "TestFactory []";\n}',
                        LocationMatcher( '', 32, 4 ),
                        LocationMatcher( '', 32, 4 ) ),
        ),
      } ),
    )
  } )

  contents = ReadFile( filepath )
  # Wait for jdt.ls to have parsed the file and returned some diagnostics
  for tries in range( 0, 60 ):
    results = app.post_json( '/event_notification',
                             BuildRequest( filepath = filepath,
                                           filetype = 'java',
                                           contents = contents,
                                           event_name = 'FileReadyToParse' ) )
    if results.json:
      break

    time.sleep( .25 )

  with patch(
    'ycmd.completers.language_server.language_server_protocol.UriToFilePath',
    side_effect = lsp.InvalidUriException ):
    RunTest( app, {
      'description': 'Invalid URIs do not make us crash',
      'request': {
        'command': 'FixIt',
        'line_num': 27,
        'column_num': 12,
        'filepath': filepath,
      },
      'expect': {
        'response': requests.codes.ok,
        'data': fixits,
      }
    } )


@WithRetry
@SharedYcmd
def Subcommands_Format_WholeFile_Spaces_test( app ):
  RunTest( app, {
    'description': 'Formatting is applied on the whole file '
                   'with tabs composed of 4 spaces',
    'request': {
      'command': 'Format',
      'filepath': TEST_JAVA,
      'options': {
        'tab_size': 4,
        'insert_spaces': True
      }
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'fixits': contains_exactly( has_entries( {
          'chunks': contains_exactly(
            ChunkMatcher( '\n    ',
                          LocationMatcher( TEST_JAVA,  3, 20 ),
                          LocationMatcher( TEST_JAVA,  4,  3 ) ),
            ChunkMatcher( '\n\n    ',
                          LocationMatcher( TEST_JAVA,  4, 22 ),
                          LocationMatcher( TEST_JAVA,  6,  3 ) ),
            ChunkMatcher( '\n        ',
                          LocationMatcher( TEST_JAVA,  6, 34 ),
                          LocationMatcher( TEST_JAVA,  7,  5 ) ),
            ChunkMatcher( '\n        ',
                          LocationMatcher( TEST_JAVA,  7, 35 ),
                          LocationMatcher( TEST_JAVA,  8,  5 ) ),
            ChunkMatcher( '',
                          LocationMatcher( TEST_JAVA,  8, 25 ),
                          LocationMatcher( TEST_JAVA,  8, 26 ) ),
            ChunkMatcher( '\n    ',
                          LocationMatcher( TEST_JAVA,  8, 27 ),
                          LocationMatcher( TEST_JAVA,  9,  3 ) ),
            ChunkMatcher( '\n\n    ',
                          LocationMatcher( TEST_JAVA,  9,  4 ),
                          LocationMatcher( TEST_JAVA, 11,  3 ) ),
            ChunkMatcher( '\n        ',
                          LocationMatcher( TEST_JAVA, 11, 29 ),
                          LocationMatcher( TEST_JAVA, 12,  5 ) ),
            ChunkMatcher( '\n        ',
                          LocationMatcher( TEST_JAVA, 12, 26 ),
                          LocationMatcher( TEST_JAVA, 13,  5 ) ),
            ChunkMatcher( '',
                          LocationMatcher( TEST_JAVA, 13, 24 ),
                          LocationMatcher( TEST_JAVA, 13, 25 ) ),
            ChunkMatcher( '',
                          LocationMatcher( TEST_JAVA, 13, 29 ),
                          LocationMatcher( TEST_JAVA, 13, 30 ) ),
            ChunkMatcher( '\n\n        ',
                          LocationMatcher( TEST_JAVA, 13, 32 ),
                          LocationMatcher( TEST_JAVA, 15,  5 ) ),
            ChunkMatcher( '\n        ',
                          LocationMatcher( TEST_JAVA, 15, 58 ),
                          LocationMatcher( TEST_JAVA, 16,  5 ) ),
            ChunkMatcher( '\n    ',
                          LocationMatcher( TEST_JAVA, 16, 42 ),
                          LocationMatcher( TEST_JAVA, 17,  3 ) ),
            ChunkMatcher( '\n\n    ',
                          LocationMatcher( TEST_JAVA, 17,  4 ),
                          LocationMatcher( TEST_JAVA, 20,  3 ) ),
            ChunkMatcher( '\n        ',
                          LocationMatcher( TEST_JAVA, 20, 28 ),
                          LocationMatcher( TEST_JAVA, 21,  5 ) ),
            ChunkMatcher( '\n        ',
                          LocationMatcher( TEST_JAVA, 21, 28 ),
                          LocationMatcher( TEST_JAVA, 22,  5 ) ),
            ChunkMatcher( '\n        ',
                          LocationMatcher( TEST_JAVA, 22, 30 ),
                          LocationMatcher( TEST_JAVA, 23,  5 ) ),
            ChunkMatcher( '\n        ',
                          LocationMatcher( TEST_JAVA, 23, 23 ),
                          LocationMatcher( TEST_JAVA, 24,  5 ) ),
            ChunkMatcher( '\n    ',
                          LocationMatcher( TEST_JAVA, 24, 27 ),
                          LocationMatcher( TEST_JAVA, 25,  3 ) ),
          )
        } ) )
      } )
    }
  } )


@WithRetry
@SharedYcmd
def Subcommands_Format_WholeFile_Tabs_test( app ):
  RunTest( app, {
    'description': 'Formatting is applied on the whole file '
                   'with tabs composed of 2 spaces',
    'request': {
      'command': 'Format',
      'filepath': TEST_JAVA,
      'options': {
        'tab_size': 4,
        'insert_spaces': False
      }
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'fixits': contains_exactly( has_entries( {
          'chunks': contains_exactly(
            ChunkMatcher( '\n\t',
                          LocationMatcher( TEST_JAVA,  3, 20 ),
                          LocationMatcher( TEST_JAVA,  4,  3 ) ),
            ChunkMatcher( '\n\n\t',
                          LocationMatcher( TEST_JAVA,  4, 22 ),
                          LocationMatcher( TEST_JAVA,  6,  3 ) ),
            ChunkMatcher( '\n\t\t',
                          LocationMatcher( TEST_JAVA,  6, 34 ),
                          LocationMatcher( TEST_JAVA,  7,  5 ) ),
            ChunkMatcher( '\n\t\t',
                          LocationMatcher( TEST_JAVA,  7, 35 ),
                          LocationMatcher( TEST_JAVA,  8,  5 ) ),
            ChunkMatcher( '',
                          LocationMatcher( TEST_JAVA,  8, 25 ),
                          LocationMatcher( TEST_JAVA,  8, 26 ) ),
            ChunkMatcher( '\n\t',
                          LocationMatcher( TEST_JAVA,  8, 27 ),
                          LocationMatcher( TEST_JAVA,  9,  3 ) ),
            ChunkMatcher( '\n\n\t',
                          LocationMatcher( TEST_JAVA,  9,  4 ),
                          LocationMatcher( TEST_JAVA, 11,  3 ) ),
            ChunkMatcher( '\n\t\t',
                          LocationMatcher( TEST_JAVA, 11, 29 ),
                          LocationMatcher( TEST_JAVA, 12,  5 ) ),
            ChunkMatcher( '\n\t\t',
                          LocationMatcher( TEST_JAVA, 12, 26 ),
                          LocationMatcher( TEST_JAVA, 13,  5 ) ),
            ChunkMatcher( '',
                          LocationMatcher( TEST_JAVA, 13, 24 ),
                          LocationMatcher( TEST_JAVA, 13, 25 ) ),
            ChunkMatcher( '',
                          LocationMatcher( TEST_JAVA, 13, 29 ),
                          LocationMatcher( TEST_JAVA, 13, 30 ) ),
            ChunkMatcher( '\n\n\t\t',
                          LocationMatcher( TEST_JAVA, 13, 32 ),
                          LocationMatcher( TEST_JAVA, 15,  5 ) ),
            ChunkMatcher( '\n\t\t',
                          LocationMatcher( TEST_JAVA, 15, 58 ),
                          LocationMatcher( TEST_JAVA, 16,  5 ) ),
            ChunkMatcher( '\n\t',
                          LocationMatcher( TEST_JAVA, 16, 42 ),
                          LocationMatcher( TEST_JAVA, 17,  3 ) ),
            ChunkMatcher( '\n\n\t',
                          LocationMatcher( TEST_JAVA, 17,  4 ),
                          LocationMatcher( TEST_JAVA, 20,  3 ) ),
            ChunkMatcher( '\n\t\t',
                          LocationMatcher( TEST_JAVA, 20, 28 ),
                          LocationMatcher( TEST_JAVA, 21,  5 ) ),
            ChunkMatcher( '\n\t\t',
                          LocationMatcher( TEST_JAVA, 21, 28 ),
                          LocationMatcher( TEST_JAVA, 22,  5 ) ),
            ChunkMatcher( '\n\t\t',
                          LocationMatcher( TEST_JAVA, 22, 30 ),
                          LocationMatcher( TEST_JAVA, 23,  5 ) ),
            ChunkMatcher( '\n\t\t',
                          LocationMatcher( TEST_JAVA, 23, 23 ),
                          LocationMatcher( TEST_JAVA, 24,  5 ) ),
            ChunkMatcher( '\n\t',
                          LocationMatcher( TEST_JAVA, 24, 27 ),
                          LocationMatcher( TEST_JAVA, 25,  3 ) ),
          )
        } ) )
      } )
    }
  } )


@WithRetry
@SharedYcmd
def Subcommands_Format_Range_Spaces_test( app ):
  RunTest( app, {
    'description': 'Formatting is applied on some part of the file '
                   'with tabs composed of 4 spaces',
    'request': {
      'command': 'Format',
      'filepath': TEST_JAVA,
      'range': {
        'start': {
          'line_num': 20,
          'column_num': 1,
        },
        'end': {
          'line_num': 25,
          'column_num': 4
        }
      },
      'options': {
        'tab_size': 4,
        'insert_spaces': True
      }
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'fixits': contains_exactly( has_entries( {
          'chunks': contains_exactly(
            ChunkMatcher( '  ',
                          LocationMatcher( TEST_JAVA, 20,  1 ),
                          LocationMatcher( TEST_JAVA, 20,  3 ) ),
            ChunkMatcher( '\n      ',
                          LocationMatcher( TEST_JAVA, 20, 28 ),
                          LocationMatcher( TEST_JAVA, 21,  5 ) ),
            ChunkMatcher( '\n      ',
                          LocationMatcher( TEST_JAVA, 21, 28 ),
                          LocationMatcher( TEST_JAVA, 22,  5 ) ),
            ChunkMatcher( '\n      ',
                          LocationMatcher( TEST_JAVA, 22, 30 ),
                          LocationMatcher( TEST_JAVA, 23,  5 ) ),
            ChunkMatcher( '\n      ',
                          LocationMatcher( TEST_JAVA, 23, 23 ),
                          LocationMatcher( TEST_JAVA, 24,  5 ) ),
          )
        } ) )
      } )
    }
  } )


@WithRetry
@SharedYcmd
def Subcommands_Format_Range_Tabs_test( app ):
  RunTest( app, {
    'description': 'Formatting is applied on some part of the file '
                   'with tabs instead of spaces',
    'request': {
      'command': 'Format',
      'filepath': TEST_JAVA,
      'range': {
        'start': {
          'line_num': 20,
          'column_num': 1,
        },
        'end': {
          'line_num': 25,
          'column_num': 4
        }
      },
      'options': {
        'tab_size': 4,
        'insert_spaces': False
      }
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'fixits': contains_exactly( has_entries( {
          'chunks': contains_exactly(
            ChunkMatcher( '\t',
                          LocationMatcher( TEST_JAVA, 20,  1 ),
                          LocationMatcher( TEST_JAVA, 20,  3 ) ),
            ChunkMatcher( '\n\t\t',
                          LocationMatcher( TEST_JAVA, 20, 28 ),
                          LocationMatcher( TEST_JAVA, 21,  5 ) ),
            ChunkMatcher( '\n\t\t',
                          LocationMatcher( TEST_JAVA, 21, 28 ),
                          LocationMatcher( TEST_JAVA, 22,  5 ) ),
            ChunkMatcher( '\n\t\t',
                          LocationMatcher( TEST_JAVA, 22, 30 ),
                          LocationMatcher( TEST_JAVA, 23,  5 ) ),
            ChunkMatcher( '\n\t\t',
                          LocationMatcher( TEST_JAVA, 23, 23 ),
                          LocationMatcher( TEST_JAVA, 24,  5 ) ),
            ChunkMatcher( '\n\t',
                          LocationMatcher( TEST_JAVA, 24, 27 ),
                          LocationMatcher( TEST_JAVA, 25,  3 ) ),
          )
        } ) )
      } )
    }
  } )


@WithRetry
@SharedYcmd
def RunGoToTest( app, description, filepath, line, col, cmd, goto_response ):
  RunTest( app, {
    'description': description,
    'request': {
      'command': cmd,
      'line_num': line,
      'column_num': col,
      'filepath': filepath
    },
    'expect': {
      'response': requests.codes.ok,
      'data': goto_response,
    }
  } )


@pytest.mark.parametrize( 'test', [
    # Member function local variable
    { 'request': { 'line': 28, 'col': 5, 'filepath': TESTLAUNCHER_JAVA },
      'response': { 'line_num': 27, 'column_num': 18,
                    'filepath': TESTLAUNCHER_JAVA },
      'description': 'GoTo works for member local variable' },
    # Member variable
    { 'request': { 'line': 22, 'col': 7, 'filepath': TESTLAUNCHER_JAVA },
      'response': { 'line_num': 8, 'column_num': 16,
                    'filepath': TESTLAUNCHER_JAVA },
      'description': 'GoTo works for member variable' },
    # Method
    { 'request': { 'line': 28, 'col': 7, 'filepath': TESTLAUNCHER_JAVA },
      'response': { 'line_num': 21, 'column_num': 16,
                    'filepath': TESTLAUNCHER_JAVA },
      'description': 'GoTo works for method' },
    # Constructor
    { 'request': { 'line': 38, 'col': 26, 'filepath': TESTLAUNCHER_JAVA },
      'response': { 'line_num': 10, 'column_num': 10,
                    'filepath': TESTLAUNCHER_JAVA },
      'description': 'GoTo works for jumping to constructor' },
    # Jump to self - main()
    { 'request': { 'line': 26, 'col': 22, 'filepath': TESTLAUNCHER_JAVA },
      'response': { 'line_num': 26, 'column_num': 22,
                    'filepath': TESTLAUNCHER_JAVA },
      'description': 'GoTo works for jumping to the same position' },
    # Static method
    { 'request': { 'line': 37, 'col': 11, 'filepath': TESTLAUNCHER_JAVA },
      'response': { 'line_num': 13, 'column_num': 21,
                    'filepath': TESTLAUNCHER_JAVA },
      'description': 'GoTo works for static method' },
    # Static variable
    { 'request': { 'line': 14, 'col': 11, 'filepath': TESTLAUNCHER_JAVA },
      'response': { 'line_num': 12, 'column_num': 21,
                    'filepath': TESTLAUNCHER_JAVA },
      'description': 'GoTo works for static variable' },
    # Argument variable
    { 'request': { 'line': 23, 'col': 5, 'filepath': TESTLAUNCHER_JAVA },
      'response': { 'line_num': 21, 'column_num': 32,
                    'filepath': TESTLAUNCHER_JAVA },
      'description': 'GoTo works for argument variable' },
    # Class
    { 'request': { 'line': 27, 'col': 10, 'filepath': TESTLAUNCHER_JAVA },
      'response': { 'line_num': 6, 'column_num': 7,
                    'filepath': TESTLAUNCHER_JAVA },
      'description': 'GoTo works for jumping to class declaration' },
    # Unicode
    { 'request': { 'line': 8, 'col': 12, 'filepath': TEST_JAVA },
      'response': { 'line_num': 7, 'column_num': 12, 'filepath': TEST_JAVA },
      'description': 'GoTo works for unicode identifiers' }
  ] )
@pytest.mark.parametrize( 'command', [ 'GoTo',
                                       'GoToDefinition',
                                       'GoToDeclaration' ] )
@SharedYcmd
def Subcommands_GoTo_test( app, command, test ):
  RunGoToTest( app,
               test[ 'description' ],
               test[ 'request' ][ 'filepath' ],
               test[ 'request' ][ 'line' ],
               test[ 'request' ][ 'col' ],
               command,
               has_entries( test[ 'response' ] ) )


@pytest.mark.parametrize( 'test', [
    # Member function local variable
    { 'request': { 'line': 28, 'col': 5, 'filepath': TESTLAUNCHER_JAVA },
      'response': { 'line_num': 6, 'column_num': 7,
                    'filepath': TESTLAUNCHER_JAVA },
      'description': 'GoToType works for member local variable' },
    # Member variable
    { 'request': { 'line': 22, 'col': 7, 'filepath': TESTLAUNCHER_JAVA },
      'response': { 'line_num': 6, 'column_num': 14, 'filepath': TSET_JAVA },
      'description': 'GoToType works for member variable' },
  ] )
@SharedYcmd
def Subcommands_GoToType_test( app, test ):
  RunGoToTest( app,
               test[ 'description' ],
               test[ 'request' ][ 'filepath' ],
               test[ 'request' ][ 'line' ],
               test[ 'request' ][ 'col' ],
               'GoToType',
               has_entries( test[ 'response' ] ) )


@pytest.mark.parametrize( 'test', [
    # Interface
    { 'request': { 'line': 17, 'col': 25, 'filepath': TESTLAUNCHER_JAVA },
      'response': { 'line_num': 28, 'column_num': 16,
                    'filepath': TESTLAUNCHER_JAVA },
      'description': 'GoToImplementation on interface '
                     'jumps to its implementation' },
    # Interface reference
    { 'request': { 'line': 21, 'col': 30, 'filepath': TESTLAUNCHER_JAVA },
      'response': { 'line_num': 28, 'column_num': 16,
                    'filepath': TESTLAUNCHER_JAVA },
      'description': 'GoToImplementation on interface reference '
                     'jumpts to its implementation' },
  ] )
@SharedYcmd
def Subcommands_GoToImplementation_test( app, test ):
  RunGoToTest( app,
               test[ 'description' ],
               test[ 'request' ][ 'filepath' ],
               test[ 'request' ][ 'line' ],
               test[ 'request' ][ 'col' ],
               'GoToImplementation',
               has_entries( test[ 'response' ] ) )


@WithRetry
@SharedYcmd
def Subcommands_OrganizeImports_test( app ):
  RunTest( app, {
    'description': 'Imports are resolved and sorted, '
                   'and unused ones are removed',
    'request': {
      'command': 'OrganizeImports',
      'filepath': TESTLAUNCHER_JAVA
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'fixits': contains_exactly( has_entries( {
          'chunks': contains_exactly(
            ChunkMatcher( 'import com.youcompleteme.Test;\n'
                          'import com.youcompleteme.testing.Tset;',
                          LocationMatcher( TESTLAUNCHER_JAVA, 3,  1 ),
                          LocationMatcher( TESTLAUNCHER_JAVA, 4, 54 ) ),
          )
        } ) )
      } )
    }
  } )


@WithRetry
@SharedYcmd
@patch( 'ycmd.completers.language_server.language_server_completer.'
        'REQUEST_TIMEOUT_COMMAND',
        5 )
def Subcommands_RequestTimeout_test( app ):
  with patch.object(
    handlers._server_state.GetFiletypeCompleter( [ 'java' ] ).GetConnection(),
    'WriteData' ):
    RunTest( app, {
      'description': 'Request timeout throws an error',
      'request': {
        'command': 'FixIt',
        'line_num': 1,
        'column_num': 1,
        'filepath': TEST_JAVA,
      },
      'expect': {
        'response': requests.codes.internal_server_error,
        'data': ErrorMatcher( ResponseTimeoutException, 'Response Timeout' )
      }
    } )


@WithRetry
@SharedYcmd
def Subcommands_RequestFailed_test( app ):
  connection = handlers._server_state.GetFiletypeCompleter(
    [ 'java' ] ).GetConnection()

  def WriteJunkToServer( data ):
    junk = data.replace( bytes( b'textDocument/codeAction' ),
                         bytes( b'textDocument/codeFAILED' ) )

    with connection._stdin_lock:
      connection._server_stdin.write( junk )
      connection._server_stdin.flush()


  with patch.object( connection, 'WriteData', side_effect = WriteJunkToServer ):
    RunTest( app, {
      'description': 'Response errors propagate to the client',
      'request': {
        'command': 'FixIt',
        'line_num': 1,
        'column_num': 1,
        'filepath': TEST_JAVA,
      },
      'expect': {
        'response': requests.codes.internal_server_error,
        'data': ErrorMatcher( ResponseFailedException )
      }
    } )


@WithRetry
@SharedYcmd
def Subcommands_IndexOutOfRange_test( app ):
  RunTest( app, {
    'description': 'Request error handles the error',
    'request': {
      'command': 'FixIt',
      'line_num': 99,
      'column_num': 99,
      'filepath': TEST_JAVA,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( { 'fixits': contains_exactly( has_entries(
        { 'text': 'Generate Getters and Setters',
          'chunks': instance_of( list ) } ) ) } ),
    }
  } )


@WithRetry
@SharedYcmd
def Subcommands_DifferentFileTypesUpdate_test( app ):
  RunTest( app, {
    'description': 'Request error handles the error',
    'request': {
      'command': 'FixIt',
      'line_num': 99,
      'column_num': 99,
      'filepath': TEST_JAVA,
      'file_data': {
        '!/bin/sh': {
          'filetypes': [],
          'contents': 'this should be ignored by the completer',
        },
        '/path/to/non/project/file': {
          'filetypes': [ 'c' ],
          'contents': 'this should be ignored by the completer',
        },
        TESTLAUNCHER_JAVA: {
          'filetypes': [ 'some', 'java', 'junk', 'also' ],
          'contents': ReadFile( TESTLAUNCHER_JAVA ),
        },
        '!/usr/bin/sh': {
          'filetypes': [ 'java' ],
          'contents': '\n',
        },
      }
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( { 'fixits': contains_exactly( has_entries(
        { 'text': 'Generate Getters and Setters',
          'chunks': instance_of( list ) } ) ) } ),
    }
  } )


@WithRetry
@IsolatedYcmd( { 'extra_conf_globlist':
                 PathToTestFile( 'extra_confs', '*' ) } )
def Subcommands_ExtraConf_SettingsValid_test( app ):
  filepath = PathToTestFile( 'extra_confs',
                             'simple_extra_conf_project',
                             'src',
                             'ExtraConf.java' )
  RunTest( app, {
    'description': 'RefactorRename is disabled in extra conf.',
    'request': {
      'command': 'RefactorRename',
      'arguments': [ 'renamed_l' ],
      'filepath': filepath,
      'line_num': 1,
      'column_num': 7,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'fixits': contains_exactly( has_entries( {
          'chunks': empty(),
          'location': LocationMatcher( filepath, 1, 7 )
        } ) )
      } )
    }
  } )


@WithRetry
@IsolatedYcmd( { 'extra_conf_globlist':
                 PathToTestFile( 'extra_confs', '*' ) } )
def Subcommands_AdditionalFormatterOptions_test( app ):
  filepath = PathToTestFile( 'extra_confs',
                             'simple_extra_conf_project',
                             'src',
                             'ExtraConf.java' )
  RunTest( app, {
    'description': 'Format respects settings from extra conf.',
    'request': {
      'command': 'Format',
      'filepath': filepath,
      'options': {
        'tab_size': 4,
        'insert_spaces': True
      }
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'fixits': contains_exactly( has_entries( {
          'chunks': contains_exactly(
            ChunkMatcher( '\n    ',
                          LocationMatcher( filepath,  1, 18 ),
                          LocationMatcher( filepath,  2,  3 ) ),
            ChunkMatcher( '\n            ',
                          LocationMatcher( filepath,  2, 20 ),
                          LocationMatcher( filepath,  2, 21 ) ),
            ChunkMatcher( '',
                          LocationMatcher( filepath,  2, 29 ),
                          LocationMatcher( filepath,  2, 30 ) ),
            ChunkMatcher( '\n    ',
                          LocationMatcher( filepath,  2, 33 ),
                          LocationMatcher( filepath,  2, 33 ) ),
            ChunkMatcher( '\n\n    ',
                          LocationMatcher( filepath,  2, 34 ),
                          LocationMatcher( filepath,  4,  3 ) ),
            ChunkMatcher( '\n            ',
                          LocationMatcher( filepath,  4, 27 ),
                          LocationMatcher( filepath,  4, 28 ) ),
            ChunkMatcher( '',
                          LocationMatcher( filepath,  4, 41 ),
                          LocationMatcher( filepath,  4, 42 ) ),
            ChunkMatcher( '\n        ',
                          LocationMatcher( filepath,  4, 45 ),
                          LocationMatcher( filepath,  5,  5 ) ),
            ChunkMatcher( '\n                ',
                          LocationMatcher( filepath,  5, 33 ),
                          LocationMatcher( filepath,  5, 34 ) ),
            ChunkMatcher( '',
                          LocationMatcher( filepath,  5, 36 ),
                          LocationMatcher( filepath,  5, 37 ) ),
            ChunkMatcher( '\n        ',
                          LocationMatcher( filepath,  5, 39 ),
                          LocationMatcher( filepath,  6,  5 ) ),
            ChunkMatcher( '\n                ',
                          LocationMatcher( filepath,  6, 33 ),
                          LocationMatcher( filepath,  6, 34 ) ),
            ChunkMatcher( '',
                          LocationMatcher( filepath,  6, 35 ),
                          LocationMatcher( filepath,  6, 36 ) ),
            ChunkMatcher( '\n        ',
                          LocationMatcher( filepath,  6, 38 ),
                          LocationMatcher( filepath,  7,  5 ) ),
            ChunkMatcher( '\n        ',
                          LocationMatcher( filepath,  7, 11 ),
                          LocationMatcher( filepath,  8,  5 ) ),
            ChunkMatcher( '\n    ',
                          LocationMatcher( filepath,  8, 11 ),
                          LocationMatcher( filepath,  9,  3 ) ),
          ),
          'location': LocationMatcher( filepath, 1, 1 )
        } ) )
      } )
    }
  } )


@WithRetry
@IsolatedYcmd()
def Subcommands_ExtraConf_SettingsValid_UnknownExtraConf_test( app ):
  filepath = PathToTestFile( 'extra_confs',
                             'simple_extra_conf_project',
                             'src',
                             'ExtraConf.java' )
  contents = ReadFile( filepath )

  response = app.post_json( '/event_notification',
                            BuildRequest( **{
                              'event_name': 'FileReadyToParse',
                              'contents': contents,
                              'filepath': filepath,
                              'line_num': 1,
                              'column_num': 7,
                              'filetype': 'java',
                            } ),
                            expect_errors = True )

  print( 'FileReadyToParse result: {}'.format( json.dumps( response.json,
                                                           indent = 2 ) ) )

  assert_that( response.status_code,
               equal_to( requests.codes.internal_server_error ) )
  assert_that( response.json, ErrorMatcher( UnknownExtraConf ) )

  app.post_json(
    '/ignore_extra_conf_file',
    { 'filepath': PathToTestFile( 'extra_confs', '.ycm_extra_conf.py' ) } )

  RunTest( app, {
    'description': 'RefactorRename is disabled in extra conf but ignored.',
    'request': {
      'command': 'RefactorRename',
      'arguments': [ 'renamed_l' ],
      'filepath': filepath,
      'contents': contents,
      'line_num': 1,
      'column_num': 7,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'fixits': contains_exactly( has_entries( {
          # Just prove that we actually got a reasonable result
          'chunks': is_not( empty() ),
        } ) )
      } )
    }
  } )


@SharedYcmd
def Subcommands_ExecuteCommand_NoArguments_test( app ):
  RunTest( app, {
    'description': 'Running a command without args fails',
    'request': {
      'command': 'ExecuteCommand',
      'line_num': 1,
      'column_num': 1,
      'filepath': TEST_JAVA,
    },
    'expect': {
      'response': requests.codes.internal_server_error,
      'data': ErrorMatcher( ValueError,
                            'Must specify a command to execute' ),
    }
  } )


@SharedYcmd
def Subcommands_ExecuteCommand_test( app ):
  RunTest( app, {
    'description': 'Running a command does what it says it does',
    'request': {
      'command': 'ExecuteCommand',
      'arguments': [ 'java.edit.organizeImports' ],
      'line_num': 1,
      'column_num': 1,
      'filepath': TEST_JAVA,
    },
    'expect': {
      # We dont specify the path for import organize, and jdt.ls returns shrug
      'response': requests.codes.ok,
      'data': ''
    }
  } )
