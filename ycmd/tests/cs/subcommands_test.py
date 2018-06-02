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

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa

from hamcrest import assert_that, has_entry, has_entries, contains
from mock import patch
from nose.tools import eq_, ok_
from webtest import AppError
import pprint
import os.path

from ycmd import user_options_store
from ycmd.tests.cs import ( IsolatedYcmd, PathToTestFile, SharedYcmd,
                            WrapOmniSharpServer )
from ycmd.tests.test_utils import ( BuildRequest,
                                    ChunkMatcher,
                                    LocationMatcher,
                                    MockProcessTerminationTimingOut,
                                    WaitUntilCompleterServerReady )
from ycmd.utils import ReadFile


@SharedYcmd
def Subcommands_GoTo_Basic_test( app ):
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  with WrapOmniSharpServer( app, filepath ):
    contents = ReadFile( filepath )

    goto_data = BuildRequest( completer_target = 'filetype_default',
                              command_arguments = [ 'GoTo' ],
                              line_num = 9,
                              column_num = 15,
                              contents = contents,
                              filetype = 'cs',
                              filepath = filepath )

    eq_( {
      'filepath': PathToTestFile( 'testy', 'Program.cs' ),
      'line_num': 7,
      'column_num': 3
    }, app.post_json( '/run_completer_command', goto_data ).json )


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

    eq_( {
      'filepath': PathToTestFile( 'testy', 'Unicode.cs' ),
      'line_num': 30,
      'column_num': 37
    }, app.post_json( '/run_completer_command', goto_data ).json )


@SharedYcmd
def Subcommands_GoToImplementation_Basic_test( app ):
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  with WrapOmniSharpServer( app, filepath ):
    contents = ReadFile( filepath )

    goto_data = BuildRequest(
      completer_target = 'filetype_default',
      command_arguments = [ 'GoToImplementation' ],
      line_num = 13,
      column_num = 13,
      contents = contents,
      filetype = 'cs',
      filepath = filepath
    )

    eq_( {
      'filepath': PathToTestFile( 'testy', 'GotoTestCase.cs' ),
      'line_num': 30,
      'column_num': 3
    }, app.post_json( '/run_completer_command', goto_data ).json )


@SharedYcmd
def Subcommands_GoToImplementation_NoImplementation_test( app ):
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  with WrapOmniSharpServer( app, filepath ):
    contents = ReadFile( filepath )

    goto_data = BuildRequest(
      completer_target = 'filetype_default',
      command_arguments = [ 'GoToImplementation' ],
      line_num = 17,
      column_num = 13,
      contents = contents,
      filetype = 'cs',
      filepath = filepath
    )

    try:
      app.post_json( '/run_completer_command', goto_data ).json
      raise Exception( "Expected a 'No implementations found' error" )
    except AppError as e:
      if 'No implementations found' in str( e ):
        pass
      else:
        raise


@SharedYcmd
def Subcommands_CsCompleter_InvalidLocation_test( app ):
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  with WrapOmniSharpServer( app, filepath ):
    contents = ReadFile( filepath )

    goto_data = BuildRequest(
      completer_target = 'filetype_default',
      command_arguments = [ 'GoToImplementation' ],
      line_num = 2,
      column_num = 1,
      contents = contents,
      filetype = 'cs',
      filepath = filepath
    )

    try:
      app.post_json( '/run_completer_command', goto_data ).json
      raise Exception( 'Expected a "Can\\\'t jump to implementation" error' )
    except AppError as e:
      if 'Can\\\'t jump to implementation' in str( e ):
        pass
      else:
        raise


@SharedYcmd
def Subcommands_GoToImplementationElseDeclaration_NoImplementation_test( app ):
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  with WrapOmniSharpServer( app, filepath ):
    contents = ReadFile( filepath )

    goto_data = BuildRequest(
      completer_target = 'filetype_default',
      command_arguments = [ 'GoToImplementationElseDeclaration' ],
      line_num = 17,
      column_num = 13,
      contents = contents,
      filetype = 'cs',
      filepath = filepath
    )

    eq_( {
      'filepath': PathToTestFile( 'testy', 'GotoTestCase.cs' ),
      'line_num': 35,
      'column_num': 3
    }, app.post_json( '/run_completer_command', goto_data ).json )


@SharedYcmd
def Subcommands_GoToImplementationElseDeclaration_SingleImplementation_test(
  app ):
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  with WrapOmniSharpServer( app, filepath ):
    contents = ReadFile( filepath )

    goto_data = BuildRequest(
      completer_target = 'filetype_default',
      command_arguments = [ 'GoToImplementationElseDeclaration' ],
      line_num = 13,
      column_num = 13,
      contents = contents,
      filetype = 'cs',
      filepath = filepath
    )

    eq_( {
      'filepath': PathToTestFile( 'testy', 'GotoTestCase.cs' ),
      'line_num': 30,
      'column_num': 3
    }, app.post_json( '/run_completer_command', goto_data ).json )


@SharedYcmd
def Subcommands_GoToImplementationElseDeclaration_MultipleImplementations_test(
  app ):
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  with WrapOmniSharpServer( app, filepath ):
    contents = ReadFile( filepath )

    goto_data = BuildRequest(
      completer_target = 'filetype_default',
      command_arguments = [ 'GoToImplementationElseDeclaration' ],
      line_num = 21,
      column_num = 13,
      contents = contents,
      filetype = 'cs',
      filepath = filepath
    )

    eq_( [ {
      'filepath': PathToTestFile( 'testy', 'GotoTestCase.cs' ),
      'line_num': 43,
      'column_num': 3
    }, {
      'filepath': PathToTestFile( 'testy', 'GotoTestCase.cs' ),
      'line_num': 48,
      'column_num': 3
    } ], app.post_json( '/run_completer_command', goto_data ).json )


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

    eq_( [ {
      'filepath': PathToTestFile( 'testy', 'Unicode.cs' ),
      'line_num': 49,
      'column_num': 54
    }, {
      'filepath': PathToTestFile( 'testy', 'Unicode.cs' ),
      'line_num': 50,
      'column_num': 50
    } ], app.post_json( '/run_completer_command', goto_data ).json )


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

    eq_( {
      u'message': u""
    }, app.post_json( '/run_completer_command', gettype_data ).json )


@SharedYcmd
def Subcommands_GetType_VariableDeclaration_test( app ):
  filepath = PathToTestFile( 'testy', 'GetTypeTestCase.cs' )
  with WrapOmniSharpServer( app, filepath ):
    contents = ReadFile( filepath )

    gettype_data = BuildRequest( completer_target = 'filetype_default',
                                 command_arguments = [ 'GetType' ],
                                 line_num = 4,
                                 column_num = 5,
                                 contents = contents,
                                 filetype = 'cs',
                                 filepath = filepath )

    eq_( {
      u'message': u"string"
    }, app.post_json( '/run_completer_command', gettype_data ).json )


@SharedYcmd
def Subcommands_GetType_VariableUsage_test( app ):
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

    eq_( {
      u'message': u"string str"
    }, app.post_json( '/run_completer_command', gettype_data ).json )


@SharedYcmd
def Subcommands_GetType_Constant_test( app ):
  filepath = PathToTestFile( 'testy', 'GetTypeTestCase.cs' )
  with WrapOmniSharpServer( app, filepath ):
    contents = ReadFile( filepath )

    gettype_data = BuildRequest( completer_target = 'filetype_default',
                                 command_arguments = [ 'GetType' ],
                                 line_num = 4,
                                 column_num = 14,
                                 contents = contents,
                                 filetype = 'cs',
                                 filepath = filepath )

    eq_( {
      u'message': u"System.String"
    }, app.post_json( '/run_completer_command', gettype_data ).json )


@SharedYcmd
def Subcommands_GetType_DocsIgnored_test( app ):
  filepath = PathToTestFile( 'testy', 'GetTypeTestCase.cs' )
  with WrapOmniSharpServer( app, filepath ):
    contents = ReadFile( filepath )

    gettype_data = BuildRequest( completer_target = 'filetype_default',
                                 command_arguments = [ 'GetType' ],
                                 line_num = 9,
                                 column_num = 34,
                                 contents = contents,
                                 filetype = 'cs',
                                 filepath = filepath )

    eq_( {
      u'message': u"int GetTypeTestCase.an_int_with_docs;",
    }, app.post_json( '/run_completer_command', gettype_data ).json )


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

    eq_( {
      'detailed_info': 'int GetDocTestCase.an_int;\n'
                       'an integer, or something',
    }, app.post_json( '/run_completer_command', getdoc_data ).json )


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

    # It seems that Omnisharp server eats newlines
    eq_( {
      'detailed_info': 'int GetDocTestCase.DoATest();\n'
                       ' Very important method. With multiple lines of '
                       'commentary And Format- -ting',
    }, app.post_json( '/run_completer_command', getdoc_data ).json )


def RunFixItTest( app,
                  line,
                  column,
                  result_matcher,
                  filepath = [ 'testy', 'FixItTestCase.cs' ] ):
  filepath = PathToTestFile( *filepath )
  with WrapOmniSharpServer( app, filepath ):
    contents = ReadFile( filepath )

    fixit_data = BuildRequest( completer_target = 'filetype_default',
                               command_arguments = [ 'FixIt' ],
                               line_num = line,
                               column_num = column,
                               contents = contents,
                               filetype = 'cs',
                               filepath = filepath )

    response = app.post_json( '/run_completer_command', fixit_data ).json

    pprint.pprint( response )

    assert_that( response, result_matcher )


@SharedYcmd
def Subcommands_FixIt_RemoveSingleLine_test( app ):
  filepath = PathToTestFile( 'testy', 'FixItTestCase.cs' )
  RunFixItTest( app, 11, 1, has_entries( {
    'fixits': contains( has_entries( {
      'location': LocationMatcher( filepath, 11, 1 ),
      'chunks': contains( ChunkMatcher( '',
                                        LocationMatcher( filepath, 10, 20 ),
                                        LocationMatcher( filepath, 11, 30 ) ) )
    } ) )
  } ) )


@SharedYcmd
def Subcommands_FixIt_MultipleLines_test( app ):
  filepath = PathToTestFile( 'testy', 'FixItTestCase.cs' )
  RunFixItTest( app, 19, 1, has_entries( {
    'fixits': contains( has_entries( {
      'location': LocationMatcher( filepath, 19, 1 ),
      'chunks': contains( ChunkMatcher( 'return On',
                                        LocationMatcher( filepath, 20, 13 ),
                                        LocationMatcher( filepath, 21, 35 ) ) )
    } ) )
  } ) )


@SharedYcmd
def Subcommands_FixIt_SpanFileEdge_test( app ):
  filepath = PathToTestFile( 'testy', 'FixItTestCase.cs' )
  RunFixItTest( app, 1, 1, has_entries( {
    'fixits': contains( has_entries( {
      'location': LocationMatcher( filepath, 1, 1 ),
      'chunks': contains( ChunkMatcher( 'System',
                                        LocationMatcher( filepath, 1, 7 ),
                                        LocationMatcher( filepath, 3, 18 ) ) )
    } ) )
  } ) )


@SharedYcmd
def Subcommands_FixIt_AddTextInLine_test( app ):
  filepath = PathToTestFile( 'testy', 'FixItTestCase.cs' )
  RunFixItTest( app, 9, 1, has_entries( {
    'fixits': contains( has_entries( {
      'location': LocationMatcher( filepath, 9, 1 ),
      'chunks': contains( ChunkMatcher( ', StringComparison.Ordinal',
                                        LocationMatcher( filepath, 9, 29 ),
                                        LocationMatcher( filepath, 9, 29 ) ) )
    } ) )
  } ) )


@SharedYcmd
def Subcommands_FixIt_ReplaceTextInLine_test( app ):
  filepath = PathToTestFile( 'testy', 'FixItTestCase.cs' )
  RunFixItTest( app, 10, 1, has_entries( {
    'fixits': contains( has_entries( {
      'location': LocationMatcher( filepath, 10, 1 ),
      'chunks': contains( ChunkMatcher( 'const int',
                                        LocationMatcher( filepath, 10, 13 ),
                                        LocationMatcher( filepath, 10, 16 ) ) )
    } ) )
  } ) )


@SharedYcmd
def Subcommands_FixIt_Unicode_test( app ):
  filepath = PathToTestFile( 'testy', 'Unicode.cs' )
  RunFixItTest( app, 30, 54, has_entries( {
    'fixits': contains( has_entries( {
      'location': LocationMatcher( filepath, 30, 54 ),
      'chunks': contains( ChunkMatcher( ' readonly',
                                        LocationMatcher( filepath, 30, 44 ),
                                        LocationMatcher( filepath, 30, 44 ) ) )
    } ) )
  } ), filepath = [ 'testy', 'Unicode.cs' ] )


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
                 has_entry( 'servers', contains(
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
      ok_( os.path.exists( logfile ),
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
      ok_( os.path.exists( logfile ),
           'Logfile should still exist at {0}'.format( logfile ) )
  else:
    for logfile in logfiles:
      ok_( not os.path.exists( logfile ),
           'Logfile should no longer exist at {0}'.format( logfile ) )


@IsolatedYcmd( { 'server_keep_logfiles': 1 } )
def Subcommands_StopServer_KeepLogFiles_test( app ):
  StopServer_KeepLogFiles( app )


@IsolatedYcmd( { 'server_keep_logfiles': 0 } )
def Subcommands_StopServer_DoNotKeepLogFiles_test( app ):
  StopServer_KeepLogFiles( app )


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
                 has_entry( 'servers', contains(
                   has_entry( 'is_running', False )
                 ) )
               ) )
