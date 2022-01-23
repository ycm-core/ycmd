# Copyright (C) 2021 ycmd contributors
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
                       has_items,
                       contains_exactly,
                       contains_string,
                       equal_to,
                       has_entries,
                       has_entry,
                       matches_regexp )
from unittest.mock import patch
from unittest import TestCase
from pprint import pprint
import itertools
import requests
import os.path

from ycmd import handlers
from ycmd.tests.clangd import setUpModule, tearDownModule # noqa
from ycmd.tests.clangd import ( IsolatedYcmd,
                                SharedYcmd,
                                PathToTestFile,
                                RunAfterInitialized )
from ycmd.tests.test_utils import ( BuildRequest,
                                    ChunkMatcher,
                                    CombineRequest,
                                    LineColMatcher,
                                    LocationMatcher,
                                    ErrorMatcher,
                                    WithRetry,
                                    WaitUntilCompleterServerReady )
from ycmd.utils import ReadFile


def RunGoToTest_all( app, folder, command, test ):
  req = test[ 'req' ]
  filepath = PathToTestFile( folder, req[ 0 ] )
  request = {
    'completer_target' : 'filetype_default',
    'filepath'         : filepath,
    'contents'         : ReadFile( filepath ),
    'filetype'         : 'cpp',
    'line_num'         : req[ 1 ],
    'column_num'       : req[ 2 ],
    'command_arguments': [ command ] + ( [] if len( req ) < 4 else req[ 3 ] ),
  }

  response = test[ 'res' ]

  if isinstance( response, list ):
    expect = {
      'response': requests.codes.ok,
      'data': contains_exactly( *[
        LocationMatcher(
          PathToTestFile( folder, os.path.normpath( location[ 0 ] ) ),
          location[ 1 ],
          location[ 2 ],
          **( {} if len( location ) < 4 else location[ 3 ] )
        ) for location in response
      ] )
    }
  elif isinstance( response, tuple ):
    expect = {
      'response': requests.codes.ok,
      'data': LocationMatcher(
        PathToTestFile( folder, os.path.normpath( response[ 0 ] ) ),
        response[ 1 ],
        response[ 2 ],
        **( {} if len( response ) < 4 else response[ 3 ] )
      )
    }
  else:
    expect = {
      'response': requests.codes.internal_server_error,
      'data': ErrorMatcher( RuntimeError, test[ 'res' ] )
    }

  RunAfterInitialized( app, {
    'request': request,
    'route'  : '/run_completer_command',
    'expect' : expect
  } )


def RunGetSemanticTest( app,
                        filepath,
                        filetype,
                        test,
                        command,
                        response = requests.codes.ok ):
  contents = ReadFile( filepath )
  common_args = {
    'completer_target' : 'filetype_default',
    'command_arguments': command,
    'line_num'         : 10,
    'column_num'       : 3,
    'filepath'         : filepath,
    'contents'         : contents,
    'filetype'         : filetype
  }

  request = common_args
  request.update( test[ 0 ] )
  test = { 'request': request,
           'route': '/run_completer_command',
           'expect': { 'response': response,
                       'data': test[ 1 ] } }
  RunAfterInitialized( app, test )


def RunFixItTest( app, line, column, lang, file_path, check ):
  contents = ReadFile( file_path )

  language_options = {
    'cpp11': {
      'filetype'         : 'cpp',
    },
    'cuda': {
      'filetype'         : 'cuda',
    },
    'objective-c': {
      'filetype'         : 'objc',
    },
  }

  args = {
    'completer_target' : 'filetype_default',
    'contents'         : contents,
    'filepath'         : file_path,
    'command_arguments': [ 'FixIt' ],
    'line_num'         : line,
    'column_num'       : column,
  }
  args.update( language_options[ lang ] )
  test = { 'request': args, 'route': '/detailed_diagnostic' }
  # First get diags.
  diags = RunAfterInitialized( app, test )
  while 'message' in diags and 'diagnostics' in diags[ 'message' ].lower():
    receive_diags = { 'request': args, 'route': '/receive_messages' }
    RunAfterInitialized( app, receive_diags )
    diags = RunAfterInitialized( app, test )

  results = app.post_json( '/run_completer_command',
                           BuildRequest( **args ) ).json

  pprint( results )
  check( results )


def FixIt_Check_cpp11_Ins( results ):
  # First fixit
  #   switch(A()) { // expected-error{{explicit conversion to}}
  assert_that( results, has_entries( {
    'fixits': has_items( has_entries( {
      'kind': 'quickfix',
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
      'location': has_entries( { 'line_num': 16, 'column_num': 1 } )
    } ) )
  } ) )


def FixIt_Check_cpp11_InsMultiLine( results ):
  # Similar to FixIt_Check_cpp11_1 but inserts split across lines
  #
  assert_that( results, has_entries( {
    'fixits': has_items( has_entries( {
      'kind': 'quickfix',
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
      'location': has_entries( { 'line_num': 25, 'column_num': 14 } )
    } ) )
  } ) )


def FixIt_Check_cpp11_Del( results ):
  # Removal of ::
  assert_that( results, has_entries( {
    'fixits': has_items( has_entries( {
      'kind': 'quickfix',
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
    'fixits': has_items( has_entries( {
      'kind': 'quickfix',
      'text': "change 'bar' to 'foo'",
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
    'fixits': has_items(
      has_entries( {
        'kind': 'quickfix',
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
      } ),
      has_entries( {
        'chunks': contains_exactly(
          has_entries( {
            'replacement_text': equal_to( '= default;' ),
            'range': has_entries( {
              'start': has_entries( { 'line_num': 48, 'column_num': 15 } ),
              'end'  : has_entries( { 'line_num': 48, 'column_num': 17 } ),
            } ),
          } ),
        ),
        'location': has_entries( { 'line_num': 48, 'column_num': 3 } )
      } ),
      # Unresolved, requires /resolve_fixit request
      has_entries( {
        'text': 'Move function body to declaration',
        'resolve': True,
        'command': has_entries( { 'command': 'clangd.applyTweak' } )
      } ),
    )
  } ) )


def FixIt_Check_objc( results ):
  assert_that( results, has_entries( {
    'fixits': has_items( has_entries( {
      'kind': 'quickfix',
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
    'fixits': has_items(
      # first fix-it at 54,16
      has_entries( {
        'kind': 'quickfix',
        'chunks': contains_exactly(
          has_entries( {
            'replacement_text': equal_to( 'foo' ),
            'range': has_entries( {
              'start': has_entries( { 'line_num': 54, 'column_num': 16 } ),
              'end'  : has_entries( { 'line_num': 54, 'column_num': 19 } ),
            } ),
          } )
        ),
        'location': has_entries( { 'line_num': 54, 'column_num': 15 } )
      } ),
    )
  } ) )


def FixIt_Check_cpp11_MultiSecond( results ):
  assert_that( results, has_entries( {
    'fixits': has_items(
      # second fix-it at 54,52
      has_entries( {
        'kind': 'quickfix',
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
        'location': has_entries( { 'line_num': 54, 'column_num': 51 } )
      } ),
      has_entries( {
        'kind': 'quickfix',
        'chunks': contains_exactly(
          has_entries( {
            'replacement_text': equal_to( '= default;' ),
            'range': has_entries( {
              'start': has_entries( { 'line_num': 54, 'column_num': 64 } ),
              'end'  : has_entries( { 'line_num': 54, 'column_num': 67 } ),
            } ),
          } )
        ),
        'location': has_entries( { 'line_num': 54, 'column_num': 51 } )
      } ),
    )
  } ) )


def FixIt_Check_unicode_Ins( results ):
  assert_that( results, has_entries( {
    'fixits': has_items( has_entries( {
      'kind': 'quickfix',
      'chunks': contains_exactly(
        has_entries( {
          'replacement_text': equal_to( '=' ),
          'range': has_entries( {
            'start': has_entries( { 'line_num': 21, 'column_num': 9 } ),
            'end'  : has_entries( { 'line_num': 21, 'column_num': 11 } ),
          } ),
        } )
      ),
      'location': has_entries( { 'line_num': 21, 'column_num': 16 } )
    } ) )
  } ) )


def FixIt_Check_cpp11_Note( results ):
  assert_that( results, has_entries( {
    'fixits': has_items(
      # First note: put parens around it
      has_entries( {
        'kind': 'quickfix',
        'text': contains_string( 'parentheses around the assignment' ),
        'chunks': contains_exactly(
          ChunkMatcher( '(',
                        LineColMatcher( 59, 8 ),
                        LineColMatcher( 59, 8 ) ),
          ChunkMatcher( ')',
                        LineColMatcher( 61, 12 ),
                        LineColMatcher( 61, 12 ) )
        ),
        'location': LineColMatcher( 60, 1 ),
      } ),

      # Second note: change to ==
      has_entries( {
        'kind': 'quickfix',
        'text': contains_string( '==' ),
        'chunks': contains_exactly(
          ChunkMatcher( '==',
                        LineColMatcher( 60, 8 ),
                        LineColMatcher( 60, 9 ) )
        ),
        'location': LineColMatcher( 60, 1 ),
      } ),
    )
  } ) )


def FixIt_Check_cpp11_SpellCheck( results ):
  assert_that( results, has_entries( {
    'fixits': has_items(
      # Change to SpellingIsNotMyStrongPoint
      has_entries( {
        'kind': 'quickfix',
        'text': contains_string( "change 'SpellingIsNotMyStringPiont' to "
                                 "'SpellingIsNotMyStrongPoint'" ),
        'chunks': contains_exactly(
          ChunkMatcher( 'SpellingIsNotMyStrongPoint',
                        LineColMatcher( 72, 9 ),
                        LineColMatcher( 72, 35 ) )
        ),
        'location': LineColMatcher( 72, 9 ),
      } ),
      has_entries( {
        'kind': 'refactor',
        'text': contains_string( "Add using-declaration for "
                                 "SpellingIsNotMyStringPiont and "
                                 "remove qualifier" ),
        'resolve': True
      } ) )
  } ) )


def FixIt_Check_cuda( results ):
  assert_that( results, has_entries( {
    'fixits': has_items(
      has_entries( {
        'kind': 'quickfix',
        'text': contains_string(
           "change 'int' to 'void'" ),
        'chunks': contains_exactly(
          ChunkMatcher( 'void',
                        LineColMatcher( 3, 12 ),
                        LineColMatcher( 3, 15 ) )
        ),
        'location': LineColMatcher( 3, 12 ),
      } ) )
  } ) )


def FixIt_Check_SubexprExtract_Resolved( results ):
  assert_that( results, has_entries( {
    'fixits': has_items( has_entries( {
        'text': 'Extract subexpression to variable',
        'chunks': contains_exactly(
          ChunkMatcher( 'auto placeholder = i + 3;\n  ',
                        LineColMatcher( 84, 3 ),
                        LineColMatcher( 84, 3 ) ),
          ChunkMatcher( 'placeholder',
                        LineColMatcher( 84, 14 ),
                        LineColMatcher( 84, 21 ) ),
        )
    } ) )
  } ) )


def FixIt_Check_RawStringReplace_Resolved( results ):
  assert_that( results, has_entries( {
    'fixits': has_items( has_entries( {
        'text': 'Convert to raw string',
        'chunks': contains_exactly(
          ChunkMatcher( 'R"(\\\\r\\asd\n\\v)"',
                        LineColMatcher( 80, 19 ),
                        LineColMatcher( 80, 36 ) ),
        )
    } ) )
  } ) )


def FixIt_Check_MacroExpand_Resolved( results ):
  assert_that( results, has_entries( {
    'fixits': has_items( has_entries( {
        'text': "Expand macro 'DECLARE_INT'",
        'chunks': contains_exactly(
          ChunkMatcher( 'int i',
                        LineColMatcher( 83,  3 ),
                        LineColMatcher( 83, 17 ) ),
        )
    } ) )
  } ) )


def FixIt_Check_AutoExpand_Resolved( results ):
  assert_that( results, has_entries( {
    'fixits': has_items( has_entries( {
        'text': "Expand auto type",
        'chunks': contains_exactly(
          ChunkMatcher( 'const char *',
                        LineColMatcher( 80, 1 ),
                        LineColMatcher( 80, 6 ) ),
        )
    } ) )
  } ) )


def RunRangedFixItTest( app, rng, expected, chosen_fixit = 0 ):
  contents = ReadFile( PathToTestFile( 'FixIt_Clang_cpp11.cpp' ) )
  args = {
    'completer_target' : 'filetype_default',
    'contents'         : contents,
    'filepath'         : PathToTestFile( 'FixIt_Clang_cpp11.cpp' ),
    'command_arguments': [ 'FixIt' ],
    'range'            : rng,
    'filetype'         : 'cpp'
  }
  app.post_json( '/event_notification',
                 CombineRequest( args, {
                   'event_name': 'FileReadyToParse',
                 } ),
                 expect_errors = True )
  WaitUntilCompleterServerReady( app, 'cpp' )
  response = app.post_json( '/run_completer_command',
                            BuildRequest( **args ) ).json
  args[ 'fixit' ] = response[ 'fixits' ][ chosen_fixit ]
  response = app.post_json( '/resolve_fixit',
                            BuildRequest( **args ) ).json
  print( 'Resolved fixit response = ' )
  print( response )
  expected( response )


class SubcommandsTest( TestCase ):
  # This test is isolated to trigger objcpp hooks, rather than fetching
  # completer from cache.
  @IsolatedYcmd()
  def test_Subcommands_DefinedSubcommands( self, app ):
    file_path = PathToTestFile( 'GoTo_Clang_ZeroBasedLineAndColumn_test.cc' )
    RunAfterInitialized( app, {
        'request': {
          'completer_target': 'filetype_default',
          'line_num': 10,
          'column_num': 3,
          'filetype': 'objcpp',
          'filepath': file_path
        },
        'expect': {
          'response': requests.codes.ok,
          'data': contains_exactly( *sorted( [ 'ExecuteCommand',
                                               'FixIt',
                                               'Format',
                                               'GetDoc',
                                               'GetDocImprecise',
                                               'GetType',
                                               'GetTypeImprecise',
                                               'GoTo',
                                               'GoToCallees',
                                               'GoToCallers',
                                               'GoToDeclaration',
                                               'GoToDefinition',
                                               'GoToDocumentOutline',
                                               'GoToImprecise',
                                               'GoToImplementation',
                                               'GoToInclude',
                                               'GoToReferences',
                                               'GoToSymbol',
                                               'GoToType',
                                               'RefactorRename',
                                               'RestartServer',
                                               'GoToAlternateFile' ] ) )
        },
        'route': '/defined_subcommands',
    } )


  @WithRetry()
  @SharedYcmd
  def test_Subcommands_ServerNotInitialized( self, app ):
    for cmd in [
      'FixIt',
      'Format',
      'GetDoc',
      'GetDocImprecise',
      'GetType',
      'GetTypeImprecise',
      'GoTo',
      'GoToCallees',
      'GoToCallers',
      'GoToDeclaration',
      'GoToDefinition',
      'GoToInclude',
      'GoToImplementation',
      'GoToReferences',
      'RefactorRename',
    ]:
      with self.subTest( cmd = cmd ):
        completer = handlers._server_state.GetFiletypeCompleter( [ 'cpp' ] )

        @patch.object( completer, '_ServerIsInitialized', return_value = False )
        def Test( app, cmd, *args ):
          request = {
            'line_num': 1,
            'column_num': 1,
            'event_name': 'FileReadyToParse',
            'filetype': 'cpp',
            'command_arguments': [ cmd ]
          }
          app.post_json( '/event_notification',
                         BuildRequest( **request ),
                         expect_errors = True )
          response = app.post_json(
            '/run_completer_command',
            BuildRequest( **request ),
            expect_errors = True
          )
          assert_that( response.status_code,
                       equal_to( requests.codes.server_error ) )
          assert_that( response.json,
                       ErrorMatcher( RuntimeError,
                                     'Server is initializing. Please wait.' ) )

        Test( app, cmd )


  @SharedYcmd
  def test_Subcommands_GoTo_ZeroBasedLineAndColumn( self, app ):
    file_path = PathToTestFile( 'GoTo_Clang_ZeroBasedLineAndColumn_test.cc' )
    RunAfterInitialized( app, {
        'request': {
            'contents': ReadFile( file_path ),
            'completer_target': 'filetype_default',
            'command_arguments': [ 'GoToDefinition' ],
            'line_num': 10,
            'column_num': 3,
            'filetype': 'cpp',
            'filepath': file_path
        },
        'expect': {
            'response': requests.codes.ok,
            'data': {
                'filepath': os.path.abspath( file_path ),
                'line_num': 2,
                'column_num': 8
            }
        },
        'route': '/run_completer_command',
    } )


  @SharedYcmd
  def test_Subcommands_GoTo_all( self, app ):
    for test, cmd in itertools.product(
      [
        # Local::x -> definition/declaration of x
        { 'req': ( 'goto.cc', 23, 21 ), 'res': ( 'goto.cc', 4, 9 ) },
        # Local::in_line -> definition/declaration of Local::in_line
        { 'req': ( 'goto.cc', 24, 26 ), 'res': ( 'goto.cc', 6, 10 ) },
        # Local -> definition/declaration of Local
        { 'req': ( 'goto.cc', 24, 16 ), 'res': ( 'goto.cc', 2, 11 ) },
        # Local::out_of_line -> definition of Local::out_of_line
        { 'req': ( 'goto.cc', 25, 27 ), 'res': ( 'goto.cc', 14, 13 ) },
        # GoToDeclaration alternates between definition and declaration
        { 'req': ( 'goto.cc', 14, 13 ), 'res': ( 'goto.cc', 11, 10 ) },
        { 'req': ( 'goto.cc', 11, 10 ), 'res': ( 'goto.cc', 14, 13 ) },
        # test -> definition and declaration of test
        { 'req': ( 'goto.cc', 21,  5 ), 'res': ( 'goto.cc', 19, 5 ) },
        { 'req': ( 'goto.cc', 19,  5 ), 'res': ( 'goto.cc', 21, 5 ) },
        # Unicøde
        { 'req': ( 'goto.cc', 34,  9 ), 'res': ( 'goto.cc', 32, 26 ) },
        # Another_Unicøde
        { 'req': ( 'goto.cc', 36, 17 ), 'res': ( 'goto.cc', 32, 54 ) },
        { 'req': ( 'goto.cc', 36, 25 ), 'res': ( 'goto.cc', 32, 54 ) },
        { 'req': ( 'goto.cc', 38,  3 ), 'res': ( 'goto.cc', 36, 28 ) },
        # Expected failures
        { 'req': ( 'goto.cc', 13,  1 ), 'res': 'Cannot jump to location' },
        { 'req': ( 'goto.cc', 16,  6 ), 'res': 'Cannot jump to location' },
      ],
      [ 'GoToImprecise', 'GoToDefinition', 'GoTo' ] ):
      with self.subTest( test = test, cmd = cmd ):
        RunGoToTest_all( app, '', cmd, test )


  @SharedYcmd
  def test_Subcommands_GoToDeclaration_all( self, app ):
    for test in [
      # Local::x -> definition/declaration of x
      { 'req': ( 'goto.cc', 23, 21 ), 'res': ( 'goto.cc', 4, 9 ) },
      # Local::in_line -> definition/declaration of Local::in_line
      { 'req': ( 'goto.cc', 24, 26 ), 'res': ( 'goto.cc', 6, 10 ) },
      # Local -> definition/declaration of Local
      { 'req': ( 'goto.cc', 24, 16 ), 'res': ( 'goto.cc', 2, 11 ) },
      # Local::out_of_line -> declaration of Local::out_of_line
      { 'req': ( 'goto.cc', 25, 27 ), 'res': ( 'goto.cc', 11, 10 ) },
      # GoToDeclaration alternates between definition and declaration
      { 'req': ( 'goto.cc', 14, 13 ), 'res': ( 'goto.cc', 11, 10 ) },
      { 'req': ( 'goto.cc', 11, 10 ), 'res': ( 'goto.cc', 14, 13 ) },
      # test -> definition and declaration of test
      { 'req': ( 'goto.cc', 21,  5 ), 'res': ( 'goto.cc', 19, 5 ) },
      { 'req': ( 'goto.cc', 19,  5 ), 'res': ( 'goto.cc', 21, 5 ) },
      # Unicøde
      { 'req': ( 'goto.cc', 34,  9 ), 'res': ( 'goto.cc', 32, 26 ) },
      # Another_Unicøde
      { 'req': ( 'goto.cc', 36, 17 ), 'res': ( 'goto.cc', 32, 54 ) },
      { 'req': ( 'goto.cc', 36, 25 ), 'res': ( 'goto.cc', 32, 54 ) },
      { 'req': ( 'goto.cc', 38,  3 ), 'res': ( 'goto.cc', 36, 28 ) },
      # Expected failures
      { 'req': ( 'goto.cc', 13,  1 ), 'res': 'Cannot jump to location' },
      { 'req': ( 'goto.cc', 16,  6 ), 'res': 'Cannot jump to location' },
    ]:
      with self.subTest( test = test ):
        RunGoToTest_all( app, '', 'GoToDeclaration', test )


  @SharedYcmd
  def test_Subcommands_GoToInclude( self, app ):
    for test, cmd in itertools.product( [
        { 'req': ( 'main.cpp',  1,  6 ), 'res': ( 'a.hpp',        1, 1 ) },
        { 'req': ( 'main.cpp',  2, 14 ), 'res': ( 'system/a.hpp', 1, 1 ) },
        { 'req': ( 'main.cpp',  3,  1 ), 'res': ( 'quote/b.hpp',  1, 1 ) },
        # FIXME: should fail since b.hpp is included with angled brackets but
        # its folder is added with -iquote.
        { 'req': ( 'main.cpp',  4, 10 ), 'res': ( 'quote/b.hpp',  1, 1 ) },
        { 'req': ( 'main.cpp',  5, 11 ), 'res': ( 'system/c.hpp', 1, 1 ) },
        { 'req': ( 'main.cpp',  6, 11 ), 'res': ( 'system/c.hpp', 1, 1 ) },
        # Expected failures
        { 'req': ( 'main.cpp',  7,  1 ), 'res': 'Cannot jump to location' },
        { 'req': ( 'main.cpp', 10, 13 ), 'res': 'Cannot jump to location' },
      ],
      [ 'GoToImprecise', 'GoToInclude', 'GoTo' ] ):
      with self.subTest( test = test, cmd = cmd ):
        RunGoToTest_all( app, 'test-include', cmd, test )

  @SharedYcmd
  def test_Subcommands_GoToAlternateFile( self, app ):
    for test in [
            { 'req': ( 'go-to-alternate-file/a.cpp', 1, 1 ),
              'res': ( 'go-to-alternate-file/a.h', 1, 1 ) },
            { 'req': ( 'go-to-alternate-file/a.h', 1, 1 ),
              'res': ( 'go-to-alternate-file/a.cpp', 1, 1 ) },
    ]:
      with self.subTest( test = test ):
        RunGoToTest_all( app, '', 'GoToAlternateFile', test )

  @SharedYcmd
  def test_Subcommands_GoToReferences( self, app ):
    for test in [
      # Function
      { 'req': ( 'goto.cc', 14, 21 ), 'res': [ ( 'goto.cc', 11, 10 ),
                                               ( 'goto.cc', 14, 13 ),
                                               ( 'goto.cc', 25, 22 ) ] },
      # Namespace
      { 'req': ( 'goto.cc', 24, 17 ), 'res': [ ( 'goto.cc',  2, 11 ),
                                               ( 'goto.cc', 14,  6 ),
                                               ( 'goto.cc', 23, 14 ),
                                               ( 'goto.cc', 24, 15 ),
                                               ( 'goto.cc', 25, 15 ) ] },
      # Expected failure
      { 'req': ( 'goto.cc', 27,  8 ), 'res': 'Cannot jump to location' },
    ]:
      with self.subTest( test = test ):
        RunGoToTest_all( app, '', 'GoToReferences', test )


  @SharedYcmd
  def test_Subcommands_GoToSymbol( self, app ):
    for test in [
      # In same file - 1 result
      { 'req': ( 'goto.cc', 1, 1, [ 'out_of_line' ] ),
        'res': ( 'goto.cc', 14, 13, {
          'description': 'Function: out_of_line',
          'extra_data': { 'kind': 'Function', 'name': 'out_of_line', } }
        ) },
      # In same file - multiple results
      { 'req': ( 'goto.cc', 1, 1, [ 'line' ] ),
        'res': [
          ( 'goto.cc', 6, 10, {
            'description': 'Function: in_line',
            'extra_data': { 'kind': 'Function', 'name': 'in_line' },
          } ),
          ( 'goto.cc', 14, 13, {
            'description': 'Function: out_of_line',
            'extra_data': { 'kind': 'Function', 'name': 'out_of_line' },
          } ),
      ] },
      # None
      { 'req': ( 'goto.cc', 1, 1, [ 'none' ] ), 'res': 'Symbol not found' },

      # Note we don't actually have any testdata that has a full index, so we
      # can't test multiple files easily, but that's really a clangd thing, not
      # a ycmd thing.
    ]:
      with self.subTest( test = test ):
        RunGoToTest_all( app, '', 'GoToSymbol', test )


  @SharedYcmd
  def test_Subcommands_GoToDocumentOutline( self, app ):
    for test in [
      # In same file - multiple results
      { 'req': ( 'goto.cc', 1, 1 ),
        'res': [
          ( 'goto.cc', 2, 1, {
            'description': "Namespace: Local",
            'extra_data': { 'kind': 'Namespace', 'name': 'Local' } } ),
          ( 'goto.cc', 14, 1, {
            'description': "Function: Local::out_of_line",
            'extra_data': { 'kind': 'Function',
                            'name': 'Local::out_of_line' } } ),
          ( 'goto.cc', 6, 5, {
            'description': "Function: in_line",
            'extra_data': { 'kind': 'Function', 'name': 'in_line' } } ),
          ( 'goto.cc', 11, 5, {
            'description': 'Function: out_of_line',
            'extra_data': { 'kind': 'Function', 'name': 'out_of_line' } } ),
          ( 'goto.cc', 19, 1, {
            'description': "Function: test",
            'extra_data': { 'kind': 'Function', 'name': 'test' } } ),
          ( 'goto.cc', 21, 1, {
            'description': "Function: test",
            'extra_data': { 'kind': 'Function', 'name': 'test' } } ),
          ( 'goto.cc', 30, 1, {
            'description': "Function: unicode",
            'extra_data': { 'kind': 'Function', 'name': 'unicode' } } ),
          ( 'goto.cc', 4, 5, {
            'description': "Variable: x",
            'extra_data': { 'kind': 'Variable', 'name': 'x' } } ),
        ] } ]:
      with self.subTest( test = test ):
        RunGoToTest_all( app, '', 'GoToDocumentOutline', test )


  @SharedYcmd
  def test_Subcommands_GoToImplementation( self, app ):
    for test in [
      { 'req': ( 'virtual.cpp', 1, 9 ),
        'res': [
          ( 'virtual.cpp', 5, 8 ),
          ( 'virtual.cpp', 13, 8, ),
          ( 'virtual.cpp', 9, 8 ),
      ] },
      { 'req': ( 'virtual.cpp', 2, 15 ),
        'res': [
          ( 'virtual.cpp', 10, 15 ),
          ( 'virtual.cpp', 6, 7 ),
      ] },
      { 'req': ( 'virtual.cpp', 9, 8 ),
        'res': ( 'virtual.cpp', 14, 8 ) },
      { 'req': ( 'virtual.cpp', 13, 15 ),
        'res': [
          ( 'virtual.cpp', 5, 8 ),
          ( 'virtual.cpp', 13, 8, ),
          ( 'virtual.cpp', 9, 8 ),
      ] },
      { 'req': ( 'virtual.cpp', 10, 15 ),
        'res': 'Cannot jump to location' },
    ]:
      with self.subTest( test = test ):
        RunGoToTest_all( app, '', 'GoToImplementation', test )


  @SharedYcmd
  def test_Subcommands_GoToCallers( self, app ):
    for test in [
      { 'req': ( 'call_hierarchy.cc', 1, 6 ), # Simple case.
        'res': [ ( 'call_hierarchy.cc', 4, 10 ) ] },
      { 'req': ( 'call_hierarchy.cc', 6, 6 ),
        'res': [
          ( 'call_hierarchy.cc', 15, 3 ), # More than one location in response.
          ( 'call_hierarchy.cc', 11, 3 ),
          ( 'call_hierarchy.cc',  7, 3 ), # Recursive call.
      ] },
      { 'req': ( 'call_hierarchy.cc', 3, 6 ), # Top of call hierarchy.
        'res': 'No incoming calls found.' }
    ]:
      with self.subTest( test = test ):
        RunGoToTest_all( app, '', 'GoToCallers', test )


  @SharedYcmd
  def test_Subcommands_GetType( self, app ):
    for test, cmd in itertools.product( [
        # Basic pod types
        [ { 'line_num': 24, 'column_num':  3 },
          has_entry( 'message', equal_to( 'struct Foo {}' ) ),
          requests.codes.ok ],
        # [ { 'line_num': 12, 'column_num':  2 }, 'Foo',
        [ { 'line_num': 12, 'column_num':  8 },
          has_entry( 'message', equal_to( 'struct Foo {}' ) ),
          requests.codes.ok ],
        [ { 'line_num': 12, 'column_num':  9 },
          has_entry( 'message', equal_to( 'struct Foo {}' ) ),
          requests.codes.ok ],
        [ { 'line_num': 12, 'column_num': 10 },
          has_entry( 'message', equal_to( 'struct Foo {}' ) ),
          requests.codes.ok ],
        # [ { 'line_num': 13, 'column_num':  3 }, 'int',
        [ { 'line_num': 13, 'column_num':  7 },
          has_entry( 'message', equal_to( 'public: int x; // In Foo' ) ),
          requests.codes.ok ],
        # [ { 'line_num': 15, 'column_num':  7 }, 'char' ],

        # Function
        # [ { 'line_num': 22, 'column_num':  2 }, 'int main()' ],
        [ { 'line_num': 22, 'column_num':  6 },
          'int main()',
          requests.codes.ok ],

        # Declared and canonical type
        # On Ns::
        [ { 'line_num': 25, 'column_num':  3 },
          'namespace Ns',
          requests.codes.ok ],
        # On Type (Type)
        # [ { 'line_num': 25, 'column_num':  8 },
        # 'Ns::Type => Ns::BasicType<char>' ],
        # On "a" (Ns::Type)
        # [ { 'line_num': 25, 'column_num': 15 },
        # 'Ns::Type => Ns::BasicType<char>' ],
        # [ { 'line_num': 26, 'column_num': 13 },
        # 'Ns::Type => Ns::BasicType<char>' ],

        # Cursor on decl for refs & pointers
        [ { 'line_num': 39, 'column_num':  3 },
          has_entry( 'message', equal_to( 'struct Foo {}' ) ),
          requests.codes.ok ],
        [ { 'line_num': 39, 'column_num': 11 },
          has_entry( 'message', equal_to( 'Foo &rFoo = foo; // In main' ) ),
          requests.codes.ok ],
        [ { 'line_num': 39, 'column_num': 15 },
          has_entry( 'message', equal_to( 'Foo foo; // In main' ) ),
          requests.codes.ok ],
        [ { 'line_num': 40, 'column_num':  3 },
          has_entry( 'message', equal_to( 'struct Foo {}' ) ),
          requests.codes.ok ],
        [ { 'line_num': 40, 'column_num': 11 },
          has_entry( 'message', equal_to( 'Foo *pFoo = &foo; // In main' ) ),
          requests.codes.ok ],
        [ { 'line_num': 40, 'column_num': 18 },
          has_entry( 'message', equal_to( 'Foo foo; // In main' ) ),
          requests.codes.ok ],
        # [ { 'line_num': 42, 'column_num':  3 }, 'const Foo &' ],
        [ { 'line_num': 42, 'column_num': 16 },
          has_entry( 'message',
                     equal_to( 'const Foo &crFoo = foo; // In main' ) ),
          requests.codes.ok ],
        # [ { 'line_num': 43, 'column_num':  3 }, 'const Foo *' ],
        [ { 'line_num': 43, 'column_num': 16 },
          has_entry( 'message',
                     equal_to( 'const Foo *cpFoo = &foo; // In main' ) ),
          requests.codes.ok ],

        # Cursor on usage
        [ { 'line_num': 45, 'column_num': 13 },
          has_entry( 'message',
                     equal_to( 'const Foo &crFoo = foo; // In main' ) ),
          requests.codes.ok ],
        # [ { 'line_num': 45, 'column_num': 19 }, 'const int' ],
        [ { 'line_num': 46, 'column_num': 13 },
          has_entry( 'message',
                     equal_to( 'const Foo *cpFoo = &foo; // In main' ) ),
          requests.codes.ok ],
        # [ { 'line_num': 46, 'column_num': 20 }, 'const int' ],
        [ { 'line_num': 47, 'column_num': 12 },
          has_entry( 'message', equal_to( 'Foo &rFoo = foo; // In main' ) ),
          requests.codes.ok ],
        [ { 'line_num': 47, 'column_num': 17 },
          has_entry( 'message', equal_to( 'public: int y; // In Foo' ) ),
          requests.codes.ok ],
        [ { 'line_num': 48, 'column_num': 12 },
          has_entry( 'message', equal_to( 'Foo *pFoo = &foo; // In main' ) ),
          requests.codes.ok ],
        [ { 'line_num': 48, 'column_num': 18 },
          has_entry( 'message', equal_to( 'public: int x; // In Foo' ) ),
          requests.codes.ok ],

        # Auto in declaration
        # [ { 'line_num': 28, 'column_num':  3 }, 'struct Foo &' ],
        # [ { 'line_num': 28, 'column_num': 11 }, 'struct Foo &' ],
        [ { 'line_num': 28, 'column_num': 18 },
          has_entry( 'message', equal_to( 'Foo foo; // In main' ) ),
          requests.codes.ok ],
        # [ { 'line_num': 29, 'column_num':  3 }, 'Foo *' ],
        # [ { 'line_num': 29, 'column_num': 11 }, 'Foo *' ],
        [ { 'line_num': 29, 'column_num': 18 },
          has_entry( 'message', equal_to( 'Foo foo; // In main' ) ),
          requests.codes.ok ],
        # [ { 'line_num': 31, 'column_num':  3 }, 'const Foo &' ],
        # [ { 'line_num': 31, 'column_num': 16 }, 'const Foo &' ],
        # [ { 'line_num': 32, 'column_num':  3 }, 'const Foo *' ],
        # [ { 'line_num': 32, 'column_num': 16 }, 'const Foo *' ],

        # Auto in usage
        # [ { 'line_num': 34, 'column_num': 14 }, 'const Foo' ],
        # [ { 'line_num': 34, 'column_num': 21 }, 'const int' ],
        # [ { 'line_num': 35, 'column_num': 14 }, 'const Foo *' ],
        # [ { 'line_num': 35, 'column_num': 22 }, 'const int' ],
        [ { 'line_num': 36, 'column_num': 13 },
          has_entry( 'message', equal_to( 'auto &arFoo = foo; // In main' ) ),
          requests.codes.ok ],
        [ { 'line_num': 36, 'column_num': 19 },
          has_entry( 'message', equal_to( 'public: int y; // In Foo' ) ),
          requests.codes.ok ],
        # [ { 'line_num': 37, 'column_num': 13 }, 'Foo *' ],
        [ { 'line_num': 37, 'column_num': 20 },
          has_entry( 'message', equal_to( 'public: int x; // In Foo' ) ),
          requests.codes.ok ],

        # Unicode
        [ { 'line_num': 51, 'column_num': 13 },
          has_entry( 'message', equal_to( 'Unicøde *ø; // In main' ) ),
          requests.codes.ok ],

        # Bound methods
        # On Win32, methods pick up an __attribute__((thiscall)) to annotate
        # their calling convention.  This shows up in the type, which isn't
        # ideal, but also prohibitively complex to try and strip out.
        [ { 'line_num': 53, 'column_num': 15 },
          has_entry( 'message', matches_regexp(
              r'int bar\(int i\)(?: '
              r'__attribute__\(\(thiscall\)\))?; // In Foo' ) ),
          requests.codes.ok ],
        [ { 'line_num': 54, 'column_num': 18 },
          has_entry( 'message', matches_regexp(
              r'int bar\(int i\)(?: _'
              r'_attribute__\(\(thiscall\)\))?; // In Foo' ) ),
          requests.codes.ok ],
        # Multi-line function declaration
        [ { 'line_num': 58, 'column_num': 20 },
          has_entry( 'message', equal_to(
              'unsigned long long long_function_name(unsigned long long first, '
              'unsigned long long second)' ) ),
          requests.codes.ok ],
        [ { 'line_num': 61, 'column_num': 20 },
          has_entry( 'message', equal_to(
              'unsigned long long long_function_name(unsigned long long first, '
              'unsigned long long second); // In namespace ns' ) ),
          requests.codes.ok ],
      ],
      [ 'GetType', 'GetTypeImprecise' ] ):
      with self.subTest( test = test, cmd = cmd ):
        RunGetSemanticTest( app,
                            PathToTestFile( 'GetType_Clang_test.cc' ),
                            'cpp',
                            test,
                            [ cmd ],
                            test[ 2 ] )


  @SharedYcmd
  def test_Subcommands_GetDoc( self, app ):
    for test, cmd in itertools.product( [
        # from local file
        [ { 'line_num': 5, 'column_num': 10 },
          has_entry( 'detailed_info', equal_to(
            'function docstring_int_main_TU_file\n\n→ void\ndocstring\n\n'
            'void docstring_int_main_TU_file()' ) ),
          requests.codes.ok ],
        # from header
        [ { 'line_num': 6, 'column_num': 10 },
          has_entry( 'detailed_info', equal_to(
            'function docstring_from_header_file\n\n→ void\ndocstring\n\n'
            'void docstring_from_header_file()' ) ),
          requests.codes.ok ],
        # no docstring
        [ { 'line_num': 7, 'column_num': 7 },
          has_entry( 'detailed_info', equal_to(
            'variable x\n\nType: int\nValue = 3\n\n'
            '// In docstring_int_main_TU_file\nint x = 3' ) ),
          requests.codes.ok ],
        # no hover
        [ { 'line_num': 8, 'column_num': 1 },
          ErrorMatcher( RuntimeError, 'No documentation available.' ),
          requests.codes.server_error ]
      ],
      [ 'GetDoc', 'GetDocImprecise' ] ):
      with self.subTest( test = test, cmd = cmd ):
        RunGetSemanticTest( app,
                            PathToTestFile( 'GetDoc_Clang_test.cc' ),
                            'cpp',
                            test,
                            [ cmd ],
                            test[ 2 ] )


  @SharedYcmd
  def test_Subcommands_FixIt_all( self, app ):
    for line, column, language, filepath, check in [
      [ 16, 1,  'cpp11', PathToTestFile( 'FixIt_Clang_cpp11.cpp' ),
        FixIt_Check_cpp11_Ins ],
      [ 25, 14, 'cpp11', PathToTestFile( 'FixIt_Clang_cpp11.cpp' ),
        FixIt_Check_cpp11_InsMultiLine ],
      [ 35, 7,  'cpp11', PathToTestFile( 'FixIt_Clang_cpp11.cpp' ),
        FixIt_Check_cpp11_Del ],
      [ 40, 6,  'cpp11', PathToTestFile( 'FixIt_Clang_cpp11.cpp' ),
        FixIt_Check_cpp11_Repl ],
      [ 48, 3,  'cpp11', PathToTestFile( 'FixIt_Clang_cpp11.cpp' ),
        FixIt_Check_cpp11_DelAdd ],
      [ 5, 3,   'objective-c', PathToTestFile( 'objc', 'FixIt_Clang_objc.m' ),
        FixIt_Check_objc ],
      [ 7, 1,   'objective-c', PathToTestFile( 'objc', 'FixIt_Clang_objc.m' ),
        FixIt_Check_objc_NoFixIt ],
      [ 3, 12,  'cuda', PathToTestFile( 'cuda', 'fixit_test.cu' ),
        FixIt_Check_cuda ],
      # multiple errors on a single line; both with fixits. The cursor is on the
      # first one (so just that one is fixed)
      [ 54, 15, 'cpp11', PathToTestFile( 'FixIt_Clang_cpp11.cpp' ),
        FixIt_Check_cpp11_MultiFirst ],
      # should put closest fix-it first?
      [ 54, 51, 'cpp11', PathToTestFile( 'FixIt_Clang_cpp11.cpp' ),
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
      with self.subTest( line = line,
                         column = column,
                         language = language,
                         filepath = filepath,
                         check = check ):
        RunFixItTest( app, line, column, language, filepath, check )


  @WithRetry()
  @SharedYcmd
  def test_Subcommands_FixIt_Ranged( self, app ):
    for test in [
      [ {
          'start': { 'line_num': 80, 'column_num': 1 },
          'end': { 'line_num': 80, 'column_num': 4 },
        },
        FixIt_Check_AutoExpand_Resolved ],
      [ {
          'start': { 'line_num': 83, 'column_num': 3 },
          'end': { 'line_num': 83, 'column_num': 13 },
        },
        FixIt_Check_MacroExpand_Resolved ],
      [ {
          'start': { 'line_num': 84, 'column_num': 14 },
          'end': { 'line_num': 84, 'column_num': 20 },
        },
        FixIt_Check_SubexprExtract_Resolved ],
      [ {
          'start': { 'line_num': 80, 'column_num': 19 },
          'end': { 'line_num': 80, 'column_num': 35 },
        },
        FixIt_Check_RawStringReplace_Resolved ],
    ]:
      with self.subTest( test = test ):
        RunRangedFixItTest( app, test[ 0 ], test[ 1 ] )


  @WithRetry()
  @SharedYcmd
  def test_Subcommands_FixIt_AlreadyResolved( self, app ):
    filename = PathToTestFile( 'FixIt_Clang_cpp11.cpp' )
    request = {
      'completer_target' : 'filetype_default',
      'contents'         : ReadFile( filename ),
      'filepath'         : filename,
      'command_arguments': [ 'FixIt' ],
      'line_num'         : 16,
      'column_num'       : 1,
      'filetype'         : 'cpp'
    }
    app.post_json( '/event_notification',
                   CombineRequest( request, {
                     'event_name': 'FileReadyToParse',
                   } ),
                   expect_errors = True )
    WaitUntilCompleterServerReady( app, 'cpp' )
    expected = app.post_json( '/run_completer_command',
                              BuildRequest( **request ) ).json
    print( 'expected = ' )
    print( expected )
    request[ 'fixit' ] = expected[ 'fixits' ][ 0 ]
    actual = app.post_json( '/resolve_fixit',
                            BuildRequest( **request ) ).json
    print( 'actual = ' )
    print( actual )
    assert_that( actual, equal_to( expected ) )


  @WithRetry()
  @IsolatedYcmd( { 'clangd_args': [ '-hidden-features' ] } )
  def test_Subcommands_FixIt_ClangdTweaks( self, app ):
    selection = {
        'start': { 'line_num': 80, 'column_num': 19 },
        'end': { 'line_num': 80, 'column_num': 4 }
    }

    def NoFixitsProduced( results ):
      assert_that( results, has_entries( {
        'fixits': contains_exactly( has_entries( {
          'chunks': [],
          'location': LocationMatcher(
                        PathToTestFile( 'FixIt_Clang_cpp11.cpp' ), 1, 1 )
        } ) )
      } ) )
    RunRangedFixItTest( app, selection, NoFixitsProduced, 2 )


  @SharedYcmd
  def test_Subcommands_RefactorRename( self, app ):
    basic_cpp = PathToTestFile( 'basic.cpp' )
    gettype_clang_text_cc = PathToTestFile( 'GetType_Clang_test.cc' )
    goto_clang_zerobasedline = PathToTestFile(
        'GoTo_Clang_ZeroBasedLineAndColumn_test.cc' )
    test = {
      'request': {
        'filetype': 'cpp',
        'completer_target': 'filetype_default',
        'contents': ReadFile( basic_cpp ),
        'filepath': basic_cpp,
        'command_arguments': [ 'RefactorRename', 'Bar' ],
        'line_num': 17,
        'column_num': 4,
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'fixits': contains_exactly( has_entries( {
            'chunks': contains_exactly(
              ChunkMatcher( 'Bar',
                            LocationMatcher( gettype_clang_text_cc, 12, 8 ),
                            LocationMatcher( gettype_clang_text_cc, 12, 11 ) ),
              ChunkMatcher( 'Bar',
                            LocationMatcher( gettype_clang_text_cc, 24, 3 ),
                            LocationMatcher( gettype_clang_text_cc, 24, 6 ) ),
              ChunkMatcher( 'Bar',
                            LocationMatcher( gettype_clang_text_cc, 39, 3 ),
                            LocationMatcher( gettype_clang_text_cc, 39, 6 ) ),
              ChunkMatcher( 'Bar',
                            LocationMatcher( gettype_clang_text_cc, 40, 3 ),
                            LocationMatcher( gettype_clang_text_cc, 40, 6 ) ),
              ChunkMatcher( 'Bar',
                            LocationMatcher( gettype_clang_text_cc, 42, 9 ),
                            LocationMatcher( gettype_clang_text_cc, 42, 12 ) ),
              ChunkMatcher( 'Bar',
                            LocationMatcher( gettype_clang_text_cc, 43, 9 ),
                            LocationMatcher( gettype_clang_text_cc, 43, 12 ) ),
              ChunkMatcher(
                'Bar',
                LocationMatcher( goto_clang_zerobasedline, 2, 8 ),
                LocationMatcher( goto_clang_zerobasedline, 2, 11 ) ),
              ChunkMatcher(
                'Bar',
                LocationMatcher( goto_clang_zerobasedline, 10, 3 ),
                LocationMatcher( goto_clang_zerobasedline, 10, 6 ) ),
              ChunkMatcher( 'Bar',
                            LocationMatcher( basic_cpp, 1, 8 ),
                            LocationMatcher( basic_cpp, 1, 11 ) ),
              ChunkMatcher( 'Bar',
                            LocationMatcher( basic_cpp, 9, 3 ),
                            LocationMatcher( basic_cpp, 9, 6 ) ),
              ChunkMatcher( 'Bar',
                            LocationMatcher( basic_cpp, 15,  8 ),
                            LocationMatcher( basic_cpp, 15, 11 ) ),
              ChunkMatcher( 'Bar',
                            LocationMatcher( basic_cpp, 17, 3 ),
                            LocationMatcher( basic_cpp, 17, 6 ) ),
            )
          } ) )
        } )
      },
      'route': '/run_completer_command'
    }
    RunAfterInitialized( app, test )
