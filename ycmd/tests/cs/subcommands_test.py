#!/usr/bin/env python
#
# Copyright (C) 2015 ycmd contributors.
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

from webtest import TestApp, AppError
from nose.tools import eq_, ok_
from ... import handlers
from .cs_handlers_test import Cs_Handlers_test
import re
import os.path


class Cs_Subcommands_test( Cs_Handlers_test ):

  def GoTo_Basic_test( self ):
    filepath = self._PathToTestFile( 'testy', 'GotoTestCase.cs' )
    contents = open( filepath ).read()
    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'cs',
                                     contents = contents,
                                     event_name = 'FileReadyToParse' )

    self._app.post_json( '/event_notification', event_data )
    self._WaitUntilOmniSharpServerReady( filepath )

    goto_data = self._BuildRequest( completer_target = 'filetype_default',
                                    command_arguments = [ 'GoTo' ],
                                    line_num = 9,
                                    column_num = 15,
                                    contents = contents,
                                    filetype = 'cs',
                                    filepath = filepath )

    eq_( {
      'filepath': self._PathToTestFile( 'testy', 'Program.cs' ),
      'line_num': 7,
      'column_num': 3
    }, self._app.post_json( '/run_completer_command', goto_data ).json )

    self._StopOmniSharpServer( filepath )


  def GoToImplementation_Basic_test( self ):
    filepath = self._PathToTestFile( 'testy', 'GotoTestCase.cs' )
    contents = open( filepath ).read()
    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'cs',
                                     contents = contents,
                                     event_name = 'FileReadyToParse' )

    self._app.post_json( '/event_notification', event_data )
    self._WaitUntilOmniSharpServerReady( filepath )

    goto_data = self._BuildRequest(
      completer_target = 'filetype_default',
      command_arguments = [ 'GoToImplementation' ],
      line_num = 13,
      column_num = 13,
      contents = contents,
      filetype = 'cs',
      filepath = filepath
    )

    eq_( {
      'filepath': self._PathToTestFile( 'testy', 'GotoTestCase.cs' ),
      'line_num': 30,
      'column_num': 3
    }, self._app.post_json( '/run_completer_command', goto_data ).json )

    self._StopOmniSharpServer( filepath )


  def GoToImplementation_NoImplementation_test( self ):
    filepath = self._PathToTestFile( 'testy', 'GotoTestCase.cs' )
    contents = open( filepath ).read()
    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'cs',
                                     contents = contents,
                                     event_name = 'FileReadyToParse' )

    self._app.post_json( '/event_notification', event_data )
    self._WaitUntilOmniSharpServerReady( filepath )

    goto_data = self._BuildRequest(
      completer_target = 'filetype_default',
      command_arguments = [ 'GoToImplementation' ],
      line_num = 17,
      column_num = 13,
      contents = contents,
      filetype = 'cs',
      filepath = filepath
    )

    try:
      self._app.post_json( '/run_completer_command', goto_data ).json
      raise Exception("Expected a 'No implementations found' error")
    except AppError as e:
      if 'No implementations found' in str(e):
        pass
      else:
        raise
    finally:
      self._StopOmniSharpServer( filepath )


  def CsCompleter_InvalidLocation_test( self ):
    filepath = self._PathToTestFile( 'testy', 'GotoTestCase.cs' )
    contents = open( filepath ).read()
    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'cs',
                                     contents = contents,
                                     event_name = 'FileReadyToParse' )

    self._app.post_json( '/event_notification', event_data )
    self._WaitUntilOmniSharpServerReady( filepath )

    goto_data = self._BuildRequest(
      completer_target = 'filetype_default',
      command_arguments = [ 'GoToImplementation' ],
      line_num = 2,
      column_num = 1,
      contents = contents,
      filetype = 'cs',
      filepath = filepath
    )

    try:
      self._app.post_json( '/run_completer_command', goto_data ).json
      raise Exception( 'Expected a "Can\\\'t jump to implementation" error' )
    except AppError as e:
      if 'Can\\\'t jump to implementation' in str(e):
        pass
      else:
        raise
    finally:
      self._StopOmniSharpServer( filepath )


  def GoToImplementationElseDeclaration_NoImplementation_test( self ):
    filepath = self._PathToTestFile( 'testy', 'GotoTestCase.cs' )
    contents = open( filepath ).read()
    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'cs',
                                     contents = contents,
                                     event_name = 'FileReadyToParse' )

    self._app.post_json( '/event_notification', event_data )
    self._WaitUntilOmniSharpServerReady( filepath )

    goto_data = self._BuildRequest(
      completer_target = 'filetype_default',
      command_arguments = [ 'GoToImplementationElseDeclaration' ],
      line_num = 17,
      column_num = 13,
      contents = contents,
      filetype = 'cs',
      filepath = filepath
    )

    eq_( {
      'filepath': self._PathToTestFile( 'testy', 'GotoTestCase.cs' ),
      'line_num': 35,
      'column_num': 3
    }, self._app.post_json( '/run_completer_command', goto_data ).json )

    self._StopOmniSharpServer( filepath )


  def GoToImplementationElseDeclaration_SingleImplementation_test( self ):
    filepath = self._PathToTestFile( 'testy', 'GotoTestCase.cs' )
    contents = open( filepath ).read()
    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'cs',
                                     contents = contents,
                                     event_name = 'FileReadyToParse' )

    self._app.post_json( '/event_notification', event_data )
    self._WaitUntilOmniSharpServerReady( filepath )

    goto_data = self._BuildRequest(
      completer_target = 'filetype_default',
      command_arguments = [ 'GoToImplementationElseDeclaration' ],
      line_num = 13,
      column_num = 13,
      contents = contents,
      filetype = 'cs',
      filepath = filepath
    )

    eq_( {
      'filepath': self._PathToTestFile( 'testy', 'GotoTestCase.cs' ),
      'line_num': 30,
      'column_num': 3
    }, self._app.post_json( '/run_completer_command', goto_data ).json )

    self._StopOmniSharpServer( filepath )


  def GoToImplementationElseDeclaration_MultipleImplementations_test( self ):
    filepath = self._PathToTestFile( 'testy', 'GotoTestCase.cs' )
    contents = open( filepath ).read()
    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'cs',
                                     contents = contents,
                                     event_name = 'FileReadyToParse' )

    self._app.post_json( '/event_notification', event_data )
    self._WaitUntilOmniSharpServerReady( filepath )

    goto_data = self._BuildRequest(
      completer_target = 'filetype_default',
      command_arguments = [ 'GoToImplementationElseDeclaration' ],
      line_num = 21,
      column_num = 13,
      contents = contents,
      filetype = 'cs',
      filepath = filepath
    )

    eq_( [ {
      'filepath': self._PathToTestFile( 'testy', 'GotoTestCase.cs' ),
      'line_num': 43,
      'column_num': 3
    }, {
      'filepath': self._PathToTestFile( 'testy', 'GotoTestCase.cs' ),
      'line_num': 48,
      'column_num': 3
    } ], self._app.post_json( '/run_completer_command', goto_data ).json )

    self._StopOmniSharpServer( filepath )


  def GetType_EmptyMessage_test( self ):
    filepath = self._PathToTestFile( 'testy', 'GetTypeTestCase.cs' )
    contents = open( filepath ).read()
    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'cs',
                                     contents = contents,
                                     event_name = 'FileReadyToParse' )

    self._app.post_json( '/event_notification', event_data )
    self._WaitUntilOmniSharpServerReady( filepath )

    gettype_data = self._BuildRequest( completer_target = 'filetype_default',
                                       command_arguments = [ 'GetType' ],
                                       line_num = 1,
                                       column_num = 1,
                                       contents = contents,
                                       filetype = 'cs',
                                       filepath = filepath )

    eq_( {
      u'message': u""
    }, self._app.post_json( '/run_completer_command', gettype_data ).json )

    self._StopOmniSharpServer( filepath )


  def GetType_VariableDeclaration_test( self ):
    filepath = self._PathToTestFile( 'testy', 'GetTypeTestCase.cs' )
    contents = open( filepath ).read()
    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'cs',
                                     contents = contents,
                                     event_name = 'FileReadyToParse' )

    self._app.post_json( '/event_notification', event_data )
    self._WaitUntilOmniSharpServerReady( filepath )

    gettype_data = self._BuildRequest( completer_target = 'filetype_default',
                                       command_arguments = [ 'GetType' ],
                                       line_num = 4,
                                       column_num = 5,
                                       contents = contents,
                                       filetype = 'cs',
                                       filepath = filepath )

    eq_( {
      u'message': u"string"
    }, self._app.post_json( '/run_completer_command', gettype_data ).json )

    self._StopOmniSharpServer( filepath )


  def GetType_VariableUsage_test( self ):
    filepath = self._PathToTestFile( 'testy', 'GetTypeTestCase.cs' )
    contents = open( filepath ).read()
    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'cs',
                                     contents = contents,
                                     event_name = 'FileReadyToParse' )

    self._app.post_json( '/event_notification', event_data )
    self._WaitUntilOmniSharpServerReady( filepath )

    gettype_data = self._BuildRequest( completer_target = 'filetype_default',
                                       command_arguments = [ 'GetType' ],
                                       line_num = 5,
                                       column_num = 5,
                                       contents = contents,
                                       filetype = 'cs',
                                       filepath = filepath )

    eq_( {
      u'message': u"string str"
    }, self._app.post_json( '/run_completer_command', gettype_data ).json )

    self._StopOmniSharpServer( filepath )


  def GetType_Constant_test( self ):
    filepath = self._PathToTestFile( 'testy', 'GetTypeTestCase.cs' )
    contents = open( filepath ).read()
    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'cs',
                                     contents = contents,
                                     event_name = 'FileReadyToParse' )

    self._app.post_json( '/event_notification', event_data )
    self._WaitUntilOmniSharpServerReady( filepath )

    gettype_data = self._BuildRequest( completer_target = 'filetype_default',
                                       command_arguments = [ 'GetType' ],
                                       line_num = 4,
                                       column_num = 14,
                                       contents = contents,
                                       filetype = 'cs',
                                       filepath = filepath )

    eq_( {
      u'message': u"System.String"
    }, self._app.post_json( '/run_completer_command', gettype_data ).json )

    self._StopOmniSharpServer( filepath )


  def GetType_DocsIgnored_test( self ):
    filepath = self._PathToTestFile( 'testy', 'GetTypeTestCase.cs' )
    contents = open( filepath ).read()
    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'cs',
                                     contents = contents,
                                     event_name = 'FileReadyToParse' )

    self._app.post_json( '/event_notification', event_data )
    self._WaitUntilOmniSharpServerReady( filepath )

    gettype_data = self._BuildRequest( completer_target = 'filetype_default',
                                       command_arguments = [ 'GetType' ],
                                       line_num = 9,
                                       column_num = 34,
                                       contents = contents,
                                       filetype = 'cs',
                                       filepath = filepath )

    eq_( {
      u'message': u"int GetTypeTestCase.an_int_with_docs;",
    }, self._app.post_json( '/run_completer_command', gettype_data ).json )

    self._StopOmniSharpServer( filepath )


  def GetDoc_Variable_test( self ):
    filepath = self._PathToTestFile( 'testy', 'GetDocTestCase.cs' )
    contents = open( filepath ).read()
    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'cs',
                                     contents = contents,
                                     event_name = 'FileReadyToParse' )

    self._app.post_json( '/event_notification', event_data )
    self._WaitUntilOmniSharpServerReady( filepath )

    getdoc_data = self._BuildRequest( completer_target = 'filetype_default',
                                      command_arguments = [ 'GetDoc' ],
                                      line_num = 13,
                                      column_num = 28,
                                      contents = contents,
                                      filetype = 'cs',
                                      filepath = filepath )

    eq_( {
      'detailed_info': 'int GetDocTestCase.an_int;\n'
                       'an integer, or something',
    }, self._app.post_json( '/run_completer_command', getdoc_data ).json )

    self._StopOmniSharpServer( filepath )


  def GetDoc_Function_test( self ):
    filepath = self._PathToTestFile( 'testy', 'GetDocTestCase.cs' )
    contents = open( filepath ).read()
    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'cs',
                                     contents = contents,
                                     event_name = 'FileReadyToParse' )

    self._app.post_json( '/event_notification', event_data )
    self._WaitUntilOmniSharpServerReady( filepath )

    getdoc_data = self._BuildRequest( completer_target = 'filetype_default',
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
    }, self._app.post_json( '/run_completer_command', getdoc_data ).json )

    self._StopOmniSharpServer( filepath )


  def _RunFixIt( self, line, column, expected_result ):
    filepath = self._PathToTestFile( 'testy', 'FixItTestCase.cs' )
    contents = open( filepath ).read()
    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'cs',
                                     contents = contents,
                                     event_name = 'FileReadyToParse' )

    self._app.post_json( '/event_notification', event_data )
    self._WaitUntilOmniSharpServerReady( filepath )

    fixit_data = self._BuildRequest( completer_target = 'filetype_default',
                                     command_arguments = [ 'FixIt' ],
                                     line_num = line,
                                     column_num = column,
                                     contents = contents,
                                     filetype = 'cs',
                                     filepath = filepath )

    eq_( expected_result,
         self._app.post_json( '/run_completer_command', fixit_data ).json )

    self._StopOmniSharpServer( filepath )


  def FixIt_RemoveSingleLine_test( self ):
    filepath = self._PathToTestFile( 'testy', 'FixItTestCase.cs' )
    self._RunFixIt( 11, 1, {
      u'fixits': [
        {
          u'location': {
            u'line_num': 11,
            u'column_num': 1,
            u'filepath': filepath
          },
          u'chunks': [
            {
              u'replacement_text': '',
              u'range': {
                u'start': {
                  u'line_num': 10,
                  u'column_num': 20,
                  u'filepath': filepath
                },
                u'end': {
                  u'line_num': 11,
                  u'column_num': 30,
                  u'filepath': filepath
                },
              }
            }
          ]
        }
      ]
    } )


  def FixIt_MultipleLines_test( self ):
    filepath = self._PathToTestFile( 'testy', 'FixItTestCase.cs' )
    self._RunFixIt( 19, 1, {
      u'fixits': [
        {
          u'location': {
            u'line_num': 19,
            u'column_num': 1,
            u'filepath': filepath
          },
          u'chunks': [
            {
              u'replacement_text': "return On",
              u'range': {
                u'start': {
                  u'line_num': 20,
                  u'column_num': 13,
                  u'filepath': filepath
                },
                u'end': {
                  u'line_num': 21,
                  u'column_num': 35,
                  u'filepath': filepath
                },
              }
            }
          ]
        }
      ]
    } )


  def FixIt_SpanFileEdge_test( self ):
    filepath = self._PathToTestFile( 'testy', 'FixItTestCase.cs' )
    self._RunFixIt( 1, 1, {
      u'fixits': [
        {
          u'location': {
            u'line_num': 1,
            u'column_num': 1,
            u'filepath': filepath
          },
          u'chunks': [
            {
              u'replacement_text': 'System',
              u'range': {
                u'start': {
                  u'line_num': 1,
                  u'column_num': 7,
                  u'filepath': filepath
                },
                u'end': {
                  u'line_num': 3,
                  u'column_num': 18,
                  u'filepath': filepath
                },
              }
            }
          ]
        }
      ]
    } )


  def FixIt_AddTextInLine_test( self ):
    filepath = self._PathToTestFile( 'testy', 'FixItTestCase.cs' )
    self._RunFixIt( 9, 1, {
      u'fixits': [
        {
          u'location': {
            u'line_num': 9,
            u'column_num': 1,
            u'filepath': filepath
          },
          u'chunks': [
            {
              u'replacement_text': ', StringComparison.Ordinal',
              u'range': {
                u'start': {
                  u'line_num': 9,
                  u'column_num': 29,
                  u'filepath': filepath
                },
                u'end': {
                  u'line_num': 9,
                  u'column_num': 29,
                  u'filepath': filepath
                },
              }
            }
          ]
        }
      ]
    } )


  def FixIt_ReplaceTextInLine_test( self ):
    filepath = self._PathToTestFile( 'testy', 'FixItTestCase.cs' )
    self._RunFixIt( 10, 1, {
      u'fixits': [
        {
          u'location': {
            u'line_num': 10,
            u'column_num': 1,
            u'filepath': filepath
          },
          u'chunks': [
            {
              u'replacement_text': 'const int',
              u'range': {
                u'start': {
                  u'line_num': 10,
                  u'column_num': 13,
                  u'filepath': filepath
                },
                u'end': {
                  u'line_num': 10,
                  u'column_num': 16,
                  u'filepath': filepath
                },
              }
            }
          ]
        }
      ]
    } )


  def StopServer_NoErrorIfNotStarted_test( self ):
    filepath = self._PathToTestFile( 'testy', 'GotoTestCase.cs' )
    self._StopOmniSharpServer( filepath )
    # Success = no raise


  def StopServer_KeepLogFiles_test( self ):
    yield self._StopServer_KeepLogFiles, True
    yield self._StopServer_KeepLogFiles, False


  def _StopServer_KeepLogFiles( self, keeping_log_files ):
    self._ChangeSpecificOptions(
      { 'server_keep_logfiles': keeping_log_files } )
    self._app = TestApp( handlers.app )
    self._app.post_json(
      '/ignore_extra_conf_file',
      { 'filepath': self._PathToTestFile( '.ycm_extra_conf.py' ) } )
    filepath = self._PathToTestFile( 'testy', 'GotoTestCase.cs' )
    contents = open( filepath ).read()
    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'cs',
                                     contents = contents,
                                     event_name = 'FileReadyToParse' )

    self._app.post_json( '/event_notification', event_data )
    self._WaitUntilOmniSharpServerReady( filepath )

    event_data = self._BuildRequest( filetype = 'cs', filepath = filepath )

    debuginfo = self._app.post_json( '/debug_info', event_data ).json

    log_files_match = re.search( "^OmniSharp logfiles:\n(.*)\n(.*)",
                                 debuginfo,
                                 re.MULTILINE )
    stdout_logfiles_location = log_files_match.group( 1 )
    stderr_logfiles_location = log_files_match.group( 2 )

    try:
      ok_( os.path.exists(stdout_logfiles_location ),
           "Logfile should exist at {0}".format( stdout_logfiles_location ) )
      ok_( os.path.exists( stderr_logfiles_location ),
           "Logfile should exist at {0}".format( stderr_logfiles_location ) )
    finally:
      self._StopOmniSharpServer( filepath )

    if keeping_log_files:
      ok_( os.path.exists( stdout_logfiles_location ),
           "Logfile should still exist at "
           "{0}".format( stdout_logfiles_location ) )
      ok_( os.path.exists( stderr_logfiles_location ),
           "Logfile should still exist at "
           "{0}".format( stderr_logfiles_location ) )
    else:
      ok_( not os.path.exists( stdout_logfiles_location ),
           "Logfile should no longer exist at "
           "{0}".format( stdout_logfiles_location ) )
      ok_( not os.path.exists( stderr_logfiles_location ),
           "Logfile should no longer exist at "
           "{0}".format( stderr_logfiles_location ) )
