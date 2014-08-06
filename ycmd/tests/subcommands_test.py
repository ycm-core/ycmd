#!/usr/bin/env python
#
# Copyright (C) 2013  Google Inc.
#
# This file is part of YouCompleteMe.
#
# YouCompleteMe is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# YouCompleteMe is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with YouCompleteMe.  If not, see <http://www.gnu.org/licenses/>.

from ..server_utils import SetUpPythonPath
SetUpPythonPath()
from .test_utils import ( Setup, BuildRequest, PathToTestFile, StopOmniSharpServer,
                          WaitUntilOmniSharpServerReady, ChangeSpecificOptions )
from webtest import TestApp, AppError
from nose.tools import eq_, with_setup
from .. import handlers
import bottle
import re
import os.path

bottle.debug( True )


@with_setup( Setup )
def RunCompleterCommand_GoTo_Jedi_ZeroBasedLineAndColumn_test():
  app = TestApp( handlers.app )
  contents = """
def foo():
  pass

foo()
"""

  goto_data = BuildRequest( completer_target = 'filetype_default',
                            command_arguments = ['GoToDefinition'],
                            line_num = 5,
                            contents = contents,
                            filetype = 'python',
                            filepath = '/foo.py' )

  eq_( {
         'filepath': '/foo.py',
         'line_num': 2,
         'column_num': 5
       },
       app.post_json( '/run_completer_command', goto_data ).json )


@with_setup( Setup )
def RunCompleterCommand_GoTo_Clang_ZeroBasedLineAndColumn_test():
  app = TestApp( handlers.app )
  contents = """
struct Foo {
  int x;
  int y;
  char c;
};

int main()
{
  Foo foo;
  return 0;
}
"""

  goto_data = BuildRequest( completer_target = 'filetype_default',
                            command_arguments = ['GoToDefinition'],
                            compilation_flags = ['-x', 'c++'],
                            line_num = 10,
                            column_num = 3,
                            contents = contents,
                            filetype = 'cpp' )

  eq_( {
        'filepath': '/foo',
        'line_num': 2,
        'column_num': 8
      },
      app.post_json( '/run_completer_command', goto_data ).json )


@with_setup( Setup )
def RunCompleterCommand_GoTo_CsCompleter_Works_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy/GotoTestCase.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app )

  goto_data = BuildRequest( completer_target = 'filetype_default',
                            command_arguments = ['GoTo'],
                            line_num = 9,
                            column_num = 15,
                            contents = contents,
                            filetype = 'cs',
                            filepath = filepath )

  eq_( {
        'filepath': PathToTestFile( 'testy/Program.cs' ),
        'line_num': 7,
        'column_num': 3
      },
      app.post_json( '/run_completer_command', goto_data ).json )

  StopOmniSharpServer( app )


@with_setup( Setup )
def RunCompleterCommand_GoToImplementation_CsCompleter_Works_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy/GotoTestCase.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app )

  goto_data = BuildRequest( completer_target = 'filetype_default',
                            command_arguments = ['GoToImplementation'],
                            line_num = 13,
                            column_num = 13,
                            contents = contents,
                            filetype = 'cs',
                            filepath = filepath )

  eq_( {
        'filepath': PathToTestFile( 'testy/GotoTestCase.cs' ),
        'line_num': 30,
        'column_num': 3
      },
      app.post_json( '/run_completer_command', goto_data ).json )

  StopOmniSharpServer( app )


@with_setup( Setup )
def RunCompleterCommand_GoToImplementation_CsCompleter_NoImplementation_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy/GotoTestCase.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app )

  goto_data = BuildRequest( completer_target = 'filetype_default',
                            command_arguments = ['GoToImplementation'],
                            line_num = 17,
                            column_num = 13,
                            contents = contents,
                            filetype = 'cs',
                            filepath = filepath )

  try:
    app.post_json( '/run_completer_command', goto_data ).json
    raise Exception("Expected a 'No implementations found' error")
  except AppError as e:
    if 'No implementations found' in str(e):
      pass
    else:
      raise
  finally:
    StopOmniSharpServer( app )


@with_setup( Setup )
def RunCompleterCommand_GoToImplementation_CsCompleter_InvalidLocation_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy/GotoTestCase.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app )

  goto_data = BuildRequest( completer_target = 'filetype_default',
                            command_arguments = ['GoToImplementation'],
                            line_num = 2,
                            column_num = 1,
                            contents = contents,
                            filetype = 'cs',
                            filepath = filepath )

  try:
    app.post_json( '/run_completer_command', goto_data ).json
    raise Exception('Expected a "Can\\\'t jump to implementation" error')
  except AppError as e:
    if 'Can\\\'t jump to implementation' in str(e):
      pass
    else:
      raise
  finally:
    StopOmniSharpServer( app )


@with_setup( Setup )
def RunCompleterCommand_GoToImplementationElseDeclaration_CsCompleter_NoImplementation_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy/GotoTestCase.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app )

  goto_data = BuildRequest( completer_target = 'filetype_default',
                            command_arguments = ['GoToImplementationElseDeclaration'],
                            line_num = 17,
                            column_num = 13,
                            contents = contents,
                            filetype = 'cs',
                            filepath = filepath )

  eq_( {
        'filepath': PathToTestFile( 'testy/GotoTestCase.cs' ),
        'line_num': 35,
        'column_num': 3
      },
      app.post_json( '/run_completer_command', goto_data ).json )

  StopOmniSharpServer( app )


@with_setup( Setup )
def RunCompleterCommand_GoToImplementationElseDeclaration_CsCompleter_SingleImplementation_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy/GotoTestCase.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app )

  goto_data = BuildRequest( completer_target = 'filetype_default',
                            command_arguments = ['GoToImplementationElseDeclaration'],
                            line_num = 13,
                            column_num = 13,
                            contents = contents,
                            filetype = 'cs',
                            filepath = filepath )

  eq_( {
        'filepath': PathToTestFile( 'testy/GotoTestCase.cs' ),
        'line_num': 30,
        'column_num': 3
      },
      app.post_json( '/run_completer_command', goto_data ).json )

  StopOmniSharpServer( app )


@with_setup( Setup )
def RunCompleterCommand_GoToImplementationElseDeclaration_CsCompleter_MultipleImplementations_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy/GotoTestCase.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app )

  goto_data = BuildRequest( completer_target = 'filetype_default',
                            command_arguments = ['GoToImplementationElseDeclaration'],
                            line_num = 21,
                            column_num = 13,
                            contents = contents,
                            filetype = 'cs',
                            filepath = filepath )

  eq_( [{
        'filepath': PathToTestFile( 'testy/GotoTestCase.cs' ),
        'line_num': 43,
        'column_num': 3
      }, {
        'filepath': PathToTestFile( 'testy/GotoTestCase.cs' ),
        'line_num': 48,
        'column_num': 3
      }],
      app.post_json( '/run_completer_command', goto_data ).json )

  StopOmniSharpServer( app )


@with_setup( Setup )
def RunCompleterCommand_StopServer_CsCompleter_KeepLogFiles_test():
  yield  _RunCompleterCommand_StopServer_CsCompleter_KeepLogFiles, True
  yield  _RunCompleterCommand_StopServer_CsCompleter_KeepLogFiles, False


def _RunCompleterCommand_StopServer_CsCompleter_KeepLogFiles( keeping_log_files ):
  ChangeSpecificOptions( { 'server_keep_logfiles': keeping_log_files } )
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy/GotoTestCase.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app )

  event_data = BuildRequest( filetype = 'cs' )

  debuginfo = app.post_json( '/debug_info', event_data ).json

  log_files_match = re.search( "^OmniSharp logfiles:\n(.*)\n(.*)", debuginfo, re.MULTILINE )
  stdout_logfiles_location = log_files_match.group( 1 )
  stderr_logfiles_location = log_files_match.group( 2 )

  try:
    assert os.path.exists( stdout_logfiles_location ), "Logfile should exist at " + stdout_logfiles_location
    assert os.path.exists( stderr_logfiles_location ), "Logfile should exist at " + stderr_logfiles_location
  finally:
    StopOmniSharpServer( app )

  if ( keeping_log_files ):
    assert os.path.exists( stdout_logfiles_location ), "Logfile should still exist at " + stdout_logfiles_location
    assert os.path.exists( stderr_logfiles_location ), "Logfile should still exist at " + stderr_logfiles_location
  else:
    assert not os.path.exists( stdout_logfiles_location ), "Logfile should no longer exist at " + stdout_logfiles_location
    assert not os.path.exists( stderr_logfiles_location ), "Logfile should no longer exist at " + stderr_logfiles_location


@with_setup( Setup )
def DefinedSubcommands_Works_test():
  app = TestApp( handlers.app )
  subcommands_data = BuildRequest( completer_target = 'python' )

  eq_( [ 'GoToDefinition',
         'GoToDeclaration',
         'GoTo' ],
       app.post_json( '/defined_subcommands', subcommands_data ).json )


@with_setup( Setup )
def DefinedSubcommands_WorksWhenNoExplicitCompleterTargetSpecified_test():
  app = TestApp( handlers.app )
  subcommands_data = BuildRequest( filetype = 'python' )

  eq_( [ 'GoToDefinition',
         'GoToDeclaration',
         'GoTo' ],
       app.post_json( '/defined_subcommands', subcommands_data ).json )

