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

from webtest import AppError
from nose.tools import eq_
from hamcrest import ( assert_that, calling, contains, equal_to,
                       has_entries, raises )
from ycmd.completers.cpp.clang_completer import NO_DOCUMENTATION_MESSAGE
from clang_handlers_test import Clang_Handlers_test
from pprint import pprint
import os.path
import httplib


class Clang_Subcommands_test( Clang_Handlers_test ):

  def GoTo_ZeroBasedLineAndColumn_test( self ):
    contents = open( self._PathToTestFile(
      'GoTo_Clang_ZeroBasedLineAndColumn_test.cc' ) ).read()

    goto_data = self._BuildRequest( completer_target = 'filetype_default',
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
    }, self._app.post_json( '/run_completer_command', goto_data ).json )


  def _GoTo_all( self, filename, command, test ):
    contents = open( self._PathToTestFile( filename ) ).read()
    common_request = {
      'completer_target' : 'filetype_default',
      'command_arguments': command,
      'compilation_flags': ['-x',
                            'c++'],
      'line_num'         : 10,
      'column_num'       : 3,
      'contents'         : contents,
      'filetype'         : 'cpp'
    }
    common_response = {
      'filepath': os.path.abspath( '/foo' ),
    }

    request = common_request
    request.update( {
        'line_num'  : test['request'][0],
        'column_num': test['request'][1],
    })
    response = common_response
    response.update({
        'line_num'  : test['response'][0],
        'column_num': test['response'][1],
    })

    goto_data = self._BuildRequest( **request )

    eq_( response,
         self._app.post_json( '/run_completer_command', goto_data ).json )


  def GoTo_all_test( self ):
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
      yield ( self._GoTo_all,
              'GoTo_all_Clang_test.cc',
              [ 'GoToDeclaration' ],
              test )

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
      yield ( self._GoTo_all,
              'GoTo_all_Clang_test.cc',
              [ 'GoToDefinition' ],
              test )

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
      yield ( self._GoTo_all,
              'GoTo_all_Clang_test.cc',
              [ 'GoTo' ],
              test )

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
      yield ( self._GoTo_all,
              'GoTo_all_Clang_test.cc',
              [ 'GoToImprecise' ],
              test )


  def _GoToInclude( self, command, test ):
    self._app.post_json(
      '/load_extra_conf_file',
      { 'filepath': self._PathToTestFile( 'test-include',
                                          '.ycm_extra_conf.py' ) } )

    filepath = self._PathToTestFile( 'test-include', 'main.cpp' )
    goto_data = self._BuildRequest( filepath = filepath,
                                    filetype = 'cpp',
                                    contents = open( filepath ).read(),
                                    command_arguments = [ command ],
                                    line_num = test[ 'request' ][ 0 ],
                                    column_num = test[ 'request' ][ 1 ] )

    response = {
      'filepath'   : self._PathToTestFile( 'test-include', test[ 'response' ] ),
      'line_num'   : 1,
      'column_num' : 1,
    }

    eq_( response,
         self._app.post_json( '/run_completer_command', goto_data ).json )


  def GoToInclude_test( self ):
    tests = [
      { 'request': [ 1, 1 ], 'response': 'a.hpp' },
      { 'request': [ 2, 1 ], 'response': os.path.join( 'system', 'a.hpp' ) },
      { 'request': [ 3, 1 ], 'response': os.path.join( 'quote',  'b.hpp' ) },
      { 'request': [ 5, 1 ], 'response': os.path.join( 'system', 'c.hpp' ) },
      { 'request': [ 6, 1 ], 'response': os.path.join( 'system', 'c.hpp' ) },
    ]
    for test in tests:
      yield self._GoToInclude, 'GoToInclude', test
      yield self._GoToInclude, 'GoTo', test
      yield self._GoToInclude, 'GoToImprecise', test


  def GoToInclude_Fail_test( self ):
    test = { 'request': [ 4, 1 ], 'response': '' }
    assert_that(
      calling( self._GoToInclude ).with_args( 'GoToInclude', test ),
      raises( AppError, 'Include file not found.' ) )
    assert_that(
      calling( self._GoToInclude ).with_args( 'GoTo', test ),
      raises( AppError, 'Include file not found.' ) )
    assert_that(
      calling( self._GoToInclude ).with_args( 'GoToImprecise', test ),
      raises( AppError, 'Include file not found.' ) )

    test = { 'request': [ 7, 1 ], 'response': '' }
    assert_that(
      calling( self._GoToInclude ).with_args( 'GoToInclude', test ),
      raises( AppError, 'Not an include/import line.' ) )
    assert_that(
      calling( self._GoToInclude ).with_args( 'GoTo', test ),
      raises( AppError, r'Can\\\'t jump to definition or declaration.' ) )
    assert_that(
      calling( self._GoToInclude ).with_args( 'GoToImprecise', test ),
      raises( AppError, r'Can\\\'t jump to definition or declaration.' ) )


  def _Message( self, filename, test, command):
    contents = open( self._PathToTestFile( filename ) ).read()

    # We use the -fno-delayed-template-parsing flag to not delay
    # parsing of templates on Windows.  This is the default on
    # other platforms.  See the _ExtraClangFlags function in
    # ycmd/completers/cpp/flags.py file for more information.
    common_args = {
      'completer_target' : 'filetype_default',
      'command_arguments': command,
      'compilation_flags': [ '-x',
                             'c++',
                             # C++11 flag is needed for lambda functions
                             '-std=c++11',
                             '-fno-delayed-template-parsing' ],
      'line_num'         : 10,
      'column_num'       : 3,
      'contents'         : contents,
      'filetype'         : 'cpp'
    }

    args = test[ 0 ]
    expected = test[ 1 ]

    request = common_args
    request.update( args )

    request_data = self._BuildRequest( **request )

    eq_( { 'message': expected },
         self._app.post_json( '/run_completer_command', request_data ).json )


  def GetType_test( self ):
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
      yield ( self._Message,
              'GetType_Clang_test.cc',
              test,
              [ 'GetType' ] )


  def GetParent_test( self ):
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
      yield ( self._Message,
              'GetParent_Clang_test.cc',
              test,
              [ 'GetParent' ] )


  def _RunFixIt( self, line, column, lang, file_name, check ):
    contents = open( self._PathToTestFile( file_name ) ).read()

    language_options = {
      'cpp11': {
        'compilation_flags': [ '-x',
                                'c++',
                                '-std=c++11',
                                '-Wall',
                                '-Wextra',
                                '-pedantic' ],
        'filetype'         : 'cpp',
      },
      'objective-c': {
        'compilation_flags': [ '-x',
                               'objective-c',
                               '-Wall',
                               '-Wextra' ],
        'filetype'         : 'objc',
      },
    }

    # Build the command arguments from the standard ones and the language-specific
    # arguments.
    args = {
      'completer_target' : 'filetype_default',
      'contents'         : contents,
      'command_arguments': [ 'FixIt' ],
      'line_num'         : line,
      'column_num'       : column,
    }
    args.update( language_options[ lang ] )

    # get the diagnostics for the file
    event_data = self._BuildRequest( **args )

    results = self._app.post_json( '/run_completer_command', event_data ).json

    pprint( results )
    check( results )


  def _FixIt_Check_cpp11_Ins( self, results ):
    # First fixit
    #   switch(A()) { // expected-error{{explicit conversion to}}
    assert_that( results, has_entries( {
      'fixits': contains( has_entries( {
        'chunks': contains(
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
        'location': has_entries( { 'line_num': 16, 'column_num': 3 } )
      } ) )
    } ) )


  def _FixIt_Check_cpp11_InsMultiLine( self, results ):
    # Similar to _FixIt_Check_cpp11_1 but inserts split across lines
    #
    assert_that( results, has_entries( {
      'fixits': contains( has_entries( {
        'chunks': contains(
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
        'location': has_entries( { 'line_num': 25, 'column_num': 3 } )
      } ) )
    } ) )


  def _FixIt_Check_cpp11_Del( self, results ):
    # Removal of ::
    assert_that( results, has_entries( {
      'fixits': contains( has_entries( {
        'chunks': contains(
          has_entries( {
            'replacement_text': equal_to(''),
            'range': has_entries( {
              'start': has_entries( { 'line_num': 35, 'column_num': 7 } ),
              'end'  : has_entries( { 'line_num': 35, 'column_num': 9 } ),
            } ),
          } )
        ),
        'location': has_entries( { 'line_num': 35, 'column_num': 7 } )
      } ) )
    } ) )


  def _FixIt_Check_cpp11_Repl( self, results ):
    assert_that( results, has_entries( {
      'fixits': contains( has_entries( {
        'chunks': contains(
          has_entries( {
            'replacement_text': equal_to('foo'),
            'range': has_entries( {
              'start': has_entries( { 'line_num': 40, 'column_num': 6 } ),
              'end'  : has_entries( { 'line_num': 40, 'column_num': 9 } ),
            } ),
          } )
        ),
        'location': has_entries( { 'line_num': 40, 'column_num': 6 } )
      } ) )
    } ) )


  def _FixIt_Check_cpp11_DelAdd( self, results ):
    assert_that( results, has_entries( {
      'fixits': contains( has_entries( {
        'chunks': contains(
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
        'location': has_entries( { 'line_num': 48, 'column_num': 3 } )
      } ) )
    } ) )


  def _FixIt_Check_objc( self, results ):
    assert_that( results, has_entries( {
      'fixits': contains( has_entries( {
        'chunks': contains(
          has_entries( {
            'replacement_text': equal_to('id'),
            'range': has_entries( {
              'start': has_entries( { 'line_num': 5, 'column_num': 3 } ),
              'end'  : has_entries( { 'line_num': 5, 'column_num': 3 } ),
            } ),
          } )
        ),
        'location': has_entries( { 'line_num': 5, 'column_num': 3 } )
      } ) )
    } ) )


  def _FixIt_Check_objc_NoFixIt( self, results ):
    # and finally, a warning with no fixits
    assert_that( results, equal_to( { 'fixits': [] } ) )


  def _FixIt_Check_cpp11_MultiFirst( self, results ):
    assert_that( results, has_entries( {
      'fixits': contains(
        # first fix-it at 54,16
        has_entries( {
          'chunks': contains(
            has_entries( {
              'replacement_text': equal_to('foo'),
              'range': has_entries( {
                'start': has_entries( { 'line_num': 54, 'column_num': 16 } ),
                'end'  : has_entries( { 'line_num': 54, 'column_num': 19 } ),
              } ),
            } )
          ),
          'location': has_entries( { 'line_num': 54, 'column_num': 16 } )
        } ),
        # second fix-it at 54,52
        has_entries( {
          'chunks': contains(
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
          'location': has_entries( { 'line_num': 54, 'column_num': 52 } )
        } )
      )
    } ) )


  def _FixIt_Check_cpp11_MultiSecond( self, results ):
    assert_that( results, has_entries( {
      'fixits': contains(
        # second fix-it at 54,52
        has_entries( {
          'chunks': contains(
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
          'location': has_entries( { 'line_num': 54, 'column_num': 52 } )
        } ),
        # first fix-it at 54,16
        has_entries( {
          'chunks': contains(
            has_entries( {
              'replacement_text': equal_to('foo'),
              'range': has_entries( {
                'start': has_entries( { 'line_num': 54, 'column_num': 16 } ),
                'end'  : has_entries( { 'line_num': 54, 'column_num': 19 } ),
              } ),
            } )
          ),
          'location': has_entries( { 'line_num': 54, 'column_num': 16 } )
        } )
      )
    } ) )


  def FixIt_all_test( self ):
    cfile = 'FixIt_Clang_cpp11.cpp'
    mfile = 'FixIt_Clang_objc.m'

    tests = [
      [ 16, 0,  'cpp11', cfile, self._FixIt_Check_cpp11_Ins ],
      [ 16, 1,  'cpp11', cfile, self._FixIt_Check_cpp11_Ins ],
      [ 16, 10, 'cpp11', cfile, self._FixIt_Check_cpp11_Ins ],
      [ 25, 14, 'cpp11', cfile, self._FixIt_Check_cpp11_InsMultiLine ],
      [ 25, 0,  'cpp11', cfile, self._FixIt_Check_cpp11_InsMultiLine ],
      [ 35, 7,  'cpp11', cfile, self._FixIt_Check_cpp11_Del ],
      [ 40, 6,  'cpp11', cfile, self._FixIt_Check_cpp11_Repl ],
      [ 48, 3,  'cpp11', cfile, self._FixIt_Check_cpp11_DelAdd ],

      [ 5, 3,   'objective-c', mfile, self._FixIt_Check_objc ],
      [ 7, 1,   'objective-c', mfile, self._FixIt_Check_objc_NoFixIt ],

      # multiple errors on a single line; both with fixits
      [ 54, 15, 'cpp11', cfile, self._FixIt_Check_cpp11_MultiFirst ],
      [ 54, 16, 'cpp11', cfile, self._FixIt_Check_cpp11_MultiFirst ],
      [ 54, 16, 'cpp11', cfile, self._FixIt_Check_cpp11_MultiFirst ],
      [ 54, 17, 'cpp11', cfile, self._FixIt_Check_cpp11_MultiFirst ],
      [ 54, 18, 'cpp11', cfile, self._FixIt_Check_cpp11_MultiFirst ],

      # should put closest fix-it first?
      [ 54, 51, 'cpp11', cfile, self._FixIt_Check_cpp11_MultiSecond ],
      [ 54, 52, 'cpp11', cfile, self._FixIt_Check_cpp11_MultiSecond ],
      [ 54, 53, 'cpp11', cfile, self._FixIt_Check_cpp11_MultiSecond ],
    ]

    for test in tests:
      yield self._RunFixIt, test[0], test[1], test[2], test[3], test[4]


  def GetDoc_Variable_test( self ):
    filepath = self._PathToTestFile( 'GetDoc_Clang.cc' )
    contents = open( filepath ).read()

    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'cpp',
                                     compilation_flags = [ '-x', 'c++' ],
                                     line_num = 70,
                                     column_num = 24,
                                     contents = contents,
                                     command_arguments = [ 'GetDoc' ],
                                     completer_target = 'filetype_default' )

    response = self._app.post_json( '/run_completer_command', event_data ).json

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


  def GetDoc_Method_test( self ):
    filepath = self._PathToTestFile( 'GetDoc_Clang.cc' )
    contents = open( filepath ).read()

    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'cpp',
                                     compilation_flags = [ '-x', 'c++' ],
                                     line_num = 22,
                                     column_num = 13,
                                     contents = contents,
                                     command_arguments = [ 'GetDoc' ],
                                     completer_target = 'filetype_default' )

    response = self._app.post_json( '/run_completer_command', event_data ).json

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


  def GetDoc_Namespace_test( self ):
    filepath = self._PathToTestFile( 'GetDoc_Clang.cc' )
    contents = open( filepath ).read()

    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'cpp',
                                     compilation_flags = [ '-x', 'c++' ],
                                     line_num = 65,
                                     column_num = 14,
                                     contents = contents,
                                     command_arguments = [ 'GetDoc' ],
                                     completer_target = 'filetype_default' )

    response = self._app.post_json( '/run_completer_command', event_data ).json

    pprint( response )

    eq_( response, {
      'detailed_info': """\
namespace Test {}
This is a test namespace
Type: 
Name: Test
---
This is a test namespace""" } )


  def GetDoc_Undocumented_test( self ):
    filepath = self._PathToTestFile( 'GetDoc_Clang.cc' )
    contents = open( filepath ).read()

    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'cpp',
                                     compilation_flags = [ '-x', 'c++' ],
                                     line_num = 81,
                                     column_num = 17,
                                     contents = contents,
                                     command_arguments = [ 'GetDoc' ],
                                     completer_target = 'filetype_default' )

    response = self._app.post_json( '/run_completer_command',
                                    event_data,
                                    expect_errors = True )

    eq_( response.status_code, httplib.INTERNAL_SERVER_ERROR )

    assert_that( response.json,
                 self._ErrorMatcher( ValueError, NO_DOCUMENTATION_MESSAGE ) )


  def GetDoc_NoCursor_test( self ):
    filepath = self._PathToTestFile( 'GetDoc_Clang.cc' )
    contents = open( filepath ).read()

    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'cpp',
                                     compilation_flags = [ '-x', 'c++' ],
                                     line_num = 1,
                                     column_num = 1,
                                     contents = contents,
                                     command_arguments = [ 'GetDoc' ],
                                     completer_target = 'filetype_default' )

    response = self._app.post_json( '/run_completer_command',
                                    event_data,
                                    expect_errors = True )

    eq_( response.status_code, httplib.INTERNAL_SERVER_ERROR )

    assert_that( response.json,
                 self._ErrorMatcher( ValueError, NO_DOCUMENTATION_MESSAGE ) )


  # Following tests repeat the tests above, but without re-parsing the file
  def GetDocQuick_Variable_test( self ):
    filepath = self._PathToTestFile( 'GetDoc_Clang.cc' )
    contents = open( filepath ).read()

    self._app.post_json( '/event_notification',
                         self._BuildRequest( filepath = filepath,
                                             filetype = 'cpp',
                                             compilation_flags = [ '-x', 'c++' ],
                                             contents = contents,
                                             event_name = 'FileReadyToParse' ) )

    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'cpp',
                                     compilation_flags = [ '-x', 'c++' ],
                                     line_num = 70,
                                     column_num = 24,
                                     contents = contents,
                                     command_arguments = [ 'GetDocQuick' ],
                                     completer_target = 'filetype_default' )

    response = self._app.post_json( '/run_completer_command', event_data ).json

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


  def GetDocQuick_Method_test( self ):
    filepath = self._PathToTestFile( 'GetDoc_Clang.cc' )
    contents = open( filepath ).read()

    self._app.post_json(
      '/event_notification',
      self._BuildRequest( filepath = filepath,
                          filetype = 'cpp',
                          compilation_flags = [ '-x', 'c++' ],
                          contents = contents,
                          event_name = 'FileReadyToParse' )
    )

    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'cpp',
                                     compilation_flags = [ '-x', 'c++' ],
                                     line_num = 22,
                                     column_num = 13,
                                     contents = contents,
                                     command_arguments = [ 'GetDocQuick' ],
                                     completer_target = 'filetype_default' )

    response = self._app.post_json( '/run_completer_command', event_data ).json

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


  def GetDocQuick_Namespace_test( self ):
    filepath = self._PathToTestFile( 'GetDoc_Clang.cc' )
    contents = open( filepath ).read()

    self._app.post_json(
      '/event_notification',
      self._BuildRequest( filepath = filepath,
                          filetype = 'cpp',
                          compilation_flags = [ '-x', 'c++' ],
                          contents = contents,
                          event_name = 'FileReadyToParse' )
    )

    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'cpp',
                                     compilation_flags = [ '-x', 'c++' ],
                                     line_num = 65,
                                     column_num = 14,
                                     contents = contents,
                                     command_arguments = [ 'GetDocQuick' ],
                                     completer_target = 'filetype_default' )

    response = self._app.post_json( '/run_completer_command', event_data ).json

    pprint( response )

    eq_( response, {
      'detailed_info': """\
namespace Test {}
This is a test namespace
Type: 
Name: Test
---
This is a test namespace""" } )


  def GetDocQuick_Undocumented_test( self ):
    filepath = self._PathToTestFile( 'GetDoc_Clang.cc' )
    contents = open( filepath ).read()

    self._app.post_json(
      '/event_notification',
      self._BuildRequest( filepath = filepath,
                          filetype = 'cpp',
                          compilation_flags = [ '-x', 'c++' ],
                          contents = contents,
                          event_name = 'FileReadyToParse' )
    )

    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'cpp',
                                     compilation_flags = [ '-x', 'c++' ],
                                     line_num = 81,
                                     column_num = 17,
                                     contents = contents,
                                     command_arguments = [ 'GetDocQuick' ],
                                     completer_target = 'filetype_default' )

    response = self._app.post_json( '/run_completer_command',
                                    event_data,
                                    expect_errors = True )

    eq_( response.status_code, httplib.INTERNAL_SERVER_ERROR )

    assert_that( response.json,
                 self._ErrorMatcher( ValueError, NO_DOCUMENTATION_MESSAGE ) )


  def GetDocQuick_NoCursor_test( self ):
    filepath = self._PathToTestFile( 'GetDoc_Clang.cc' )
    contents = open( filepath ).read()

    self._app.post_json(
      '/event_notification',
      self._BuildRequest( filepath = filepath,
                          filetype = 'cpp',
                          compilation_flags = [ '-x', 'c++' ],
                          contents = contents,
                          event_name = 'FileReadyToParse' )
    )

    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'cpp',
                                     compilation_flags = [ '-x', 'c++' ],
                                     line_num = 1,
                                     column_num = 1,
                                     contents = contents,
                                     command_arguments = [ 'GetDocQuick' ],
                                     completer_target = 'filetype_default' )

    response = self._app.post_json( '/run_completer_command',
                                    event_data,
                                    expect_errors = True )

    eq_( response.status_code, httplib.INTERNAL_SERVER_ERROR )

    assert_that( response.json,
                 self._ErrorMatcher( ValueError, NO_DOCUMENTATION_MESSAGE ) )


  def GetDocQuick_NoReadyToParse_test( self ):
    filepath = self._PathToTestFile( 'GetDoc_Clang.cc' )
    contents = open( filepath ).read()

    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'cpp',
                                     compilation_flags = [ '-x', 'c++' ],
                                     line_num = 11,
                                     column_num = 18,
                                     contents = contents,
                                     command_arguments = [ 'GetDocQuick' ],
                                     completer_target = 'filetype_default' )

    response = self._app.post_json( '/run_completer_command', event_data ).json

    eq_( response, {
      'detailed_info': """\
int get_a_global_variable(bool test)
This is a method which is only pretend global
Type: int (bool)
Name: get_a_global_variable
---
This is a method which is only pretend global
@param test Set this to true. Do it.""" } )
