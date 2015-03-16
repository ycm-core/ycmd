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
         'column_num': 1
       },
       app.post_json( '/run_completer_command', goto_data ).json )


@with_setup( Setup )
def RunCompleterCommand_GoTo_Clang_ZeroBasedLineAndColumn_test():
  app = TestApp( handlers.app )
  contents = open(
        PathToTestFile( 'GoTo_Clang_ZeroBasedLineAndColumn_test.cc' ) ).read()

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

def _RunCompleterCommand_GoTo_all_Clang(filename, command, test):
  contents = open( PathToTestFile( filename ) ).read()
  app = TestApp( handlers.app )
  common_request = {
    'completer_target'  : 'filetype_default',
    'command_arguments' : command,
    'compilation_flags' : ['-x',
                           'c++',
                           '-std=c++11'],
    'line_num'          : 10,
    'column_num'        : 3,
    'contents'          : contents,
    'filetype'          : 'cpp'
  }
  common_response = {
    'filepath'  : '/foo',
  }

  request = common_request
  request.update({
      'line_num'  : test['request'][0],
      'column_num': test['request'][1],
  })
  response = common_response
  response.update({
      'line_num'  : test['response'][0],
      'column_num': test['response'][1],
  })

  goto_data = BuildRequest( **request )

  eq_( response,
       app.post_json( '/run_completer_command', goto_data ).json )

@with_setup( Setup )
def RunCompleterCommand_GoTo_all_Clang_test():
  # GoToDeclaration
  #
  # the semantics of this seem the wrong way round to me. GoToDeclaration should
  # go to where a method is declared, not where it is defined.
  #
  tests = [
    # Local::x -> declaration of x
    { 'request': [24,25], 'response': [5 ,9 ] },
    # Local::in_line -> declaration of Local::inline
    { 'request': [25,29], 'response': [7 ,10] },
    # Local -> declaration of Local
    { 'request': [25,19], 'response': [3 ,11] },
    # sic: Local::out_of_line -> definition of Local::out_of_line
    { 'request': [26,30], 'response': [15,13 ] }, # sic
    # sic: GoToDeclaration on definition of out_of_line moves to itself
    { 'request': [15,13], 'response': [15,13] }, # sic
    # main -> definition of main (not declaration)
    { 'request': [22,7 ], 'response': [22,5] }, # sic
  ]

  for test in tests:
    yield _RunCompleterCommand_GoTo_all_Clang, \
          'GoTo_all_Clang_test.cc',            \
          ['GoToDeclaration'],                 \
          test

  # GoToDefinition - identical to GoToDeclaration
  #
  # the semantics of this seem the wrong way round to me. GoToDefinition should
  # go to where a method is implemented, not where it is declared.
  #
  tests = [
    # Local::x -> declaration of x
    { 'request': [24,25], 'response': [5 ,9 ] },
    # Local::in_line -> declaration of Local::inline
    { 'request': [25,29], 'response': [7 ,10] },
    # Local -> declaration of Local
    { 'request': [25,19], 'response': [3 ,11] },
    # sic: Local::out_of_line -> definition of Local::out_of_line
    { 'request': [26,30], 'response': [15,13 ] }, # sic
    # sic: GoToDeclaration on definition of out_of_line moves to itself
    { 'request': [15,13], 'response': [15,13] }, # sic
    # main -> definition of main (not declaration)
    { 'request': [22,7 ], 'response': [22,5] }, # sic
  ]

  for test in tests:
    yield _RunCompleterCommand_GoTo_all_Clang, \
          'GoTo_all_Clang_test.cc',            \
          ['GoToDefinition'],                  \
          test

  # GoTo - identical to GoToDeclaration
  #
  # the semantics of this seem the wrong way round to me. GoToDefinition should
  # go to where a method is implemented, not where it is declared.
  #
  tests = [
    # Local::x -> declaration of x
    { 'request': [24,25], 'response': [5 ,9 ] },
    # Local::in_line -> declaration of Local::inline
    { 'request': [25,29], 'response': [7 ,10] },
    # Local -> declaration of Local
    { 'request': [25,19], 'response': [3 ,11] },
    # sic: Local::out_of_line -> definition of Local::out_of_line
    { 'request': [26,30], 'response': [15,13 ] }, # sic
    # sic: GoToDeclaration on definition of out_of_line moves to itself
    { 'request': [15,13], 'response': [15,13] }, # sic
    # main -> definition of main (not declaration)
    { 'request': [22,7 ], 'response': [22,5] }, # sic
  ]

  for test in tests:
    yield _RunCompleterCommand_GoTo_all_Clang, \
          'GoTo_all_Clang_test.cc',            \
          ['GoTo'],                            \
          test

  # GoToImprecise - identical to GoToDeclaration
  #
  # the semantics of this seem the wrong way round to me. GoToDefinition should
  # go to where a method is implemented, not where it is declared.
  #
  tests = [
    # Local::x -> declaration of x
    { 'request': [24,25], 'response': [5 ,9 ] },
    # Local::in_line -> declaration of Local::inline
    { 'request': [25,29], 'response': [7 ,10] },
    # Local -> declaration of Local
    { 'request': [25,19], 'response': [3 ,11] },
    # sic: Local::out_of_line -> definition of Local::out_of_line
    { 'request': [26,30], 'response': [15,13 ] }, # sic
    # sic: GoToDeclaration on definition of out_of_line moves to itself
    { 'request': [15,13], 'response': [15,13] }, # sic
    # main -> definition of main (not declaration)
    { 'request': [22,7 ], 'response': [22,5] }, # sic
  ]

  for test in tests:
    yield _RunCompleterCommand_GoTo_all_Clang, \
          'GoTo_all_Clang_test.cc',            \
          ['GoToImprecise'],                   \
          test

def _RunCompleterCommand_Message_Clang(filename, test, command):
  contents = open( PathToTestFile( filename ) ).read()
  app = TestApp( handlers.app )

  common_args = {
    'completer_target'  : 'filetype_default',
    'command_arguments' : command,
    'compilation_flags' : ['-x',
                           'c++',
                           '-std=c++11'],
    'line_num'          : 10,
    'column_num'        : 3,
    'contents'          : contents,
    'filetype'          : 'cpp'
  }

  args = test[0]
  expected = test[1];

  request = common_args
  request.update( args )

  request_data = BuildRequest( **request )

  eq_( {'message': expected},
        app.post_json( '/run_completer_command', request_data ).json )


@with_setup( Setup )
def RunCompleterCommand_GetType_Clang_test():
  tests = [
  # basic pod types
    [{'line_num' : 12, 'column_num': 3} , 'Foo'],
    [{'line_num' : 1,  'column_num': 1} , 'Internal error: cursor not valid'],
    [{'line_num' : 4,  'column_num': 2} , 'Foo'],
    [{'line_num' : 4,  'column_num': 8} , 'Foo'],
    [{'line_num' : 4,  'column_num': 9} , 'Foo'],
    [{'line_num' : 4,  'column_num': 10} , 'Foo'],
    [{'line_num' : 5,  'column_num': 3} , 'int'],
    [{'line_num' : 5,  'column_num': 7} , 'int'],
    [{'line_num' : 7,  'column_num': 7} , 'char'],

  # function
    [{'line_num' : 10, 'column_num': 2} , 'int ()'],
    [{'line_num' : 10, 'column_num': 6} , 'int ()'],

  # std::string and canonical type
    # on std:: (Unknown)
    [{'line_num' : 13, 'column_num': 3} , 'Unknown type'], # sic
    # on string (string)
    [{'line_num' : 13, 'column_num': 8} ,
                                  'string => std::basic_string<char>'], # sic
    # on a (std::string)
    [{'line_num' : 13, 'column_num': 15} ,
                                  'std::string => std::basic_string<char>'],
    [{'line_num' : 14, 'column_num': 16} ,
                                  'std::string => std::basic_string<char>'],

  # cursor on decl for refs & pointers
    [{'line_num' : 27, 'column_num': 3} ,  'Foo'],
    [{'line_num' : 27, 'column_num': 11} , 'Foo &'],
    [{'line_num' : 27, 'column_num': 15} , 'Foo'],
    [{'line_num' : 28, 'column_num': 3} ,  'Foo'],
    [{'line_num' : 28, 'column_num': 11} , 'Foo *'],
    [{'line_num' : 28, 'column_num': 18} , 'Foo'],
    [{'line_num' : 30, 'column_num': 3} ,  'const Foo &'],
    [{'line_num' : 30, 'column_num': 16} , 'const Foo &'],
    [{'line_num' : 31, 'column_num': 3} ,  'const Foo *'],
    [{'line_num' : 31, 'column_num': 16} , 'const Foo *'],
  # cursor on usage
    [{'line_num' : 33, 'column_num': 17} , 'const Foo'],
    [{'line_num' : 33, 'column_num': 21} , 'const int'],
    [{'line_num' : 34, 'column_num': 17} , 'const Foo *'],
    [{'line_num' : 34, 'column_num': 22} , 'const int'],
    [{'line_num' : 35, 'column_num': 17} , 'Foo'],
    [{'line_num' : 35, 'column_num': 21} , 'int'],
    [{'line_num' : 36, 'column_num': 17} , 'Foo *'],
    [{'line_num' : 36, 'column_num': 22} , 'int'],

  # auto behaves strangely (bug in libclang)
    [{'line_num' : 16, 'column_num': 3} ,  'auto &'], # sic
    [{'line_num' : 16, 'column_num': 11} , 'auto &'], # sic
    [{'line_num' : 16, 'column_num': 18} , 'Foo'],
    [{'line_num' : 17, 'column_num': 3} ,  'auto *'], # sic
    [{'line_num' : 17, 'column_num': 11} , 'auto *'], # sic
    [{'line_num' : 17, 'column_num': 18} , 'Foo'],
    [{'line_num' : 19, 'column_num': 3} ,  'const auto &'], # sic
    [{'line_num' : 19, 'column_num': 16} , 'const auto &'], # sic
    [{'line_num' : 20, 'column_num': 3} ,  'const auto *'], # sic
    [{'line_num' : 20, 'column_num': 16} , 'const auto *'], # sic
  # auto sort of works in usage (but canonical types apparently differ)
    [{'line_num' : 22, 'column_num': 17} , 'const Foo => const Foo'], #sic
    [{'line_num' : 22, 'column_num': 23} , 'const int'],
    [{'line_num' : 23, 'column_num': 17} , 'const Foo * => const Foo *'], #sic
    [{'line_num' : 23, 'column_num': 24} , 'const int'],
    [{'line_num' : 24, 'column_num': 17} , 'Foo => Foo'], #sic
    [{'line_num' : 24, 'column_num': 22} , 'int'],
    [{'line_num' : 25, 'column_num': 17} , 'Foo * => Foo *'], #sic
    [{'line_num' : 25, 'column_num': 23} , 'int'],

  ]

  for test in tests:
    yield _RunCompleterCommand_Message_Clang, \
          'GetType_Clang_test.cc',            \
          test,                               \
          ['GetType']

@with_setup( Setup )
def RunCompleterCommand_GetParent_Clang_test():
  tests = [
    [{'line_num' : 1 ,  'column_num': 1 } , 'Internal error: cursor not valid'],
  # would be file name if we had one:
    [{'line_num' : 3 ,  'column_num': 8 } , '/foo'],

  # the reported scope does not include parents
    [{'line_num' : 4 ,  'column_num': 11} , 'A'],
    [{'line_num' : 5 ,  'column_num': 13} , 'B'],
    [{'line_num' : 6 ,  'column_num': 13} , 'B'],
    [{'line_num' : 10,  'column_num': 17} , 'do_z_inline()'],
    [{'line_num' : 16,  'column_num': 22} , 'do_anything(T &)'],
    [{'line_num' : 20,  'column_num': 9 } , 'A'],
    [{'line_num' : 21,  'column_num': 9 } , 'A'],
    [{'line_num' : 23,  'column_num': 12} , 'A'],
    [{'line_num' : 24,  'column_num': 5 } , 'do_Z_inline()'],
    [{'line_num' : 25,  'column_num': 12} , 'do_Z_inline()'],
    [{'line_num' : 29,  'column_num': 14} , 'A'],

    [{'line_num' : 35,  'column_num': 1 } , 'do_anything(T &)'],
    [{'line_num' : 40,  'column_num': 1 } , 'do_x()'],
    [{'line_num' : 45,  'column_num': 1 } , 'do_y()'],
    [{'line_num' : 50,  'column_num': 1 } , 'main()'],

  # lambdas report the name of the variable
    [{'line_num' : 50,  'column_num': 14} , 'l'],
    [{'line_num' : 51,  'column_num': 19} , 'l'],
    [{'line_num' : 52,  'column_num': 16} , 'main()'],

  ]

  for test in tests:
    yield _RunCompleterCommand_Message_Clang, \
          'GetParent_Clang_test.cc',          \
          test,                               \
          ['GetParent']

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

