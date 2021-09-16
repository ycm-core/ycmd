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
                       equal_to,
                       has_entry,
                       has_entries )
from unittest.mock import patch
from unittest import TestCase
from pprint import pformat
import requests

from ycmd.tests.tern import setUpModule, tearDownModule # noqa
from ycmd.tests.tern import ( IsolatedYcmd, PathToTestFile, SharedYcmd,
                              StartJavaScriptCompleterServerInDirectory )
from ycmd.tests.test_utils import ( BuildRequest,
                                    ChunkMatcher,
                                    CombineRequest,
                                    ErrorMatcher,
                                    LocationMatcher,
                                    MockProcessTerminationTimingOut )
from ycmd.utils import ReadFile


def RunTest( app, test, contents = None ):
  if not contents:
    contents = ReadFile( test[ 'request' ][ 'filepath' ] )

  # Because we aren't testing this command, we *always* ignore errors. This
  # is mainly because we (may) want to test scenarios where the completer
  # throws an exception and the easiest way to do that is to throw from
  # within the FlagsForFile function.
  app.post_json( '/event_notification',
                 CombineRequest( test[ 'request' ], {
                                 'event_name': 'FileReadyToParse',
                                 'contents': contents,
                                 'filetype': 'javascript',
                                 } ),
                 expect_errors = True )

  # We also ignore errors here, but then we check the response code
  # ourself. This is to allow testing of requests returning errors.
  response = app.post_json(
    '/run_completer_command',
    CombineRequest( test[ 'request' ], {
      'completer_target': 'filetype_default',
      'contents': contents,
      'filetype': 'javascript',
      'command_arguments': ( [ test[ 'request' ][ 'command' ] ]
                             + test[ 'request' ].get( 'arguments', [] ) )
    } ),
    expect_errors = True
  )

  print( f'completer response: { pformat( response.json ) }' )

  assert_that( response.status_code,
               equal_to( test[ 'expect' ][ 'response' ] ) )

  assert_that( response.json, test[ 'expect' ][ 'data' ] )


class SubcommandsTest( TestCase ):
  @SharedYcmd
  def test_Subcommands_DefinedSubcommands( self, app ):
    subcommands_data = BuildRequest( completer_target = 'javascript' )

    assert_that( app.post_json( '/defined_subcommands', subcommands_data ).json,
                 contains_inanyorder(
                   'GoToDefinition',
                   'GoTo',
                   'GetDoc',
                   'GetType',
                   'GoToReferences',
                   'RefactorRename',
                   'RestartServer' ) )


  @SharedYcmd
  def test_Subcommands_GoToDefinition( self, app ):
    RunTest( app, {
      'description': 'GoToDefinition works within file',
      'request': {
        'command': 'GoToDefinition',
        'line_num': 13,
        'column_num': 25,
        'filepath': PathToTestFile( 'simple_test.js' ),
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'filepath': PathToTestFile( 'simple_test.js' ),
          'line_num': 1,
          'column_num': 5,
        } )
      }
    } )


  @SharedYcmd
  def test_Subcommands_GoToDefinition_Unicode( self, app ):
    RunTest( app, {
      'description': 'GoToDefinition works within file with unicode',
      'request': {
        'command': 'GoToDefinition',
        'line_num': 11,
        'column_num': 12,
        'filepath': PathToTestFile( 'unicode.js' ),
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'filepath': PathToTestFile( 'unicode.js' ),
          'line_num': 6,
          'column_num': 26,
        } )
      }
    } )


  @SharedYcmd
  def test_Subcommands_GoTo( self, app ):
    RunTest( app, {
      'description': 'GoTo works the same as GoToDefinition within file',
      'request': {
        'command': 'GoTo',
        'line_num': 13,
        'column_num': 25,
        'filepath': PathToTestFile( 'simple_test.js' ),
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'filepath': PathToTestFile( 'simple_test.js' ),
          'line_num': 1,
          'column_num': 5,
        } )
      }
    } )


  @IsolatedYcmd()
  def test_Subcommands_GoTo_RelativePath( self, app ):
    StartJavaScriptCompleterServerInDirectory( app, PathToTestFile() )
    RunTest(
      app,
      {
        'description': 'GoTo works when the buffer differs '
                       'from the file on disk',
        'request': {
          'command': 'GoTo',
          'line_num': 43,
          'column_num': 25,
          'filepath': PathToTestFile( 'simple_test.js' ),
        },
        'expect': {
          'response': requests.codes.ok,
          'data': has_entries( {
            'filepath': PathToTestFile( 'simple_test.js' ),
            'line_num': 31,
            'column_num': 5,
          } )
        }
      },
      contents = ReadFile( PathToTestFile( 'simple_test.modified.js' ) ) )


  @SharedYcmd
  def test_Subcommands_GetDoc( self, app ):
    RunTest( app, {
      'description': 'GetDoc works within file',
      'request': {
        'command': 'GetDoc',
        'line_num': 7,
        'column_num': 16,
        'filepath': PathToTestFile( 'coollib', 'cool_object.js' ),
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'detailed_info': (
            'Name: mine_bitcoin\n'
            'Type: fn(how_much: ?) -> number\n\n'
            'This function takes a number and invests it in bitcoin. It '
            'returns\nthe expected value (in notional currency) after 1 year.'
          )
        } )
      }
    } )


  @SharedYcmd
  def test_Subcommands_GetType( self, app ):
    RunTest( app, {
      'description': 'GetType works within file',
      'request': {
        'command': 'GetType',
        'line_num': 11,
        'column_num': 14,
        'filepath': PathToTestFile( 'coollib', 'cool_object.js' ),
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'message': 'number'
        } )
      }
    } )


  @SharedYcmd
  def test_Subcommands_GoToReferences( self, app ):
    RunTest( app, {
      'description': 'GoToReferences works within file',
      'request': {
        'command': 'GoToReferences',
        'line_num': 17,
        'column_num': 29,
        'filepath': PathToTestFile( 'coollib', 'cool_object.js' ),
      },
      'expect': {
        'response': requests.codes.ok,
        'data': contains_inanyorder(
          has_entries( {
            'filepath': PathToTestFile( 'coollib', 'cool_object.js' ),
            'line_num': 17,
            'column_num': 29,
          } ),
          has_entries( {
            'filepath': PathToTestFile( 'coollib', 'cool_object.js' ),
            'line_num': 12,
            'column_num': 9,
          } )
        )
      }
    } )


  @SharedYcmd
  def test_Subcommands_GoToReferences_Unicode( self, app ):
    RunTest( app, {
      'description': 'GoToReferences works within file with unicode chars',
      'request': {
        'command': 'GoToReferences',
        'line_num': 11,
        'column_num': 5,
        'filepath': PathToTestFile( 'unicode.js' ),
      },
      'expect': {
        'response': requests.codes.ok,
        'data': contains_inanyorder(
          has_entries( {
            'filepath': PathToTestFile( 'unicode.js' ),
            'line_num': 5,
            'column_num': 5,
          } ),
          has_entries( {
            'filepath': PathToTestFile( 'unicode.js' ),
            'line_num': 9,
            'column_num': 1,
          } ),
          has_entries( {
            'filepath': PathToTestFile( 'unicode.js' ),
            'line_num': 11,
            'column_num': 1,
          } )
        )
      }
    } )


  @SharedYcmd
  def test_Subcommands_GetDocWithNoIdentifier( self, app ):
    RunTest( app, {
      'description': 'GetDoc works when no identifier',
      'request': {
        'command': 'GetDoc',
        'filepath': PathToTestFile( 'simple_test.js' ),
        'line_num': 12,
        'column_num': 1,
      },
      'expect': {
        'response': requests.codes.internal_server_error,
        'data': ErrorMatcher( RuntimeError, 'TernError: No type found '
                                            'at the given position.' ),
      }
    } )


  @SharedYcmd
  def test_Subcommands_RefactorRename_Simple( self, app ):
    filepath = PathToTestFile( 'simple_test.js' )
    RunTest( app, {
      'description': 'RefactorRename works within a single scope/file',
      'request': {
        'command': 'RefactorRename',
        'arguments': [ 'test' ],
        'filepath': filepath,
        'line_num': 15,
        'column_num': 32,
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'fixits': contains_exactly( has_entries( {
            'chunks': contains_exactly(
                ChunkMatcher( 'test',
                              LocationMatcher( filepath, 1, 5 ),
                              LocationMatcher( filepath, 1, 22 ) ),
                ChunkMatcher( 'test',
                              LocationMatcher( filepath, 13, 25 ),
                              LocationMatcher( filepath, 13, 42 ) ),
                ChunkMatcher( 'test',
                              LocationMatcher( filepath, 14, 24 ),
                              LocationMatcher( filepath, 14, 41 ) ),
                ChunkMatcher( 'test',
                              LocationMatcher( filepath, 15, 24 ),
                              LocationMatcher( filepath, 15, 41 ) ),
                ChunkMatcher( 'test',
                              LocationMatcher( filepath, 21, 7 ),
                              LocationMatcher( filepath, 21, 24 ) ),
                # On the same line, ensuring offsets are as expected (as
                # unmodified source, similar to clang)
                ChunkMatcher( 'test',
                              LocationMatcher( filepath, 21, 28 ),
                              LocationMatcher( filepath, 21, 45 ) ),
            ),
            'location': LocationMatcher( filepath, 15, 32 )
          } ) )
        } )
      }
    } )


  @SharedYcmd
  def test_Subcommands_RefactorRename_MultipleFiles( self, app ):
    file1 = PathToTestFile( 'file1.js' )
    file2 = PathToTestFile( 'file2.js' )
    file3 = PathToTestFile( 'file3.js' )

    RunTest( app, {
      'description': 'RefactorRename works across files',
      'request': {
        'command': 'RefactorRename',
        'arguments': [ 'a-quite-long-string' ],
        'filepath': file1,
        'line_num': 3,
        'column_num': 14,
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'fixits': contains_exactly( has_entries( {
            'chunks': contains_exactly(
              ChunkMatcher(
                'a-quite-long-string',
                LocationMatcher( file1, 1, 5 ),
                LocationMatcher( file1, 1, 11 ) ),
              ChunkMatcher(
                'a-quite-long-string',
                LocationMatcher( file1, 3, 14 ),
                LocationMatcher( file1, 3, 20 ) ),
              ChunkMatcher(
                'a-quite-long-string',
                LocationMatcher( file2, 2, 14 ),
                LocationMatcher( file2, 2, 20 ) ),
              ChunkMatcher(
                'a-quite-long-string',
                LocationMatcher( file3, 3, 12 ),
                LocationMatcher( file3, 3, 18 ) )
            ),
            'location': LocationMatcher( file1, 3, 14 )
          } ) )
        } )
      }
    } )


  # Needs to be isolated to prevent interfering with other tests (this test
  # loads an extra file into tern's project memory)
  @IsolatedYcmd()
  def test_Subcommands_RefactorRename_MultipleFiles_OnFileReadyToParse(
      self, app ):
    StartJavaScriptCompleterServerInDirectory( app, PathToTestFile() )

    file1 = PathToTestFile( 'file1.js' )
    file2 = PathToTestFile( 'file2.js' )
    file3 = PathToTestFile( 'file3.js' )

    # This test is roughly the same as the previous one, except here file4.js is
    # pushed into the Tern engine via 'opening it in the editor' (i.e.
    # FileReadyToParse event). The first 3 are loaded into the tern server
    # because they are listed in the .tern-project file's loadEagerly option.
    file4 = PathToTestFile( 'file4.js' )

    app.post_json( '/event_notification',
                   BuildRequest( **{
                     'filetype': 'javascript',
                     'event_name': 'FileReadyToParse',
                     'contents': ReadFile( file4 ),
                     'filepath': file4,
                   } ),
                   expect_errors = False )

    RunTest( app, {
      'description': 'FileReadyToParse loads files into tern server',
      'request': {
        'command': 'RefactorRename',
        'arguments': [ 'a-quite-long-string' ],
        'filepath': file1,
        'line_num': 3,
        'column_num': 14,
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'fixits': contains_exactly( has_entries( {
            'chunks': contains_exactly(
              ChunkMatcher(
                'a-quite-long-string',
                LocationMatcher( file1, 1, 5 ),
                LocationMatcher( file1, 1, 11 ) ),
              ChunkMatcher(
                'a-quite-long-string',
                LocationMatcher( file1, 3, 14 ),
                LocationMatcher( file1, 3, 20 ) ),
              ChunkMatcher(
                'a-quite-long-string',
                LocationMatcher( file2, 2, 14 ),
                LocationMatcher( file2, 2, 20 ) ),
              ChunkMatcher(
                'a-quite-long-string',
                LocationMatcher( file3, 3, 12 ),
                LocationMatcher( file3, 3, 18 ) ),
              ChunkMatcher(
                'a-quite-long-string',
                LocationMatcher( file4, 4, 22 ),
                LocationMatcher( file4, 4, 28 ) )
            ),
            'location': LocationMatcher( file1, 3, 14 )
          } ) )
        } )
      }
    } )


  @SharedYcmd
  def test_Subcommands_RefactorRename_Missing_New_Name( self, app ):
    RunTest( app, {
      'description': 'RefactorRename raises an error without new name',
      'request': {
        'command': 'RefactorRename',
        'line_num': 17,
        'column_num': 29,
        'filepath': PathToTestFile( 'coollib', 'cool_object.js' ),
      },
      'expect': {
        'response': requests.codes.internal_server_error,
        'data': ErrorMatcher( ValueError,
                              'Please specify a new name to rename it to.\n'
                              'Usage: RefactorRename <new name>' ),
      }
    } )


  @SharedYcmd
  def test_Subcommands_RefactorRename_Unicode( self, app ):
    filepath = PathToTestFile( 'unicode.js' )
    RunTest( app, {
      'description': 'RefactorRename works with unicode identifiers',
      'request': {
        'command': 'RefactorRename',
        'arguments': [ '†es†' ],
        'filepath': filepath,
        'line_num': 11,
        'column_num': 3,
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'fixits': contains_exactly( has_entries( {
            'chunks': contains_exactly(
                ChunkMatcher( '†es†',
                              LocationMatcher( filepath, 5, 5 ),
                              LocationMatcher( filepath, 5, 13 ) ),
                ChunkMatcher( '†es†',
                              LocationMatcher( filepath, 9, 1 ),
                              LocationMatcher( filepath, 9, 9 ) ),
                ChunkMatcher( '†es†',
                              LocationMatcher( filepath, 11, 1 ),
                              LocationMatcher( filepath, 11, 9 ) )
            ),
            'location': LocationMatcher( filepath, 11, 3 )
          } ) )
        } )
      }
    } )


  @IsolatedYcmd()
  @patch( 'ycmd.utils.WaitUntilProcessIsTerminated',
          MockProcessTerminationTimingOut )
  def test_Subcommands_StopServer_Timeout( self, app ):
    StartJavaScriptCompleterServerInDirectory( app, PathToTestFile() )

    app.post_json(
      '/run_completer_command',
      BuildRequest(
        filetype = 'javascript',
        command_arguments = [ 'StopServer' ]
      )
    )

    request_data = BuildRequest( filetype = 'javascript' )
    assert_that( app.post_json( '/debug_info', request_data ).json,
                 has_entry(
                   'completer',
                   has_entry( 'servers', contains_exactly(
                     has_entry( 'is_running', False )
                   ) )
                 ) )
