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
from ycmd.tests.go import setUpModule, tearDownModule # noqa
from ycmd.tests.go import ( PathToTestFile,
                            SharedYcmd,
                            IsolatedYcmd,
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
    test.get( 'route', '/run_completer_command' ),
    CombineRequest( test[ 'request' ], {
      'completer_target': 'filetype_default',
      'contents': contents,
      'filetype': 'go',
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


def RunFixItTest( app,
                  description,
                  filepath,
                  line,
                  col,
                  fixits_for_line,
                  chosen_fixit = None ):
  test = {
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
  }
  if chosen_fixit is not None:
    test_no_expect = test.copy()
    test_no_expect.pop( 'expect' )
    response = RunTest( app, test_no_expect )
    request = test[ 'request' ]
    request.update( {
      'fixit': response[ 'fixits' ][ chosen_fixit ]
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
    expect = {
      'response': requests.codes.internal_server_error,
      'data': ErrorMatcher( RuntimeError, response )
    }

  RunTest( app, {
    'request': request,
    'expect' : expect
  } )


class SubcommandsTest( TestCase ):
  @SharedYcmd
  def test_Subcommands_DefinedSubcommands( self, app ):
    subcommands_data = BuildRequest( completer_target = 'go' )

    assert_that( app.post_json( '/defined_subcommands', subcommands_data ).json,
                 contains_inanyorder( 'Format',
                                      'GetDoc',
                                      'GetType',
                                      'RefactorRename',
                                      'GoTo',
                                      'GoToCallers',
                                      'GoToCallees',
                                      'GoToDeclaration',
                                      'GoToDefinition',
                                      'GoToDocumentOutline',
                                      'GoToReferences',
                                      'GoToImplementation',
                                      'GoToType',
                                      'GoToSymbol',
                                      'FixIt',
                                      'CallHierarchy',
                                      'ResolveCallHierarchyItem',
                                      'RestartServer',
                                      'ExecuteCommand' ) )


  @SharedYcmd
  def test_Subcommands_ServerNotInitialized( self, app ):
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
    Test( app, 'CallHierarchy', [] )
    Test( app, 'GoToType', [] )
    Test( app, 'FixIt', [] )


  @SharedYcmd
  def test_Subcommands_Format_WholeFile( self, app ):
    filepath = PathToTestFile( 'goto.go' )

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
              ChunkMatcher( '\t',
                            LocationMatcher( filepath, 8, 1 ),
                            LocationMatcher( filepath, 8, 5 ) ),
              ChunkMatcher( '\t',
                            LocationMatcher( filepath, 12, 1 ),
                            LocationMatcher( filepath, 12, 5 ) ),
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
    filepath = PathToTestFile( 'goto.go' )

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
  def test_Subcommands_GetDoc_UnknownType( self, app ):
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
  def test_Subcommands_GetDoc_Function( self, app ):
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
  def test_Subcommands_GetType_UnknownType( self, app ):
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
  def test_Subcommands_GetType_Function( self, app ):
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


  @SharedYcmd
  def test_Subcommands_GoTo( self, app ):
    for command, test in itertools.product(
      [ 'GoTo', 'GoToDeclaration', 'GoToDefinition' ],
      [
        # Struct
        { 'req': ( os.path.join( 'unicode', 'unicode.go' ), 13, 5 ),
          'res': ( os.path.join( 'unicode', 'unicode.go' ), 10, 5 ) },
        # Function
        { 'req': ( 'goto.go', 8, 5 ), 'res': ( 'goto.go', 3, 6 ) },
        # Keyword
        { 'req': ( 'goto.go', 3, 2 ), 'res': 'Cannot jump to location' },
      ] ):
      with self.subTest( command = command, test = test ):
        RunGoToTest( app, command, test )


  @SharedYcmd
  def test_Subcommands_GoToType( self, app ):
    for test in [
      # Works
      { 'req': ( os.path.join( 'unicode', 'unicode.go' ), 13, 5 ),
        'res': ( os.path.join( 'unicode', 'unicode.go' ), 3, 6 ) },
      # Fails
      { 'req': ( os.path.join( 'unicode', 'unicode.go' ), 11, 7 ),
        'res': 'Cannot jump to location' } ]:
      with self.subTest( test = test ):
        RunGoToTest( app, 'GoToType', test )


  @SharedYcmd
  def test_Subcommands_GoToImplementation( self, app ):
    for test in [
      # Works
      { 'req': ( 'thing.go', 5, 8 ),
        'res': ( 'thing.go', 9, 6 ) },
      # Fails
      { 'req': ( 'thing.go', 10, 1 ),
        'res': 'Cannot jump to location' } ]:
      with self.subTest( test = test ):
        RunGoToTest( app, 'GoToImplementation', test )


  @ExpectedFailure(
    'Gopls bug. See https://github.com/golang/go/issues/68904',
    matches_regexp( 'Browse free symbols' ) )
  @SharedYcmd
  def test_Subcommands_FixIt_NullResponse( self, app ):
    filepath = PathToTestFile( 'td', 'test.go' )
    RunFixItTest( app,
                  'Gopls returned NULL for response[ \'result\' ]',
                  filepath, 1, 1, has_entry( 'fixits', empty() ) )


  @SharedYcmd
  def test_Subcommands_FixIt_Simple( self, app ):
    filepath = PathToTestFile( 'fixit.go' )
    fixit = has_entries( {
      'fixits': contains_exactly(
        has_entries( {
          'text': "Organize Imports",
          'chunks': contains_exactly(
            ChunkMatcher( '',
                          LocationMatcher( filepath, 2, 1 ),
                          LocationMatcher( filepath, 3, 1 ) ),
          ),
          'kind': 'source.organizeImports',
        } ),
      )
    } )
    RunFixItTest( app, 'Only one fixit returned', filepath, 1, 1, fixit, 0 )


  @SharedYcmd
  def test_Subcommands_RefactorRename( self, app ):
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
  def test_Subcommands_GoToReferences( self, app ):
    filepath = PathToTestFile( 'unicode', 'unicode.go' )
    test = { 'req': ( filepath, 10, 5 ), 'res': [ ( filepath, 10, 5 ),
                                                  ( filepath, 13, 5 ) ] }
    RunGoToTest( app, 'GoToReferences', test )


  @SharedYcmd
  def test_Subcommands_GoToCallees( self, app ):
    filepath = PathToTestFile( 'call_hierarchy.go' )
    for test in [
      { 'req': ( filepath, 4, 6 ),
        'res': [ ( filepath, 5, 2 ) ] },
      { 'req': ( filepath, 8, 6 ),
        'res': [ ( filepath, 9, 2 ), ] },
      { 'req': ( filepath, 11, 6 ),
        'res': [
          ( filepath, 12, 2 ),
          ( filepath, 13, 2 ) ] },
      { 'req': ( filepath, 15, 6 ),
        'res': [
          ( filepath, 16, 2 ),
          ( filepath, 17, 2 ),
          ( filepath, 18, 2 ) ] },
    ]:
      with self.subTest( test = test ):
        RunGoToTest( app, 'GoToCallees', test )


  @SharedYcmd
  def test_Subcommands_GoToCallers( self, app ):
    filepath = PathToTestFile( 'call_hierarchy.go' )
    for test in [
      { 'req': ( filepath, 3, 6 ),
        'res': [ ( filepath, 5, 2 ) ] },
      { 'req': ( filepath, 8, 6 ),
        'res': [
          ( filepath, 9, 2 ),
          ( filepath, 12, 2 ),
          ( filepath, 16, 2 ) ] },
      { 'req': ( filepath, 11, 6 ),
        'res': [
          ( filepath, 13, 2 ),
          ( filepath, 17, 2 ) ] },
      { 'req': ( filepath, 15, 6 ),
        'res': [ ( filepath, 18, 2 ) ] }
    ]:
      with self.subTest( test = test ):
        RunGoToTest( app, 'GoToCallers', test )


  @IsolatedYcmd()
  def test_Subcommands_GoTo_WorksAfterSwitchingProjects( self, app ):
    project_dir = PathToTestFile( module_dir = 'go_module_2' )
    StartGoCompleterServerInDirectory( app, project_dir )
    go_module_2_main = PathToTestFile( 'main.go', module_dir = 'go_module_2' )
    thing_go = PathToTestFile( 'thing.go' )
    td_test_go = PathToTestFile( 'td', 'test.go' )
    for test in [
      { 'req': ( go_module_2_main, 6, 3 ),
        'res': ( go_module_2_main, 3, 6 ) },
      { 'req': ( thing_go, 12, 8 ),
        'res': ( td_test_go, 9, 6 ) }
    ]:
      with self.subTest( test = test ):
        RunGoToTest( app, 'GoTo', test )


  @SharedYcmd
  def test_Subcommands_OutgoingCallHierarchy( self, app ):
    filepath = PathToTestFile( 'hierarchies.go' )
    for location, response, code in [
      [ ( filepath, 9, 6 ),
        contains_inanyorder(
          has_entries( {
            'locations': contains_exactly(
                           LocationMatcher( filepath, 10, 13 ) ),
            'kind': 'Function',
            'name': 'g'
          } ),
          has_entries( {
            'locations': contains_exactly(
                           LocationMatcher( filepath, 11, 12 ) ),
            'kind': 'Function',
            'name': 'f'
          } )
        ),
        requests.codes.ok ],
      [ ( filepath, 6, 6 ),
        contains_inanyorder(
          has_entries( {
            'locations': contains_exactly(
                           LocationMatcher( filepath, 7, 12 ),
                           LocationMatcher( filepath, 7, 18 ) ),
            'kind': 'Function',
            'name': 'f'
          } ),
        ),
        requests.codes.ok ],
      [ ( filepath, 3, 6 ),
        ErrorMatcher( RuntimeError, 'No outgoing calls found.' ),
        requests.codes.server_error ]
    ]:
      with self.subTest( location = location, response = response ):
        RunHierarchyTest( app, 'call', 'outgoing', location, response, code )


  @SharedYcmd
  def test_Subcommands_IncomingCallHierarchy( self, app ):
    filepath = PathToTestFile( 'hierarchies.go' )
    for location, response, code in [
      [ ( filepath, 3, 6 ),
        contains_inanyorder(
          has_entries( {
            'locations': contains_exactly(
                           LocationMatcher( filepath, 7, 12 ),
                           LocationMatcher( filepath, 7, 18 ) ),
            'root_location': LocationMatcher( filepath, 6, 6 ),
            'name': 'g',
            'kind': 'Function'
          } ),
          has_entries( {
            'locations': contains_exactly(
                           LocationMatcher( filepath, 11, 12 ) ),
            'root_location': LocationMatcher( filepath, 9, 6 ),
            'name': 'h',
            'kind': 'Function'
          } )
        ),
        requests.codes.ok ],
      [ ( filepath, 6, 6 ),
        contains_inanyorder(
          has_entries( {
            'locations': contains_exactly(
                           LocationMatcher( filepath, 10, 13 ) ),
            'root_location': LocationMatcher( filepath, 9, 6 ),
            'name': 'h',
            'kind': 'Function'
          } )
        ),
        requests.codes.ok ],
      [ ( filepath, 9, 6 ),
        ErrorMatcher( RuntimeError, 'No incoming calls found.' ),
        requests.codes.server_error ]
    ]:
      with self.subTest( location = location, response = response ):
        RunHierarchyTest( app, 'call', 'incoming', location, response, code )


  @SharedYcmd
  def test_Subcommands_NoHierarchyFound( self, app ):
    filepath = PathToTestFile( 'hierarchies.go' )
    request = {
      'completer_target' : 'filetype_default',
      'command': 'CallHierarchy',
      'line_num'         : 2,
      'column_num'       : 1,
      'filepath'         : filepath,
      'filetype'         : 'go'
    }
    test = { 'request': request,
             'route': '/run_completer_command',
             'expect': {
               'response': requests.codes.server_error,
               'data': ErrorMatcher(
                   RuntimeError, 'No call hierarchy found.' ) } }
    RunTest( app, test )
