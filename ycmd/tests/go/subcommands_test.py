# Copyright (C) 2015-2019 ycmd contributors
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

from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa

from hamcrest import ( assert_that,
                       contains,
                       contains_inanyorder,
                       empty,
                       equal_to,
                       has_entries,
                       has_entry,
                       matches_regexp )
from mock import patch
from pprint import pformat
import os
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


@SharedYcmd
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
                                    'GetType',
                                    'GoTo',
                                    'GoToDeclaration',
                                    'GoToDefinition',
                                    'GoToType',
                                    'FixIt',
                                    'RestartServer' ) )


def Subcommands_ServerNotInitialized_test():
  filepath = PathToTestFile( 'goto.go' )

  completer = handlers._server_state.GetFiletypeCompleter( [ 'go' ] )

  @SharedYcmd
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

  yield Test, 'Format', []
  yield Test, 'GetType', []
  yield Test, 'GoTo', []
  yield Test, 'GoToDeclaration', []
  yield Test, 'GoToDefinition', []
  yield Test, 'GoToType', []
  yield Test, 'FixIt', []


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
        'fixits': contains( has_entries( {
          'chunks': contains(
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
        'fixits': contains( has_entries( {
          'chunks': contains(
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
      'line_num': 8,
      'column_num': 6,
      'filepath': PathToTestFile( 'td', 'test.go' ),
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entry( 'message', 'func Hello()' ),
    }
  } )


@SharedYcmd
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
      'data': contains( *[
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


def Subcommands_GoTo_test():
  unicode_go_path = os.path.join( 'unicode', 'unicode.go' )
  tests = [
    # Struct
    { 'req': ( unicode_go_path, 13, 5 ), 'res': ( unicode_go_path, 10, 5 ) },
    # Function
    { 'req': ( 'goto.go', 8, 5 ), 'res': ( 'goto.go', 3, 6 ) },
    # Keyword
    { 'req': ( 'goto.go', 3, 2 ), 'res': 'Cannot jump to location' },
  ]

  for test in tests:
    for command in [ 'GoToDeclaration', 'GoToDefinition', 'GoTo' ]:
      yield RunGoToTest, command, test


def Subcommands_GoToType_test():
  unicode_go_path = os.path.join( 'unicode', 'unicode.go' )
  tests = [
    # Works
    { 'req': ( unicode_go_path, 13, 5 ), 'res': ( unicode_go_path, 3, 6 ) },
    # Fails
    { 'req': ( unicode_go_path, 11, 7 ), 'res': 'Cannot jump to location' } ]
  for test in tests:
    yield RunGoToTest, 'GoToType', test


def Subcommands_FixIt_NullResponse_test():
  filepath = PathToTestFile( 'td', 'test.go' )
  yield ( RunFixItTest, 'Gopls returned NULL for response[ \'result\' ]',
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


def Subcommands_FixIt_Simple_test():
  filepath = PathToTestFile( 'goto.go' )
  fixit = has_entries( {
    'fixits': contains(
      has_entries( {
        'text': "Organize Imports",
        'chunks': contains(
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
        ),
      } ),
    )
  } )
  yield ( RunFixItTest, 'Only one fixit returned',
          filepath, 1, 1, fixit )
