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
                       empty,
                       has_entries,
                       has_entry,
                       contains_exactly )
from unittest.mock import patch
import os.path

from ycmd import user_options_store
from ycmd.tests.cs import ( IsolatedYcmd, PathToTestFile, SharedYcmd,
                            WrapOmniSharpServer )
from ycmd.tests.test_utils import ( BuildRequest,
                                    ChunkMatcher,
                                    ErrorMatcher,
                                    LocationMatcher,
                                    MockProcessTerminationTimingOut,
                                    RangeMatcher,
                                    WaitUntilCompleterServerReady,
                                    WithRetry )
from ycmd.utils import ReadFile, LOGGER


@SharedYcmd
def Subcommands_FixIt_NoFixitsFound_test( app ):
  fixit_test = PathToTestFile( 'testy', 'FixItTestCase.cs' )
  with WrapOmniSharpServer( app, fixit_test ):
    contents = ReadFile( fixit_test )

    request = BuildRequest( completer_target = 'filetype_default',
                            command_arguments = [ 'FixIt' ],
                            line_num = 1,
                            column_num = 1,
                            contents = contents,
                            filetype = 'cs',
                            filepath = fixit_test )
    response = app.post_json( '/run_completer_command', request ).json
    assert_that( response, has_entries( { 'fixits': empty() } ) )


@SharedYcmd
def Subcommands_FixIt_Multi_test( app ):
  fixit_test = PathToTestFile( 'testy', 'FixItTestCase.cs' )
  with WrapOmniSharpServer( app, fixit_test ):
    contents = ReadFile( fixit_test )

    request = BuildRequest( completer_target = 'filetype_default',
                            command_arguments = [ 'FixIt' ],
                            line_num = 4,
                            column_num = 27,
                            contents = contents,
                            filetype = 'cs',
                            filepath = fixit_test )
    response = app.post_json( '/run_completer_command', request ).json
    assert_that( response, has_entries( {
      'fixits': contains_exactly(
        has_entries( {
          'text': 'Introduce constant',
          'command': has_entries( { 'index': 0 } ),
          'resolve': True } ),
        has_entries( {
          'text': 'Convert to binary',
          'command': has_entries( { 'index': 1 } ),
          'resolve': True } ),
        has_entries( {
          'text': 'Convert to hex',
          'command': has_entries( { 'index': 2 } ),
          'resolve': True } ),
      ) } ) )
    request.pop( 'command_arguments' )
    request.update( { 'fixit': response[ 'fixits' ][ 1 ] } )
    response = app.post_json( '/resolve_fixit', request ).json
    LOGGER.debug( 'r = %s', response )
    assert_that( response, has_entries( {
      'fixits': contains_exactly( has_entries( {
        'location': LocationMatcher( fixit_test, 4, 27 ),
        'chunks': contains_exactly(
          has_entries( { 'replacement_text': '0b101', } ) )
      } ) ) } ) )


@SharedYcmd
def Subcommands_FixIt_Range_test( app ):
  fixit_test = PathToTestFile( 'testy', 'FixItTestCase.cs' )
  with WrapOmniSharpServer( app, fixit_test ):
    contents = ReadFile( fixit_test )

    request = BuildRequest( completer_target = 'filetype_default',
                            command_arguments = [ 'FixIt' ],
                            line_num = 4,
                            column_num = 23,
                            contents = contents,
                            filetype = 'cs',
                            filepath = fixit_test )
    request.update( { 'range': {
      'start': { 'line_num': 4, 'column_num': 23 },
      'end': { 'line_num': 4, 'column_num': 27 }
    } } )
    response = app.post_json( '/run_completer_command', request ).json
    assert_that( response, has_entries( {
      'fixits': contains_exactly( has_entries( {
        'location': LocationMatcher( fixit_test, 4, 23 ),
        'chunks': contains_exactly(
          has_entries( {
            'replacement_text':
              '\n        {\n            NewMethod();\n        }\n\n'
              '        private static void NewMethod()\n        {\r\n',
            'range': RangeMatcher( fixit_test, ( 3, 31 ), ( 4, 1 ) ) } )
        ) } ) ) } ) )


@SharedYcmd
def Subcommands_FixIt_Single_test( app ):
  fixit_test = PathToTestFile( 'testy', 'FixItTestCase.cs' )
  with WrapOmniSharpServer( app, fixit_test ):
    contents = ReadFile( fixit_test )

    request = BuildRequest( completer_target = 'filetype_default',
                            command_arguments = [ 'FixIt' ],
                            line_num = 4,
                            column_num = 23,
                            contents = contents,
                            filetype = 'cs',
                            filepath = fixit_test )
    response = app.post_json( '/run_completer_command', request ).json
    LOGGER.debug( 'r = %s', response )
    assert_that( response, has_entries( {
      'fixits': contains_exactly( has_entries( {
        'location': LocationMatcher( fixit_test, 4, 23 ),
        'chunks': contains_exactly(
          has_entries( {
            'replacement_text':
              '\n        {\n            NewMethod();\n        }\n\n'
              '        private static void NewMethod()\n        {\r\n',
            'range': RangeMatcher( fixit_test, ( 3, 31 ), ( 4, 1 ) ) } )
        ) } ) ) } ) )


@SharedYcmd
def Subcommands_RefactorRename_MissingNewName_test( app ):
  continuous_test = PathToTestFile( 'testy', 'ContinuousTest.cs' )
  with WrapOmniSharpServer( app, continuous_test ):
    contents = ReadFile( continuous_test )

    request = BuildRequest( completer_target = 'filetype_default',
                            command_arguments = [ 'RefactorRename' ],
                            line_num = 5,
                            column_num = 15,
                            contents = contents,
                            filetype = 'cs',
                            filepath = continuous_test )
    response = app.post_json( '/run_completer_command',
                              request,
                              expect_errors = True ).json
    assert_that( response, ErrorMatcher( ValueError,
                            'Please specify a new name to rename it to.\n'
                            'Usage: RefactorRename <new name>' ) )


@SharedYcmd
def Subcommands_RefactorRename_Unicode_test( app ):
  unicode_test = PathToTestFile( 'testy', 'Unicode.cs' )
  with WrapOmniSharpServer( app, unicode_test ):
    contents = ReadFile( unicode_test )

    request = BuildRequest( completer_target = 'filetype_default',
                            command_arguments = [ 'RefactorRename', 'x' ],
                            line_num = 30,
                            column_num = 31,
                            contents = contents,
                            filetype = 'cs',
                            filepath = unicode_test )
    response = app.post_json( '/run_completer_command', request ).json
    assert_that( response, has_entries( {
      'fixits': contains_exactly( has_entries( {
        'location': LocationMatcher( unicode_test, 30, 31 ),
        'chunks': contains_exactly(
          has_entries( {
            'replacement_text': 'x',
            'range': RangeMatcher( unicode_test, ( 30, 29 ), ( 30, 35 ) ) } )
        ) } ) ) } ) )


@SharedYcmd
def Subcommands_RefactorRename_Basic_test( app ):
  continuous_test = PathToTestFile( 'testy', 'ContinuousTest.cs' )
  with WrapOmniSharpServer( app, continuous_test ):
    contents = ReadFile( continuous_test )

    request = BuildRequest( completer_target = 'filetype_default',
                            command_arguments = [ 'RefactorRename', 'x' ],
                            line_num = 5,
                            column_num = 15,
                            contents = contents,
                            filetype = 'cs',
                            filepath = continuous_test )
    response = app.post_json( '/run_completer_command', request ).json
    assert_that( response, has_entries( {
      'fixits': contains_exactly( has_entries( {
        'location': LocationMatcher( continuous_test, 5, 15 ),
        'chunks': contains_exactly(
          has_entries( {
            'replacement_text': 'x',
            'range': RangeMatcher( continuous_test, ( 5, 15 ), ( 5, 29 ) ) } )
        ) } ) ) } ) )


@WithRetry
@IsolatedYcmd()
def Subcommands_GoTo_Basic_test( app ):
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  contents = ReadFile( filepath )
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilCompleterServerReady( app, 'cs' )
  destination = PathToTestFile( 'testy', 'Program.cs' )

  goto_data = BuildRequest( completer_target = 'filetype_default',
                            command_arguments = [ 'GoTo' ],
                            line_num = 10,
                            column_num = 15,
                            contents = contents,
                            filetype = 'cs',
                            filepath = filepath )

  response = app.post_json( '/run_completer_command', goto_data ).json
  assert_that( response, LocationMatcher( destination, 7, 22 ) )


@SharedYcmd
def Subcommands_GoTo_Unicode_test( app ):
  filepath = PathToTestFile( 'testy', 'Unicode.cs' )
  with WrapOmniSharpServer( app, filepath ):
    contents = ReadFile( filepath )

    goto_data = BuildRequest( completer_target = 'filetype_default',
                              command_arguments = [ 'GoTo' ],
                              line_num = 45,
                              column_num = 43,
                              contents = contents,
                              filetype = 'cs',
                              filepath = filepath )

    response = app.post_json( '/run_completer_command', goto_data ).json
    assert_that( response, LocationMatcher( filepath, 30, 54 ) )


@SharedYcmd
def Subcommands_GoToImplementation_Basic_test( app ):
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  with WrapOmniSharpServer( app, filepath ):
    contents = ReadFile( filepath )

    goto_data = BuildRequest(
      completer_target = 'filetype_default',
      command_arguments = [ 'GoToImplementation' ],
      line_num = 14,
      column_num = 13,
      contents = contents,
      filetype = 'cs',
      filepath = filepath
    )

    response = app.post_json( '/run_completer_command', goto_data ).json
    assert_that( response, LocationMatcher( filepath, 31, 15 ) )


@SharedYcmd
def Subcommands_GoToImplementation_NoImplementation_test( app ):
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  with WrapOmniSharpServer( app, filepath ):
    contents = ReadFile( filepath )

    goto_data = BuildRequest(
      completer_target = 'filetype_default',
      command_arguments = [ 'GoToImplementation' ],
      line_num = 18,
      column_num = 13,
      contents = contents,
      filetype = 'cs',
      filepath = filepath
    )

    response =  app.post_json( '/run_completer_command',
                               goto_data,
                               expect_errors = True ).json
    assert_that( response, ErrorMatcher( RuntimeError,
                                         'No implementations found' ) )


@SharedYcmd
def Subcommands_CsCompleter_InvalidLocation_test( app ):
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  with WrapOmniSharpServer( app, filepath ):
    contents = ReadFile( filepath )

    goto_data = BuildRequest(
      completer_target = 'filetype_default',
      command_arguments = [ 'GoToImplementation' ],
      line_num = 3,
      column_num = 1,
      contents = contents,
      filetype = 'cs',
      filepath = filepath
    )

    response =  app.post_json( '/run_completer_command',
                               goto_data,
                               expect_errors = True ).json
    assert_that( response, ErrorMatcher( RuntimeError,
                                         "Can't jump to implementation" ) )


@SharedYcmd
def Subcommands_GoToImplementationElseDeclaration_NoImplementation_test( app ):
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  with WrapOmniSharpServer( app, filepath ):
    contents = ReadFile( filepath )

    goto_data = BuildRequest(
      completer_target = 'filetype_default',
      command_arguments = [ 'GoToImplementationElseDeclaration' ],
      line_num = 18,
      column_num = 13,
      contents = contents,
      filetype = 'cs',
      filepath = filepath
    )

    response = app.post_json( '/run_completer_command', goto_data ).json
    assert_that( response, LocationMatcher( filepath, 36, 8 ) )


@SharedYcmd
def Subcommands_GoToImplementationElseDeclaration_SingleImplementation_test(
  app ):
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  with WrapOmniSharpServer( app, filepath ):
    contents = ReadFile( filepath )

    goto_data = BuildRequest(
      completer_target = 'filetype_default',
      command_arguments = [ 'GoToImplementationElseDeclaration' ],
      line_num = 14,
      column_num = 13,
      contents = contents,
      filetype = 'cs',
      filepath = filepath
    )

    response = app.post_json( '/run_completer_command', goto_data ).json
    assert_that( response, LocationMatcher( filepath, 31, 15 ) )


@SharedYcmd
def Subcommands_GoToImplementationElseDeclaration_MultipleImplementations_test(
  app ):
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  with WrapOmniSharpServer( app, filepath ):
    contents = ReadFile( filepath )

    goto_data = BuildRequest(
      completer_target = 'filetype_default',
      command_arguments = [ 'GoToImplementationElseDeclaration' ],
      line_num = 22,
      column_num = 13,
      contents = contents,
      filetype = 'cs',
      filepath = filepath
    )

    response = app.post_json( '/run_completer_command', goto_data ).json
    assert_that( response,
                 contains_exactly( LocationMatcher( filepath, 44, 15 ),
                                   LocationMatcher( filepath, 49, 15 ) ) )


@SharedYcmd
def Subcommands_GoToReferences_InvalidLocation_test( app ):
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  with WrapOmniSharpServer( app, filepath ):
    contents = ReadFile( filepath )

    goto_data = BuildRequest(
      completer_target = 'filetype_default',
      command_arguments = [ 'GoToReferences' ],
      line_num = 3,
      column_num = 1,
      contents = contents,
      filetype = 'cs',
      filepath = filepath
    )

    response = app.post_json( '/run_completer_command',
                              goto_data,
                              expect_errors = True ).json
    assert_that( response, ErrorMatcher( RuntimeError, 'No references found' ) )


@SharedYcmd
def Subcommands_GoToReferences_MultipleReferences_test( app ):
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  with WrapOmniSharpServer( app, filepath ):
    contents = ReadFile( filepath )

    goto_data = BuildRequest(
      completer_target = 'filetype_default',
      command_arguments = [ 'GoToReferences' ],
      line_num = 18,
      column_num = 4,
      contents = contents,
      filetype = 'cs',
      filepath = filepath
    )

    response = app.post_json( '/run_completer_command', goto_data ).json
    assert_that( response,
                 contains_exactly( LocationMatcher( filepath, 17, 54 ),
                                   LocationMatcher( filepath, 18, 4 ) ) )


@SharedYcmd
def Subcommands_GoToReferences_Basic_test( app ):
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  with WrapOmniSharpServer( app, filepath ):
    contents = ReadFile( filepath )

    goto_data = BuildRequest(
      completer_target = 'filetype_default',
      command_arguments = [ 'GoToReferences' ],
      line_num = 21,
      column_num = 29,
      contents = contents,
      filetype = 'cs',
      filepath = filepath
    )

    response = app.post_json( '/run_completer_command', goto_data ).json
    assert_that( response, LocationMatcher( filepath, 21, 15 ) )


@SharedYcmd
def Subcommands_GetToImplementation_Unicode_test( app ):
  filepath = PathToTestFile( 'testy', 'Unicode.cs' )
  with WrapOmniSharpServer( app, filepath ):
    contents = ReadFile( filepath )

    goto_data = BuildRequest(
      completer_target = 'filetype_default',
      command_arguments = [ 'GoToImplementation' ],
      line_num = 48,
      column_num = 44,
      contents = contents,
      filetype = 'cs',
      filepath = filepath
    )

    response = app.post_json( '/run_completer_command', goto_data ).json
    assert_that( response,
                 contains_exactly( LocationMatcher( filepath, 49, 66 ),
                                   LocationMatcher( filepath, 50, 62 ) ) )


@SharedYcmd
def Subcommands_GetType_EmptyMessage_test( app ):
  filepath = PathToTestFile( 'testy', 'GetTypeTestCase.cs' )
  with WrapOmniSharpServer( app, filepath ):
    contents = ReadFile( filepath )

    gettype_data = BuildRequest( completer_target = 'filetype_default',
                                 command_arguments = [ 'GetType' ],
                                 line_num = 1,
                                 column_num = 1,
                                 contents = contents,
                                 filetype = 'cs',
                                 filepath = filepath )

    response = app.post_json( '/run_completer_command',
                              gettype_data,
                              expect_errors = True ).json
    assert_that( response, ErrorMatcher( RuntimeError,
                                         'No type info available.' ) )


@SharedYcmd
def Subcommands_GetType_VariableDeclaration_test( app ):
  filepath = PathToTestFile( 'testy', 'GetTypeTestCase.cs' )
  with WrapOmniSharpServer( app, filepath ):
    contents = ReadFile( filepath )

    gettype_data = BuildRequest( completer_target = 'filetype_default',
                                 command_arguments = [ 'GetType' ],
                                 line_num = 5,
                                 column_num = 5,
                                 contents = contents,
                                 filetype = 'cs',
                                 filepath = filepath )

    response = app.post_json( '/run_completer_command', gettype_data ).json
    assert_that( response, has_entry( 'message', 'System.String' ) )


@SharedYcmd
def Subcommands_GetType_VariableUsage_test( app ):
  filepath = PathToTestFile( 'testy', 'GetTypeTestCase.cs' )
  with WrapOmniSharpServer( app, filepath ):
    contents = ReadFile( filepath )

    gettype_data = BuildRequest( completer_target = 'filetype_default',
                                 command_arguments = [ 'GetType' ],
                                 line_num = 6,
                                 column_num = 5,
                                 contents = contents,
                                 filetype = 'cs',
                                 filepath = filepath )

    response = app.post_json( '/run_completer_command', gettype_data ).json
    assert_that( response, has_entry( 'message', 'string str' ) )


@SharedYcmd
def Subcommands_GetType_DocsIgnored_test( app ):
  filepath = PathToTestFile( 'testy', 'GetTypeTestCase.cs' )
  with WrapOmniSharpServer( app, filepath ):
    contents = ReadFile( filepath )

    gettype_data = BuildRequest( completer_target = 'filetype_default',
                                 command_arguments = [ 'GetType' ],
                                 line_num = 10,
                                 column_num = 34,
                                 contents = contents,
                                 filetype = 'cs',
                                 filepath = filepath )

    response = app.post_json( '/run_completer_command', gettype_data ).json
    assert_that( response, has_entry(
      'message', 'int GetTypeTestCase.an_int_with_docs' ) )


@SharedYcmd
def Subcommands_GetDoc_Invalid_test( app ):
  filepath = PathToTestFile( 'testy', 'GetDocTestCase.cs' )
  with WrapOmniSharpServer( app, filepath ):
    contents = ReadFile( filepath )

    getdoc_data = BuildRequest( completer_target = 'filetype_default',
                                command_arguments = [ 'GetDoc' ],
                                line_num = 1,
                                column_num = 1,
                                contents = contents,
                                filetype = 'cs',
                                filepath = filepath )

    response = app.post_json( '/run_completer_command',
                              getdoc_data,
                              expect_errors = True ).json
    assert_that( response, ErrorMatcher( RuntimeError,
                                         'No documentation available.' ) )


@SharedYcmd
def Subcommands_GetDoc_Variable_test( app ):
  filepath = PathToTestFile( 'testy', 'GetDocTestCase.cs' )
  with WrapOmniSharpServer( app, filepath ):
    contents = ReadFile( filepath )

    getdoc_data = BuildRequest( completer_target = 'filetype_default',
                                command_arguments = [ 'GetDoc' ],
                                line_num = 13,
                                column_num = 28,
                                contents = contents,
                                filetype = 'cs',
                                filepath = filepath )

    response = app.post_json( '/run_completer_command', getdoc_data ).json
    assert_that( response,
                 has_entry( 'detailed_info',
                            'int GetDocTestCase.an_int\n'
                            'an integer, or something' ) )


@SharedYcmd
def Subcommands_GetDoc_Function_test( app ):
  filepath = PathToTestFile( 'testy', 'GetDocTestCase.cs' )
  with WrapOmniSharpServer( app, filepath ):
    contents = ReadFile( filepath )

    getdoc_data = BuildRequest( completer_target = 'filetype_default',
                                command_arguments = [ 'GetDoc' ],
                                line_num = 33,
                                column_num = 27,
                                contents = contents,
                                filetype = 'cs',
                                filepath = filepath )

    response = app.post_json( '/run_completer_command', getdoc_data ).json
    assert_that( response, has_entry( 'detailed_info',
      'int GetDocTestCase.DoATest()\n'
      'Very important method.\n\nWith multiple lines of '
      'commentary\nAnd Format-\n-ting' ) )


@IsolatedYcmd()
def Subcommands_StopServer_NoErrorIfNotStarted_test( app ):
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  app.post_json(
    '/run_completer_command',
    BuildRequest(
      filetype = 'cs',
      filepath = filepath,
      command_arguments = [ 'StopServer' ]
    )
  )

  request_data = BuildRequest( filetype = 'cs', filepath = filepath )
  assert_that( app.post_json( '/debug_info', request_data ).json,
               has_entry(
                 'completer',
                 has_entry( 'servers', contains_exactly(
                   has_entry( 'is_running', False )
                 ) )
               ) )


def StopServer_KeepLogFiles( app ):
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  contents = ReadFile( filepath )
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilCompleterServerReady( app, 'cs' )

  event_data = BuildRequest( filetype = 'cs', filepath = filepath )

  response = app.post_json( '/debug_info', event_data ).json

  logfiles = []
  for server in response[ 'completer' ][ 'servers' ]:
    logfiles.extend( server[ 'logfiles' ] )

  try:
    for logfile in logfiles:
      assert_that( os.path.exists( logfile ),
           'Logfile should exist at {0}'.format( logfile ) )
  finally:
    app.post_json(
      '/run_completer_command',
      BuildRequest(
        filetype = 'cs',
        filepath = filepath,
        command_arguments = [ 'StopServer' ]
      )
    )

  if user_options_store.Value( 'server_keep_logfiles' ):
    for logfile in logfiles:
      assert_that( os.path.exists( logfile ),
           'Logfile should still exist at {0}'.format( logfile ) )
  else:
    for logfile in logfiles:
      assert_that( not os.path.exists( logfile ),
           'Logfile should no longer exist at {0}'.format( logfile ) )


@IsolatedYcmd( { 'server_keep_logfiles': 1 } )
def Subcommands_StopServer_KeepLogFiles_test( app ):
  StopServer_KeepLogFiles( app )


@IsolatedYcmd( { 'server_keep_logfiles': 0 } )
def Subcommands_StopServer_DoNotKeepLogFiles_test( app ):
  StopServer_KeepLogFiles( app )


@IsolatedYcmd()
def Subcommands_RestartServer_PidChanges_test( app ):
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  contents = ReadFile( filepath )
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )

  try:
    WaitUntilCompleterServerReady( app, 'cs' )

    def GetPid():
      request_data = BuildRequest( filetype = 'cs', filepath = filepath )
      debug_info = app.post_json( '/debug_info', request_data ).json
      return debug_info[ "completer" ][ "servers" ][ 0 ][ "pid" ]

    old_pid = GetPid()

    app.post_json(
      '/run_completer_command',
      BuildRequest(
        filetype = 'cs',
        filepath = filepath,
        command_arguments = [ 'RestartServer' ]
      )
    )
    WaitUntilCompleterServerReady( app, 'cs' )

    new_pid = GetPid()

    assert old_pid != new_pid, '%r == %r' % ( old_pid, new_pid )
  finally:
    app.post_json(
      '/run_completer_command',
      BuildRequest(
        filetype = 'cs',
        filepath = filepath,
        command_arguments = [ 'StopServer' ]
      )
    )


@IsolatedYcmd()
@patch( 'ycmd.utils.WaitUntilProcessIsTerminated',
        MockProcessTerminationTimingOut )
def Subcommands_StopServer_Timeout_test( app ):
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  contents = ReadFile( filepath )
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilCompleterServerReady( app, 'cs' )

  app.post_json(
    '/run_completer_command',
    BuildRequest(
      filetype = 'cs',
      filepath = filepath,
      command_arguments = [ 'StopServer' ]
    )
  )

  request_data = BuildRequest( filetype = 'cs', filepath = filepath )
  assert_that( app.post_json( '/debug_info', request_data ).json,
               has_entry(
                 'completer',
                 has_entry( 'servers', contains_exactly(
                   has_entry( 'is_running', False )
                 ) )
               ) )


@SharedYcmd
def Subcommands_Format_Works_test( app ):
  filepath = PathToTestFile( 'testy', 'Program.cs' )
  with WrapOmniSharpServer( app, filepath ):
    contents = ReadFile( filepath )

    request = BuildRequest( command_arguments = [ 'Format' ],
                            line_num = 1,
                            column_num = 1,
                            contents = contents,
                            filetype = 'cs',
                            filepath = filepath )

    response = app.post_json( '/run_completer_command', request ).json
    print( 'completer response = ', response )
    assert_that( response, has_entries( {
      'fixits': contains_exactly( has_entries( {
        'location': LocationMatcher( filepath, 1, 1 ),
        'chunks': contains_exactly(
          ChunkMatcher(
            '\n        }\n    ',
            LocationMatcher( filepath, 11, 1 ),
            LocationMatcher( filepath, 12, 2 )
          ),
          ChunkMatcher(
            '            ',
            LocationMatcher( filepath, 10, 1 ),
            LocationMatcher( filepath, 10, 4 )
          ),
          ChunkMatcher(
            '        {\n            ',
            LocationMatcher( filepath, 8, 1 ),
            LocationMatcher( filepath, 9, 4 )
          ),
          ChunkMatcher(
            '',
            LocationMatcher( filepath, 7, 26 ),
            LocationMatcher( filepath, 7, 27 )
          ),
          ChunkMatcher(
            '    class MainClass\n    {\n        ',
            LocationMatcher( filepath, 5, 1 ),
            LocationMatcher( filepath, 7, 3 )
          ),
        ) } ) ) } ) )


@SharedYcmd
def Subcommands_RangeFormat_Works_test( app ):
  filepath = PathToTestFile( 'testy', 'Program.cs' )
  with WrapOmniSharpServer( app, filepath ):
    contents = ReadFile( filepath )

    request = BuildRequest( command_arguments = [ 'Format' ],
                            line_num = 11,
                            column_num = 2,
                            contents = contents,
                            filetype = 'cs',
                            filepath = filepath )
    request[ 'range' ] = {
      'start': { 'line_num':  8, 'column_num': 1 },
      'end':   { 'line_num': 11, 'column_num': 4 }
    }
    response = app.post_json( '/run_completer_command', request ).json
    print( 'completer response = ', response )
    assert_that( response, has_entries( {
      'fixits': contains_exactly( has_entries( {
        'location': LocationMatcher( filepath, 11, 2 ),
        'chunks': contains_exactly(
          ChunkMatcher(
            '\n        ',
            LocationMatcher( filepath, 11, 1 ),
            LocationMatcher( filepath, 11, 3 )
          ),
          ChunkMatcher(
            '            ',
            LocationMatcher( filepath, 10, 1 ),
            LocationMatcher( filepath, 10, 4 )
          ),
          ChunkMatcher(
            '        {\n            ',
            LocationMatcher( filepath, 8, 1 ),
            LocationMatcher( filepath, 9, 4 )
          ),
        ) } ) ) } ) )


@SharedYcmd
def Subcommands_RefactorRename_MultiFile_test( app ):
  continuous_test = PathToTestFile( 'testy', 'ContinuousTest.cs' )
  fixit_test = PathToTestFile( 'testy', 'FixItTestCase.cs' )
  get_type_test = PathToTestFile( 'testy', 'GetTypeTestCase.cs' )
  goto_test = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  import_test = PathToTestFile( 'testy', 'ImportTest.cs' )
  program = PathToTestFile( 'testy', 'Program.cs' )
  get_doc_test = PathToTestFile( 'testy', 'GetDocTestCase.cs' )
  unicode_test = PathToTestFile( 'testy', 'Unicode.cs' )
  with WrapOmniSharpServer( app, continuous_test ):
    contents = ReadFile( continuous_test )

    request = BuildRequest( completer_target = 'filetype_default',
                            command_arguments = [ 'RefactorRename', 'x' ],
                            line_num = 3,
                            column_num = 11,
                            contents = contents,
                            filetype = 'cs',
                            filepath = continuous_test )

    response = app.post_json( '/run_completer_command', request ).json
    print( 'response = ', response )
    assert_that( response, has_entries( {
      'fixits': contains_exactly( has_entries( {
        'location': LocationMatcher( continuous_test, 3, 11 ),
        'chunks': contains_exactly(
          has_entries( {
            'replacement_text': 'x',
            'range': RangeMatcher( continuous_test, ( 3, 11 ), ( 3, 16 ) )
          } ),
          has_entries( {
            'replacement_text': 'x',
            'range': RangeMatcher( fixit_test, ( 1, 11 ), ( 1, 16 ) )
          } ),
          has_entries( {
            'replacement_text': 'x',
            'range': RangeMatcher( get_doc_test, ( 4, 11 ), ( 4, 16 ) )
          } ),
          has_entries( {
            'replacement_text': 'x',
            'range': RangeMatcher( get_type_test, ( 2, 11 ), ( 2, 16 ) )
          } ),
          has_entries( {
            'replacement_text': 'x',
            'range': RangeMatcher( goto_test, ( 4, 11 ), ( 4, 16 ) )
          } ),
          has_entries( {
            'replacement_text': 'x',
            'range': RangeMatcher( import_test, ( 3, 11 ), ( 3, 16 ) )
          } ),
          has_entries( {
            'replacement_text': 'x',
            'range': RangeMatcher( program, ( 3, 11 ), ( 3, 16 ) )
          } ),
          has_entries( {
            'replacement_text': 'x',
            'range': RangeMatcher( unicode_test, ( 4, 11 ), ( 4, 16 ) )
          } ),
        ) } ) ) } ) )
