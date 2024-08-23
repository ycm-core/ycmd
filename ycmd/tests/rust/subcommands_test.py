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

from hamcrest import ( assert_that,
                       has_item,
                       contains_exactly,
                       contains_inanyorder,
                       empty,
                       equal_to,
                       has_entries,
                       has_entry,
                       matches_regexp )
from unittest.mock import patch
from unittest import TestCase
from pprint import pformat
import itertools
import os
import requests

from ycmd import handlers
from ycmd.tests.rust import setUpModule, tearDownModule # noqa
from ycmd.tests.rust import ( PathToTestFile,
                              SharedYcmd,
                              IsolatedYcmd,
                              StartRustCompleterServerInDirectory )
from ycmd.tests.test_utils import ( BuildRequest,
                                    ChunkMatcher,
                                    ErrorMatcher,
                                    ExpectedFailure,
                                    LocationMatcher,
                                    WaitForDiagnosticsToBeReady,
                                    WithRetry )
from ycmd.utils import ReadFile


RESPONSE_TIMEOUT = 5


def RunTest( app, test, contents = None ):
  filepath = test[ 'request' ][ 'filepath' ]
  if not contents:
    contents = ReadFile( filepath )

  def CombineRequest( request, data ):
    kw = request
    request.update( data )
    return BuildRequest( **kw )

  # Because we aren't testing this command, we *always* ignore errors. This
  # is mainly because we (may) want to test scenarios where the completer
  # throws an exception and the easiest way to do that is to throw from
  # within the FlagsForFile function.
  app.post_json( test.get( 'route', '/run_completer_command' ),
                 CombineRequest( test[ 'request' ], {
                                 'event_name': 'FileReadyToParse',
                                 'contents': contents,
                                 'filetype': 'rust',
                                 } ),
                 expect_errors = True )

  # rust-analyzer sometimes needs a bit of time after opening a new file.
  # Probably to relax after some hard work...
  WaitForDiagnosticsToBeReady( app, filepath, contents, 'rust' )

  # We also ignore errors here, but then we check the response code
  # ourself. This is to allow testing of requests returning errors.
  response = app.post_json(
    test.get( 'route', '/run_completer_command' ),
    CombineRequest( test[ 'request' ], {
      'completer_target': 'filetype_default',
      'contents': contents,
      'filetype': 'rust',
      'command_arguments': ( [ test[ 'request' ][ 'command' ] ]
                             + test[ 'request' ].get( 'arguments', [] ) )
    } ),
    expect_errors = True
  )

  print( f'completer response: { pformat( response.json ) }' )

  if 'expect' in test:
    assert_that( response.status_code,
                 equal_to( test[ 'expect' ][ 'response' ] ) )
    assert_that( response.json, test[ 'expect' ][ 'data' ] )
  return response.json


def RunFixItTest( app, test ):
  if 'chosen_fixit' in test:
    test_no_expect = test.copy()
    test_no_expect.pop( 'expect' )
    response = RunTest( app, test_no_expect )
    request = test[ 'request' ]
    request.update( {
      'fixit': response[ 'fixits' ][ test[ 'chosen_fixit' ] ]
    } )
    test[ 'route' ] = '/resolve_fixit'
  RunTest( app, test )


def RunHierarchyTest( app, kind, direction, location, expected, code ):
  file, line, column = location
  request = {
    'completer_target' : 'filetype_default',
    'command': f'{ kind.title() }Hierarchy',
    'line_num'         : line,
    'column_num'       : column,
    'filepath'         : file,
  }
  test = { 'request': request,
           'route': '/run_completer_command' }
  prepare_hierarchy_response = RunTest( app, test )
  request.update( {
    'command': f'Resolve{ kind.title() }HierarchyItem',
    'arguments': [
      prepare_hierarchy_response[ 0 ],
      direction
    ]
  } )
  test[ 'expect' ] = {
    'response': code,
    'data': expected
  }
  RunTest( app, test )


def RunGoToTest( app, command, test, *, project_root = 'common' ):
  folder = PathToTestFile( project_root, 'src' )
  filepath = os.path.join( folder, test[ 'req' ][ 0 ] )
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
      'data': contains_inanyorder( *[
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
    error_type = test.get( 'exc', RuntimeError )
    expect = {
      'response': requests.codes.internal_server_error,
      'data': ErrorMatcher( error_type, test[ 'res' ] )
    }

  RunTest( app, {
    'request': request,
    'expect' : expect
  } )


class SubcommandsTest( TestCase ):
  @SharedYcmd
  def test_Subcommands_DefinedSubcommands( self, app ):
    subcommands_data = BuildRequest( completer_target = 'rust' )

    assert_that( app.post_json( '/defined_subcommands', subcommands_data ).json,
                 contains_inanyorder( 'FixIt',
                                      'Format',
                                      'GetDoc',
                                      'GetType',
                                      'GoTo',
                                      'GoToCallees',
                                      'GoToCallers',
                                      'GoToDeclaration',
                                      'GoToDefinition',
                                      'GoToDocumentOutline',
                                      'GoToImplementation',
                                      'GoToReferences',
                                      'GoToSymbol',
                                      'GoToType',
                                      'CallHierarchy',
                                      'ResolveCallHierarchyItem',
                                      'RefactorRename',
                                      'RestartServer' ) )


  @SharedYcmd
  def test_Subcommands_ServerNotInitialized( self, app ):
    filepath = PathToTestFile( 'common', 'src', 'main.rs' )

    completer = handlers._server_state.GetFiletypeCompleter( [ 'rust' ] )

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
    Test( app, 'FixIt', [] )
    Test( app, 'GetType', [] )
    Test( app, 'GetDoc', [] )
    Test( app, 'GoTo', [] )
    Test( app, 'GoToDeclaration', [] )
    Test( app, 'GoToDefinition', [] )
    Test( app, 'GoToImplementation', [] )
    Test( app, 'GoToReferences', [] )
    Test( app, 'CallHierarchy', [] )
    Test( app, 'RefactorRename', [ 'test' ] )


  @WithRetry()
  @SharedYcmd
  def test_Subcommands_Format_WholeFile( self, app ):
    filepath = PathToTestFile( 'common', 'src', 'main.rs' )

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
              ChunkMatcher( "",
                            LocationMatcher( filepath, 18,  4 ),
                            LocationMatcher( filepath, 18, 16 ) ),
              ChunkMatcher( "",
                            LocationMatcher( filepath, 19,  1 ),
                            LocationMatcher( filepath, 20,  1 ) ),
              ChunkMatcher( "",
                            LocationMatcher( filepath, 20,  8 ),
                            LocationMatcher( filepath, 21,  8 ) ),
              ChunkMatcher( "",
                            LocationMatcher( filepath, 21, 10 ),
                            LocationMatcher( filepath, 21, 11 ) ),
              ChunkMatcher( "",
                            LocationMatcher( filepath, 21, 13 ),
                            LocationMatcher( filepath, 22,  1 ) ),
            )
          } ) )
        } )
      }
    } )


  @ExpectedFailure(
    'rangeFormat is not yet implemented',
    matches_regexp( '\nExpected: <200>\n     but: was <500>\n' ) )
  @SharedYcmd
  def test_Subcommands_Format_Range( self, app ):
    filepath = PathToTestFile( 'common', 'src', 'main.rs' )

    RunTest( app, {
      'description': 'Formatting is applied on some part of the file',
      'request': {
        'command': 'Format',
        'filepath': filepath,
        'range': {
          'start': {
            'line_num': 18,
            'column_num': 1,
          },
          'end': {
            'line_num': 23,
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
              ChunkMatcher( 'fn format_test() {\n'
                            '\tlet a: i32 = 5;\n',
                            LocationMatcher( filepath, 18, 1 ),
                            LocationMatcher( filepath, 23, 1 ) ),
            )
          } ) )
        } )
      }
    } )


  @SharedYcmd
  def test_Subcommands_GetDoc_NoDocumentation( self, app ):
    RunTest( app, {
      'description': 'GetDoc on a function with no documentation '
                     'raises an error',
      'request': {
        'command': 'GetDoc',
        'line_num': 3,
        'column_num': 11,
        'filepath': PathToTestFile( 'common', 'src', 'test.rs' ),
      },
      'expect': {
        'response': requests.codes.internal_server_error,
        'data': ErrorMatcher( RuntimeError,
                              'No documentation available.' )
      }
    } )


  @WithRetry()
  @SharedYcmd
  def test_Subcommands_GetDoc_Function( self, app ):
    RunTest( app, {
      'description': 'GetDoc on a function returns its documentation',
      'request': {
        'command': 'GetDoc',
        'line_num': 2,
        'column_num': 8,
        'filepath': PathToTestFile( 'common', 'src', 'test.rs' ),
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entry( 'detailed_info',
                           'common::test\n'
                           'pub fn create_universe()\n'
                           '---\n'
                           'Be careful when using that function' ),
      }
    } )


  @SharedYcmd
  def test_Subcommands_GetType_UnknownType( self, app ):
    RunTest( app, {
      'description': 'GetType on a unknown type raises an error',
      'request': {
        'command': 'GetType',
        'line_num': 3,
        'column_num': 4,
        'filepath': PathToTestFile( 'common', 'src', 'test.rs' ),
      },
      'expect': {
        'response': requests.codes.internal_server_error,
        'data': ErrorMatcher( RuntimeError, 'Unknown type.' )
      }
    } )


  @WithRetry()
  @SharedYcmd
  def test_Subcommands_GetType_Function( self, app ):
    RunTest( app, {
      'description': 'GetType on a function returns its type',
      'request': {
        'command': 'GetType',
        'line_num': 2,
        'column_num': 22,
        'filepath': PathToTestFile( 'common', 'src', 'test.rs' ),
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entry( 'message', 'pub fn create_universe()' ),
      }
    } )


  @SharedYcmd
  def test_Subcommands_GoToType_Basic( self, app ):
    for test in [
      # Variable
      { 'req': ( 'main.rs', 15,  5 ), 'res': ( 'test.rs', 4, 12 ) },
      # Type
      { 'req': ( 'main.rs', 14, 19 ), 'res': ( 'test.rs', 4, 12 ) },
      # Function
      { 'req': ( 'main.rs', 13, 14 ), 'res': 'Cannot jump to location' },
      # Keyword
      { 'req': ( 'main.rs',  4,  2 ), 'res': 'Cannot jump to location' },
    ]:
      with self.subTest( test = test ):
        RunGoToTest( app, 'GoToType', test )


  @WithRetry()
  @SharedYcmd
  def test_Subcommands_GoTo( self, app ):
    for test, command in itertools.product(
        [
          # Structure
          { 'req': ( 'main.rs',  9, 24 ), 'res': ( 'main.rs', 6, 8 ) },
          # Function
          { 'req': ( 'main.rs', 13, 14 ), 'res': ( 'test.rs', 2, 8 ) },
          # Implementation
          { 'req': ( 'main.rs',  10, 12 ), 'res': ( 'main.rs', 8, 7 ) },
          # Keyword
          { 'req': ( 'main.rs',  4,  2 ), 'res': 'Cannot jump to location' },
        ],
        [ 'GoToDefinition', 'GoTo' ] ):
      with self.subTest( test = test, command = command ):
        RunGoToTest( app, command, test )


  @WithRetry()
  @SharedYcmd
  def test_Subcommands_GoToImplementation( self, app ):
    for test in [
      # Structure
      { 'req': ( 'main.rs',  6,  9 ), 'res': ( 'main.rs', 9, 21 ) },
      # Trait
      { 'req': ( 'main.rs',  8,  7 ), 'res': [ ( 'main.rs', 9, 21 ),
                                               ( 'main.rs', 10, 21 ) ] },
    ]:
      with self.subTest( test = test ):
        RunGoToTest( app, 'GoToImplementation', test )


  @WithRetry()
  @SharedYcmd
  def test_Subcommands_GoToImplementation_Failure( self, app ):
    RunGoToTest( app,
                 'GoToImplementation',
                 { 'req': ( 'main.rs', 12,  2 ),
                   'res': 'Cannot jump to location',
                   'exc': RuntimeError } )


  @SharedYcmd
  def test_Subcommands_GoToReferences( self, app ):
    for test in [
      # Struct
      { 'req': ( 'main.rs', 10, 22 ), 'res': [ ( 'main.rs',  7,  8 ),
                                               ( 'main.rs', 10, 21 ) ] },
      # Function
      { 'req': ( 'main.rs', 13,  8 ), 'res': [ ( 'test.rs',  2,  8 ),
                                               ( 'main.rs', 13,  5 ) ] },
      # Implementation
      { 'req': ( 'main.rs',  9, 10 ), 'res': [ ( 'main.rs',  8,  7 ),
                                               ( 'main.rs',  9,  6 ),
                                               ( 'main.rs', 10,  6 ) ] },
      # Keyword
      { 'req': ( 'main.rs',  2,  1 ), 'res': 'Cannot jump to location' }
    ]:
      with self.subTest( test = test ):
        RunGoToTest( app, 'GoToReferences', test )


  @WithRetry()
  @SharedYcmd
  def test_Subcommands_RefactorRename_Works( self, app ):
    main_filepath = PathToTestFile( 'common', 'src', 'main.rs' )
    test_filepath = PathToTestFile( 'common', 'src', 'test.rs' )

    RunTest( app, {
      'description': 'RefactorRename on a function renames all its occurences',
      'request': {
        'command': 'RefactorRename',
        'arguments': [ 'update_universe' ],
        'line_num': 13,
        'column_num': 16,
        'filepath': main_filepath
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'fixits': contains_exactly( has_entries( {
            'text': '',
            'chunks': contains_exactly(
              ChunkMatcher( 'update_universe',
                            LocationMatcher( main_filepath, 13,  5 ),
                            LocationMatcher( main_filepath, 13, 20 ) ),
              ChunkMatcher( 'update_universe',
                            LocationMatcher( test_filepath,  2,  8 ),
                            LocationMatcher( test_filepath,  2, 23 ) ),
            )
          } ) )
        } )
      }
    } )


  @SharedYcmd
  def test_Subcommands_RefactorRename_Invalid( self, app ):
    RunTest( app, {
      'description': 'RefactorRename raises an error when cursor is invalid',
      'request': {
        'command': 'RefactorRename',
        'arguments': [ 'update_universe' ],
        'line_num': 16,
        'column_num': 7,
        'filepath': PathToTestFile( 'common', 'src', 'main.rs' )
      },
      'expect': {
        'response': requests.codes.internal_server_error,
        'data': ErrorMatcher( RuntimeError,
                              'Cannot rename the symbol under cursor.' )
      }
    } )


  @SharedYcmd
  def test_Subcommands_FixIt_EmptyResponse( self, app ):
    filepath = PathToTestFile( 'common', 'src', 'main.rs' )

    RunFixItTest( app, {
      'description': 'FixIt on a line with no '
                     'codeAction returns empty response',
      'request': {
        'command': 'FixIt',
        'line_num': 17,
        'column_num': 1,
        'filepath': filepath
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entry( 'fixits', empty() )
      }
    } )


  @SharedYcmd
  def test_Subcommands_FixIt_Basic( self, app ):
    filepath = PathToTestFile( 'common', 'src', 'main.rs' )

    RunFixItTest( app, {
      'description': 'Simple FixIt test',
      'chosen_fixit': 2,
      'request': {
        'command': 'FixIt',
        'line_num': 18,
        'column_num': 2,
        'filepath': filepath
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'fixits': has_item( has_entries( {
            'chunks': contains_exactly(
              ChunkMatcher( 'pub(crate) ',
                            LocationMatcher( filepath, 18, 1 ),
                            LocationMatcher( filepath, 18, 1 ) )
            )
          } ) )
        } )
      },
    } )


  @WithRetry()
  @IsolatedYcmd()
  def test_Subcommands_GoTo_WorksAfterChangingProject( self, app ):
    filepath = PathToTestFile( 'macro', 'src', 'main.rs' )
    StartRustCompleterServerInDirectory( app, filepath )

    for test, root in [
        (
          { 'req': ( 'main.rs', 31, 24 ), 'res': ( 'main.rs', 14, 9 ) },
          'macro'
        ),
        (
          { 'req': ( 'main.rs', 14, 19 ), 'res': ( 'test.rs', 4, 12 ) },
          'common'
        ),
    ]:
      with self.subTest( test = test, root = root ):
        RunGoToTest( app, 'GoTo', test, project_root = root )


  @SharedYcmd
  def test_Subcommands_OutgoingCallHierarchy( self, app ):
    filepath = PathToTestFile( 'common', 'src', 'hierarchies.rs' )
    for location, response, code in [
      [ ( filepath, 9, 4 ),
        contains_inanyorder(
          has_entries( {
            'locations': contains_exactly(
                           LocationMatcher( filepath, 10, 13 ) ),
            'kind': 'Function',
            'name': 'g'
          } ),
          has_entries( {
            'locations': contains_exactly(
                           LocationMatcher( filepath, 11, 5 ) ),
            'kind': 'Function',
            'name': 'f'
          } )
        ),
        requests.codes.ok ],
      [ ( filepath, 5, 4 ),
        contains_inanyorder(
          has_entry( 'locations',
                     contains_exactly(
                       LocationMatcher( filepath, 6, 5 ),
                       LocationMatcher( filepath, 6, 11 )
                     ) ) ),
        requests.codes.ok ],
      [ ( filepath, 1, 4 ),
        ErrorMatcher( RuntimeError, 'No outgoing calls found.' ),
        requests.codes.server_error ]
    ]:
      with self.subTest( location = location, response = response ):
        RunHierarchyTest( app, 'call', 'outgoing', location, response, code )


  @SharedYcmd
  def test_Subcommands_IncomingCallHierarchy( self, app ):
    filepath = PathToTestFile( 'common', 'src', 'hierarchies.rs' )
    for location, response, code in [
      [ ( filepath, 1, 4 ),
        contains_inanyorder(
          has_entries( {
            'locations': contains_exactly(
                           LocationMatcher( filepath, 6, 5 ),
                           LocationMatcher( filepath, 6, 11 ) ),
            'root_location': LocationMatcher( filepath, 5, 4 ),
            'name': 'g',
            'kind': 'Function'
          } ),
          has_entries( {
            'locations': contains_exactly(
                           LocationMatcher( filepath, 11, 5 ) ),
            'root_location': LocationMatcher( filepath, 9, 4 ),
            'name': 'h',
            'kind': 'Function'
          } )
        ),
        requests.codes.ok ],
      [ ( filepath, 5, 4 ),
        contains_inanyorder(
          has_entries( {
            'locations': contains_exactly(
                           LocationMatcher( filepath, 10, 13 ) ),
            'root_location': LocationMatcher( filepath, 9, 4 ),
            'name': 'h',
            'kind': 'Function'
          } )
        ),
        requests.codes.ok ],
      [ ( filepath, 9, 4 ),
        ErrorMatcher( RuntimeError, 'No incoming calls found.' ),
        requests.codes.server_error ]
    ]:
      with self.subTest( location = location, response = response ):
        RunHierarchyTest( app, 'call', 'incoming', location, response, code )


  @SharedYcmd
  def test_Subcommands_NoHierarchyFound( self, app ):
    filepath = PathToTestFile( 'common', 'src', 'hierarchies.rs' )
    request = {
      'completer_target' : 'filetype_default',
      'command': 'CallHierarchy',
      'line_num'         : 4,
      'column_num'       : 1,
      'filepath'         : filepath,
      'filetype'         : 'rust'
    }
    test = { 'request': request,
             'route': '/run_completer_command',
             'expect': {
               'response': requests.codes.server_error,
               'data': ErrorMatcher(
                   RuntimeError, 'No call hierarchy found.' ) } }
    RunTest( app, test )
