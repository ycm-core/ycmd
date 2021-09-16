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

from hamcrest import ( assert_that, calling, contains_exactly,
                       contains_inanyorder, contains_string, empty, equal_to,
                       has_entry, has_entries, raises, matches_regexp )
from unittest.mock import patch
from unittest import TestCase
from pprint import pprint
from webtest import AppError
import itertools
import requests
import os.path

from ycmd import handlers
from ycmd.completers.cpp.clang_completer import ( NO_DOCUMENTATION_MESSAGE,
                                                  PARSING_FILE_MESSAGE )
from ycmd.tests.clang import setUpModule # noqa
from ycmd.tests.clang import ( MockCoreClangCompleter,
                               PathToTestFile,
                               SharedYcmd )
from ycmd.tests.test_utils import ( BuildRequest,
                                    ErrorMatcher,
                                    ChunkMatcher,
                                    LocationMatcher,
                                    LineColMatcher )
from ycmd.utils import ReadFile


def RunGoToTest_all( app, filename, command, test ):
  contents = ReadFile( PathToTestFile( filename ) )
  common_request = {
    'completer_target' : 'filetype_default',
    'filepath'         : PathToTestFile( filename ),
    'command_arguments': command,
    'compilation_flags': [ '-x',
                           'c++' ],
    'line_num'         : 10,
    'column_num'       : 3,
    'contents'         : contents,
    'filetype'         : 'cpp'
  }
  common_response = {
    'filepath': os.path.abspath( PathToTestFile( filename ) ),
  }

  if 'extra_conf' in test:
    common_request.pop( 'compilation_flags' )
    app.post_json( '/load_extra_conf_file', {
      'filepath': PathToTestFile( *test[ 'extra_conf' ] ) } )

  request = common_request
  request.update( {
      'line_num'  : test[ 'request' ][ 0 ],
      'column_num': test[ 'request' ][ 1 ],
  } )
  response = common_response
  response.update( {
      'line_num'  : test[ 'response' ][ 0 ],
      'column_num': test[ 'response' ][ 1 ],
  } )
  if len( test[ 'response' ] ) > 2:
    response.update( {
      'filepath': PathToTestFile( test[ 'response' ][ 2 ] )
    } )

  goto_data = BuildRequest( **request )

  actual_response = app.post_json( '/run_completer_command', goto_data ).json
  pprint( actual_response )
  assert_that( response, equal_to( actual_response ) )


def RunGoToIncludeTest( app, command, test ):
  app.post_json(
    '/load_extra_conf_file',
    { 'filepath': PathToTestFile( 'test-include',
                                  '.ycm_extra_conf.py' ) } )

  filepath = PathToTestFile( 'test-include', 'main.cpp' )
  goto_data = BuildRequest( filepath = filepath,
                            filetype = 'cpp',
                            contents = ReadFile( filepath ),
                            command_arguments = [ command ],
                            line_num = test[ 'request' ][ 0 ],
                            column_num = test[ 'request' ][ 1 ] )

  response = {
    'filepath'   : PathToTestFile( 'test-include', test[ 'response' ] ),
    'line_num'   : 1,
    'column_num' : 1,
  }

  actual_response = app.post_json( '/run_completer_command', goto_data ).json
  pprint( actual_response )
  assert_that( response, equal_to( actual_response ) )


def RunGetSemanticTest( app, filepath, filetype, test, command ):
  contents = ReadFile( filepath )
  language = { 'cpp': 'c++', 'cuda': 'cuda' }

  # We use the -fno-delayed-template-parsing flag to not delay
  # parsing of templates on Windows.  This is the default on
  # other platforms.  See the _ExtraClangFlags function in
  # ycmd/completers/cpp/flags.py file for more information.
  common_args = {
    'completer_target' : 'filetype_default',
    'command_arguments': command,
    'compilation_flags': [ '-x',
                           language[ filetype ],
                           # C++11 flag is needed for lambda functions
                           '-std=c++11',
                           '-fno-delayed-template-parsing' ],
    'line_num'         : 10,
    'column_num'       : 3,
    'filepath'         : filepath,
    'contents'         : contents,
    'filetype'         : filetype
  }

  args = test[ 0 ]
  expected = test[ 1 ]

  if 'extra_conf' in args:
    common_args.pop( 'compilation_flags' )
    app.post_json( '/load_extra_conf_file', {
      'filepath': PathToTestFile( *args[ 'extra_conf' ] ) } )
    args.pop( 'extra_conf' )

  request = common_args
  request.update( args )

  request_data = BuildRequest( **request )

  response = app.post_json( '/run_completer_command', request_data ).json
  pprint( response )
  assert_that( response, has_entry( 'message', expected ) )


def FixIt_Check_cpp11_Ins( results ):
  # First fixit
  #   switch(A()) { // expected-error{{explicit conversion to}}
  assert_that( results, has_entries( {
    'fixits': contains_exactly( has_entries( {
      'chunks': contains_exactly(
        has_entries( {
          'replacement_text': equal_to( 'static_cast<int>(' ),
          'range': has_entries( {
            'start': has_entries( { 'line_num': 16, 'column_num': 10 } ),
            'end'  : has_entries( { 'line_num': 16, 'column_num': 10 } ),
          } ),
        } ),
        has_entries( {
          'replacement_text': equal_to( ')' ),
          'range': has_entries( {
            'start': has_entries( { 'line_num': 16, 'column_num': 13 } ),
            'end'  : has_entries( { 'line_num': 16, 'column_num': 13 } ),
          } ),
        } )
      ),
      'location': has_entries( { 'line_num': 16, 'column_num': 3 } )
    } ) )
  } ) )


def FixIt_Check_cpp11_InsMultiLine( results ):
  # Similar to FixIt_Check_cpp11_1 but inserts split across lines
  #
  assert_that( results, has_entries( {
    'fixits': contains_exactly( has_entries( {
      'chunks': contains_exactly(
        has_entries( {
          'replacement_text': equal_to( 'static_cast<int>(' ),
          'range': has_entries( {
            'start': has_entries( { 'line_num': 26, 'column_num': 7 } ),
            'end'  : has_entries( { 'line_num': 26, 'column_num': 7 } ),
          } ),
        } ),
        has_entries( {
          'replacement_text': equal_to( ')' ),
          'range': has_entries( {
            'start': has_entries( { 'line_num': 28, 'column_num': 2 } ),
            'end'  : has_entries( { 'line_num': 28, 'column_num': 2 } ),
          } ),
        } )
      ),
      'location': has_entries( { 'line_num': 25, 'column_num': 3 } )
    } ) )
  } ) )


def FixIt_Check_cpp11_Del( results ):
  # Removal of ::
  assert_that( results, has_entries( {
    'fixits': contains_exactly( has_entries( {
      'chunks': contains_exactly(
        has_entries( {
          'replacement_text': equal_to( '' ),
          'range': has_entries( {
            'start': has_entries( { 'line_num': 35, 'column_num': 7 } ),
            'end'  : has_entries( { 'line_num': 35, 'column_num': 9 } ),
          } ),
        } )
      ),
      'location': has_entries( { 'line_num': 35, 'column_num': 7 } )
    } ) )
  } ) )


def FixIt_Check_cpp11_Repl( results ):
  assert_that( results, has_entries( {
    'fixits': contains_exactly( has_entries( {
      'chunks': contains_exactly(
        has_entries( {
          'replacement_text': equal_to( 'foo' ),
          'range': has_entries( {
            'start': has_entries( { 'line_num': 40, 'column_num': 6 } ),
            'end'  : has_entries( { 'line_num': 40, 'column_num': 9 } ),
          } ),
        } )
      ),
      'location': has_entries( { 'line_num': 40, 'column_num': 6 } )
    } ) )
  } ) )


def FixIt_Check_cpp11_DelAdd( results ):
  assert_that( results, has_entries( {
    'fixits': contains_exactly( has_entries( {
      'chunks': contains_exactly(
        has_entries( {
          'replacement_text': equal_to( '' ),
          'range': has_entries( {
            'start': has_entries( { 'line_num': 48, 'column_num': 3 } ),
            'end'  : has_entries( { 'line_num': 48, 'column_num': 4 } ),
          } ),
        } ),
        has_entries( {
          'replacement_text': equal_to( '~' ),
          'range': has_entries( {
            'start': has_entries( { 'line_num': 48, 'column_num': 9 } ),
            'end'  : has_entries( { 'line_num': 48, 'column_num': 9 } ),
          } ),
        } ),
      ),
      'location': has_entries( { 'line_num': 48, 'column_num': 3 } )
    } ) )
  } ) )


def FixIt_Check_objc( results ):
  assert_that( results, has_entries( {
    'fixits': contains_exactly( has_entries( {
      'chunks': contains_exactly(
        has_entries( {
          'replacement_text': equal_to( 'id' ),
          'range': has_entries( {
            'start': has_entries( { 'line_num': 5, 'column_num': 3 } ),
            'end'  : has_entries( { 'line_num': 5, 'column_num': 3 } ),
          } ),
        } )
      ),
      'location': has_entries( { 'line_num': 5, 'column_num': 3 } )
    } ) )
  } ) )


def FixIt_Check_objc_NoFixIt( results ):
  # and finally, a warning with no fixits
  assert_that( results, equal_to( { 'fixits': [] } ) )


def FixIt_Check_cpp11_MultiFirst( results ):
  assert_that( results, has_entries( {
    'fixits': contains_exactly(
      # first fix-it at 54,16
      has_entries( {
        'chunks': contains_exactly(
          has_entries( {
            'replacement_text': equal_to( 'foo' ),
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
        'chunks': contains_exactly(
          has_entries( {
            'replacement_text': equal_to( '' ),
            'range': has_entries( {
              'start': has_entries( { 'line_num': 54, 'column_num': 52 } ),
              'end'  : has_entries( { 'line_num': 54, 'column_num': 53 } ),
            } ),
          } ),
          has_entries( {
            'replacement_text': equal_to( '~' ),
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


def FixIt_Check_cpp11_MultiSecond( results ):
  assert_that( results, has_entries( {
    'fixits': contains_exactly(
      # second fix-it at 54,52
      has_entries( {
        'chunks': contains_exactly(
          has_entries( {
            'replacement_text': equal_to( '' ),
            'range': has_entries( {
              'start': has_entries( { 'line_num': 54, 'column_num': 52 } ),
              'end'  : has_entries( { 'line_num': 54, 'column_num': 53 } ),
            } ),
          } ),
          has_entries( {
            'replacement_text': equal_to( '~' ),
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
        'chunks': contains_exactly(
          has_entries( {
            'replacement_text': equal_to( 'foo' ),
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


def FixIt_Check_unicode_Ins( results ):
  assert_that( results, has_entries( {
    'fixits': contains_exactly( has_entries( {
      'chunks': contains_exactly(
        has_entries( {
          'replacement_text': equal_to( ';' ),
          'range': has_entries( {
            'start': has_entries( { 'line_num': 21, 'column_num': 39 } ),
            'end'  : has_entries( { 'line_num': 21, 'column_num': 39 } ),
          } ),
        } )
      ),
      'location': has_entries( { 'line_num': 21, 'column_num': 39 } )
    } ) )
  } ) )


def FixIt_Check_cpp11_Note( results ):
  assert_that( results, has_entries( {
    'fixits': contains_exactly(
      # First note: put parens around it
      has_entries( {
        'text': contains_string( 'parentheses around the assignment' ),
        'chunks': contains_exactly(
          ChunkMatcher( '(',
                        LineColMatcher( 59, 8 ),
                        LineColMatcher( 59, 8 ) ),
          ChunkMatcher( ')',
                        LineColMatcher( 61, 12 ),
                        LineColMatcher( 61, 12 ) )
        ),
        'location': LineColMatcher( 60, 8 ),
      } ),

      # Second note: change to ==
      has_entries( {
        'text': contains_string( '==' ),
        'chunks': contains_exactly(
          ChunkMatcher( '==',
                        LineColMatcher( 60, 8 ),
                        LineColMatcher( 60, 9 ) )
        ),
        'location': LineColMatcher( 60, 8 ),
      } )
    )
  } ) )


def FixIt_Check_cpp11_SpellCheck( results ):
  assert_that( results, has_entries( {
    'fixits': contains_exactly(
      # Change to SpellingIsNotMyStrongPoint
      has_entries( {
        'text': contains_string( "did you mean 'SpellingIsNotMyStrongPoint'" ),
        'chunks': contains_exactly(
          ChunkMatcher( 'SpellingIsNotMyStrongPoint',
                        LineColMatcher( 72, 9 ),
                        LineColMatcher( 72, 35 ) )
        ),
        'location': LineColMatcher( 72, 9 ),
      } ) )
  } ) )


def FixIt_Check_cuda( results ):
  assert_that( results, has_entries( {
    'fixits': contains_exactly(
      has_entries( {
        'text': contains_string(
           "error: kernel function type 'int ()' must have void " ),
        'chunks': contains_exactly(
          ChunkMatcher( 'void',
                        LineColMatcher( 3, 12 ),
                        LineColMatcher( 3, 15 ) )
        ),
        'location': LineColMatcher( 3, 12 ),
      } ) )
  } ) )


def RunFixItTest( app, line, column, lang, file_path, check ):
  contents = ReadFile( file_path )

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
    'cuda': {
      'compilation_flags': [ '-x',
                             'cuda',
                             '-std=c++11',
                             '-Wall',
                             '-Wextra',
                             '-pedantic' ],
      'filetype'         : 'cuda',
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
    'filepath'         : file_path,
    'command_arguments': [ 'FixIt' ],
    'line_num'         : line,
    'column_num'       : column,
  }
  args.update( language_options[ lang ] )

  # Get the fixes for the file.
  event_data = BuildRequest( **args )

  results = app.post_json( '/run_completer_command', event_data ).json

  pprint( results )
  check( results )


def Subcommands_StillParsingError( app, command ):
  filepath = PathToTestFile( 'test.cpp' )

  data = BuildRequest( command_arguments = [ command ],
                       compilation_flags = [ '-x', 'c++' ],
                       line_num = 1,
                       column_num = 1,
                       filepath = filepath,
                       contents = '',
                       filetype = 'cpp' )

  response = app.post_json( '/run_completer_command',
                            data,
                            expect_errors = True )

  assert_that( response.status_code,
               equal_to( requests.codes.internal_server_error ) )

  pprint( response.json )

  assert_that( response.json, ErrorMatcher( RuntimeError,
                                            PARSING_FILE_MESSAGE ) )


class SubcommandsTest( TestCase ):
  @SharedYcmd
  def test_Subcommands_DefinedSubcommands( self, app ):
    subcommands_data = BuildRequest( completer_target = 'cpp' )
    assert_that( app.post_json( '/defined_subcommands', subcommands_data ).json,
                 contains_inanyorder(
                   'ClearCompilationFlagCache',
                   'FixIt',
                   'GetDoc',
                   'GetDocImprecise',
                   'GetParent',
                   'GetType',
                   'GetTypeImprecise',
                   'GoTo',
                   'GoToDeclaration',
                   'GoToDefinition',
                   'GoToImprecise',
                   'GoToInclude' ) )


  @SharedYcmd
  def test_Subcommands_GoTo_ZeroBasedLineAndColumn( self, app ):
    contents = ReadFile( PathToTestFile(
      'GoTo_Clang_ZeroBasedLineAndColumn_test.cc' ) )

    goto_data = BuildRequest( completer_target = 'filetype_default',
                              command_arguments = [ 'GoToDefinition' ],
                              compilation_flags = [ '-x', 'c++' ],
                              line_num = 10,
                              column_num = 3,
                              contents = contents,
                              filetype = 'cpp' )

    assert_that( app.post_json( '/run_completer_command', goto_data ).json,
                 LocationMatcher( os.path.abspath( '/foo' ), 2, 8 ) )


  @SharedYcmd
  def test_Subcommands_GoTo_CUDA( self, app ):
    filepath = PathToTestFile( 'cuda', 'basic.cu' )
    contents = ReadFile( filepath )

    goto_data = BuildRequest( completer_target = 'filetype_default',
                              command_arguments = [ 'GoToDefinition' ],
                              compilation_flags = [ '-x', 'cuda' ],
                              line_num = 8,
                              column_num = 3,
                              filepath = filepath,
                              contents = contents,
                              filetype = 'cuda' )

    assert_that( app.post_json( '/run_completer_command', goto_data ).json,
                 LocationMatcher( filepath, 4, 17 ) )


  @SharedYcmd
  def test_Subcommands_GoTo_all( self, app ):
    # GoToDeclaration
    tests = [
      # Local::x -> definition/declaration of x
      { 'request': [ 23, 21 ], 'response': [ 4,   9 ] },
      # Local::in_line -> definition/declaration of Local::in_line
      { 'request': [ 24, 26 ], 'response': [ 6,  10 ] },
      # Local -> definition/declaration of Local
      { 'request': [ 24, 16 ], 'response': [ 2,  11 ] },
      # Local::out_of_line -> declaration of Local::out_of_line
      { 'request': [ 25, 27 ], 'response': [ 11, 10 ] },
      # GoToDeclaration on definition of out_of_line moves to declaration
      { 'request': [ 14, 13 ], 'response': [ 11, 10 ] },
      # main -> declaration of main
      { 'request': [ 21,  7 ], 'response': [ 19,  5 ] },
      # Unicøde
      { 'request': [ 34,  8 ], 'response': [ 32, 26 ] },
      # Another_Unicøde
      { 'request': [ 36, 25 ], 'response': [ 32, 54 ] },
      { 'request': [ 38,  3 ], 'response': [ 36, 28 ] },
    ]

    for test in tests:
      RunGoToTest_all( app,
                       'GoTo_all_Clang_test.cc',
                       [ 'GoToDeclaration' ],
                       test )

    # GoToDefinition
    tests = [
      # Local::x -> declaration/definition of x
      { 'request': [ 23, 21 ], 'response': [ 4,   9 ] },
      # Local::in_line -> declaration/definition of Local::in_line
      { 'request': [ 24, 26 ], 'response': [ 6,  10 ] },
      # Local -> declaration/definition of Local
      { 'request': [ 24, 16 ], 'response': [ 2,  11 ] },
      # Local::out_of_line -> definition of Local::out_of_line
      { 'request': [ 25, 27 ], 'response': [ 14, 13 ] },
      # GoToDefinition on definition of out_of_line moves to itself
      { 'request': [ 14, 13 ], 'response': [ 14, 13 ] },
      # main -> definition of main (not declaration)
      { 'request': [ 21,  7 ], 'response': [ 21,  5 ] },
      # Unicøde
      { 'request': [ 34,  8 ], 'response': [ 32, 26 ] },
    ]

    for test in tests:
      RunGoToTest_all( app,
                       'GoTo_all_Clang_test.cc',
                       [ 'GoToDefinition' ],
                       test )

    # GoTo
    tests = [
      # Local::x -> declaration/definition of x
      { 'request': [ 23, 21 ], 'response': [ 4,   9 ] },
      # Local::in_line -> declaration/definition of Local::in_line
      { 'request': [ 24, 26 ], 'response': [ 6,  10 ] },
      # Local -> declaration/definition of Local
      { 'request': [ 24, 16 ], 'response': [ 2,  11 ] },
      # Local::out_of_line -> definition of Local::out_of_line
      { 'request': [ 25, 27 ], 'response': [ 14, 13 ] },
      # GoTo on definition of out_of_line moves to declaration
      { 'request': [ 14, 13 ], 'response': [ 11, 10 ] },
      # GoTo on declaration of out_of_line moves to definition
      { 'request': [ 11, 17 ], 'response': [ 14, 13 ] },
      # main -> definition of main
      { 'request': [ 21,  7 ], 'response': [ 19,  5 ] },
      # Unicøde
      { 'request': [ 34,  8 ], 'response': [ 32, 26 ] },
      # Another_Unicøde
      { 'request': [ 36, 25 ], 'response': [ 32, 54 ] },
      { 'request': [ 38,  3 ], 'response': [ 36, 28 ] },
    ]

    for test in tests:
      RunGoToTest_all( app,
                       'GoTo_all_Clang_test.cc',
                       [ 'GoTo' ],
                       test )

    # GoToImprecise - identical to GoTo
    tests = [
      # Local::x -> declaration/definition of x
      { 'request': [ 23, 21 ], 'response': [ 4,   9 ] },
      # Local::in_line -> declaration/definition of Local::in_line
      { 'request': [ 24, 26 ], 'response': [ 6,  10 ] },
      # Local -> declaration/definition of Local
      { 'request': [ 24, 16 ], 'response': [ 2,  11 ] },
      # Local::out_of_line -> definition of Local::out_of_line
      { 'request': [ 25, 27 ], 'response': [ 14, 13 ] },
      # GoToImprecise on definition of out_of_line moves to declaration
      { 'request': [ 14, 13 ], 'response': [ 11, 10 ] },
      # GoToImprecise on declaration of out_of_line moves to definition
      { 'request': [ 11, 17 ], 'response': [ 14, 13 ] },
      # main -> definition of main
      { 'request': [ 21,  7 ], 'response': [ 19,  5 ] },
      # Unicøde
      { 'request': [ 34,  8 ], 'response': [ 32, 26 ] },
      # Another_Unicøde
      { 'request': [ 36, 25 ], 'response': [ 32, 54 ] },
      { 'request': [ 38,  3 ], 'response': [ 36, 28 ] },
    ]

    for test in tests:
      RunGoToTest_all( app,
                       'GoTo_all_Clang_test.cc',
                       [ 'GoToImprecise' ],
                       test )


  @SharedYcmd
  def test_Subcommands_GoTo_all_Fail( self, app ):
    cursor_on_nothing = { 'request': [ 13, 1 ], 'response': [ 1, 1 ] }
    cursor_on_another_unicode = { 'request': [ 36, 17 ], 'response': [ 1, 1 ] }
    cursor_on_keyword = { 'request': [ 16, 6 ], 'response': [ 1, 1 ] }

    # GoToDeclaration
    assert_that(
      calling( RunGoToTest_all ).with_args( app,
                                            'GoTo_all_Clang_test.cc',
                                            [ 'GoToDeclaration' ],
                                            cursor_on_nothing ),
      raises( AppError, r'Can\\\'t jump to declaration.' ) )
    assert_that(
      calling( RunGoToTest_all ).with_args( app,
                                            'GoTo_all_Clang_test.cc',
                                            [ 'GoToDeclaration' ],
                                            cursor_on_keyword ),
      raises( AppError, r'Can\\\'t jump to declaration.' ) )

    # GoToDefinition
    assert_that(
      calling( RunGoToTest_all ).with_args( app,
                                            'GoTo_all_Clang_test.cc',
                                            [ 'GoToDefinition' ],
                                            cursor_on_nothing ),
      raises( AppError, r'Can\\\'t jump to definition.' ) )
    assert_that(
      calling( RunGoToTest_all ).with_args( app,
                                            'GoTo_all_Clang_test.cc',
                                            [ 'GoToDefinition' ],
                                            cursor_on_another_unicode ),
      raises( AppError, r'Can\\\'t jump to definition.' ) )

    # GoTo
    assert_that(
      calling( RunGoToTest_all ).with_args( app,
                                            'GoTo_all_Clang_test.cc',
                                            [ 'GoTo' ],
                                            cursor_on_nothing ),
      raises( AppError, r'Can\\\'t jump to definition or declaration.' ) )
    assert_that(
      calling( RunGoToTest_all ).with_args( app,
                                            'GoTo_all_Clang_test.cc',
                                            [ 'GoTo' ],
                                            cursor_on_keyword ),
      raises( AppError, r'Can\\\'t jump to definition or declaration.' ) )

    # GoToImprecise
    assert_that(
      calling( RunGoToTest_all ).with_args( app,
                                            'GoTo_all_Clang_test.cc',
                                            [ 'GoToImprecise' ],
                                            cursor_on_nothing ),
      raises( AppError, r'Can\\\'t jump to definition or declaration.' ) )
    assert_that(
      calling( RunGoToTest_all ).with_args( app,
                                            'GoTo_all_Clang_test.cc',
                                            [ 'GoToImprecise' ],
                                            cursor_on_keyword ),
      raises( AppError, r'Can\\\'t jump to definition or declaration.' ) )


  @SharedYcmd
  def test_Subcommands_GoToInclude( self, app ):
    for cmd, test in itertools.product(
      [ 'GoToInclude', 'GoTo', 'GoToImprecise' ],
      [
        { 'request': [ 1, 1 ], 'response': 'a.hpp' },
        { 'request': [ 2, 1 ], 'response': os.path.join( 'system', 'a.hpp' ) },
        { 'request': [ 3, 1 ], 'response': os.path.join( 'quote',  'b.hpp' ) },
        { 'request': [ 5, 1 ], 'response': os.path.join( 'system', 'c.hpp' ) },
        { 'request': [ 6, 1 ], 'response': os.path.join( 'system', 'c.hpp' ) },
        { 'request': [ 7, 1 ], 'response': os.path.join( 'Frameworks',
                                                         'OpenGL.framework',
                                                         'Headers',
                                                         'gl.h' ) },
        { 'request': [ 8, 1 ], 'response': os.path.join( 'Frameworks',
                                                         'OpenGL.framework',
                                                         'Headers',
                                                         'gl.h' ) },
      ] ):
      with self.subTest( cmd = cmd, test = test ):
        RunGoToIncludeTest( app, cmd, test )


  @SharedYcmd
  def test_Subcommands_GoToInclude_Fail( self, app ):
    test = { 'request': [ 4, 1 ], 'response': '' }
    assert_that(
      calling( RunGoToIncludeTest ).with_args( app,
                                               'GoToInclude', test ),
      raises( AppError, 'Include file not found.' ) )
    assert_that(
      calling( RunGoToIncludeTest ).with_args( app,
                                               'GoTo', test ),
      raises( AppError, 'Include file not found.' ) )
    assert_that(
      calling( RunGoToIncludeTest ).with_args( app,
                                               'GoToImprecise', test ),
      raises( AppError, 'Include file not found.' ) )

    test = { 'request': [ 9, 1 ], 'response': '' }
    assert_that(
      calling( RunGoToIncludeTest ).with_args( app,
                                               'GoToInclude', test ),
      raises( AppError, 'Not an include/import line.' ) )
    assert_that(
      calling( RunGoToIncludeTest ).with_args( app,
                                               'GoTo', test ),
      raises( AppError, r'Can\\\'t jump to definition or declaration.' ) )
    assert_that(
      calling( RunGoToIncludeTest ).with_args( app,
                                               'GoToImprecise', test ),
      raises( AppError, r'Can\\\'t jump to definition or declaration.' ) )

    # Unclosed #include statement.
    test = { 'request': [ 12, 13 ], 'response': '' }
    assert_that(
      calling( RunGoToIncludeTest ).with_args( app,
                                               'GoToInclude', test ),
      raises( AppError, 'Not an include/import line.' ) )
    assert_that(
      calling( RunGoToIncludeTest ).with_args( app,
                                               'GoTo', test ),
      raises( AppError, r'Can\\\'t jump to definition or declaration.' ) )
    assert_that(
      calling( RunGoToIncludeTest ).with_args( app,
                                               'GoToImprecise', test ),
      raises( AppError, r'Can\\\'t jump to definition or declaration.' ) )


  @SharedYcmd
  def test_Subcommands_GoTo_Unity( self, app ):
    RunGoToTest_all( app, 'unitya.cc', [ 'GoToDeclaration' ], {
      'request': [ 8, 21 ],
      'response': [ 1, 8, 'unity.cc' ],
      'extra_conf': [ '.ycm_extra_conf.py' ],
    } )
    RunGoToTest_all( app, 'unitya.cc', [ 'GoToInclude' ], {
      'request': [ 1, 14 ],
      'response': [ 1, 1, 'unity.h' ],
      'extra_conf': [ '.ycm_extra_conf.py' ],
    } )


  @SharedYcmd
  def test_Subcommands_GetType( self, app ):
    for cmd, test in itertools.product(
       [ 'GetType', 'GetTypeImprecise' ],
       [
         # Basic pod types
         [ { 'line_num': 24, 'column_num':  3 }, 'Foo' ],
         [ { 'line_num':  1, 'column_num':  1 }, 'Internal error: '
                                                 'cursor not valid' ],
         [ { 'line_num': 12, 'column_num':  2 }, 'Foo' ],
         [ { 'line_num': 12, 'column_num':  8 }, 'Foo' ],
         [ { 'line_num': 12, 'column_num':  9 }, 'Foo' ],
         [ { 'line_num': 12, 'column_num': 10 }, 'Foo' ],
         [ { 'line_num': 13, 'column_num':  3 }, 'int' ],
         [ { 'line_num': 13, 'column_num':  7 }, 'int' ],
         [ { 'line_num': 15, 'column_num':  7 }, 'char' ],

         # Function
         [ { 'line_num': 22, 'column_num':  2 }, 'int ()' ],
         [ { 'line_num': 22, 'column_num':  6 }, 'int ()' ],

         # Declared and canonical type
         # On Ns:: (Unknown)
         [ { 'line_num': 25, 'column_num':  3 }, 'Unknown type' ], # sic
         # On Type (Type)
         [ { 'line_num': 25, 'column_num':  8 },
           'Ns::Type => Ns::BasicType<char>' ],
         # On "a" (Ns::Type)
         [ { 'line_num': 25, 'column_num': 15 },
           'Ns::Type => Ns::BasicType<char>' ],
         [ { 'line_num': 26, 'column_num': 13 },
           'Ns::Type => Ns::BasicType<char>' ],

         # Cursor on decl for refs & pointers
         [ { 'line_num': 39, 'column_num':  3 }, 'Foo' ],
         [ { 'line_num': 39, 'column_num': 11 }, 'Foo &' ],
         [ { 'line_num': 39, 'column_num': 15 }, 'Foo' ],
         [ { 'line_num': 40, 'column_num':  3 }, 'Foo' ],
         [ { 'line_num': 40, 'column_num': 11 }, 'Foo *' ],
         [ { 'line_num': 40, 'column_num': 18 }, 'Foo' ],
         [ { 'line_num': 42, 'column_num':  3 }, 'const Foo &' ],
         [ { 'line_num': 42, 'column_num': 16 }, 'const Foo &' ],
         [ { 'line_num': 43, 'column_num':  3 }, 'const Foo *' ],
         [ { 'line_num': 43, 'column_num': 16 }, 'const Foo *' ],

         # Cursor on usage
         [ { 'line_num': 45, 'column_num': 13 }, 'const Foo' ],
         [ { 'line_num': 45, 'column_num': 19 }, 'const int' ],
         [ { 'line_num': 46, 'column_num': 13 }, 'const Foo *' ],
         [ { 'line_num': 46, 'column_num': 20 }, 'const int' ],
         [ { 'line_num': 47, 'column_num': 12 }, 'Foo' ],
         [ { 'line_num': 47, 'column_num': 17 }, 'int' ],
         [ { 'line_num': 48, 'column_num': 12 }, 'Foo *' ],
         [ { 'line_num': 48, 'column_num': 18 }, 'int' ],

         # Auto in declaration
         [ { 'line_num': 28, 'column_num':  3 }, 'Foo &' ],
         [ { 'line_num': 28, 'column_num': 11 }, 'Foo &' ],
         [ { 'line_num': 28, 'column_num': 18 }, 'Foo' ],
         [ { 'line_num': 29, 'column_num':  3 }, 'Foo *' ],
         [ { 'line_num': 29, 'column_num': 11 }, 'Foo *' ],
         [ { 'line_num': 29, 'column_num': 18 }, 'Foo' ],
         [ { 'line_num': 31, 'column_num':  3 }, 'const Foo &' ],
         [ { 'line_num': 31, 'column_num': 16 }, 'const Foo &' ],
         [ { 'line_num': 32, 'column_num':  3 }, 'const Foo *' ],
         [ { 'line_num': 32, 'column_num': 16 }, 'const Foo *' ],

         # Auto in usage
         [ { 'line_num': 34, 'column_num': 14 }, 'const Foo' ],
         [ { 'line_num': 34, 'column_num': 21 }, 'const int' ],
         [ { 'line_num': 35, 'column_num': 14 }, 'const Foo *' ],
         [ { 'line_num': 35, 'column_num': 22 }, 'const int' ],
         [ { 'line_num': 36, 'column_num': 13 }, 'Foo' ],
         [ { 'line_num': 36, 'column_num': 19 }, 'int' ],
         [ { 'line_num': 37, 'column_num': 13 }, 'Foo *' ],
         [ { 'line_num': 37, 'column_num': 20 }, 'int' ],

         # Unicode
         [ { 'line_num': 51, 'column_num': 13 }, 'Unicøde *' ],

         # Bound methods On Win32, methods pick up an __attribute__((thiscall))
         # to annotate their calling convention.  This shows up in the type,
         # which isn't ideal, but also prohibitively complex to try and strip
         # out.
         [ { 'line_num': 53, 'column_num': 15 },
           matches_regexp( r'int \(int\)(?: '
                           r'__attribute__\(\(thiscall\)\))?' ) ],
         [ { 'line_num': 54, 'column_num': 18 },
           matches_regexp( r'int \(int\)(?: '
                           r'__attribute__\(\(thiscall\)\))?' ) ],
       ] ):
      with self.subTest( cmd = cmd, test = test ):
        RunGetSemanticTest( app,
                            PathToTestFile( 'GetType_Clang_test.cc' ),
                            'cpp',
                            test,
                            [ cmd ] )


  @SharedYcmd
  def test_SubCommands_GetType_CUDA( self, app ):
    test = [ { 'line_num': 8, 'column_num': 3, }, 'void ()' ]
    RunGetSemanticTest( app,
                        PathToTestFile( 'cuda', 'basic.cu' ),
                        'cuda',
                        test,
                        [ 'GetType' ] )


  @SharedYcmd
  def test_SubCommands_GetType_Unity( self, app ):
    test = [
      {
        'line_num': 10,
        'column_num': 25,
        'extra_conf': [ '.ycm_extra_conf.py' ]
      },
      'int'
    ]
    RunGetSemanticTest( app,
                        PathToTestFile( 'unitya.cc' ),
                        'cpp',
                        test,
                        [ 'GetType' ] )


  @SharedYcmd
  def test_Subcommands_GetParent( self, app ):
    for test in [
      [ { 'line_num':  1,  'column_num':  1 }, 'Internal error: '
                                              'cursor not valid' ],
      [ { 'line_num':  2,  'column_num':  8 },
        PathToTestFile( 'GetParent_Clang_test.cc' ) ],

      # The reported scope does not include parents
      [ { 'line_num':  3,  'column_num': 11 }, 'A' ],
      [ { 'line_num':  4,  'column_num': 13 }, 'B' ],
      [ { 'line_num':  5,  'column_num': 13 }, 'B' ],
      [ { 'line_num':  9,  'column_num': 17 }, 'do_z_inline()' ],
      [ { 'line_num': 15,  'column_num': 22 }, 'do_anything(T &)' ],
      [ { 'line_num': 19,  'column_num':  9 }, 'A' ],
      [ { 'line_num': 20,  'column_num':  9 }, 'A' ],
      [ { 'line_num': 22,  'column_num': 12 }, 'A' ],
      [ { 'line_num': 23,  'column_num':  5 }, 'do_Z_inline()' ],
      [ { 'line_num': 24,  'column_num': 12 }, 'do_Z_inline()' ],
      [ { 'line_num': 28,  'column_num': 14 }, 'A' ],

      [ { 'line_num': 34,  'column_num':  1 }, 'do_anything(T &)' ],
      [ { 'line_num': 39,  'column_num':  1 }, 'do_x()' ],
      [ { 'line_num': 44,  'column_num':  1 }, 'do_y()' ],
      [ { 'line_num': 49,  'column_num':  1 }, 'main()' ],

      # Lambdas report the name of the variable
      [ { 'line_num': 49,  'column_num': 14 }, 'l' ],
      [ { 'line_num': 50,  'column_num': 19 }, 'l' ],
      [ { 'line_num': 51,  'column_num': 16 }, 'main()' ],
    ]:
      with self.subTest( test = test ):
        RunGetSemanticTest( app,
                            PathToTestFile( 'GetParent_Clang_test.cc' ),
                            'cpp',
                            test,
                            [ 'GetParent' ] )


  @SharedYcmd
  def test_Subcommands_FixIt_all( self, app ):
    for test in [
      # L
      # i   C
      # n   o
      # e   l   Lang     File,  Checker
      [ 16, 0,  'cpp11', PathToTestFile( 'FixIt_Clang_cpp11.cpp' ),
        FixIt_Check_cpp11_Ins ],
      [ 16, 1,  'cpp11', PathToTestFile( 'FixIt_Clang_cpp11.cpp' ),
        FixIt_Check_cpp11_Ins ],
      [ 16, 10, 'cpp11', PathToTestFile( 'FixIt_Clang_cpp11.cpp' ),
        FixIt_Check_cpp11_Ins ],
      [ 25, 14, 'cpp11', PathToTestFile( 'FixIt_Clang_cpp11.cpp' ),
        FixIt_Check_cpp11_InsMultiLine ],
      [ 25, 0,  'cpp11', PathToTestFile( 'FixIt_Clang_cpp11.cpp' ),
        FixIt_Check_cpp11_InsMultiLine ],
      [ 35, 7,  'cpp11', PathToTestFile( 'FixIt_Clang_cpp11.cpp' ),
        FixIt_Check_cpp11_Del ],
      [ 40, 6,  'cpp11', PathToTestFile( 'FixIt_Clang_cpp11.cpp' ),
        FixIt_Check_cpp11_Repl ],
      [ 48, 3,  'cpp11', PathToTestFile( 'FixIt_Clang_cpp11.cpp' ),
        FixIt_Check_cpp11_DelAdd ],

      [ 5, 3,   'objective-c', PathToTestFile( 'FixIt_Clang_objc.m' ),
        FixIt_Check_objc ],
      [ 7, 1,   'objective-c', PathToTestFile( 'FixIt_Clang_objc.m' ),
        FixIt_Check_objc_NoFixIt ],

      [ 3, 12,  'cuda', PathToTestFile( 'cuda', 'fixit_test.cu' ),
        FixIt_Check_cuda ],

      # multiple errors on a single line; both with fixits
      [ 54, 15, 'cpp11', PathToTestFile( 'FixIt_Clang_cpp11.cpp' ),
        FixIt_Check_cpp11_MultiFirst ],
      [ 54, 16, 'cpp11', PathToTestFile( 'FixIt_Clang_cpp11.cpp' ),
        FixIt_Check_cpp11_MultiFirst ],
      [ 54, 16, 'cpp11', PathToTestFile( 'FixIt_Clang_cpp11.cpp' ),
        FixIt_Check_cpp11_MultiFirst ],
      [ 54, 17, 'cpp11', PathToTestFile( 'FixIt_Clang_cpp11.cpp' ),
        FixIt_Check_cpp11_MultiFirst ],
      [ 54, 18, 'cpp11', PathToTestFile( 'FixIt_Clang_cpp11.cpp' ),
        FixIt_Check_cpp11_MultiFirst ],

      # should put closest fix-it first?
      [ 54, 51, 'cpp11', PathToTestFile( 'FixIt_Clang_cpp11.cpp' ),
        FixIt_Check_cpp11_MultiSecond ],
      [ 54, 52, 'cpp11', PathToTestFile( 'FixIt_Clang_cpp11.cpp' ),
        FixIt_Check_cpp11_MultiSecond ],
      [ 54, 53, 'cpp11', PathToTestFile( 'FixIt_Clang_cpp11.cpp' ),
        FixIt_Check_cpp11_MultiSecond ],

      # unicode in line for fixit
      [ 21, 16, 'cpp11', PathToTestFile( 'unicode.cc' ),
        FixIt_Check_unicode_Ins ],

      # FixIt attached to a "child" diagnostic (i.e. a Note)
      [ 60, 1,  'cpp11', PathToTestFile( 'FixIt_Clang_cpp11.cpp' ),
        FixIt_Check_cpp11_Note ],

      # FixIt due to forced spell checking
      [ 72, 9,  'cpp11', PathToTestFile( 'FixIt_Clang_cpp11.cpp' ),
        FixIt_Check_cpp11_SpellCheck ],
    ]:
      with self.subTest( test = test ):
        RunFixItTest( app,
                      test[ 0 ],
                      test[ 1 ],
                      test[ 2 ],
                      test[ 3 ],
                      test[ 4 ] )


  @SharedYcmd
  def test_Subcommands_FixIt_Unity( self, app ):
    file_path = PathToTestFile( 'unitya.cc' )
    args = {
      'filetype'         : 'cpp',
      'completer_target' : 'filetype_default',
      'contents'         : ReadFile( file_path ),
      'filepath'         : file_path,
      'command_arguments': [ 'FixIt' ],
      'line_num'         : 11,
      'column_num'       : 17,
    }
    app.post_json( '/load_extra_conf_file', {
      'filepath': PathToTestFile( '.ycm_extra_conf.py' ),
    } )

    # Get the fixes for the file.
    event_data = BuildRequest( **args )

    results = app.post_json( '/run_completer_command', event_data ).json

    pprint( results )
    assert_that( results, has_entries( {
      'fixits': contains_exactly( has_entries( {
        'text': contains_string( "expected ';' after expression" ),
        'chunks': contains_exactly(
          ChunkMatcher( ';',
                        LocationMatcher( file_path, 11, 18 ),
                        LocationMatcher( file_path, 11, 18 ) ),
        ),
        'location': LocationMatcher( file_path, 11, 18 ),
      } ) )
    } ) )


  @SharedYcmd
  def test_Subcommands_FixIt_UnityDifferentFile( self, app ):
    # This checks that we only return FixIt for the requested file, not a fixit
    # on the same line in a different file
    file_path = PathToTestFile( 'unity.cc' )
    args = {
      'filetype'         : 'cpp',
      'completer_target' : 'filetype_default',
      'contents'         : ReadFile( file_path ),
      'filepath'         : file_path,
      'command_arguments': [ 'FixIt' ],
      'line_num'         : 11,
      'column_num'       : 17,
    }
    app.post_json( '/load_extra_conf_file', {
      'filepath': PathToTestFile( '.ycm_extra_conf.py' ),
    } )

    # Get the fixes for the file.
    event_data = BuildRequest( **args )

    results = app.post_json( '/run_completer_command', event_data ).json

    pprint( results )
    assert_that( results, has_entries( {
      'fixits': empty()
    } ) )


  @SharedYcmd
  def test_Subcommands_FixIt_NonExistingFile( self, app ):
    # This checks that FixIt is working for a non-existing file and that the
    # path is properly normalized ('.' and '..' are removed from the path).
    file_path = PathToTestFile( 'non_existing_dir',
                                '..',
                                '.',
                                'non_existing.cc' )
    normal_file_path = PathToTestFile( 'non_existing.cc' )
    args = {
      'filetype'         : 'cpp',
      'completer_target' : 'filetype_default',
      'contents'         : 'int test',
      'filepath'         : file_path,
      'command_arguments': [ 'FixIt' ],
      'line_num'         : 1,
      'column_num'       : 1,
    }
    app.post_json( '/load_extra_conf_file', {
      'filepath': PathToTestFile( '.ycm_extra_conf.py' ),
    } )

    # Get the fixes for the file.
    event_data = BuildRequest( **args )

    results = app.post_json( '/run_completer_command', event_data ).json

    pprint( results )
    assert_that( results, has_entries( {
      'fixits': contains_exactly( has_entries( {
        'text': contains_string( "expected ';' after top level declarator" ),
        'chunks': contains_exactly(
          ChunkMatcher( ';',
                        LocationMatcher( normal_file_path, 1, 9 ),
                        LocationMatcher( normal_file_path, 1, 9 ) ),
        ),
        'location': LocationMatcher( normal_file_path, 1, 9 ),
      } ) )
    } ) )


  @SharedYcmd
  def test_Subcommands_GetDoc_Variable( self, app ):
    filepath = PathToTestFile( 'GetDoc_Clang.cc' )
    contents = ReadFile( filepath )

    event_data = BuildRequest( filepath = filepath,
                               filetype = 'cpp',
                               compilation_flags = [ '-x', 'c++' ],
                               line_num = 70,
                               column_num = 24,
                               contents = contents,
                               command_arguments = [ 'GetDoc' ] )

    response = app.post_json( '/run_completer_command', event_data ).json

    pprint( response )

    assert_that( response, has_entry(
      'detailed_info', """\
char a_global_variable
This really is a global variable.
Type: char
Name: a_global_variable
---
This really is a global variable.

The first line of comment is the brief.""" ) )


  @SharedYcmd
  def test_Subcommands_GetDoc_Method( self, app ):
    filepath = PathToTestFile( 'GetDoc_Clang.cc' )
    contents = ReadFile( filepath )

    event_data = BuildRequest( filepath = filepath,
                               filetype = 'cpp',
                               compilation_flags = [ '-x', 'c++' ],
                               line_num = 22,
                               column_num = 13,
                               contents = contents,
                               command_arguments = [ 'GetDoc' ] )

    response = app.post_json( '/run_completer_command', event_data ).json

    pprint( response )

    assert_that( response, has_entry(
      'detailed_info', """\
char with_brief()
brevity is for suckers
Type: char ()
Name: with_brief
---

This is not the brief.

\\brief brevity is for suckers

This is more information
""" ) )


  @SharedYcmd
  def test_Subcommands_GetDoc_Namespace( self, app ):
    filepath = PathToTestFile( 'GetDoc_Clang.cc' )
    contents = ReadFile( filepath )

    event_data = BuildRequest( filepath = filepath,
                               filetype = 'cpp',
                               compilation_flags = [ '-x', 'c++' ],
                               line_num = 65,
                               column_num = 14,
                               contents = contents,
                               command_arguments = [ 'GetDoc' ] )

    response = app.post_json( '/run_completer_command', event_data ).json

    pprint( response )

    assert_that( response, has_entry(
    'detailed_info', """\
namespace Test {}
This is a test namespace
Type: 
Name: Test
---
This is a test namespace""" ) ) # noqa


  @SharedYcmd
  def test_Subcommands_GetDoc_Undocumented( self, app ):
    filepath = PathToTestFile( 'GetDoc_Clang.cc' )
    contents = ReadFile( filepath )

    event_data = BuildRequest( filepath = filepath,
                               filetype = 'cpp',
                               compilation_flags = [ '-x', 'c++' ],
                               line_num = 81,
                               column_num = 17,
                               contents = contents,
                               command_arguments = [ 'GetDoc' ] )

    response = app.post_json( '/run_completer_command',
                              event_data,
                              expect_errors = True )

    assert_that( response.status_code,
                 equal_to( requests.codes.internal_server_error ) )

    assert_that( response.json,
                 ErrorMatcher( ValueError, NO_DOCUMENTATION_MESSAGE ) )


  @SharedYcmd
  def test_Subcommands_GetDoc_NoCursor( self, app ):
    filepath = PathToTestFile( 'GetDoc_Clang.cc' )
    contents = ReadFile( filepath )

    event_data = BuildRequest( filepath = filepath,
                               filetype = 'cpp',
                               compilation_flags = [ '-x', 'c++' ],
                               line_num = 1,
                               column_num = 1,
                               contents = contents,
                               command_arguments = [ 'GetDoc' ] )

    response = app.post_json( '/run_completer_command',
                              event_data,
                              expect_errors = True )

    assert_that( response.status_code,
                 equal_to( requests.codes.internal_server_error ) )

    assert_that( response.json,
                 ErrorMatcher( ValueError, NO_DOCUMENTATION_MESSAGE ) )


  @SharedYcmd
  def test_Subcommands_GetDoc_SystemHeaders( self, app ):
    app.post_json( '/load_extra_conf_file', {
      'filepath': PathToTestFile( 'get_doc', '.ycm_extra_conf.py' ) } )

    filepath = PathToTestFile( 'get_doc', 'test.cpp' )
    contents = ReadFile( filepath )

    event_data = BuildRequest( filepath = filepath,
                               filetype = 'cpp',
                               line_num = 4,
                               column_num = 7,
                               contents = contents,
                               command_arguments = [ 'GetDoc' ] )

    response = app.post_json( '/run_completer_command', event_data ).json

    assert_that( response,
                 has_entry( 'detailed_info', """\
int test()
This is a function.
Type: int ()
Name: test
---

\\brief This is a function.

This function is defined in a system header.
""" ) )


  # Following tests repeat the tests above, but without re-parsing the file
  @SharedYcmd
  def test_Subcommands_GetDocImprecise_Variable( self, app ):
    filepath = PathToTestFile( 'GetDoc_Clang.cc' )
    contents = ReadFile( filepath )

    app.post_json( '/event_notification',
                   BuildRequest( filepath = filepath,
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
                               command_arguments = [ 'GetDocImprecise' ] )

    response = app.post_json( '/run_completer_command', event_data ).json

    pprint( response )

    assert_that( response, has_entry(
      'detailed_info', """\
char a_global_variable
This really is a global variable.
Type: char
Name: a_global_variable
---
This really is a global variable.

The first line of comment is the brief.""" ) )


  @SharedYcmd
  def test_Subcommands_GetDocImprecise_Method( self, app ):
    filepath = PathToTestFile( 'GetDoc_Clang.cc' )
    contents = ReadFile( filepath )

    app.post_json(
      '/event_notification',
      BuildRequest( filepath = filepath,
                    filetype = 'cpp',
                    compilation_flags = [ '-x', 'c++' ],
                    contents = contents,
                    event_name = 'FileReadyToParse' )
    )

    event_data = BuildRequest( filepath = filepath,
                               filetype = 'cpp',
                               compilation_flags = [ '-x', 'c++' ],
                               line_num = 22,
                               column_num = 13,
                               contents = contents,
                               command_arguments = [ 'GetDocImprecise' ] )

    response = app.post_json( '/run_completer_command', event_data ).json

    pprint( response )

    assert_that( response, has_entry(
      'detailed_info', """\
char with_brief()
brevity is for suckers
Type: char ()
Name: with_brief
---

This is not the brief.

\\brief brevity is for suckers

This is more information
""" ) )


  @SharedYcmd
  def test_Subcommands_GetDocImprecise_Namespace( self, app ):
    filepath = PathToTestFile( 'GetDoc_Clang.cc' )
    contents = ReadFile( filepath )

    app.post_json(
      '/event_notification',
      BuildRequest( filepath = filepath,
                    filetype = 'cpp',
                    compilation_flags = [ '-x', 'c++' ],
                    contents = contents,
                    event_name = 'FileReadyToParse' )
    )

    event_data = BuildRequest( filepath = filepath,
                               filetype = 'cpp',
                               compilation_flags = [ '-x', 'c++' ],
                               line_num = 65,
                               column_num = 14,
                               contents = contents,
                               command_arguments = [ 'GetDocImprecise' ] )

    response = app.post_json( '/run_completer_command', event_data ).json

    pprint( response )

    assert_that( response, has_entry(
    'detailed_info', """\
namespace Test {}
This is a test namespace
Type: 
Name: Test
---
This is a test namespace""" ) ) # noqa


  @SharedYcmd
  def test_Subcommands_GetDocImprecise_Undocumented( self, app ):
    filepath = PathToTestFile( 'GetDoc_Clang.cc' )
    contents = ReadFile( filepath )

    app.post_json(
      '/event_notification',
      BuildRequest( filepath = filepath,
                    filetype = 'cpp',
                    compilation_flags = [ '-x', 'c++' ],
                    contents = contents,
                    event_name = 'FileReadyToParse' )
    )

    event_data = BuildRequest( filepath = filepath,
                               filetype = 'cpp',
                               compilation_flags = [ '-x', 'c++' ],
                               line_num = 81,
                               column_num = 17,
                               contents = contents,
                               command_arguments = [ 'GetDocImprecise' ] )

    response = app.post_json( '/run_completer_command',
                              event_data,
                              expect_errors = True )

    assert_that( response.status_code,
                 equal_to( requests.codes.internal_server_error ) )

    assert_that( response.json,
                 ErrorMatcher( ValueError, NO_DOCUMENTATION_MESSAGE ) )


  @SharedYcmd
  def test_Subcommands_GetDocImprecise_NoCursor( self, app ):
    filepath = PathToTestFile( 'GetDoc_Clang.cc' )
    contents = ReadFile( filepath )

    app.post_json(
      '/event_notification',
      BuildRequest( filepath = filepath,
                    filetype = 'cpp',
                    compilation_flags = [ '-x', 'c++' ],
                    contents = contents,
                    event_name = 'FileReadyToParse' )
    )

    event_data = BuildRequest( filepath = filepath,
                               filetype = 'cpp',
                               compilation_flags = [ '-x', 'c++' ],
                               line_num = 1,
                               column_num = 1,
                               contents = contents,
                               command_arguments = [ 'GetDocImprecise' ] )

    response = app.post_json( '/run_completer_command',
                              event_data,
                              expect_errors = True )

    assert_that( response.status_code,
                 equal_to( requests.codes.internal_server_error ) )

    assert_that( response.json,
                 ErrorMatcher( ValueError, NO_DOCUMENTATION_MESSAGE ) )


  @SharedYcmd
  def test_Subcommands_GetDocImprecise_NoReadyToParse( self, app ):
    filepath = PathToTestFile( 'GetDoc_Clang.cc' )
    contents = ReadFile( filepath )

    event_data = BuildRequest( filepath = filepath,
                               filetype = 'cpp',
                               compilation_flags = [ '-x', 'c++' ],
                               line_num = 11,
                               column_num = 18,
                               contents = contents,
                               command_arguments = [ 'GetDocImprecise' ] )

    response = app.post_json( '/run_completer_command', event_data ).json

    assert_that( response, has_entry(
      'detailed_info', """\
int get_a_global_variable(bool test)
This is a method which is only pretend global
Type: int (bool)
Name: get_a_global_variable
---
This is a method which is only pretend global
@param test Set this to true. Do it.""" ) )


  @SharedYcmd
  def test_Subcommands_GetDocImprecise_SystemHeaders( self, app ):
    app.post_json( '/load_extra_conf_file', {
      'filepath': PathToTestFile( 'get_doc', '.ycm_extra_conf.py' ) } )

    filepath = PathToTestFile( 'get_doc', 'test.cpp' )
    contents = ReadFile( filepath )

    event_data = BuildRequest( filepath = filepath,
                               filetype = 'cpp',
                               line_num = 4,
                               column_num = 7,
                               contents = contents,
                               command_arguments = [ 'GetDocImprecise' ] )

    response = app.post_json( '/run_completer_command', event_data ).json

    assert_that( response,
                 has_entry( 'detailed_info', """\
int test()
This is a function.
Type: int ()
Name: test
---

\\brief This is a function.

This function is defined in a system header.
""" ) )


  @SharedYcmd
  def test_Subcommands_GetDoc_Unicode( self, app ):
    filepath = PathToTestFile( 'unicode.cc' )
    contents = ReadFile( filepath )

    event_data = BuildRequest( filepath = filepath,
                               filetype = 'cpp',
                               compilation_flags = [ '-x', 'c++' ],
                               line_num = 21,
                               column_num = 16,
                               contents = contents,
                               command_arguments = [ 'GetDoc' ],
                               completer_target = 'filetype_default' )

    response = app.post_json( '/run_completer_command', event_data ).json

    pprint( response )

    assert_that( response, has_entry(
      'detailed_info', """\
int member_with_å_unicøde
This method has unicøde in it
Type: int
Name: member_with_å_unicøde
---

This method has unicøde in it
""" ) )


  @SharedYcmd
  def test_Subcommands_GetDoc_CUDA( self, app ):
    filepath = PathToTestFile( 'cuda', 'basic.cu' )
    contents = ReadFile( filepath )

    event_data = BuildRequest( filepath = filepath,
                               filetype = 'cuda',
                               compilation_flags = [ '-x', 'cuda' ],
                               line_num = 8,
                               column_num = 3,
                               contents = contents,
                               command_arguments = [ 'GetDoc' ],
                               completer_target = 'filetype_default' )

    response = app.post_json( '/run_completer_command', event_data ).json

    pprint( response )

    assert_that( response, has_entry(
      'detailed_info', """\
void kernel()
This is a test kernel
Type: void ()
Name: kernel
---
This is a test kernel""" ) )


  @SharedYcmd
  def test_Subcommands_StillParsingError( self, app ):
    completer = handlers._server_state.GetFiletypeCompleter( [ 'cpp' ] )
    with patch.object( completer, '_completer', MockCoreClangCompleter() ):
      Subcommands_StillParsingError( app, 'FixIt' )
      Subcommands_StillParsingError( app, 'GetDoc' )
      Subcommands_StillParsingError( app, 'GetDocImprecise' )
      Subcommands_StillParsingError( app, 'GetParent' )
      Subcommands_StillParsingError( app, 'GetType' )
      Subcommands_StillParsingError( app, 'GetTypeImprecise' )
      Subcommands_StillParsingError( app, 'GoTo' )
      Subcommands_StillParsingError( app, 'GoToDeclaration' )
      Subcommands_StillParsingError( app, 'GoToDefinition' )
      Subcommands_StillParsingError( app, 'GoToImprecise' )
