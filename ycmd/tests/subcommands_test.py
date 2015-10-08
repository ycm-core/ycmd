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
from .test_utils import ( Setup,
                          BuildRequest,
                          PathToTestFile,
                          StopOmniSharpServer,
                          WaitUntilOmniSharpServerReady,
                          ChangeSpecificOptions,
                          ErrorMatcher )
from webtest import TestApp, AppError
from nose.tools import eq_, with_setup
from .. import handlers
import bottle
import re
import os.path
import httplib
from pprint import pprint

from hamcrest import ( assert_that, contains, has_entries, equal_to, raises, calling )

from ycmd.completers.cpp.clang_completer import NO_DOCUMENTATION_MESSAGE

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
         'filepath': os.path.abspath( '/foo.py' ),
         'line_num': 2,
         'column_num': 5
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
        'filepath': os.path.abspath( '/foo' ),
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
                           'c++'],
    'line_num'          : 10,
    'column_num'        : 3,
    'contents'          : contents,
    'filetype'          : 'cpp'
  }
  common_response = {
    'filepath'  : os.path.abspath( '/foo' ),
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


def _RunCompleterCommand_GoToInclude_Clang( command, test ):
  app = TestApp( handlers.app )
  app.post_json( '/load_extra_conf_file',
                 { 'filepath': PathToTestFile( 'test-include',
                                               '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'test-include', 'main.cpp' )
  goto_data = BuildRequest( filepath = filepath,
                            filetype = 'cpp',
                            contents = open( filepath ).read(),
                            command_arguments = [ command ],
                            line_num = test[ 'request' ][ 0 ],
                            column_num = test[ 'request' ][ 1 ] )

  response = {
    'filepath'   : PathToTestFile( 'test-include', test[ 'response' ] ),
    'line_num'   : 1,
    'column_num' : 1,
  }

  eq_( response,
       app.post_json( '/run_completer_command', goto_data ).json )


@with_setup( Setup )
def RunCompleterCommand_GoToInclude_Clang_test():
  tests = [
    { 'request': [ 1, 1 ], 'response': 'a.hpp' },
    { 'request': [ 2, 1 ], 'response': os.path.join( 'system', 'a.hpp' ) },
    { 'request': [ 3, 1 ], 'response': os.path.join( 'quote',  'b.hpp' ) },
    { 'request': [ 5, 1 ], 'response': os.path.join( 'system', 'c.hpp' ) },
    { 'request': [ 6, 1 ], 'response': os.path.join( 'system', 'c.hpp' ) },
  ]
  for test in tests:
    yield _RunCompleterCommand_GoToInclude_Clang, 'GoToInclude', test
    yield _RunCompleterCommand_GoToInclude_Clang, 'GoTo', test
    yield _RunCompleterCommand_GoToInclude_Clang, 'GoToImprecise', test


@with_setup( Setup )
def RunCompleterCommand_GoToInclude_Clang_Fail_test():
  test = { 'request': [ 4, 1 ], 'response': '' }
  assert_that(
    calling( _RunCompleterCommand_GoToInclude_Clang ).with_args( 'GoToInclude',
                                                                  test ),
    raises( AppError, 'Include file not found.' ) )
  assert_that(
    calling( _RunCompleterCommand_GoToInclude_Clang ).with_args( 'GoTo', test ),
    raises( AppError, 'Include file not found.' ) )
  assert_that(
    calling( _RunCompleterCommand_GoToInclude_Clang ).with_args(
                                                        'GoToImprecise', test ),
    raises( AppError, 'Include file not found.' ) )

  test = { 'request': [ 7, 1 ], 'response': '' }
  assert_that(
    calling( _RunCompleterCommand_GoToInclude_Clang ).with_args( 'GoToInclude',
                                                                  test ),
    raises( AppError, 'Not an include/import line.' ) )
  assert_that(
    calling( _RunCompleterCommand_GoToInclude_Clang ).with_args( 'GoTo', test ),
    raises( AppError, r'Can\\\'t jump to definition or declaration.' ) )
  assert_that(
    calling( _RunCompleterCommand_GoToInclude_Clang ).with_args(
                                                        'GoToImprecise', test ),
    raises( AppError, r'Can\\\'t jump to definition or declaration.' ) )


@with_setup( Setup )
def RunCompleterCommand_GoTo_all_Clang_test():
  # GoToDeclaration
  tests = [
    # Local::x -> declaration of x
    { 'request': [23, 21], 'response': [ 4,  9] },
    # Local::in_line -> declaration of Local::in_line
    { 'request': [24, 26], 'response': [ 6, 10] },
    # Local -> declaration of Local
    { 'request': [24, 16], 'response': [ 2, 11] },
    # Local::out_of_line -> declaration of Local::out_of_line
    { 'request': [25, 27], 'response': [11, 10] },
    # GoToDeclaration on definition of out_of_line moves to declaration
    { 'request': [14, 13], 'response': [11, 10] },
    # main -> declaration of main
    { 'request': [21,  7], 'response': [19, 5] },
  ]

  for test in tests:
    yield _RunCompleterCommand_GoTo_all_Clang, \
          'GoTo_all_Clang_test.cc',            \
          ['GoToDeclaration'],                 \
          test

  # GoToDefinition - identical to GoToDeclaration
  #
  # The semantics of this seem the wrong way round to me. GoToDefinition should
  # go to where a method is implemented, not where it is declared.
  #
  tests = [
    # Local::x -> declaration of x
    { 'request': [23, 21], 'response': [ 4,  9] },
    # Local::in_line -> declaration of Local::in_line
    { 'request': [24, 26], 'response': [ 6, 10] },
    # Local -> declaration of Local
    { 'request': [24, 16], 'response': [ 2, 11] },
    # sic: Local::out_of_line -> definition of Local::out_of_line
    { 'request': [25, 27], 'response': [14, 13] }, # sic
    # sic: GoToDeclaration on definition of out_of_line moves to itself
    { 'request': [14, 13], 'response': [14, 13] }, # sic
    # main -> definition of main (not declaration)
    { 'request': [21,  7], 'response': [21, 5] }, # sic
  ]

  for test in tests:
    yield _RunCompleterCommand_GoTo_all_Clang, \
          'GoTo_all_Clang_test.cc',            \
          ['GoToDefinition'],                  \
          test

  # GoTo - identical to GoToDeclaration
  #
  # The semantics of this seem the wrong way round to me. GoToDefinition should
  # go to where a method is implemented, not where it is declared.
  #
  tests = [
    # Local::x -> declaration of x
    { 'request': [23, 21], 'response': [ 4,  9] },
    # Local::in_line -> declaration of Local::in_line
    { 'request': [24, 26], 'response': [ 6, 10] },
    # Local -> declaration of Local
    { 'request': [24, 16], 'response': [ 2, 11] },
    # sic: Local::out_of_line -> definition of Local::out_of_line
    { 'request': [25, 27], 'response': [14, 13] }, # sic
    # sic: GoToDeclaration on definition of out_of_line moves to itself
    { 'request': [14, 13], 'response': [14, 13] }, # sic
    # main -> definition of main (not declaration)
    { 'request': [21,  7], 'response': [21, 5] }, # sic
  ]

  for test in tests:
    yield _RunCompleterCommand_GoTo_all_Clang, \
          'GoTo_all_Clang_test.cc',            \
          ['GoTo'],                            \
          test

  # GoToImprecise - identical to GoToDeclaration
  #
  # The semantics of this seem the wrong way round to me. GoToDefinition should
  # go to where a method is implemented, not where it is declared.
  #
  tests = [
    # Local::x -> declaration of x
    { 'request': [23, 21], 'response': [ 4,  9] },
    # Local::in_line -> declaration of Local::in_line
    { 'request': [24, 26], 'response': [ 6, 10] },
    # Local -> declaration of Local
    { 'request': [24, 16], 'response': [ 2, 11] },
    # sic: Local::out_of_line -> definition of Local::out_of_line
    { 'request': [25, 27], 'response': [14, 13] }, # sic
    # sic: GoToDeclaration on definition of out_of_line moves to itself
    { 'request': [14, 13], 'response': [14, 13] }, # sic
    # main -> definition of main (not declaration)
    { 'request': [21,  7], 'response': [21, 5] }, # sic
  ]

  for test in tests:
    yield _RunCompleterCommand_GoTo_all_Clang, \
          'GoTo_all_Clang_test.cc',            \
          ['GoToImprecise'],                   \
          test


def _RunCompleterCommand_Message_Clang(filename, test, command):
  contents = open( PathToTestFile( filename ) ).read()
  app = TestApp( handlers.app )

  # We use the -fno-delayed-template-parsing flag to not delay
  # parsing of templates on Windows.  This is the default on
  # other platforms.  See the _ExtraClangFlags function in
  # ycmd/completers/cpp/flags.py file for more information.
  common_args = {
    'completer_target'  : 'filetype_default',
    'command_arguments' : command,
    'compilation_flags' : ['-x',
                           'c++',
                           # C++11 flag is needed for lambda functions
                           '-std=c++11',
                           '-fno-delayed-template-parsing'],
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
    # Basic pod types
    [{'line_num': 20, 'column_num':  3}, 'Foo'],
    [{'line_num':  1, 'column_num':  1}, 'Internal error: cursor not valid'],
    [{'line_num': 12, 'column_num':  2}, 'Foo'],
    [{'line_num': 12, 'column_num':  8}, 'Foo'],
    [{'line_num': 12, 'column_num':  9}, 'Foo'],
    [{'line_num': 12, 'column_num': 10}, 'Foo'],
    [{'line_num': 13, 'column_num':  3}, 'int'],
    [{'line_num': 13, 'column_num':  7}, 'int'],
    [{'line_num': 15, 'column_num':  7}, 'char'],

    # Function
    [{'line_num': 18, 'column_num':  2}, 'int ()'],
    [{'line_num': 18, 'column_num':  6}, 'int ()'],

    # Declared and canonical type
    # On Ns:: (Unknown)
    [{'line_num': 21, 'column_num':  3}, 'Unknown type'], # sic
    # On Type (Type)
    [{'line_num': 21, 'column_num':  8}, 'Type => Ns::BasicType<char>'], # sic
    # On "a" (Ns::Type)
    [{'line_num': 21, 'column_num': 15}, 'Ns::Type => Ns::BasicType<char>'],
    [{'line_num': 22, 'column_num': 13}, 'Ns::Type => Ns::BasicType<char>'],

    # Cursor on decl for refs & pointers
    [{'line_num': 35, 'column_num':  3}, 'Foo'],
    [{'line_num': 35, 'column_num': 11}, 'Foo &'],
    [{'line_num': 35, 'column_num': 15}, 'Foo'],
    [{'line_num': 36, 'column_num':  3}, 'Foo'],
    [{'line_num': 36, 'column_num': 11}, 'Foo *'],
    [{'line_num': 36, 'column_num': 18}, 'Foo'],
    [{'line_num': 38, 'column_num':  3}, 'const Foo &'],
    [{'line_num': 38, 'column_num': 16}, 'const Foo &'],
    [{'line_num': 39, 'column_num':  3}, 'const Foo *'],
    [{'line_num': 39, 'column_num': 16}, 'const Foo *'],

    # Cursor on usage
    [{'line_num': 41, 'column_num': 13}, 'const Foo'],
    [{'line_num': 41, 'column_num': 19}, 'const int'],
    [{'line_num': 42, 'column_num': 13}, 'const Foo *'],
    [{'line_num': 42, 'column_num': 20}, 'const int'],
    [{'line_num': 43, 'column_num': 12}, 'Foo'],
    [{'line_num': 43, 'column_num': 17}, 'int'],
    [{'line_num': 44, 'column_num': 12}, 'Foo *'],
    [{'line_num': 44, 'column_num': 18}, 'int'],

    # Auto behaves strangely (bug in libclang)
    [{'line_num': 24, 'column_num':  3}, 'auto &'], # sic
    [{'line_num': 24, 'column_num': 11}, 'auto &'], # sic
    [{'line_num': 24, 'column_num': 18}, 'Foo'],
    [{'line_num': 25, 'column_num':  3}, 'auto *'], # sic
    [{'line_num': 25, 'column_num': 11}, 'auto *'], # sic
    [{'line_num': 25, 'column_num': 18}, 'Foo'],
    [{'line_num': 27, 'column_num':  3}, 'const auto &'], # sic
    [{'line_num': 27, 'column_num': 16}, 'const auto &'], # sic
    [{'line_num': 28, 'column_num':  3}, 'const auto *'], # sic
    [{'line_num': 28, 'column_num': 16}, 'const auto *'], # sic

    # Auto sort of works in usage (but canonical types apparently differ)
    [{'line_num': 30, 'column_num': 14}, 'const Foo => const Foo'], #sic
    [{'line_num': 30, 'column_num': 21}, 'const int'],
    [{'line_num': 31, 'column_num': 14}, 'const Foo * => const Foo *'], #sic
    [{'line_num': 31, 'column_num': 22}, 'const int'],
    [{'line_num': 32, 'column_num': 13}, 'Foo => Foo'], #sic
    [{'line_num': 32, 'column_num': 19}, 'int'],
    [{'line_num': 33, 'column_num': 13}, 'Foo * => Foo *'], #sic
    [{'line_num': 33, 'column_num': 20}, 'int'],
  ]

  for test in tests:
    yield _RunCompleterCommand_Message_Clang, \
          'GetType_Clang_test.cc',            \
          test,                               \
          ['GetType']


@with_setup( Setup )
def RunCompleterCommand_GetParent_Clang_test():
  tests = [
    [{'line_num':  1,  'column_num':  1}, 'Internal error: cursor not valid'],
    # Would be file name if we had one:
    [{'line_num':  2,  'column_num':  8}, '/foo'],

    # The reported scope does not include parents
    [{'line_num':  3,  'column_num': 11}, 'A'],
    [{'line_num':  4,  'column_num': 13}, 'B'],
    [{'line_num':  5,  'column_num': 13}, 'B'],
    [{'line_num':  9,  'column_num': 17}, 'do_z_inline()'],
    [{'line_num': 15,  'column_num': 22}, 'do_anything(T &)'],
    [{'line_num': 19,  'column_num':  9}, 'A'],
    [{'line_num': 20,  'column_num':  9}, 'A'],
    [{'line_num': 22,  'column_num': 12}, 'A'],
    [{'line_num': 23,  'column_num':  5}, 'do_Z_inline()'],
    [{'line_num': 24,  'column_num': 12}, 'do_Z_inline()'],
    [{'line_num': 28,  'column_num': 14}, 'A'],

    [{'line_num': 34,  'column_num':  1}, 'do_anything(T &)'],
    [{'line_num': 39,  'column_num':  1}, 'do_x()'],
    [{'line_num': 44,  'column_num':  1}, 'do_y()'],
    [{'line_num': 49,  'column_num':  1}, 'main()'],

    # Lambdas report the name of the variable
    [{'line_num': 49,  'column_num': 14}, 'l'],
    [{'line_num': 50,  'column_num': 19}, 'l'],
    [{'line_num': 51,  'column_num': 16}, 'main()'],
  ]

  for test in tests:
    yield _RunCompleterCommand_Message_Clang, \
          'GetParent_Clang_test.cc',          \
          test,                               \
          ['GetParent']


def _RunFixItTest_Clang( line, column, lang, file_name, check ):
  contents = open( PathToTestFile( file_name ) ).read()
  app = TestApp( handlers.app )

  language_options = {
    'cpp11' : {
      'compilation_flags' : ['-x',
                             'c++',
                             '-std=c++11',
                             '-Wall',
                             '-Wextra',
                             '-pedantic'],
      'filetype'          : 'cpp',
    },

    'objective-c' : {
      'compilation_flags' : ['-x',
                             'objective-c',
                             '-Wall',
                             '-Wextra'],
      'filetype'          : 'objc',
    },
  }

  # build the command arguments from the standard ones and the language-specific
  # arguments
  args = {
    'completer_target'  : 'filetype_default',
    'contents'          : contents,
    'command_arguments' : ['FixIt'],
    'line_num'          : line,
    'column_num'        : column,
  }
  args.update(language_options[lang])

  # get the diagnostics for the file
  event_data = BuildRequest( **args )

  results = app.post_json( '/run_completer_command', event_data ).json

  pprint( results )
  check( results )


def _FixIt_Check_cpp11_Ins( results ):
  # First fixit
  #   switch(A()) { // expected-error{{explicit conversion to}}
  assert_that( results, has_entries ( {
    'fixits': contains ( has_entries ( {
      'chunks' : contains (
        has_entries( {
          'replacement_text': equal_to('static_cast<int>('),
          'range': has_entries( {
            'start': has_entries( { 'line_num': 16, 'column_num': 10 } ),
            'end'  : has_entries( { 'line_num': 16, 'column_num': 10 } ),
          } ),
        } ),
        has_entries( {
          'replacement_text': equal_to(')'),
          'range': has_entries( {
            'start': has_entries( { 'line_num': 16, 'column_num': 13 } ),
            'end'  : has_entries( { 'line_num': 16, 'column_num': 13 } ),
          } ),
        } )
      ),
      'location' : has_entries( { 'line_num': 16, 'column_num': 3 } )
    } ) )
  } ) )


def _FixIt_Check_cpp11_InsMultiLine( results ):
  # Similar to _FixIt_Check_cpp11_1 but inserts split across lines
  #
  assert_that( results, has_entries( {
    'fixits': contains( has_entries ( {
      'chunks' : contains (
        has_entries( {
          'replacement_text': equal_to('static_cast<int>('),
          'range': has_entries( {
            'start': has_entries( { 'line_num': 26, 'column_num': 7 } ),
            'end'  : has_entries( { 'line_num': 26, 'column_num': 7 } ),
          } ),
        } ),
        has_entries( {
          'replacement_text': equal_to(')'),
          'range': has_entries( {
            'start': has_entries( { 'line_num': 28, 'column_num': 2 } ),
            'end'  : has_entries( { 'line_num': 28, 'column_num': 2 } ),
          } ),
        } )
      ),
      'location' : has_entries( { 'line_num': 25, 'column_num': 3 } )
    } ) )
  } ) )


def _FixIt_Check_cpp11_Del( results ):
  # Removal of ::
  assert_that( results, has_entries( {
    'fixits': contains( has_entries ( {
      'chunks' : contains (
        has_entries( {
          'replacement_text': equal_to(''),
          'range': has_entries( {
            'start': has_entries( { 'line_num': 35, 'column_num': 7 } ),
            'end'  : has_entries( { 'line_num': 35, 'column_num': 9 } ),
          } ),
        } )
      ),
      'location' : has_entries( { 'line_num': 35, 'column_num': 7 } )
    } ) )
  } ) )


def _FixIt_Check_cpp11_Repl( results ):
  assert_that( results, has_entries( {
    'fixits': contains( has_entries ( {
      'chunks' : contains (
        has_entries( {
          'replacement_text': equal_to('foo'),
          'range': has_entries( {
            'start': has_entries( { 'line_num': 40, 'column_num': 6 } ),
            'end'  : has_entries( { 'line_num': 40, 'column_num': 9 } ),
          } ),
        } )
      ),
      'location' : has_entries( { 'line_num': 40, 'column_num': 6 } )
    } ) )
  } ) )


def _FixIt_Check_cpp11_DelAdd( results ):
  assert_that( results, has_entries( {
    'fixits': contains( has_entries ( {
      'chunks' : contains (
        has_entries( {
          'replacement_text': equal_to(''),
          'range': has_entries( {
            'start': has_entries( { 'line_num': 48, 'column_num': 3 } ),
            'end'  : has_entries( { 'line_num': 48, 'column_num': 4 } ),
          } ),
        } ),
        has_entries( {
          'replacement_text': equal_to('~'),
          'range': has_entries( {
            'start': has_entries( { 'line_num': 48, 'column_num': 9 } ),
            'end'  : has_entries( { 'line_num': 48, 'column_num': 9 } ),
          } ),
        } ),
      ),
      'location' : has_entries( { 'line_num': 48, 'column_num': 3 } )
    } ) )
  } ) )


def _FixIt_Check_objc( results ):
  assert_that( results, has_entries( {
    'fixits': contains( has_entries ( {
      'chunks' : contains (
        has_entries( {
          'replacement_text': equal_to('id'),
          'range': has_entries( {
            'start': has_entries( { 'line_num': 5, 'column_num': 3 } ),
            'end'  : has_entries( { 'line_num': 5, 'column_num': 3 } ),
          } ),
        } )
      ),
      'location' : has_entries( { 'line_num': 5, 'column_num': 3 } )
    } ) )
  } ) )


def _FixIt_Check_objc_NoFixIt( results ):
  # and finally, a warning with no fixits
  assert_that( results, equal_to( { 'fixits' : [] } ) )


def _FixIt_Check_cpp11_MultiFirst( results ):
  assert_that( results, has_entries( {
    'fixits': contains(
      # first fix-it at 54,16
      has_entries ( {
        'chunks' : contains (
          has_entries( {
            'replacement_text': equal_to('foo'),
            'range': has_entries( {
              'start': has_entries( { 'line_num': 54, 'column_num': 16 } ),
              'end'  : has_entries( { 'line_num': 54, 'column_num': 19 } ),
            } ),
          } )
        ),
        'location' : has_entries( { 'line_num': 54, 'column_num': 16 } )
      } ),
      # second fix-it at 54,52
      has_entries ( {
        'chunks' : contains (
          has_entries( {
            'replacement_text': equal_to(''),
            'range': has_entries( {
              'start': has_entries( { 'line_num': 54, 'column_num': 52 } ),
              'end'  : has_entries( { 'line_num': 54, 'column_num': 53 } ),
            } ),
          } ),
          has_entries( {
            'replacement_text': equal_to('~'),
            'range': has_entries( {
              'start': has_entries( { 'line_num': 54, 'column_num': 58 } ),
              'end'  : has_entries( { 'line_num': 54, 'column_num': 58 } ),
            } ),
          } ),
        ),
        'location' : has_entries( { 'line_num': 54, 'column_num': 52 } )
      } )
    )
  } ) )


def _FixIt_Check_cpp11_MultiSecond( results ):
  assert_that( results, has_entries( {
    'fixits': contains(
      # second fix-it at 54,52
      has_entries ( {
        'chunks' : contains (
          has_entries( {
            'replacement_text': equal_to(''),
            'range': has_entries( {
              'start': has_entries( { 'line_num': 54, 'column_num': 52 } ),
              'end'  : has_entries( { 'line_num': 54, 'column_num': 53 } ),
            } ),
          } ),
          has_entries( {
            'replacement_text': equal_to('~'),
            'range': has_entries( {
              'start': has_entries( { 'line_num': 54, 'column_num': 58 } ),
              'end'  : has_entries( { 'line_num': 54, 'column_num': 58 } ),
            } ),
          } ),
        ),
        'location' : has_entries( { 'line_num': 54, 'column_num': 52 } )
      } ),
      # first fix-it at 54,16
      has_entries ( {
        'chunks' : contains (
          has_entries( {
            'replacement_text': equal_to('foo'),
            'range': has_entries( {
              'start': has_entries( { 'line_num': 54, 'column_num': 16 } ),
              'end'  : has_entries( { 'line_num': 54, 'column_num': 19 } ),
            } ),
          } )
        ),
        'location' : has_entries( { 'line_num': 54, 'column_num': 16 } )
      } )
    )
  } ) )


@with_setup( Setup )
def RunCompleterCommand_FixIt_all_Clang_test():
  cfile = 'FixIt_Clang_cpp11.cpp'
  mfile = 'FixIt_Clang_objc.m'

  tests = [
      [ 16, 0,  'cpp11', cfile, _FixIt_Check_cpp11_Ins ],
      [ 16, 1,  'cpp11', cfile, _FixIt_Check_cpp11_Ins ],
      [ 16, 10, 'cpp11', cfile, _FixIt_Check_cpp11_Ins ],
      [ 25, 14, 'cpp11', cfile, _FixIt_Check_cpp11_InsMultiLine ],
      [ 25, 0,  'cpp11', cfile, _FixIt_Check_cpp11_InsMultiLine ],
      [ 35, 7,  'cpp11', cfile, _FixIt_Check_cpp11_Del ],
      [ 40, 6,  'cpp11', cfile, _FixIt_Check_cpp11_Repl ],
      [ 48, 3,  'cpp11', cfile, _FixIt_Check_cpp11_DelAdd ],

      [ 5, 3,   'objective-c', mfile, _FixIt_Check_objc ],
      [ 7, 1,   'objective-c', mfile, _FixIt_Check_objc_NoFixIt ],

      # multiple errors on a single line; both with fixits
      [ 54, 15, 'cpp11', cfile, _FixIt_Check_cpp11_MultiFirst ],
      [ 54, 16, 'cpp11', cfile, _FixIt_Check_cpp11_MultiFirst ],
      [ 54, 16, 'cpp11', cfile, _FixIt_Check_cpp11_MultiFirst ],
      [ 54, 17, 'cpp11', cfile, _FixIt_Check_cpp11_MultiFirst ],
      [ 54, 18, 'cpp11', cfile, _FixIt_Check_cpp11_MultiFirst ],

      # should put closest fix-it first?
      [ 54, 51, 'cpp11', cfile, _FixIt_Check_cpp11_MultiSecond ],
      [ 54, 52, 'cpp11', cfile, _FixIt_Check_cpp11_MultiSecond ],
      [ 54, 53, 'cpp11', cfile, _FixIt_Check_cpp11_MultiSecond ],
  ]

  for test in tests:
    yield _RunFixItTest_Clang, test[0], test[1], test[2], test[3], test[4]


@with_setup( Setup )
def RunCompleterCommand_GoTo_CsCompleter_Works_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app, filepath )

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
      },
      app.post_json( '/run_completer_command', goto_data ).json )

  StopOmniSharpServer( app, filepath )


@with_setup( Setup )
def RunCompleterCommand_GoToImplementation_CsCompleter_Works_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app, filepath )

  goto_data = BuildRequest( completer_target = 'filetype_default',
                            command_arguments = [ 'GoToImplementation' ],
                            line_num = 13,
                            column_num = 13,
                            contents = contents,
                            filetype = 'cs',
                            filepath = filepath )

  eq_( {
        'filepath': PathToTestFile( 'testy', 'GotoTestCase.cs' ),
        'line_num': 30,
        'column_num': 3
      },
      app.post_json( '/run_completer_command', goto_data ).json )

  StopOmniSharpServer( app, filepath )


@with_setup( Setup )
def RunCompleterCommand_GoToImplementation_CsCompleter_NoImplementation_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app, filepath )

  goto_data = BuildRequest( completer_target = 'filetype_default',
                            command_arguments = [ 'GoToImplementation' ],
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
    StopOmniSharpServer( app, filepath )


@with_setup( Setup )
def RunCompleterCommand_GoToImplementation_CsCompleter_InvalidLocation_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app, filepath )

  goto_data = BuildRequest( completer_target = 'filetype_default',
                            command_arguments = [ 'GoToImplementation' ],
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
    StopOmniSharpServer( app, filepath )


@with_setup( Setup )
def RunCompleterCommand_GoToImplementationElseDeclaration_CsCompleter_NoImplementation_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app, filepath )

  goto_data = BuildRequest( completer_target = 'filetype_default',
                            command_arguments = [ 'GoToImplementationElseDeclaration' ],
                            line_num = 17,
                            column_num = 13,
                            contents = contents,
                            filetype = 'cs',
                            filepath = filepath )

  eq_( {
        'filepath': PathToTestFile( 'testy', 'GotoTestCase.cs' ),
        'line_num': 35,
        'column_num': 3
      },
      app.post_json( '/run_completer_command', goto_data ).json )

  StopOmniSharpServer( app, filepath )


@with_setup( Setup )
def RunCompleterCommand_GoToImplementationElseDeclaration_CsCompleter_SingleImplementation_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app, filepath )

  goto_data = BuildRequest( completer_target = 'filetype_default',
                            command_arguments = [ 'GoToImplementationElseDeclaration' ],
                            line_num = 13,
                            column_num = 13,
                            contents = contents,
                            filetype = 'cs',
                            filepath = filepath )

  eq_( {
        'filepath': PathToTestFile( 'testy', 'GotoTestCase.cs' ),
        'line_num': 30,
        'column_num': 3
      },
      app.post_json( '/run_completer_command', goto_data ).json )

  StopOmniSharpServer( app, filepath )


@with_setup( Setup )
def RunCompleterCommand_GoToImplementationElseDeclaration_CsCompleter_MultipleImplementations_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app, filepath )

  goto_data = BuildRequest( completer_target = 'filetype_default',
                            command_arguments = [ 'GoToImplementationElseDeclaration' ],
                            line_num = 21,
                            column_num = 13,
                            contents = contents,
                            filetype = 'cs',
                            filepath = filepath )

  eq_( [{
        'filepath': PathToTestFile( 'testy', 'GotoTestCase.cs' ),
        'line_num': 43,
        'column_num': 3
      }, {
        'filepath': PathToTestFile( 'testy', 'GotoTestCase.cs' ),
        'line_num': 48,
        'column_num': 3
      }],
      app.post_json( '/run_completer_command', goto_data ).json )

  StopOmniSharpServer( app, filepath )


@with_setup( Setup )
def RunCompleterCommand_GetType_CsCompleter_EmptyMessage_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy', 'GetTypeTestCase.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app, filepath )

  gettype_data = BuildRequest( completer_target = 'filetype_default',
                               command_arguments = [ 'GetType' ],
                               line_num = 1,
                               column_num = 1,
                               contents = contents,
                               filetype = 'cs',
                               filepath = filepath )

  eq_( {
        u'message': u""
      },
      app.post_json( '/run_completer_command', gettype_data ).json )

  StopOmniSharpServer( app, filepath )


@with_setup( Setup )
def RunCompleterCommand_GetType_CsCompleter_VariableDeclaration_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy', 'GetTypeTestCase.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app, filepath )

  gettype_data = BuildRequest( completer_target = 'filetype_default',
                               command_arguments = [ 'GetType' ],
                               line_num = 4,
                               column_num = 5,
                               contents = contents,
                               filetype = 'cs',
                               filepath = filepath )

  eq_( {
        u'message': u"string"
      },
      app.post_json( '/run_completer_command', gettype_data ).json )

  StopOmniSharpServer( app, filepath )


@with_setup( Setup )
def RunCompleterCommand_GetType_CsCompleter_VariableUsage_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy/GetTypeTestCase.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app, filepath )

  gettype_data = BuildRequest( completer_target = 'filetype_default',
                               command_arguments = [ 'GetType' ],
                               line_num = 5,
                               column_num = 5,
                               contents = contents,
                               filetype = 'cs',
                               filepath = filepath )

  eq_( {
        u'message': u"string str"
      },
      app.post_json( '/run_completer_command', gettype_data ).json )

  StopOmniSharpServer( app, filepath )


@with_setup( Setup )
def RunCompleterCommand_GetType_CsCompleter_Constant_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy/GetTypeTestCase.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app, filepath )

  gettype_data = BuildRequest( completer_target = 'filetype_default',
                               command_arguments = [ 'GetType' ],
                               line_num = 4,
                               column_num = 14,
                               contents = contents,
                               filetype = 'cs',
                               filepath = filepath )

  eq_( {
        u'message': u"System.String"
      },
      app.post_json( '/run_completer_command', gettype_data ).json )

  StopOmniSharpServer( app, filepath )


@with_setup( Setup )
def RunCompleterCommand_GetType_CsCompleter_DocsIgnored_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy', 'GetTypeTestCase.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app, filepath )

  gettype_data = BuildRequest( completer_target = 'filetype_default',
                               command_arguments = [ 'GetType' ],
                               line_num = 9,
                               column_num = 34,
                               contents = contents,
                               filetype = 'cs',
                               filepath = filepath )

  eq_( {
        u'message': u"int GetTypeTestCase.an_int_with_docs;",
      },
      app.post_json( '/run_completer_command', gettype_data ).json )

  StopOmniSharpServer( app, filepath )


@with_setup( Setup )
def RunCompleterCommand_GetDoc_CsCompleter_Works_Var_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy', 'GetDocTestCase.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app, filepath )

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
      },
      app.post_json( '/run_completer_command', getdoc_data ).json )

  StopOmniSharpServer( app, filepath )


@with_setup( Setup )
def RunCompleterCommand_GetDoc_CsCompleter_Works_Func_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy', 'GetDocTestCase.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app, filepath )

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
      },
      app.post_json( '/run_completer_command', getdoc_data ).json )

  StopOmniSharpServer( app, filepath )


def _RunFixItTest_CsCompleter( line, column, expected_result ):
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy', 'FixItTestCase.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app, filepath )

  fixit_data = BuildRequest( completer_target = 'filetype_default',
                             command_arguments = [ 'FixIt' ],
                             line_num = line,
                             column_num = column,
                             contents = contents,
                             filetype = 'cs',
                             filepath = filepath )

  eq_( expected_result,
       app.post_json( '/run_completer_command', fixit_data ).json )

  StopOmniSharpServer( app, filepath )


@with_setup( Setup )
def RunCompleterCommand_FixIt_CsCompleter_RemoveSingleLine_test():
  filepath = PathToTestFile( 'testy', 'FixItTestCase.cs' )
  _RunFixItTest_CsCompleter( 11, 1, {
    u'fixits': [
      {
        u'location': {
          u'line_num': 11,
          u'column_num': 1,
          u'filepath': filepath
        },
        u'chunks' : [
          {
            u'replacement_text': '',
            u'range' : {
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
  })


@with_setup( Setup )
def RunCompleterCommand_FixIt_CsCompleter_MultipleLines_test():
  filepath = PathToTestFile( 'testy', 'FixItTestCase.cs' )
  _RunFixItTest_CsCompleter( 19, 1, {
    u'fixits': [
      {
        u'location': {
          u'line_num': 19,
          u'column_num': 1,
          u'filepath': filepath
        },
        u'chunks' : [
          {
            u'replacement_text': "return On",
            u'range' : {
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
  })


@with_setup( Setup )
def RunCompleterCommand_FixIt_CsCompleter_SpanFileEdge_test():
  filepath = PathToTestFile( 'testy', 'FixItTestCase.cs' )
  _RunFixItTest_CsCompleter( 1, 1, {
    u'fixits': [
      {
        u'location': {
          u'line_num': 1,
          u'column_num': 1,
          u'filepath': filepath
        },
        u'chunks' : [
          {
            u'replacement_text': 'System',
            u'range' : {
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
  })


@with_setup( Setup )
def RunCompleterCommand_FixIt_CsCompleter_AddTextInLine_test():
  filepath = PathToTestFile( 'testy', 'FixItTestCase.cs' )
  _RunFixItTest_CsCompleter( 9, 1, {
    u'fixits': [
      {
        u'location': {
          u'line_num': 9,
          u'column_num': 1,
          u'filepath': filepath
        },
        u'chunks' : [
          {
            u'replacement_text': ', StringComparison.Ordinal',
            u'range' : {
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


@with_setup( Setup )
def RunCompleterCommand_FixIt_CsCompleter_ReplaceTextInLine_test():
  filepath = PathToTestFile( 'testy', 'FixItTestCase.cs' )
  _RunFixItTest_CsCompleter( 10, 1, {
    u'fixits': [
      {
        u'location': {
          u'line_num': 10,
          u'column_num': 1,
          u'filepath': filepath
        },
        u'chunks' : [
          {
            u'replacement_text': 'const int',
            u'range' : {
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


@with_setup( Setup )
def RunCompleterCommand_StopServer_CsCompleter_NoErrorIfNotStarted_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  StopOmniSharpServer( app, filepath )
  # Success = no raise


@with_setup( Setup )
def RunCompleterCommand_StopServer_CsCompleter_KeepLogFiles_test():
  yield  _RunCompleterCommand_StopServer_CsCompleter_KeepLogFiles, True
  yield  _RunCompleterCommand_StopServer_CsCompleter_KeepLogFiles, False


def _RunCompleterCommand_StopServer_CsCompleter_KeepLogFiles( keeping_log_files ):
  ChangeSpecificOptions( { 'server_keep_logfiles': keeping_log_files } )
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app, filepath )

  event_data = BuildRequest( filetype = 'cs', filepath = filepath )

  debuginfo = app.post_json( '/debug_info', event_data ).json

  log_files_match = re.search( "^OmniSharp logfiles:\n(.*)\n(.*)", debuginfo, re.MULTILINE )
  stdout_logfiles_location = log_files_match.group( 1 )
  stderr_logfiles_location = log_files_match.group( 2 )

  try:
    assert os.path.exists( stdout_logfiles_location ), "Logfile should exist at " + stdout_logfiles_location
    assert os.path.exists( stderr_logfiles_location ), "Logfile should exist at " + stderr_logfiles_location
  finally:
    StopOmniSharpServer( app, filepath )

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
         'GoTo',
         'GetDoc' ],
       app.post_json( '/defined_subcommands', subcommands_data ).json )


@with_setup( Setup )
def DefinedSubcommands_WorksWhenNoExplicitCompleterTargetSpecified_test():
  app = TestApp( handlers.app )
  subcommands_data = BuildRequest( filetype = 'python' )

  eq_( [ 'GoToDefinition',
         'GoToDeclaration',
         'GoTo',
         'GetDoc' ],
       app.post_json( '/defined_subcommands', subcommands_data ).json )


@with_setup( Setup )
def RunCompleterCommand_GetType_TypescriptCompleter_test():
  app = TestApp( handlers.app )

  filepath = PathToTestFile( 'test.ts' )
  contents = open( filepath ).read()

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'typescript',
                             contents = contents,
                             event_name = 'BufferVisit' )

  app.post_json( '/event_notification', event_data )

  gettype_data = BuildRequest( completer_target = 'filetype_default',
                               command_arguments = [ 'GetType' ],
                               line_num = 12,
                               column_num = 1,
                               contents = contents,
                               filetype = 'typescript',
                               filepath = filepath )

  eq_( {
         'message': 'var foo: Foo'
       },
       app.post_json( '/run_completer_command', gettype_data ).json )

@with_setup( Setup )
def RunCompleterCommand_GetType_HasNoType_TypescriptCompleter_test():
  app = TestApp( handlers.app )

  filepath = PathToTestFile( 'test.ts' )
  contents = open( filepath ).read()

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'typescript',
                             contents = contents,
                             event_name = 'BufferVisit' )

  app.post_json( '/event_notification', event_data )

  gettype_data = BuildRequest( completer_target = 'filetype_default',
                               command_arguments = [ 'GetType' ],
                               line_num = 2,
                               column_num = 1,
                               contents = contents,
                               filetype = 'typescript',
                               filepath = filepath )

  assert_that( calling( app.post_json ).with_args( '/run_completer_command', gettype_data ),
               raises( AppError, 'RuntimeError.*No content available' ) )


@with_setup( Setup )
def RunCompleterCommand_GetDoc_TypescriptCompleter_Works_Method_test():
  app = TestApp( handlers.app )

  filepath = PathToTestFile( 'test.ts' )
  contents = open( filepath ).read()

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'typescript',
                             contents = contents,
                             event_name = 'BufferVisit' )

  app.post_json( '/event_notification', event_data )

  gettype_data = BuildRequest( completer_target = 'filetype_default',
                               command_arguments = [ 'GetDoc' ],
                               line_num = 29,
                               column_num = 9,
                               contents = contents,
                               filetype = 'typescript',
                               filepath = filepath )

  eq_( {
         'detailed_info': '(method) Bar.testMethod(): void\n\n'
                          'Method documentation',
       },
       app.post_json( '/run_completer_command', gettype_data ).json )


@with_setup( Setup )
def RunCompleterCommand_GetDoc_TypescriptCompleter_Works_Class_test():
  app = TestApp( handlers.app )

  filepath = PathToTestFile( 'test.ts' )
  contents = open( filepath ).read()

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'typescript',
                             contents = contents,
                             event_name = 'BufferVisit' )

  app.post_json( '/event_notification', event_data )

  gettype_data = BuildRequest( completer_target = 'filetype_default',
                               command_arguments = [ 'GetDoc' ],
                               line_num = 31,
                               column_num = 2,
                               contents = contents,
                               filetype = 'typescript',
                               filepath = filepath )

  eq_( {
         'detailed_info': 'class Bar\n\n'
                          'Class documentation\n\n'
                          'Multi-line',
       },
       app.post_json( '/run_completer_command', gettype_data ).json )


@with_setup( Setup )
def RunCompleterCommand_GetDoc_ClangCompleter_Variable_test():
  app = TestApp( handlers.app )

  filepath = PathToTestFile( 'GetDoc_Clang.cc' )
  contents = open( filepath ).read()

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cpp',
                             compilation_flags = [ '-x', 'c++' ],
                             line_num = 70,
                             column_num = 24,
                             contents = contents,
                             command_arguments = [ 'GetDoc' ],
                             completer_target = 'filetype_default' )

  response = app.post_json( '/run_completer_command', event_data ).json

  pprint( response )

  eq_( response, {
    'detailed_info': """\
char a_global_variable
This really is a global variable.
Type: char
Name: a_global_variable
---
This really is a global variable.

The first line of comment is the brief.""" } )


@with_setup( Setup )
def RunCompleterCommand_GetDoc_ClangCompleter_Method_test():
  app = TestApp( handlers.app )

  filepath = PathToTestFile( 'GetDoc_Clang.cc' )
  contents = open( filepath ).read()

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cpp',
                             compilation_flags = [ '-x', 'c++' ],
                             line_num = 22,
                             column_num = 13,
                             contents = contents,
                             command_arguments = [ 'GetDoc' ],
                             completer_target = 'filetype_default' )

  response = app.post_json( '/run_completer_command', event_data ).json

  pprint( response )

  eq_( response, {
    'detailed_info': """\
char with_brief()
brevity is for suckers
Type: char ()
Name: with_brief
---

This is not the brief.

\\brief brevity is for suckers

This is more information
""" } )


@with_setup( Setup )
def RunCompleterCommand_GetDoc_ClangCompleter_Namespace_test():
  app = TestApp( handlers.app )

  filepath = PathToTestFile( 'GetDoc_Clang.cc' )
  contents = open( filepath ).read()

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cpp',
                             compilation_flags = [ '-x', 'c++' ],
                             line_num = 65,
                             column_num = 14,
                             contents = contents,
                             command_arguments = [ 'GetDoc' ],
                             completer_target = 'filetype_default' )

  response = app.post_json( '/run_completer_command', event_data ).json

  pprint( response )

  eq_( response, {
    'detailed_info': """\
namespace Test {}
This is a test namespace
Type: 
Name: Test
---
This is a test namespace""" } )


@with_setup( Setup )
def RunCompleterCommand_GetDoc_ClangCompleter_Undocumented_test():
  app = TestApp( handlers.app )

  filepath = PathToTestFile( 'GetDoc_Clang.cc' )
  contents = open( filepath ).read()

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cpp',
                             compilation_flags = [ '-x', 'c++' ],
                             line_num = 81,
                             column_num = 17,
                             contents = contents,
                             command_arguments = [ 'GetDoc' ],
                             completer_target = 'filetype_default' )

  response = app.post_json( '/run_completer_command',
                            event_data,
                            expect_errors = True )

  eq_( response.status_code, httplib.INTERNAL_SERVER_ERROR )

  assert_that( response.json,
               ErrorMatcher( ValueError, NO_DOCUMENTATION_MESSAGE ) )


@with_setup( Setup )
def RunCompleterCommand_GetDoc_ClangCompleter_NoCursor_test():
  app = TestApp( handlers.app )

  filepath = PathToTestFile( 'GetDoc_Clang.cc' )
  contents = open( filepath ).read()

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cpp',
                             compilation_flags = [ '-x', 'c++' ],
                             line_num = 1,
                             column_num = 1,
                             contents = contents,
                             command_arguments = [ 'GetDoc' ],
                             completer_target = 'filetype_default' )

  response = app.post_json( '/run_completer_command',
                            event_data,
                            expect_errors = True )

  eq_( response.status_code, httplib.INTERNAL_SERVER_ERROR )

  assert_that( response.json,
               ErrorMatcher( ValueError, NO_DOCUMENTATION_MESSAGE ) )


# Following tests repeat the tests above, but without re-parsing the file
@with_setup( Setup )
def RunCompleterCommand_GetDocQuick_ClangCompleter_Variable_test():
  app = TestApp( handlers.app )

  filepath = PathToTestFile( 'GetDoc_Clang.cc' )
  contents = open( filepath ).read()

  app.post_json( '/event_notification',
                 BuildRequest(filepath = filepath,
                              filetype = 'cpp',
                              compilation_flags = [ '-x', 'c++' ],
                              contents = contents,
                              event_name = 'FileReadyToParse' ) )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cpp',
                             compilation_flags = [ '-x', 'c++' ],
                             line_num = 70,
                             column_num = 24,
                             contents = contents,
                             command_arguments = [ 'GetDocQuick' ],
                             completer_target = 'filetype_default' )

  response = app.post_json( '/run_completer_command', event_data ).json

  pprint( response )

  eq_( response, {
    'detailed_info': """\
char a_global_variable
This really is a global variable.
Type: char
Name: a_global_variable
---
This really is a global variable.

The first line of comment is the brief.""" } )


@with_setup( Setup )
def RunCompleterCommand_GetDocQuick_ClangCompleter_Method_test():
  app = TestApp( handlers.app )

  filepath = PathToTestFile( 'GetDoc_Clang.cc' )
  contents = open( filepath ).read()

  app.post_json( '/event_notification',
                 BuildRequest(filepath = filepath,
                              filetype = 'cpp',
                              compilation_flags = [ '-x', 'c++' ],
                              contents = contents,
                              event_name = 'FileReadyToParse' ) )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cpp',
                             compilation_flags = [ '-x', 'c++' ],
                             line_num = 22,
                             column_num = 13,
                             contents = contents,
                             command_arguments = [ 'GetDocQuick' ],
                             completer_target = 'filetype_default' )

  response = app.post_json( '/run_completer_command', event_data ).json

  pprint( response )

  eq_( response, {
    'detailed_info': """\
char with_brief()
brevity is for suckers
Type: char ()
Name: with_brief
---

This is not the brief.

\\brief brevity is for suckers

This is more information
""" } )


@with_setup( Setup )
def RunCompleterCommand_GetDocQuick_ClangCompleter_Namespace_test():
  app = TestApp( handlers.app )

  filepath = PathToTestFile( 'GetDoc_Clang.cc' )
  contents = open( filepath ).read()

  app.post_json( '/event_notification',
                 BuildRequest(filepath = filepath,
                              filetype = 'cpp',
                              compilation_flags = [ '-x', 'c++' ],
                              contents = contents,
                              event_name = 'FileReadyToParse' ) )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cpp',
                             compilation_flags = [ '-x', 'c++' ],
                             line_num = 65,
                             column_num = 14,
                             contents = contents,
                             command_arguments = [ 'GetDocQuick' ],
                             completer_target = 'filetype_default' )

  response = app.post_json( '/run_completer_command', event_data ).json

  pprint( response )

  eq_( response, {
    'detailed_info': """\
namespace Test {}
This is a test namespace
Type: 
Name: Test
---
This is a test namespace""" } )


@with_setup( Setup )
def RunCompleterCommand_GetDocQuick_ClangCompleter_Undocumented_test():
  app = TestApp( handlers.app )

  filepath = PathToTestFile( 'GetDoc_Clang.cc' )
  contents = open( filepath ).read()

  app.post_json( '/event_notification',
                 BuildRequest(filepath = filepath,
                              filetype = 'cpp',
                              compilation_flags = [ '-x', 'c++' ],
                              contents = contents,
                              event_name = 'FileReadyToParse' ) )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cpp',
                             compilation_flags = [ '-x', 'c++' ],
                             line_num = 81,
                             column_num = 17,
                             contents = contents,
                             command_arguments = [ 'GetDocQuick' ],
                             completer_target = 'filetype_default' )

  response = app.post_json( '/run_completer_command',
                            event_data,
                            expect_errors = True )

  eq_( response.status_code, httplib.INTERNAL_SERVER_ERROR )

  assert_that( response.json,
               ErrorMatcher( ValueError, NO_DOCUMENTATION_MESSAGE ) )


@with_setup( Setup )
def RunCompleterCommand_GetDocQuick_ClangCompleter_NoCursor_test():
  app = TestApp( handlers.app )

  filepath = PathToTestFile( 'GetDoc_Clang.cc' )
  contents = open( filepath ).read()

  app.post_json( '/event_notification',
                 BuildRequest(filepath = filepath,
                              filetype = 'cpp',
                              compilation_flags = [ '-x', 'c++' ],
                              contents = contents,
                              event_name = 'FileReadyToParse' ) )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cpp',
                             compilation_flags = [ '-x', 'c++' ],
                             line_num = 1,
                             column_num = 1,
                             contents = contents,
                             command_arguments = [ 'GetDocQuick' ],
                             completer_target = 'filetype_default' )

  response = app.post_json( '/run_completer_command',
                            event_data,
                            expect_errors = True )

  eq_( response.status_code, httplib.INTERNAL_SERVER_ERROR )

  assert_that( response.json,
               ErrorMatcher( ValueError, NO_DOCUMENTATION_MESSAGE ) )


@with_setup( Setup )
def RunCompleterCommand_GetDocQuick_ClangCompleter_NoReadyToParse_test():
  app = TestApp( handlers.app )

  filepath = PathToTestFile( 'GetDoc_Clang.cc' )
  contents = open( filepath ).read()

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cpp',
                             compilation_flags = [ '-x', 'c++' ],
                             line_num = 11,
                             column_num = 18,
                             contents = contents,
                             command_arguments = [ 'GetDocQuick' ],
                             completer_target = 'filetype_default' )

  response = app.post_json( '/run_completer_command', event_data ).json

  eq_( response, {
    'detailed_info': """\
int get_a_global_variable(bool test)
This is a method which is only pretend global
Type: int (bool)
Name: get_a_global_variable
---
This is a method which is only pretend global
@param test Set this to true. Do it.""" } )


@with_setup( Setup )
def RunCompleterCommand_GetDoc_Jedi_Works_Method_test():
  # Testcase1
  app = TestApp( handlers.app )

  filepath = PathToTestFile( 'GetDoc_Jedi.py' )
  contents = open( filepath ).read()

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'python',
                             line_num = 17,
                             column_num = 9,
                             contents = contents,
                             command_arguments = [ 'GetDoc' ],
                             completer_target = 'filetype_default' )

  response = app.post_json( '/run_completer_command', event_data ).json

  eq_( response, {
       'detailed_info': '_ModuleMethod()\n\n'
                        'Module method docs\n'
                        'Are dedented, like you might expect',
  } )


@with_setup( Setup )
def RunCompleterCommand_GetDoc_Jedi_Works_Class_test():
  # Testcase1
  app = TestApp( handlers.app )

  filepath = PathToTestFile( 'GetDoc_Jedi.py' )
  contents = open( filepath ).read()

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'python',
                             line_num = 19,
                             column_num = 2,
                             contents = contents,
                             command_arguments = [ 'GetDoc' ],
                             completer_target = 'filetype_default' )

  response = app.post_json( '/run_completer_command', event_data ).json

  eq_( response, {
       'detailed_info': 'Class Documentation',
  } )

