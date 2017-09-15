# Copyright (C) 2015 ycmd contributors
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

from hamcrest import (
  assert_that,
  contains,
  contains_inanyorder,
  empty,
  has_entries,
  instance_of,
)
from nose.tools import eq_
from pprint import pformat
import requests
import logging

from ycmd.utils import ReadFile
from ycmd.completers.java.java_completer import NO_DOCUMENTATION_MESSAGE
from ycmd.tests.java import ( PathToTestFile,
                              SharedYcmd,
                              IsolatedYcmdInDirectory,
                              WaitUntilCompleterServerReady,
                              DEFAULT_PROJECT_DIR )
from ycmd.tests.test_utils import ( BuildRequest,
                                    ChunkMatcher,
                                    ErrorMatcher,
                                    LocationMatcher )

_logger = logging.getLogger( __name__ )


@SharedYcmd
def Subcommands_DefinedSubcommands_test( app ):
  subcommands_data = BuildRequest( completer_target = 'java' )

  eq_( sorted( [ 'FixIt',
                 'GoToDeclaration',
                 'GoToDefinition',
                 'GoTo',
                 'GetDoc',
                 'GetType',
                 'GoToReferences',
                 'RefactorRename',
                 'RestartServer' ] ),
       app.post_json( '/defined_subcommands',
                      subcommands_data ).json )


def RunTest( app, test, contents = None ):
  if not contents:
    contents = ReadFile( test[ 'request' ][ 'filepath' ] )

  def CombineRequest( request, data ):
    kw = request
    request.update( data )
    return BuildRequest( **kw )

  # Because we aren't testing this command, we *always* ignore errors. This
  # is mainly because we (may) want to test scenarios where the completer
  # throws an exception and the easiest way to do that is to throw from
  # within the FlagsForFile function.
  app.post_json( '/event_notification',
                 CombineRequest( test[ 'request' ], {
                                 'event_name': 'FileReadyToParse',
                                 'contents': contents,
                                 'filetype': 'java',
                                 } ),
                 expect_errors = True )

  # We also ignore errors here, but then we check the response code
  # ourself. This is to allow testing of requests returning errors.
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


@IsolatedYcmdInDirectory( PathToTestFile( DEFAULT_PROJECT_DIR  ) )
def Subcommands_GetDoc_NoDoc_test( app ):
  WaitUntilCompleterServerReady( app )
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
               ErrorMatcher( ValueError, NO_DOCUMENTATION_MESSAGE ) )


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
         'message': 'Return runtime debugging info. '
                    'Useful for finding the actual code which is useful.'
  } )


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
         'message': 'This is the actual code that matters.'
                    ' This concrete implementation is the equivalent'
                    ' of the main function in other languages'
  } )


@IsolatedYcmdInDirectory( PathToTestFile( DEFAULT_PROJECT_DIR  ) )
def Subcommands_GetType_NoKnownType_test( app ):
  WaitUntilCompleterServerReady( app )
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
               ErrorMatcher( RuntimeError,
                             'No information' ) )


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
               ErrorMatcher( RuntimeError,
                             'No information' ) )


@IsolatedYcmdInDirectory( PathToTestFile( DEFAULT_PROJECT_DIR  ) )
def Subcommands_GoToReferences_NoReferences_test( app ):
  WaitUntilCompleterServerReady( app )
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
           # 'description': '',
           'line_num': 28
         },
         {
           'filepath': PathToTestFile( 'simple_eclipse_project',
                                       'src',
                                       'com',
                                       'test',
                                       'TestLauncher.java' ),
           'column_num': 11,
           # 'description': '',
           'line_num': 25
         } ] )


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
      'line_num': 21,
      'column_num': 5,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries ( {
        'fixits': contains( has_entries( {
          'chunks': contains(
              ChunkMatcher( 'renamed_l',
                            LocationMatcher( filepath, 20, 18 ),
                            LocationMatcher( filepath, 20, 19 ) ),
              ChunkMatcher( 'renamed_l',
                            LocationMatcher( filepath, 21, 5 ),
                            LocationMatcher( filepath, 21, 6 ) ),
          ),
          'location': LocationMatcher( filepath, 21, 5 )
        } ) )
      } )
    }
  } )


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
      'arguments': [ 'a-quite-long-string' ],
      'filepath': TestLauncher,
      'line_num': 25,
      'column_num': 13,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries ( {
        'fixits': contains( has_entries( {
          'chunks': contains(
            ChunkMatcher(
              'a-quite-long-string',
              LocationMatcher( AbstractTestWidget, 10, 15 ),
              LocationMatcher( AbstractTestWidget, 10, 39 ) ),
            ChunkMatcher(
              'a-quite-long-string',
              LocationMatcher( TestFactory, 28, 9 ),
              LocationMatcher( TestFactory, 28, 33 ) ),
            ChunkMatcher(
              'a-quite-long-string',
              LocationMatcher( TestLauncher, 25, 11 ),
              LocationMatcher( TestLauncher, 25, 35 ) ),
            ChunkMatcher(
              'a-quite-long-string',
              LocationMatcher( TestWidgetImpl, 20, 15 ),
              LocationMatcher( TestWidgetImpl, 20, 39 ) ),
          ),
          'location': LocationMatcher( TestLauncher, 25, 13 )
        } ) )
      } )
    }
  } )


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
  fixits_for_line = has_entries ( {
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
        'chunks': contains (
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
        'chunks': contains (
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
        'chunks': contains (
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
        'chunks': contains (
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
  fixits = has_entries ( {
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

  fixits = has_entries ( {
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

  fixits = has_entries ( {
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
