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

from hamcrest import ( assert_that,
                       empty,
                       has_entries,
                       has_entry,
                       has_items,
                       contains_exactly )
from unittest.mock import patch
from unittest import TestCase
import os.path

from ycmd import user_options_store
from ycmd.tests.cs import setUpModule, tearDownModule # noqa
from ycmd.tests.cs import ( IsolatedYcmd,
                            PathToTestFile,
                            SharedYcmd,
                            WrapOmniSharpServer )
from ycmd.tests.test_utils import ( BuildRequest,
                                    ChunkMatcher,
                                    ErrorMatcher,
                                    LocationMatcher,
                                    MockProcessTerminationTimingOut,
                                    RangeMatcher,
                                    WaitUntilCompleterServerReady,
                                    WithRetry )
from ycmd.utils import ReadFile


def StopServer_KeepLogFiles( app ):
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  with WrapOmniSharpServer( app, filepath ):
    event_data = BuildRequest( filetype = 'cs', filepath = filepath )

    response = app.post_json( '/debug_info', event_data ).json

    logfiles = []
    for server in response[ 'completer' ][ 'servers' ]:
      logfiles.extend( server[ 'logfiles' ] )

    try:
      for logfile in logfiles:
        assert_that( os.path.exists( logfile ),
                     f'Logfile should exist at { logfile }' )
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
                     f'Logfile should still exist at { logfile }' )
    else:
      for logfile in logfiles:
        assert_that( not os.path.exists( logfile ),
                     f'Logfile should no longer exist at { logfile }' )


class SubcommandsTest( TestCase ):
  @SharedYcmd
  def test_Subcommands_FixIt_NoFixitsFound( self, app ):
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
  def test_Subcommands_FixIt_Multi( self, app ):
    fixit_test = PathToTestFile( 'testy', 'FixItTestCase.cs' )
    with WrapOmniSharpServer( app, fixit_test ):
      contents = ReadFile( fixit_test )

      request = BuildRequest( completer_target = 'filetype_default',
                              command_arguments = [ 'FixIt' ],
                              line_num = 5,
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
      assert_that( response, has_entries( {
        'fixits': contains_exactly( has_entries( {
          'location': LocationMatcher( fixit_test, 5, 27 ),
          'chunks': contains_exactly(
            has_entries( { 'replacement_text': '0b101', } ) )
        } ) ) } ) )


  @SharedYcmd
  def test_Subcommands_FixIt_Range( self, app ):
    fixit_test = PathToTestFile( 'testy', 'FixItTestCase.cs' )
    with WrapOmniSharpServer( app, fixit_test ):
      contents = ReadFile( fixit_test )

      request = BuildRequest( completer_target = 'filetype_default',
                              command_arguments = [ 'FixIt' ],
                              line_num = 5,
                              column_num = 23,
                              contents = contents,
                              filetype = 'cs',
                              filepath = fixit_test )
      request.update( { 'range': {
        'start': { 'line_num': 5, 'column_num': 23 },
        'end': { 'line_num': 5, 'column_num': 27 }
      } } )
      response = app.post_json( '/run_completer_command', request ).json
      assert_that( response, has_entries( {
        'fixits': contains_exactly(
          has_entries( {
            'text': 'Extract method',
            'command': has_entries( { 'index': 0 } ),
            'resolve': True } ),
          has_entries( {
            'text': 'Extract local function',
            'command': has_entries( { 'index': 1 } ),
            'resolve': True } ),
        )
      } ) )


  @SharedYcmd
  def test_Subcommands_FixIt_Single( self, app ):
    fixit_test = PathToTestFile( 'testy', 'FixItTestCase.cs' )
    with WrapOmniSharpServer( app, fixit_test ):
      contents = ReadFile( fixit_test )

      request = BuildRequest( completer_target = 'filetype_default',
                              command_arguments = [ 'FixIt' ],
                              line_num = 4,
                              column_num = 17,
                              contents = contents,
                              filetype = 'cs',
                              filepath = fixit_test )
      response = app.post_json( '/run_completer_command', request ).json
      assert_that( response, has_entries( {
        'fixits': contains_exactly( has_entries( {
          'location': LocationMatcher( fixit_test, 4, 17 ),
          'chunks': contains_exactly(
            has_entries( {
              'replacement_text': 'var',
              'range': RangeMatcher( fixit_test, ( 4, 13 ), ( 4, 16 ) ) } )
          ) } ) ) } ) )


  @SharedYcmd
  def test_Subcommands_RefactorRename_MissingNewName( self, app ):
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
  def test_Subcommands_RefactorRename_Unicode( self, app ):
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
  def test_Subcommands_RefactorRename_Basic( self, app ):
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


  @WithRetry()
  @SharedYcmd
  def test_Subcommands_GoTo_Basic( self, app ):
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
  def test_Subcommands_GoToSymbol( self, app ):
    for identifier, expected in [
      ( 'IGotoTestMultiple',
        LocationMatcher(
          PathToTestFile( 'testy', 'GotoTestCase.cs' ), 39, 12 ) ),
      ( 'DoSomething',
        has_items(
          LocationMatcher(
            PathToTestFile( 'testy', 'GotoTestCase.cs' ), 27, 8 ),
          LocationMatcher(
            PathToTestFile( 'testy', 'GotoTestCase.cs' ), 31, 15 ),
          LocationMatcher(
            PathToTestFile( 'testy', 'GotoTestCase.cs' ), 36, 8 ),
          LocationMatcher(
            PathToTestFile( 'testy', 'GotoTestCase.cs' ), 40, 8 ),
          LocationMatcher(
            PathToTestFile( 'testy', 'GotoTestCase.cs' ), 44, 15 ),
          LocationMatcher(
            PathToTestFile( 'testy', 'GotoTestCase.cs' ), 49, 15 ) ) ),
      ( 'asd', ErrorMatcher( RuntimeError, 'No symbols found' ) )
    ]:
      with self.subTest( identifier = identifier, expected = expected ):
        filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
        with WrapOmniSharpServer( app, filepath ):
          contents = ReadFile( filepath )
          goto_data = BuildRequest( completer_target = 'filetype_default',
                                    command_arguments = [ 'GoToSymbol',
                                                          identifier ],
                                    line_num = 1,
                                    column_num = 1,
                                    contents = contents,
                                    filetype = 'cs',
                                    filepath = filepath )
          response =  app.post_json( '/run_completer_command',
                                     goto_data,
                                     expect_errors = True ).json
          assert_that( response, expected )


  @SharedYcmd
  def test_Subcommands_GoTo_Unicode( self, app ):
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
  def test_Subcommands_GoToImplementation_Basic( self, app ):
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
  def test_Subcommands_GoToImplementation_NoImplementation( self, app ):
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
  def test_Subcommands_CsCompleter_InvalidLocation( self, app ):
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
  def test_Subcommands_GoToImplementationElseDeclaration_NoImplementation(
      self, app ):
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
  def test_Subcommands_GoToImplementationElseDeclaration_SingleImplementation(
    self, app ):
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
  def test_Subcommands_GoToImplementationElseDeclaration_Multiple(
    self, app ):
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
  def test_Subcommands_GoToReferences_InvalidLocation( self, app ):
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
      assert_that( response, ErrorMatcher(
                               RuntimeError, 'No references found' ) )


  @SharedYcmd
  def test_Subcommands_GoToReferences_MultipleReferences( self, app ):
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
  def test_Subcommands_GoToReferences_Basic( self, app ):
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
  def test_Subcommands_GetToImplementation_Unicode( self, app ):
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
  def test_Subcommands_GetType_EmptyMessage( self, app ):
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
  def test_Subcommands_GetType_VariableDeclaration( self, app ):
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
  def test_Subcommands_GetType_VariableUsage( self, app ):
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
  def test_Subcommands_GetType_DocsIgnored( self, app ):
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
  def test_Subcommands_GetDoc_Invalid( self, app ):
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
  def test_Subcommands_GetDoc_Variable( self, app ):
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
  def test_Subcommands_GetDoc_Function( self, app ):
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
  def test_Subcommands_StopServer_NoErrorIfNotStarted( self, app ):
    filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
    # Don't wrap the server - we don't want to start it!
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


  @IsolatedYcmd( { 'server_keep_logfiles': 1 } )
  def test_Subcommands_StopServer_KeepLogFiles( self, app ):
    StopServer_KeepLogFiles( app )


  @IsolatedYcmd( { 'server_keep_logfiles': 0 } )
  def test_Subcommands_StopServer_DoNotKeepLogFiles( self, app ):
    StopServer_KeepLogFiles( app )


  @IsolatedYcmd()
  def test_Subcommands_RestartServer_PidChanges( self, app ):
    filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
    with WrapOmniSharpServer( app, filepath ):

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


  @IsolatedYcmd()
  @patch( 'ycmd.utils.WaitUntilProcessIsTerminated',
          MockProcessTerminationTimingOut )
  def test_Subcommands_StopServer_Timeout( self, app ):
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
  def test_Subcommands_Format_Works( self, app ):
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
  def test_Subcommands_RangeFormat_Works( self, app ):
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
  def test_Subcommands_OrganizeImports( self, app ):
    filepath = PathToTestFile( 'testy', 'ImportTest.cs' )
    with WrapOmniSharpServer( app, filepath ):
      request = BuildRequest( command_arguments = [ 'OrganizeImports' ],
                              line_num = 11,
                              column_num = 2,
                              contents = ReadFile( filepath ),
                              filetype = 'cs',
                              filepath = filepath )

      response = app.post_json( '/run_completer_command', request ).json
      print( 'completer response = ', response )
      assert_that( response, has_entries( {
        'fixits': contains_exactly( has_entries( {
          'location': LocationMatcher( filepath, 11, 2 ),
          'chunks': contains_exactly(
            ChunkMatcher(
              '    ',
              LocationMatcher( filepath, 5, 1 ),
              LocationMatcher( filepath, 5, 2 ),
            ),
            ChunkMatcher(
              '',
              LocationMatcher( filepath, 1, 1 ),
              LocationMatcher( filepath, 3, 1 ),
            )
          ) } ) ) } ) )


  @SharedYcmd
  def test_Subcommands_GoToDocumentOutline( self, app ):

    # we reuse the ImportTest.cs file as it contains a good selection of
    # symbols/ symbol types.
    filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
    with WrapOmniSharpServer( app, filepath ):

      # the command name and file are the only relevant arguments for this
      # subcommand, our current cursor position in the file doesn't matter.
      request = BuildRequest( command_arguments = [ 'GoToDocumentOutline' ],
                              line_num = 11,
                              column_num = 2,
                              contents = ReadFile( filepath ),
                              filetype = 'cs',
                              filepath = filepath )

      response = app.post_json( '/run_completer_command', request ).json

      print( 'completer response = ', response )

      assert_that( response,
        has_items(
          LocationMatcher(
            PathToTestFile( 'testy', 'GotoTestCase.cs' ), 6, 8 ),
          LocationMatcher(
            PathToTestFile( 'testy', 'GotoTestCase.cs' ), 26, 12 ),
          LocationMatcher(
            PathToTestFile( 'testy', 'GotoTestCase.cs' ), 30, 8 ),
          LocationMatcher(
            PathToTestFile( 'testy', 'GotoTestCase.cs' ), 35, 12 ),
          LocationMatcher(
            PathToTestFile( 'testy', 'GotoTestCase.cs' ), 39, 12 ),
          LocationMatcher(
            PathToTestFile( 'testy', 'GotoTestCase.cs' ), 43, 8 ),
          LocationMatcher(
            PathToTestFile( 'testy', 'GotoTestCase.cs' ), 48, 8 ),
          LocationMatcher(
            PathToTestFile( 'testy', 'GotoTestCase.cs' ), 8, 15 ),
          LocationMatcher(
            PathToTestFile( 'testy', 'GotoTestCase.cs' ), 13, 15 ),
          LocationMatcher(
            PathToTestFile( 'testy', 'GotoTestCase.cs' ), 17, 15 ),
          LocationMatcher(
            PathToTestFile( 'testy', 'GotoTestCase.cs' ), 21, 15 ),
          LocationMatcher(
            PathToTestFile( 'testy', 'GotoTestCase.cs' ), 27, 8 ),
          LocationMatcher(
            PathToTestFile( 'testy', 'GotoTestCase.cs' ), 31, 15 ),
          LocationMatcher(
            PathToTestFile( 'testy', 'GotoTestCase.cs' ), 36, 8 ),
          LocationMatcher(
            PathToTestFile( 'testy', 'GotoTestCase.cs' ), 40, 8 ),
          LocationMatcher(
            PathToTestFile( 'testy', 'GotoTestCase.cs' ), 44, 15 ),
          LocationMatcher(
            PathToTestFile( 'testy', 'GotoTestCase.cs' ), 49, 15 ),
        )
      )

  @SharedYcmd
  def test_Subcommands_GoToDocumentOutline_Empty( self, app ):

    filepath = PathToTestFile( 'testy', 'Empty.cs' )
    with WrapOmniSharpServer( app, filepath ):

      # the command name and file are the only relevant arguments for this
      # subcommand.  our current cursor position in the file doesn't matter.
      request = BuildRequest( command_arguments = [ 'GoToDocumentOutline' ],
                              line_num = 0,
                              column_num = 0,
                              contents = ReadFile( filepath ),
                              filetype = 'cs',
                              filepath = filepath )

      response = app.post_json( '/run_completer_command',
                                request,
                                expect_errors = True ).json

      print( 'completer response = ', response )

      assert_that( response, ErrorMatcher( RuntimeError,
                                           'No symbols found' ) )
