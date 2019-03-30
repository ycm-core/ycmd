# Copyright (C) 2017-2018 ycmd contributors
# encoding: utf-8
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

import time
from hamcrest import ( assert_that,
                       contains,
                       contains_inanyorder,
                       empty,
                       has_entries,
                       instance_of,
                       is_not,
                       matches_regexp )
from nose.tools import eq_
from pprint import pformat
import requests
import json

from ycmd.utils import ReadFile
from ycmd.completers.java.java_completer import NO_DOCUMENTATION_MESSAGE
from ycmd.tests.java import ( DEFAULT_PROJECT_DIR,
                              PathToTestFile,
                              SharedYcmd,
                              IsolatedYcmd )
from ycmd.tests.test_utils import ( BuildRequest,
                                    ChunkMatcher,
                                    CombineRequest,
                                    ErrorMatcher,
                                    ExpectedFailure,
                                    LocationMatcher,
                                    WithRetry )
from mock import patch
from ycmd.completers.language_server import language_server_protocol as lsp
from ycmd import handlers
from ycmd.completers.language_server.language_server_completer import (
  ResponseTimeoutException,
  ResponseFailedException
)
from ycmd.responses import UnknownExtraConf



@WithRetry
@SharedYcmd
def Subcommands_DefinedSubcommands_test( app ):
  subcommands_data = BuildRequest( completer_target = 'java' )

  eq_( sorted( [ 'FixIt',
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
                 'RestartServer' ] ),
       app.post_json( '/defined_subcommands', subcommands_data ).json )


def Subcommands_ServerNotReady_test():
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'test',
                             'AbstractTestWidget.java' )

  completer = handlers._server_state.GetFiletypeCompleter( [ 'java' ] )

  @WithRetry
  @SharedYcmd
  @patch.object( completer, 'ServerIsReady', return_value = False )
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

  yield Test, 'GoTo', []
  yield Test, 'GoToDeclaration', []
  yield Test, 'GoToDefinition', []
  yield Test, 'GoToReferences', []
  yield Test, 'GetType', []
  yield Test, 'GetDoc', []
  yield Test, 'FixIt', []
  yield Test, 'Format', []
  yield Test, 'OrganizeImports', []
  yield Test, 'RefactorRename', [ 'test' ]


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

      eq_( response.status_code, test[ 'expect' ][ 'response' ] )

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

  eq_( response.status_code, requests.codes.internal_server_error )

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

  eq_( response, {
    'detailed_info': 'Return runtime debugging info. Useful for finding the '
                     'actual code which is useful.'
  } )


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

  eq_( response, {
    'detailed_info': 'This is the actual code that matters. This concrete '
                     'implementation is the equivalent of the main function in '
                     'other languages'
  } )


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

  eq_( response.status_code, requests.codes.internal_server_error )

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

  eq_( response, {
    'message': 'com.test.TestWidgetImpl'
  } )


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

  eq_( response, {
    'message': 'com.test.TestWidgetImpl.TestWidgetImpl(String info)'
  } )


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

  eq_( response, {
      'message': 'String info'
  } )


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

  eq_( response, {
    'message': 'String info - '
                     'com.test.TestWidgetImpl.TestWidgetImpl(String)'
  } )


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

  eq_( response, {
    'message': 'int a - '
                    'com.test.TestWidgetImpl.TestWidgetImpl(String)'
  } )


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

  eq_( response, {
    'message': 'void com.test.TestWidgetImpl.doSomethingVaguelyUseful()'
  } )


@WithRetry
@SharedYcmd
def Subcommands_GetType_Unicode_test( app ):
  filepath = PathToTestFile( DEFAULT_PROJECT_DIR,
                             'src',
                             'com',
                             'youcompleteme',
                             'Test.java' )
  contents = ReadFile( filepath )

  app.post_json( '/event_notification',
                 BuildRequest( filepath = filepath,
                               filetype = 'java',
                               contents = contents,
                               event_name = 'FileReadyToParse' ) )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'java',
                             line_num = 7,
                             column_num = 17,
                             contents = contents,
                             command_arguments = [ 'GetType' ],
                             completer_target = 'filetype_default' )

  response = app.post_json( '/run_completer_command', event_data ).json

  eq_( response, {
    'message': 'String whåtawîdgé - com.youcompleteme.Test.doUnicødeTes()'
  } )


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

  eq_( response.status_code, requests.codes.internal_server_error )

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

  eq_( response.status_code, requests.codes.internal_server_error )

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

  eq_( response.status_code, requests.codes.internal_server_error )

  assert_that( response.json,
               ErrorMatcher( RuntimeError,
                             'Cannot jump to location' ) )


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

  eq_( response, [
         {
           'filepath': PathToTestFile( 'simple_eclipse_project',
                                       'src',
                                       'com',
                                       'test',
                                       'TestFactory.java' ),
           'column_num': 9,
           'description': "      w.doSomethingVaguelyUseful();",
           'line_num': 28
         },
         {
           'filepath': PathToTestFile( 'simple_eclipse_project',
                                       'src',
                                       'com',
                                       'test',
                                       'TestLauncher.java' ),
           'column_num': 11,
           'description': "        w.doSomethingVaguelyUseful();",
           'line_num': 32
         } ] )


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
        'fixits': contains( has_entries( {
          'chunks': contains(
              ChunkMatcher( 'renamed_l',
                            LocationMatcher( filepath, 27, 18 ),
                            LocationMatcher( filepath, 27, 19 ) ),
              ChunkMatcher( 'renamed_l',
                            LocationMatcher( filepath, 28, 5 ),
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
        'fixits': contains( has_entries( {
          'chunks': contains(
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
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'youcompleteme',
                             'Test.java' )
  RunTest( app, {
    'description': 'Rename works for unicode identifier',
    'request': {
      'command': 'RefactorRename',
      'arguments': [ 'shorter' ],
      'line_num': 7,
      'column_num': 21,
      'filepath': filepath,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'fixits': contains( has_entries( {
          'chunks': contains(
            ChunkMatcher(
              'shorter',
              LocationMatcher( filepath, 7, 12 ),
              LocationMatcher( filepath, 7, 25 )
            ),
            ChunkMatcher(
              'shorter',
              LocationMatcher( filepath, 8, 12 ),
              LocationMatcher( filepath, 8, 25 )
            ),
          ),
        } ) ),
      } ),
    },
  } )



@WithRetry
@SharedYcmd
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


def Subcommands_FixIt_SingleDiag_MultipleOption_Insertion_test():
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
        'chunks': contains(
          # When doing an import, eclipse likes to add two newlines
          # after the package. I suppose this is config in real eclipse,
          # but there's no mechanism to configure this in jdtl afaik.
          ChunkMatcher( '\n\n',
                        LocationMatcher( filepath, 1, 18 ),
                        LocationMatcher( filepath, 1, 18 ) ),
          # OK, so it inserts the import
          ChunkMatcher( 'import com.test.wobble.Wibble;',
                        LocationMatcher( filepath, 1, 18 ),
                        LocationMatcher( filepath, 1, 18 ) ),
          # More newlines. Who doesn't like newlines?!
          ChunkMatcher( '\n\n',
                        LocationMatcher( filepath, 1, 18 ),
                        LocationMatcher( filepath, 1, 18 ) ),
          # For reasons known only to the eclipse JDT developers, it
          # seems to want to delete the lines after the package first.
          ChunkMatcher( '',
                        LocationMatcher( filepath, 1, 18 ),
                        LocationMatcher( filepath, 3, 1 ) ),
        ),
      } ),
      has_entries( {
        'text': "Create field 'Wibble'",
        'chunks': contains(
          ChunkMatcher( '\n\n',
                        LocationMatcher( filepath, 16, 4 ),
                        LocationMatcher( filepath, 16, 4 ) ),
          ChunkMatcher( 'private Object Wibble;',
                        LocationMatcher( filepath, 16, 4 ),
                        LocationMatcher( filepath, 16, 4 ) ),
        ),
      } ),
      has_entries( {
        'text': "Create constant 'Wibble'",
        'chunks': contains(
          ChunkMatcher( '\n\n',
                        LocationMatcher( filepath, 16, 4 ),
                        LocationMatcher( filepath, 16, 4 ) ),
          ChunkMatcher( 'private static final String Wibble = null;',
                        LocationMatcher( filepath, 16, 4 ),
                        LocationMatcher( filepath, 16, 4 ) ),
        ),
      } ),
      has_entries( {
        'text': "Create parameter 'Wibble'",
        'chunks': contains(
          ChunkMatcher( ', ',
                        LocationMatcher( filepath, 18, 32 ),
                        LocationMatcher( filepath, 18, 32 ) ),
          ChunkMatcher( 'Object Wibble',
                        LocationMatcher( filepath, 18, 32 ),
                        LocationMatcher( filepath, 18, 32 ) ),
        ),
      } ),
      has_entries( {
        'text': "Create local variable 'Wibble'",
        'chunks': contains(
          ChunkMatcher( 'Object Wibble;',
                        LocationMatcher( filepath, 19, 5 ),
                        LocationMatcher( filepath, 19, 5 ) ),
          ChunkMatcher( '\n	',
                        LocationMatcher( filepath, 19, 5 ),
                        LocationMatcher( filepath, 19, 5 ) ),
        ),
      } ),
    )
  } )

  yield ( RunFixItTest, 'FixIt works at the first char of the line',
          filepath, 19, 1, fixits_for_line )

  yield ( RunFixItTest, 'FixIt works at the begin of the range of the diag.',
          filepath, 19, 15, fixits_for_line )

  yield ( RunFixItTest, 'FixIt works at the end of the range of the diag.',
          filepath, 19, 20, fixits_for_line )

  yield ( RunFixItTest, 'FixIt works at the end of line',
          filepath, 19, 34, fixits_for_line )


def Subcommands_FixIt_SingleDiag_SingleOption_Modify_test():
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
    'fixits': contains(
      has_entries( {
        'text': "Change type of 'test' to 'boolean'",
        'chunks': contains(
          # For some reason, eclipse returns modifies as deletes + adds,
          # although overlapping ranges aren't allowed.
          ChunkMatcher( 'boolean',
                        LocationMatcher( filepath, 14, 12 ),
                        LocationMatcher( filepath, 14, 12 ) ),
          ChunkMatcher( '',
                        LocationMatcher( filepath, 14, 12 ),
                        LocationMatcher( filepath, 14, 15 ) ),
        ),
      } ),
    )
  } )

  yield ( RunFixItTest, 'FixIts can change lines as well as add them',
          filepath, 27, 12, fixits )


def Subcommands_FixIt_SingleDiag_MultiOption_Delete_test():
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'test',
                             'TestFactory.java' )

  fixits = has_entries( {
    'fixits': contains_inanyorder(
      has_entries( {
        'text': "Remove 'testString', keep assignments with side effects",
        'chunks': contains(
          ChunkMatcher( '',
                        LocationMatcher( filepath, 14, 21 ),
                        LocationMatcher( filepath, 15, 5 ) ),
          ChunkMatcher( '',
                        LocationMatcher( filepath, 15, 5 ),
                        LocationMatcher( filepath, 15, 30 ) ),
        ),
      } ),
      has_entries( {
        'text': "Create getter and setter for 'testString'...",
        # The edit reported for this is juge and uninteresting really. Manual
        # testing can show that it works. This test is really about the previous
        # FixIt (and nonetheless, the previous tests ensure that we correctly
        # populate the chunks list; the contents all come from jdt.ls)
        'chunks': instance_of( list )
      } ),
    )
  } )

  yield ( RunFixItTest, 'FixIts can change lines as well as add them',
          filepath, 15, 29, fixits )


def Subcommands_FixIt_MultipleDiags_test():
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'test',
                             'TestFactory.java' )

  fixits = has_entries( {
    'fixits': contains_inanyorder(
      has_entries( {
        'text': "Change type of 'test' to 'boolean'",
        'chunks': contains(
          # For some reason, eclipse returns modifies as deletes + adds,
          # although overlapping ranges aren't allowed.
          ChunkMatcher( 'boolean',
                        LocationMatcher( filepath, 14, 12 ),
                        LocationMatcher( filepath, 14, 12 ) ),
          ChunkMatcher( '',
                        LocationMatcher( filepath, 14, 12 ),
                        LocationMatcher( filepath, 14, 15 ) ),
        ),
      } ),
      has_entries( {
        'text': "Remove argument to match 'doSomethingVaguelyUseful()'",
        'chunks': contains(
          ChunkMatcher( '',
                        LocationMatcher( filepath, 30, 48 ),
                        LocationMatcher( filepath, 30, 50 ) ),
        ),
      } ),
      has_entries( {
        'text': "Change method 'doSomethingVaguelyUseful()': Add parameter "
                "'Bar'",
        # Again, this produces quite a lot of fussy little changes (that
        # actually lead to broken code, but we can't really help that), and
        # having them in this test would just be brittle without proving
        # anything about our code
        'chunks': instance_of( list ),
      } ),
      has_entries( {
        'text': "Create method 'doSomethingVaguelyUseful(Bar)' in type "
                "'AbstractTestWidget'",
        # Again, this produces quite a lot of fussy little changes (that
        # actually lead to broken code, but we can't really help that), and
        # having them in this test would just be brittle without proving
        # anything about our code
        'chunks': instance_of( list ),
      } ),
    )
  } )

  yield ( RunFixItTest, 'diags are merged in FixIt options - start of line',
          filepath, 30, 1, fixits )
  yield ( RunFixItTest, 'diags are merged in FixIt options - start of diag 1',
          filepath, 30, 10, fixits )
  yield ( RunFixItTest, 'diags are merged in FixIt options - end of diag 1',
          filepath, 30, 15, fixits )
  yield ( RunFixItTest, 'diags are merged in FixIt options - start of diag 2',
          filepath, 30, 23, fixits )
  yield ( RunFixItTest, 'diags are merged in FixIt options - end of diag 2',
          filepath, 30, 46, fixits )
  yield ( RunFixItTest, 'diags are merged in FixIt options - end of line',
          filepath, 30, 55, fixits )


def Subcommands_FixIt_NoDiagnostics_test():
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'test',
                             'TestFactory.java' )

  yield ( RunFixItTest, "no FixIts means you gotta code it yo' self",
          filepath, 1, 1, has_entries( { 'fixits': empty() } ) )


def Subcommands_FixIt_Unicode_test():
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'youcompleteme',
                             'Test.java' )

  fixits = has_entries( {
    'fixits': contains_inanyorder(
      has_entries( {
        'text': "Remove argument to match 'doUnicødeTes()'",
        'chunks': contains(
          ChunkMatcher( '',
                        LocationMatcher( filepath, 13, 24 ),
                        LocationMatcher( filepath, 13, 29 ) ),
        ),
      } ),
      has_entries( {
        'text': "Change method 'doUnicødeTes()': Add parameter 'String'",
        'chunks': contains(
          ChunkMatcher( 'String test2',
                        LocationMatcher( filepath, 6, 31 ),
                        LocationMatcher( filepath, 6, 31 ) ),
        ),
      } ),
      has_entries( {
        'text': "Create method 'doUnicødeTes(String)'",
        'chunks': contains(
          ChunkMatcher( 'private void doUnicødeTes(String test2) {\n}',
                        LocationMatcher( filepath, 20, 3 ),
                        LocationMatcher( filepath, 20, 3 ) ),
          ChunkMatcher( '\n\n\n',
                        LocationMatcher( filepath, 20, 3 ),
                        LocationMatcher( filepath, 20, 3 ) ),
        ),
      } ),
    )
  } )

  yield ( RunFixItTest, 'FixIts and diagnostics work with unicode strings',
          filepath, 13, 1, fixits )


@WithRetry
@SharedYcmd
def Subcommands_FixIt_InvalidURI_test( app ):
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'test',
                             'TestFactory.java' )

  fixits = has_entries( {
    'fixits': contains(
      has_entries( {
        'text': "Change type of 'test' to 'boolean'",
        'chunks': contains(
          # For some reason, eclipse returns modifies as deletes + adds,
          # although overlapping ranges aren't allowed.
          ChunkMatcher( 'boolean',
                        LocationMatcher( '', 14, 12 ),
                        LocationMatcher( '', 14, 12 ) ),
          ChunkMatcher( '',
                        LocationMatcher( '', 14, 12 ),
                        LocationMatcher( '', 14, 15 ) ),
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
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'youcompleteme',
                             'Test.java' )
  RunTest( app, {
    'description': 'Formatting is applied on the whole file '
                   'with tabs composed of 4 spaces',
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
        'fixits': contains( has_entries( {
          'chunks': contains(
            ChunkMatcher( '\n    ',
                          LocationMatcher( filepath,  3, 20 ),
                          LocationMatcher( filepath,  4,  3 ) ),
            ChunkMatcher( '\n\n    ',
                          LocationMatcher( filepath,  4, 22 ),
                          LocationMatcher( filepath,  6,  3 ) ),
            ChunkMatcher( '\n        ',
                          LocationMatcher( filepath,  6, 34 ),
                          LocationMatcher( filepath,  7,  5 ) ),
            ChunkMatcher( '\n        ',
                          LocationMatcher( filepath,  7, 35 ),
                          LocationMatcher( filepath,  8,  5 ) ),
            ChunkMatcher( '',
                          LocationMatcher( filepath,  8, 25 ),
                          LocationMatcher( filepath,  8, 26 ) ),
            ChunkMatcher( '\n    ',
                          LocationMatcher( filepath,  8, 27 ),
                          LocationMatcher( filepath,  9,  3 ) ),
            ChunkMatcher( '\n\n    ',
                          LocationMatcher( filepath,  9,  4 ),
                          LocationMatcher( filepath, 11,  3 ) ),
            ChunkMatcher( '\n        ',
                          LocationMatcher( filepath, 11, 29 ),
                          LocationMatcher( filepath, 12,  5 ) ),
            ChunkMatcher( '\n        ',
                          LocationMatcher( filepath, 12, 26 ),
                          LocationMatcher( filepath, 13,  5 ) ),
            ChunkMatcher( '',
                          LocationMatcher( filepath, 13, 24 ),
                          LocationMatcher( filepath, 13, 25 ) ),
            ChunkMatcher( '',
                          LocationMatcher( filepath, 13, 29 ),
                          LocationMatcher( filepath, 13, 30 ) ),
            ChunkMatcher( '\n\n        ',
                          LocationMatcher( filepath, 13, 32 ),
                          LocationMatcher( filepath, 15,  5 ) ),
            ChunkMatcher( '\n        ',
                          LocationMatcher( filepath, 15, 58 ),
                          LocationMatcher( filepath, 16,  5 ) ),
            ChunkMatcher( '\n    ',
                          LocationMatcher( filepath, 16, 42 ),
                          LocationMatcher( filepath, 17,  3 ) ),
            ChunkMatcher( '\n\n    ',
                          LocationMatcher( filepath, 17,  4 ),
                          LocationMatcher( filepath, 20,  3 ) ),
            ChunkMatcher( '\n        ',
                          LocationMatcher( filepath, 20, 28 ),
                          LocationMatcher( filepath, 21,  5 ) ),
            ChunkMatcher( '\n        ',
                          LocationMatcher( filepath, 21, 28 ),
                          LocationMatcher( filepath, 22,  5 ) ),
            ChunkMatcher( '\n        ',
                          LocationMatcher( filepath, 22, 30 ),
                          LocationMatcher( filepath, 23,  5 ) ),
            ChunkMatcher( '\n        ',
                          LocationMatcher( filepath, 23, 23 ),
                          LocationMatcher( filepath, 24,  5 ) ),
            ChunkMatcher( '\n    ',
                          LocationMatcher( filepath, 24, 27 ),
                          LocationMatcher( filepath, 25,  3 ) ),
          )
        } ) )
      } )
    }
  } )


@WithRetry
@SharedYcmd
def Subcommands_Format_WholeFile_Tabs_test( app ):
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'youcompleteme',
                             'Test.java' )
  RunTest( app, {
    'description': 'Formatting is applied on the whole file '
                   'with tabs composed of 2 spaces',
    'request': {
      'command': 'Format',
      'filepath': filepath,
      'options': {
        'tab_size': 4,
        'insert_spaces': False
      }
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'fixits': contains( has_entries( {
          'chunks': contains(
            ChunkMatcher( '\n\t',
                          LocationMatcher( filepath,  3, 20 ),
                          LocationMatcher( filepath,  4,  3 ) ),
            ChunkMatcher( '\n\n\t',
                          LocationMatcher( filepath,  4, 22 ),
                          LocationMatcher( filepath,  6,  3 ) ),
            ChunkMatcher( '\n\t\t',
                          LocationMatcher( filepath,  6, 34 ),
                          LocationMatcher( filepath,  7,  5 ) ),
            ChunkMatcher( '\n\t\t',
                          LocationMatcher( filepath,  7, 35 ),
                          LocationMatcher( filepath,  8,  5 ) ),
            ChunkMatcher( '',
                          LocationMatcher( filepath,  8, 25 ),
                          LocationMatcher( filepath,  8, 26 ) ),
            ChunkMatcher( '\n\t',
                          LocationMatcher( filepath,  8, 27 ),
                          LocationMatcher( filepath,  9,  3 ) ),
            ChunkMatcher( '\n\n\t',
                          LocationMatcher( filepath,  9,  4 ),
                          LocationMatcher( filepath, 11,  3 ) ),
            ChunkMatcher( '\n\t\t',
                          LocationMatcher( filepath, 11, 29 ),
                          LocationMatcher( filepath, 12,  5 ) ),
            ChunkMatcher( '\n\t\t',
                          LocationMatcher( filepath, 12, 26 ),
                          LocationMatcher( filepath, 13,  5 ) ),
            ChunkMatcher( '',
                          LocationMatcher( filepath, 13, 24 ),
                          LocationMatcher( filepath, 13, 25 ) ),
            ChunkMatcher( '',
                          LocationMatcher( filepath, 13, 29 ),
                          LocationMatcher( filepath, 13, 30 ) ),
            ChunkMatcher( '\n\n\t\t',
                          LocationMatcher( filepath, 13, 32 ),
                          LocationMatcher( filepath, 15,  5 ) ),
            ChunkMatcher( '\n\t\t',
                          LocationMatcher( filepath, 15, 58 ),
                          LocationMatcher( filepath, 16,  5 ) ),
            ChunkMatcher( '\n\t',
                          LocationMatcher( filepath, 16, 42 ),
                          LocationMatcher( filepath, 17,  3 ) ),
            ChunkMatcher( '\n\n\t',
                          LocationMatcher( filepath, 17,  4 ),
                          LocationMatcher( filepath, 20,  3 ) ),
            ChunkMatcher( '\n\t\t',
                          LocationMatcher( filepath, 20, 28 ),
                          LocationMatcher( filepath, 21,  5 ) ),
            ChunkMatcher( '\n\t\t',
                          LocationMatcher( filepath, 21, 28 ),
                          LocationMatcher( filepath, 22,  5 ) ),
            ChunkMatcher( '\n\t\t',
                          LocationMatcher( filepath, 22, 30 ),
                          LocationMatcher( filepath, 23,  5 ) ),
            ChunkMatcher( '\n\t\t',
                          LocationMatcher( filepath, 23, 23 ),
                          LocationMatcher( filepath, 24,  5 ) ),
            ChunkMatcher( '\n\t',
                          LocationMatcher( filepath, 24, 27 ),
                          LocationMatcher( filepath, 25,  3 ) ),
          )
        } ) )
      } )
    }
  } )


@WithRetry
@SharedYcmd
def Subcommands_Format_Range_Spaces_test( app ):
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'youcompleteme',
                             'Test.java' )
  RunTest( app, {
    'description': 'Formatting is applied on some part of the file '
                   'with tabs composed of 4 spaces',
    'request': {
      'command': 'Format',
      'filepath': filepath,
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
        'fixits': contains( has_entries( {
          'chunks': contains(
            ChunkMatcher( '    ',
                          LocationMatcher( filepath, 20,  1 ),
                          LocationMatcher( filepath, 20,  3 ) ),
            ChunkMatcher( '\n        ',
                          LocationMatcher( filepath, 20, 28 ),
                          LocationMatcher( filepath, 21,  5 ) ),
            ChunkMatcher( '\n        ',
                          LocationMatcher( filepath, 21, 28 ),
                          LocationMatcher( filepath, 22,  5 ) ),
            ChunkMatcher( '\n        ',
                          LocationMatcher( filepath, 22, 30 ),
                          LocationMatcher( filepath, 23,  5 ) ),
            ChunkMatcher( '\n        ',
                          LocationMatcher( filepath, 23, 23 ),
                          LocationMatcher( filepath, 24,  5 ) ),
            ChunkMatcher( '\n    ',
                          LocationMatcher( filepath, 24, 27 ),
                          LocationMatcher( filepath, 25,  3 ) ),
          )
        } ) )
      } )
    }
  } )


@WithRetry
@SharedYcmd
def Subcommands_Format_Range_Tabs_test( app ):
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'youcompleteme',
                             'Test.java' )
  RunTest( app, {
    'description': 'Formatting is applied on some part of the file '
                   'with tabs instead of spaces',
    'request': {
      'command': 'Format',
      'filepath': filepath,
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
        'fixits': contains( has_entries( {
          'chunks': contains(
            ChunkMatcher( '\t',
                          LocationMatcher( filepath, 20,  1 ),
                          LocationMatcher( filepath, 20,  3 ) ),
            ChunkMatcher( '\n\t\t',
                          LocationMatcher( filepath, 20, 28 ),
                          LocationMatcher( filepath, 21,  5 ) ),
            ChunkMatcher( '\n\t\t',
                          LocationMatcher( filepath, 21, 28 ),
                          LocationMatcher( filepath, 22,  5 ) ),
            ChunkMatcher( '\n\t\t',
                          LocationMatcher( filepath, 22, 30 ),
                          LocationMatcher( filepath, 23,  5 ) ),
            ChunkMatcher( '\n\t\t',
                          LocationMatcher( filepath, 23, 23 ),
                          LocationMatcher( filepath, 24,  5 ) ),
            ChunkMatcher( '\n\t',
                          LocationMatcher( filepath, 24, 27 ),
                          LocationMatcher( filepath, 25,  3 ) ),
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


def Subcommands_GoTo_test():
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'test',
                             'TestLauncher.java' )

  unicode_filepath = PathToTestFile( 'simple_eclipse_project',
                                     'src',
                                     'com',
                                     'youcompleteme',
                                     'Test.java' )

  tests = [
    # Member function local variable
    { 'request': { 'line': 28, 'col': 5, 'filepath': filepath },
      'response': { 'line_num': 27, 'column_num': 18, 'filepath': filepath },
      'description': 'GoTo works for member local variable' },
    # Member variable
    { 'request': { 'line': 22, 'col': 7, 'filepath': filepath },
      'response': { 'line_num': 8, 'column_num': 16, 'filepath': filepath },
      'description': 'GoTo works for member variable' },
    # Method
    { 'request': { 'line': 28, 'col': 7, 'filepath': filepath },
      'response': { 'line_num': 21, 'column_num': 16, 'filepath': filepath },
      'description': 'GoTo works for method' },
    # Constructor
    { 'request': { 'line': 38, 'col': 26, 'filepath': filepath },
      'response': { 'line_num': 10, 'column_num': 10, 'filepath': filepath },
      'description': 'GoTo works for jumping to constructor' },
    # Jump to self - main()
    { 'request': { 'line': 26, 'col': 22, 'filepath': filepath },
      'response': { 'line_num': 26, 'column_num': 22, 'filepath': filepath },
      'description': 'GoTo works for jumping to the same position' },
    # Static method
    { 'request': { 'line': 37, 'col': 11, 'filepath': filepath },
      'response': { 'line_num': 13, 'column_num': 21, 'filepath': filepath },
      'description': 'GoTo works for static method' },
    # Static variable
    { 'request': { 'line': 14, 'col': 11, 'filepath': filepath },
      'response': { 'line_num': 12, 'column_num': 21, 'filepath': filepath },
      'description': 'GoTo works for static variable' },
    # Argument variable
    { 'request': { 'line': 23, 'col': 5, 'filepath': filepath },
      'response': { 'line_num': 21, 'column_num': 32, 'filepath': filepath },
      'description': 'GoTo works for argument variable' },
    # Class
    { 'request': { 'line': 27, 'col': 10, 'filepath': filepath },
      'response': { 'line_num': 6, 'column_num': 7, 'filepath': filepath },
      'description': 'GoTo works for jumping to class declaration' },
    # Unicode
    { 'request': { 'line': 8, 'col': 12, 'filepath': unicode_filepath },
      'response': { 'line_num': 7, 'column_num': 12, 'filepath':
                    unicode_filepath },
      'description': 'GoTo works for unicode identifiers' }
  ]

  for command in [ 'GoTo', 'GoToDefinition', 'GoToDeclaration' ]:
    for test in tests:
      yield ( RunGoToTest,
              test[ 'description' ],
              test[ 'request' ][ 'filepath' ],
              test[ 'request' ][ 'line' ],
              test[ 'request' ][ 'col' ],
              command,
              has_entries( test[ 'response' ] ) )


def Subcommands_GoToType_test():
  launcher_file = PathToTestFile( 'simple_eclipse_project',
                                  'src',
                                  'com',
                                  'test',
                                  'TestLauncher.java' )
  tset_file = PathToTestFile( 'simple_eclipse_project',
                              'src',
                              'com',
                              'youcompleteme',
                              'testing',
                              'Tset.java' )

  tests = [
    # Member function local variable
    { 'request': { 'line': 28, 'col': 5, 'filepath': launcher_file },
      'response': { 'line_num': 6, 'column_num': 7, 'filepath': launcher_file },
      'description': 'GoToType works for member local variable' },
    # Member variable
    { 'request': { 'line': 22, 'col': 7, 'filepath': launcher_file },
      'response': { 'line_num': 6, 'column_num': 14, 'filepath': tset_file },
      'description': 'GoToType works for member variable' },
  ]

  for test in tests:
    yield ( RunGoToTest,
            test[ 'description' ],
            test[ 'request' ][ 'filepath' ],
            test[ 'request' ][ 'line' ],
            test[ 'request' ][ 'col' ],
            'GoToType',
            has_entries( test[ 'response' ] ) )


def Subcommands_GoToImplementation_test():
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'test',
                             'TestLauncher.java' )

  tests = [
    # Interface
    { 'request': { 'line': 17, 'col': 25, 'filepath': filepath },
      'response': { 'line_num': 28, 'column_num': 16, 'filepath': filepath },
      'description': 'GoToImplementation on interface '
                     'jumps to its implementation' },
    # Interface reference
    { 'request': { 'line': 21, 'col': 30, 'filepath': filepath },
      'response': { 'line_num': 28, 'column_num': 16, 'filepath': filepath },
      'description': 'GoToImplementation on interface reference '
                     'jumpts to its implementation' },
  ]

  for test in tests:
    yield ( RunGoToTest,
            test[ 'description' ],
            test[ 'request' ][ 'filepath' ],
            test[ 'request' ][ 'line' ],
            test[ 'request' ][ 'col' ],
            'GoToImplementation',
            has_entries( test[ 'response' ] ) )


@WithRetry
@SharedYcmd
def Subcommands_OrganizeImports_test( app ):
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'test',
                             'TestLauncher.java' )
  RunTest( app, {
    'description': 'Imports are resolved and sorted, '
                   'and unused ones are removed',
    'request': {
      'command': 'OrganizeImports',
      'filepath': filepath
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'fixits': contains( has_entries( {
          'chunks': contains(
            ChunkMatcher( 'import com.youcompleteme.Test;',
                          LocationMatcher( filepath, 3,  1 ),
                          LocationMatcher( filepath, 3,  1 ) ),
            ChunkMatcher( '\n',
                          LocationMatcher( filepath, 3,  1 ),
                          LocationMatcher( filepath, 3,  1 ) ),
            ChunkMatcher( '',
                          LocationMatcher( filepath, 3, 39 ),
                          LocationMatcher( filepath, 4, 54 ) ),
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
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'youcompleteme',
                             'Test.java' )

  with patch.object(
    handlers._server_state.GetFiletypeCompleter( [ 'java' ] ).GetConnection(),
    'WriteData' ):
    RunTest( app, {
      'description': 'Request timeout throws an error',
      'request': {
        'command': 'FixIt',
        'line_num': 1,
        'column_num': 1,
        'filepath': filepath,
      },
      'expect': {
        'response': requests.codes.internal_server_error,
        'data': ErrorMatcher( ResponseTimeoutException, 'Response Timeout' )
      }
    } )


@WithRetry
@SharedYcmd
def Subcommands_RequestFailed_test( app ):
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'youcompleteme',
                             'Test.java' )

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
        'filepath': filepath,
      },
      'expect': {
        'response': requests.codes.internal_server_error,
        'data': ErrorMatcher( ResponseFailedException )
      }
    } )


@WithRetry
@SharedYcmd
def Subcommands_IndexOutOfRange_test( app ):
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'youcompleteme',
                             'Test.java' )

  RunTest( app, {
    'description': 'Request error handles the error',
    'request': {
      'command': 'FixIt',
      'line_num': 99,
      'column_num': 99,
      'filepath': filepath,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( { 'fixits': empty() } ),
    }
  } )


@WithRetry
@SharedYcmd
def Subcommands_DifferentFileTypesUpdate_test( app ):
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'youcompleteme',
                             'Test.java' )

  RunTest( app, {
    'description': 'Request error handles the error',
    'request': {
      'command': 'FixIt',
      'line_num': 99,
      'column_num': 99,
      'filepath': filepath,
      'file_data': {
        '!/bin/sh': {
          'filetypes': [],
          'contents': 'this should be ignored by the completer',
        },
        '/path/to/non/project/file': {
          'filetypes': [ 'c' ],
          'contents': 'this should be ignored by the completer',
        },
        PathToTestFile( 'simple_eclipse_project',
                        'src',
                        'com',
                        'test',
                        'TestLauncher.java' ): {
          'filetypes': [ 'some', 'java', 'junk', 'also' ],
          'contents': ReadFile( PathToTestFile( 'simple_eclipse_project',
                                                'src',
                                                'com',
                                                'test',
                                                'TestLauncher.java' ) ),
        },
        '!/usr/bin/sh': {
          'filetypes': [ 'java' ],
          'contents': '\n',
        },
      }
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( { 'fixits': empty() } ),
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
        'fixits': contains( has_entries( {
          'chunks': empty(),
          'location': LocationMatcher( filepath, 1, 7 )
        } ) )
      } )
    }
  } )


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

  eq_( response.status_code, requests.codes.internal_server_error )
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
        'fixits': contains( has_entries( {
          # Just prove that we actually got a reasonable result
          'chunks': is_not( empty() ),
        } ) )
      } )
    }
  } )
