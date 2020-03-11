# Copyright (C) 2015-2020 ycmd contributors
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
                       contains_exactly,
                       contains_inanyorder,
                       empty,
                       equal_to,
                       has_entries,
                       has_entry,
                       matches_regexp )
from unittest.mock import patch
from pprint import pformat
import os
import pytest
import requests

from ycmd import handlers
from ycmd.completers.language_server.language_server_completer import (
  ResponseFailedException
)
from ycmd.tests.go import ( PathToTestFile,
                            SharedYcmd,
                            StartGoCompleterServerInDirectory )
from ycmd.tests.test_utils import ( BuildRequest,
                                    ChunkMatcher,
                                    ErrorMatcher,
                                    ExpectedFailure,
                                    LocationMatcher )
from ycmd.utils import ReadFile


RESPONSE_TIMEOUT = 5


def RunTest( app, test, contents = None ):
  if not contents:
    contents = ReadFile( test[ 'request' ][ 'filepath' ] )

  def CombineRequest( request, data ):
    kw = request
    request.update( data )
    return BuildRequest( **kw )

  # Because we aren't testing this command, we *always* ignore errors. This
  # is mainly because we (may) want to test scenarios where the completer
  # throws an exception and the easiest way to do that is to throw from
  # within the FlagsForFile function.
  app.post_json( '/event_notification',
                 CombineRequest( test[ 'request' ], {
                                 'event_name': 'FileReadyToParse',
                                 'contents': contents,
                                 'filetype': 'go',
                                 } ),
                 expect_errors = True )

  # We also ignore errors here, but then we check the response code
  # ourself. This is to allow testing of requests returning errors.
  response = app.post_json(
    '/run_completer_command',
    CombineRequest( test[ 'request' ], {
      'completer_target': 'filetype_default',
      'contents': contents,
      'filetype': 'go',
      'command_arguments': ( [ test[ 'request' ][ 'command' ] ]
                             + test[ 'request' ].get( 'arguments', [] ) )
    } ),
    expect_errors = True
  )

  print( 'completer response: {}'.format( pformat( response.json ) ) )

  assert_that( response.status_code,
               equal_to( test[ 'expect' ][ 'response' ] ) )
  assert_that( response.json, test[ 'expect' ][ 'data' ] )


def RunFixItTest( app, description, filepath, line, col, fixits_for_line ):
  RunTest( app, {
    'description': description,
    'request': {
      'command': 'FixIt',
      'line_num': line,
      'column_num': col,
      'filepath': filepath,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': fixits_for_line,
    }
  } )


@SharedYcmd
def Subcommands_DefinedSubcommands_test( app ):
  subcommands_data = BuildRequest( completer_target = 'go' )

  assert_that( app.post_json( '/defined_subcommands', subcommands_data ).json,
               contains_inanyorder( 'Format',
                                    'GetDoc',
                                    'GetType',
                                    'RefactorRename',
                                    'GoTo',
                                    'GoToDeclaration',
                                    'GoToDefinition',
                                    'GoToReferences',
                                    'GoToImplementation',
                                    'GoToType',
                                    'FixIt',
                                    'RestartServer',
                                    'ExecuteCommand' ) )


@SharedYcmd
def Subcommands_ServerNotInitialized_test( app ):
  filepath = PathToTestFile( 'goto.go' )

  completer = handlers._server_state.GetFiletypeCompleter( [ 'go' ] )

  @patch.object( completer, '_ServerIsInitialized', return_value = False )
  def Test( app, cmd, arguments, *args ):
    RunTest( app, {
      'description': 'Subcommand ' + cmd + ' handles server not ready',
      'request': {
        'command': cmd,
        'line_num': 1,
        'column_num': 1,
        'filepath': filepath,
        'arguments': arguments,
      },
      'expect': {
        'response': requests.codes.internal_server_error,
        'data': ErrorMatcher( RuntimeError,
                              'Server is initializing. Please wait.' ),
      }
    } )

  Test( app, 'Format', [] )
  Test( app, 'GetDoc', [] )
  Test( app, 'GetType', [] )
  Test( app, 'GoTo', [] )
  Test( app, 'GoToDeclaration', [] )
  Test( app, 'GoToDefinition', [] )
  Test( app, 'GoToType', [] )
  Test( app, 'FixIt', [] )


@SharedYcmd
def Subcommands_Format_WholeFile_test( app ):
  # RLS can't execute textDocument/formatting if any file
  # under the project root has errors, so we need to use
  # a different project just for formatting.
  # For further details check https://github.com/go-lang/rls/issues/1397
  project_dir = PathToTestFile()
  StartGoCompleterServerInDirectory( app, project_dir )

  filepath = os.path.join( project_dir, 'goto.go' )

  RunTest( app, {
    'description': 'Formatting is applied on the whole file',
    'request': {
      'command': 'Format',
      'filepath': filepath,
      'options': {
        'tab_size': 2,
        'insert_spaces': True
      }
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'fixits': contains_exactly( has_entries( {
          'chunks': contains_exactly(
            ChunkMatcher( '',
                          LocationMatcher( filepath, 8, 1 ),
                          LocationMatcher( filepath, 9, 1 ) ),
            ChunkMatcher( '\tdummy() //GoTo\n',
                          LocationMatcher( filepath, 9, 1 ),
                          LocationMatcher( filepath, 9, 1 ) ),
            ChunkMatcher( '',
                          LocationMatcher( filepath, 12, 1 ),
                          LocationMatcher( filepath, 13, 1 ) ),
            ChunkMatcher( '\tdiagnostics_test\n',
                          LocationMatcher( filepath, 13, 1 ),
                          LocationMatcher( filepath, 13, 1 ) ),
          )
        } ) )
      } )
    }
  } )


@ExpectedFailure( 'rangeFormat is not yet implemented',
                  matches_regexp( '\nExpected: <200>\n     but: was <500>\n' ) )
@SharedYcmd
def Subcommands_Format_Range_test( app ):
  project_dir = PathToTestFile()
  StartGoCompleterServerInDirectory( app, project_dir )

  filepath = os.path.join( project_dir, 'goto.go' )

  RunTest( app, {
    'description': 'Formatting is applied on some part of the file',
    'request': {
      'command': 'Format',
      'filepath': filepath,
      'range': {
        'start': {
          'line_num': 7,
          'column_num': 1,
        },
        'end': {
          'line_num': 9,
          'column_num': 2
        }
      },
      'options': {
        'tab_size': 4,
        'insert_spaces': False
      }
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'fixits': contains_exactly( has_entries( {
          'chunks': contains_exactly(
            ChunkMatcher( 'fn unformatted_function(param: bool) -> bool {\n'
                          '\treturn param;\n'
                          '}\n'
                          '\n'
                          'fn \n'
                          'main()\n'
                          '                                {\n'
                          '        unformatted_function( false );\n'

                          '}\n',
                          LocationMatcher( filepath, 1, 1 ),
                          LocationMatcher( filepath, 9, 1 ) ),
          )
        } ) )
      } )
    }
  } )


@SharedYcmd
def Subcommands_GetDoc_UnknownType_test( app ):
  RunTest( app, {
    'description': 'GetDoc on a unknown type raises an error',
    'request': {
      'command': 'GetDoc',
      'line_num': 2,
      'column_num': 4,
      'filepath': PathToTestFile( 'td', 'test.go' ),
    },
    'expect': {
      'response': requests.codes.internal_server_error,
      'data': ErrorMatcher( RuntimeError, 'No documentation available.' )
    }
  } )


@SharedYcmd
def Subcommands_GetDoc_Function_test( app ):
  RunTest( app, {
    'description': 'GetDoc on a function returns its type',
    'request': {
      'command': 'GetDoc',
      'line_num': 9,
      'column_num': 6,
      'filepath': PathToTestFile( 'td', 'test.go' ),
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entry( 'detailed_info', 'func Hello()\nNow with doc!' ),
    }
  } )


@SharedYcmd
def Subcommands_GetType_UnknownType_test( app ):
  RunTest( app, {
    'description': 'GetType on a unknown type raises an error',
    'request': {
      'command': 'GetType',
      'line_num': 2,
      'column_num': 4,
      'filepath': PathToTestFile( 'td', 'test.go' ),
    },
    'expect': {
      'response': requests.codes.internal_server_error,
      'data': ErrorMatcher( RuntimeError, 'Unknown type.' )
    }
  } )


@SharedYcmd
def Subcommands_GetType_Function_test( app ):
  RunTest( app, {
    'description': 'GetType on a function returns its type',
    'request': {
      'command': 'GetType',
      'line_num': 9,
      'column_num': 6,
      'filepath': PathToTestFile( 'td', 'test.go' ),
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entry( 'message', 'func Hello()' ),
    }
  } )


def RunGoToTest( app, command, test ):
  folder = PathToTestFile()
  filepath = PathToTestFile( test[ 'req' ][ 0 ] )
  request = {
    'command': command,
    'line_num': test[ 'req' ][ 1 ],
    'column_num': test[ 'req' ][ 2 ],
    'filepath': filepath,
  }

  response = test[ 'res' ]

  if isinstance( response, list ):

    expect = {
      'response': requests.codes.ok,
      'data': contains_exactly( *[
        LocationMatcher(
          os.path.join( folder, location[ 0 ] ),
          location[ 1 ],
          location[ 2 ]
        ) for location in response
      ] )
    }
  elif isinstance( response, tuple ):
    expect = {
      'response': requests.codes.ok,
      'data': LocationMatcher(
        os.path.join( folder, response[ 0 ] ),
        response[ 1 ],
        response[ 2 ]
      )
    }
  else:
    expect = {
      'response': requests.codes.internal_server_error,
      'data': ErrorMatcher( ResponseFailedException )
    }

  RunTest( app, {
    'request': request,
    'expect' : expect
  } )


@pytest.mark.parametrize( 'command', [ 'GoToDeclaration',
                                       'GoToDefinition',
                                       'GoTo' ] )
@pytest.mark.parametrize( 'test', [
    # Struct
    { 'req': ( os.path.join( 'unicode', 'unicode.go' ), 13, 5 ),
      'res': ( os.path.join( 'unicode', 'unicode.go' ), 10, 5 ) },
    # Function
    { 'req': ( 'goto.go', 8, 5 ), 'res': ( 'goto.go', 3, 6 ) },
    # Keyword
    { 'req': ( 'goto.go', 3, 2 ), 'res': 'Cannot jump to location' },
  ] )
@SharedYcmd
def Subcommands_GoTo_test( app, command, test ):
  RunGoToTest( app, command, test )


@pytest.mark.parametrize( 'test', [
    # Works
    { 'req': ( os.path.join( 'unicode', 'unicode.go' ), 13, 5 ),
      'res': ( os.path.join( 'unicode', 'unicode.go' ), 3, 6 ) },
    # Fails
    { 'req': ( os.path.join( 'unicode', 'unicode.go' ), 11, 7 ),
      'res': 'Cannot jump to location' } ] )
@SharedYcmd
def Subcommands_GoToType_test( app, test ):
  RunGoToTest( app, 'GoToType', test )


@pytest.mark.parametrize( 'test', [
    # Works
    { 'req': ( 'thing.go', 3, 8 ),
      'res': ( 'thing.go', 7, 6 ) },
    # Fails
    { 'req': ( 'thing.go', 12, 7 ),
      'res': 'Cannot jump to location' } ] )
@SharedYcmd
def Subcommands_GoToImplementation_test( app, test ):
  RunGoToTest( app, 'GoToImplementation', test )


@ExpectedFailure( 'Gopls bug - golang/go#37702',
                  matches_regexp( '.*No item matched.*' ) )
@SharedYcmd
def Subcommands_FixIt_FixItWorksAtEndOfFile_test( app ):
  filepath = PathToTestFile( 'fixit_goplsbug.go' )
  fixit = has_entries( {
    'fixits': contains_exactly(
      has_entries( {
        'text': "Organize Imports",
        'chunks': contains_exactly(
          ChunkMatcher( '',
                        LocationMatcher( filepath, 1, 1 ),
                        LocationMatcher( filepath, 3, 1 ) ),
          ChunkMatcher( 'package main',
                        LocationMatcher( filepath, 3, 1 ),
                        LocationMatcher( filepath, 3, 1 ) ),
        ),
      } ),
    )
  } )
  RunFixItTest( app, 'Only one fixit returned', filepath, 1, 1, fixit )


@SharedYcmd
def Subcommands_FixIt_NullResponse_test( app ):
  filepath = PathToTestFile( 'td', 'test.go' )
  RunFixItTest( app,
                'Gopls returned NULL for response[ \'result\' ]',
                filepath, 1, 1, has_entry( 'fixits', empty() ) )


@SharedYcmd
def Subcommands_FixIt_ParseError_test( app ):
  RunTest( app, {
    'description': 'Parse error leads to ResponseFailedException',
    'request': {
      'command': 'FixIt',
      'line_num': 1,
      'column_num': 1,
      'filepath': PathToTestFile( 'unicode', 'unicode.go' ),
    },
    'expect': {
      'response': requests.codes.internal_server_error,
      'data': ErrorMatcher( ResponseFailedException,
                            matches_regexp( '^Request failed: \\d' ) )
    }
  } )


@SharedYcmd
def Subcommands_FixIt_Simple_test( app ):
  filepath = PathToTestFile( 'fixit.go' )
  fixit = has_entries( {
    'fixits': contains_exactly(
      has_entries( {
        'text': "Organize Imports",
        'chunks': contains_exactly(
          ChunkMatcher( '',
                        LocationMatcher( filepath, 1, 1 ),
                        LocationMatcher( filepath, 3, 1 ) ),
          ChunkMatcher( 'package main',
                        LocationMatcher( filepath, 3, 1 ),
                        LocationMatcher( filepath, 3, 1 ) ),
        ),
      } ),
    )
  } )
  RunFixItTest( app, 'Only one fixit returned', filepath, 1, 1, fixit )


@SharedYcmd
def Subcommands_RefactorRename_test( app ):
  filepath = PathToTestFile( 'unicode', 'unicode.go' )
  RunTest( app, {
    'description': 'RefactorRename on a function renames all its occurences',
    'request': {
      'command': 'RefactorRename',
      'arguments': [ 'xxx' ],
      'line_num': 10,
      'column_num': 17,
      'filepath': filepath
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'fixits': contains_exactly( has_entries( {
          'text': '',
          'chunks': contains_exactly(
            ChunkMatcher( 'xxx',
                          LocationMatcher( filepath, 3, 6 ),
                          LocationMatcher( filepath, 3, 10 ) ),
            ChunkMatcher( 'xxx',
                          LocationMatcher( filepath, 10, 16 ),
                          LocationMatcher( filepath, 10, 20 ) ),
          )
        } ) )
      } )
    }
  } )


@SharedYcmd
def Subcommands_GoToReferences_test( app ):
  filepath = os.path.join( 'unicode', 'unicode.go' )
  test = { 'req': ( filepath, 10, 5 ), 'res': [ ( filepath, 10, 5 ),
                                                ( filepath, 13, 5 ) ] }
  RunGoToTest( app, 'GoToReferences', test )
