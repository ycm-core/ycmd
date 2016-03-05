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

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()
from builtins import *  # noqa

from nose.tools import eq_, ok_
from webtest import AppError
import re
import os.path

from ycmd.tests.cs import ( IsolatedYcmd, PathToTestFile, SharedYcmd,
                            StopOmniSharpServer, WaitUntilOmniSharpServerReady,
                            WrapOmniSharpServer )
from ycmd.tests.test_utils import BuildRequest, UserOption
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
      raise Exception("Expected a 'No implementations found' error")
    except AppError as e:
      if 'No implementations found' in str(e):
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
      if 'Can\\\'t jump to implementation' in str(e):
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


def RunFixItTest( app, line, column, expected_result ):
  filepath = PathToTestFile( 'testy', 'FixItTestCase.cs' )
  with WrapOmniSharpServer( app, filepath ):
    contents = ReadFile( filepath )

    fixit_data = BuildRequest( completer_target = 'filetype_default',
                               command_arguments = [ 'FixIt' ],
                               line_num = line,
                               column_num = column,
                               contents = contents,
                               filetype = 'cs',
                               filepath = filepath )

    eq_( expected_result,
         app.post_json( '/run_completer_command', fixit_data ).json )


@SharedYcmd
def Subcommands_FixIt_RemoveSingleLine_test( app ):
  filepath = PathToTestFile( 'testy', 'FixItTestCase.cs' )
  RunFixItTest( app, 11, 1, {
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


@SharedYcmd
def Subcommands_FixIt_MultipleLines_test( app ):
  filepath = PathToTestFile( 'testy', 'FixItTestCase.cs' )
  RunFixItTest( app, 19, 1, {
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


@SharedYcmd
def Subcommands_FixIt_SpanFileEdge_test( app ):
  filepath = PathToTestFile( 'testy', 'FixItTestCase.cs' )
  RunFixItTest( app, 1, 1, {
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


@SharedYcmd
def Subcommands_FixIt_AddTextInLine_test( app ):
  filepath = PathToTestFile( 'testy', 'FixItTestCase.cs' )
  RunFixItTest( app, 9, 1, {
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


@SharedYcmd
def Subcommands_FixIt_ReplaceTextInLine_test( app ):
  filepath = PathToTestFile( 'testy', 'FixItTestCase.cs' )
  RunFixItTest( app, 10, 1, {
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


@IsolatedYcmd
def Subcommands_StopServer_NoErrorIfNotStarted_test( app ):
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  StopOmniSharpServer( app, filepath )
  # Success = no raise


@IsolatedYcmd
def StopServer_KeepLogFiles( app, keeping_log_files ):
  with UserOption( 'server_keep_logfiles', keeping_log_files ):
    filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
    contents = ReadFile( filepath )
    event_data = BuildRequest( filepath = filepath,
                               filetype = 'cs',
                               contents = contents,
                               event_name = 'FileReadyToParse' )

    app.post_json( '/event_notification', event_data )
    WaitUntilOmniSharpServerReady( app, filepath )

    event_data = BuildRequest( filetype = 'cs', filepath = filepath )

    debuginfo = app.post_json( '/debug_info', event_data ).json

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
      StopOmniSharpServer( app, filepath )

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


def Subcommands_StopServer_KeepLogFiles_test():
  yield StopServer_KeepLogFiles, True
  yield StopServer_KeepLogFiles, False
