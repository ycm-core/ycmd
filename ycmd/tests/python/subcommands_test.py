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
                       equal_to,
                       has_item,
                       has_entries,
                       has_entry,
                       matches_regexp )
from pprint import pformat
from unittest.mock import patch
import os
import pytest
import requests

from ycmd.utils import ReadFile
from ycmd.tests.python import PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import ( BuildRequest,
                                    CombineRequest,
                                    ChunkMatcher,
                                    LocationMatcher,
                                    ErrorMatcher,
                                    ExpectedFailure )

TYPESHED_PATH = os.path.normpath(
  PathToTestFile( '..', '..', '..', '..', 'third_party', 'jedi_deps', 'jedi',
    'jedi', 'third_party', 'typeshed', 'stdlib', '2and3', 'builtins.pyi' ) )


class JediDef:
  def __init__( self, col = None, line = None, path = None ):
    self.column = col
    self.line = line
    self.module_path = path
    self.description = ''


def RunTest( app, test ):
  contents = ReadFile( test[ 'request' ][ 'filepath' ] )

  # We ignore errors here and check the response code ourself.
  # This is to allow testing of requests returning errors.
  response = app.post_json(
    '/run_completer_command',
    CombineRequest( test[ 'request' ], {
      'contents': contents,
      'filetype': 'python',
      'command_arguments': ( [ test[ 'request' ][ 'command' ] ]
                             + test[ 'request' ].get( 'arguments', [] ) )
    } ),
    expect_errors = True
  )

  print( f'completer response: { pformat( response.json ) }' )

  assert_that( response.status_code,
               equal_to( test[ 'expect' ][ 'response' ] ) )

  assert_that( response.json, test[ 'expect' ][ 'data' ] )


def Subcommands_GoTo( app, test, command ):
  if isinstance( test[ 'response' ], list ):
    expect = {
      'response': requests.codes.ok,
      'data': contains_inanyorder( *[
        LocationMatcher( PathToTestFile( 'goto', r[ 0 ] ), r[ 1 ], r[ 2 ] )
          for r in test[ 'response' ]
      ] )
    }
  elif isinstance( test[ 'response' ], tuple ):
    expect = {
      'response': requests.codes.ok,
      'data': LocationMatcher( PathToTestFile( 'goto',
                                               test[ 'response' ][ 0 ] ),
                               test[ 'response' ][ 1 ],
                               test[ 'response' ][ 2 ] )
    }
  else:
    expect = {
      'response': requests.codes.internal_server_error,
      'data': ErrorMatcher( RuntimeError, test[ 'response' ] )
    }

  req = test[ 'request' ]
  RunTest( app, {
    'description': command + ' jumps to the right location',
    'request': {
      'command'   : command,
      'arguments': [] if len( req ) < 4 else req[ 3 ],
      'filetype'  : 'python',
      'filepath'  : PathToTestFile( 'goto', req[ 0 ] ),
      'line_num'  : req[ 1 ],
      'column_num': req[ 2 ]
    },
    'expect': expect,
  } )


@pytest.mark.parametrize( 'cmd', [ 'GoTo',
                                   'GoToDefinition',
                                   'GoToDeclaration' ] )
@pytest.mark.parametrize( 'test', [
    # Nothing
    { 'request': ( 'basic.py', 3,  5 ), 'response': 'Can\'t jump to '
                                                    'definition.' },
    # Keyword
    { 'request': ( 'basic.py', 4,  3 ), 'response': 'Can\'t jump to '
                                                    'definition.' },
    # Builtin
    { 'request': ( 'basic.py', 1,  4 ), 'response': ( 'basic.py', 1, 1 ) },
    { 'request': ( 'basic.py', 1, 12 ), 'response': ( TYPESHED_PATH, 947, 7 ) },
    { 'request': ( 'basic.py', 2,  2 ), 'response': ( 'basic.py', 1, 1 ) },
    # Class
    { 'request': ( 'basic.py', 4,  7 ), 'response': ( 'basic.py', 4, 7 ) },
    { 'request': ( 'basic.py', 4, 11 ), 'response': ( 'basic.py', 4, 7 ) },
    { 'request': ( 'basic.py', 7, 19 ), 'response': ( 'basic.py', 4, 7 ) },
    # Instance
    { 'request': ( 'basic.py', 7,  1 ), 'response': ( 'basic.py', 7, 1 ) },
    { 'request': ( 'basic.py', 7, 11 ), 'response': ( 'basic.py', 7, 1 ) },
    { 'request': ( 'basic.py', 8, 23 ), 'response': ( 'basic.py', 7, 1 ) },
    # Instance reference
    { 'request': ( 'basic.py', 8,  1 ), 'response': ( 'basic.py', 8, 1 ) },
    { 'request': ( 'basic.py', 8,  5 ), 'response': ( 'basic.py', 8, 1 ) },
    { 'request': ( 'basic.py', 9, 12 ), 'response': ( 'basic.py', 8, 1 ) },
    # Member access
    { 'request':  ( 'child.py', 4, 12 ),
      'response': ( 'parent.py', 2, 7 ) },
    # Builtin from different file
    { 'request':  ( 'multifile1.py', 2, 30 ),
      'response': ( 'multifile2.py', 1, 24 ) },
    { 'request':  ( 'multifile1.py', 4,  5 ),
      'response': ( 'multifile1.py', 2, 24 ) },
    # Function from different file
    { 'request':  ( 'multifile1.py', 1, 24 ),
      'response': ( 'multifile3.py', 3,  5 ) },
    { 'request':  ( 'multifile1.py', 5,  4 ),
      'response': ( 'multifile1.py', 1, 24 ) },
    # Alias from different file
    { 'request':  ( 'multifile1.py', 2, 47 ),
      'response': ( 'multifile2.py', 1, 51 ) },
    { 'request':  ( 'multifile1.py', 6, 14 ),
      'response': ( 'multifile1.py', 2, 36 ) },
    # Absolute import from nested module
    { 'request':  ( os.path.join( 'nested_import', 'importer.py' ), 1, 19 ),
      'response': ( 'basic.py', 4, 7 ) },
    { 'request':  ( os.path.join( 'nested_import', 'importer.py' ), 2, 40 ),
      'response': ( os.path.join( 'nested_import', 'to_import.py' ), 1, 5 ) },
    # Relative within nested module
    { 'request':  ( os.path.join( 'nested_import', 'importer.py' ), 3, 28 ),
      'response': ( os.path.join( 'nested_import', 'to_import.py' ), 4, 5 ) },
  ] )
@SharedYcmd
def Subcommands_GoTo_test( app, cmd, test ):
  Subcommands_GoTo( app, test, cmd )


@pytest.mark.parametrize( 'test', [
  { 'request': ( 'basic.py', 1, 1, [ 'MyClass' ] ),
    'response': ( 'basic.py', 4, 7 ) },

  { 'request': ( 'basic.py', 1, 1, [ 'class C' ] ),
    'response': ( 'child.py', 2, 7 ) },

  { 'request': ( 'basic.py', 1, 1, [ 'C.c' ] ),
    'response': [ ( 'child.py', 3, 7 ), ( 'parent.py', 3, 7 ) ] },

  { 'request': ( 'basic.py', 1, 1, [ 'nothing_here_mate' ] ),
    'response': 'Symbol not found' }
] )
@SharedYcmd
def Subcommands_GoToSymbol_test( app, test ):
  Subcommands_GoTo( app, test, 'GoToSymbol' )


@pytest.mark.parametrize( 'test', [
  { 'request': ( 'basic.py', 1, 4 ),
    'response': 'Can\'t jump to definition.', 'cmd': 'GoTo' },
  { 'request': ( 'basic.py', 1, 4 ),
    'response': 'Can\'t find references.', 'cmd': 'GoToReferences' },
  { 'request': ( 'basic.py', 1, 4 ),
    'response': 'Can\'t jump to type definition.', 'cmd': 'GoToType' }
] )
@SharedYcmd
def Subcommands_GoTo_SingleInvalidJediDefinition_test( app, test ):
  with patch( 'ycmd.completers.python.python_completer.jedi.Script.infer',
              return_value = [ JediDef() ] ):
    with patch( 'ycmd.completers.python.python_completer.jedi.Script.goto',
                return_value = [ JediDef() ] ):
      with patch( 'ycmd.completers.python.python_completer.'
                  'jedi.Script.get_references',
                  return_value = [ JediDef() ] ):
        Subcommands_GoTo( app, test, test.pop( 'cmd' ) )


def Subcommands_GetType( app, position, expected_message ):
  filepath = PathToTestFile( 'GetType.py' )
  contents = ReadFile( filepath )

  command_data = BuildRequest( filepath = filepath,
                               filetype = 'python',
                               line_num = position[ 0 ],
                               column_num = position[ 1 ],
                               contents = contents,
                               command_arguments = [ 'GetType' ] )

  assert_that(
    app.post_json( '/run_completer_command', command_data ).json,
    has_entry( 'message', expected_message )
  )


@pytest.mark.parametrize( 'position,expected_message',  [
    ( ( 11,  7 ), 'instance int' ),
    ( ( 11, 20 ), 'def some_function()' ),
    ( ( 12, 15 ), 'class SomeClass(*args, **kwargs)' ),
    ( ( 13,  8 ), 'instance SomeClass' ),
    ( ( 13, 17 ), 'def SomeMethod(first_param, second_param)' ),
    ( ( 19,  4 ), matches_regexp( '^(instance str, instance int|'
                                  'instance int, instance str)$' ) )
  ] )
@SharedYcmd
def Subcommands_GetType_test( app, position, expected_message ):
  Subcommands_GetType( app, position, expected_message )


@SharedYcmd
def Subcommands_GetType_NoTypeInformation_test( app ):
  filepath = PathToTestFile( 'GetType.py' )
  contents = ReadFile( filepath )

  command_data = BuildRequest( filepath = filepath,
                               filetype = 'python',
                               line_num = 6,
                               column_num = 3,
                               contents = contents,
                               command_arguments = [ 'GetType' ] )

  response = app.post_json( '/run_completer_command',
                            command_data,
                            expect_errors = True ).json

  assert_that( response,
               ErrorMatcher( RuntimeError, 'No type information available.' ) )


@SharedYcmd
def Subcommands_GetDoc_Method_test( app ):
  # Testcase1
  filepath = PathToTestFile( 'GetDoc.py' )
  contents = ReadFile( filepath )

  command_data = BuildRequest( filepath = filepath,
                               filetype = 'python',
                               line_num = 17,
                               column_num = 9,
                               contents = contents,
                               command_arguments = [ 'GetDoc' ] )

  assert_that(
    app.post_json( '/run_completer_command', command_data ).json,
    has_entry( 'detailed_info', '_ModuleMethod()\n\n'
                                'Module method docs\n'
                                'Are dedented, like you might expect' )
  )


@SharedYcmd
def Subcommands_GetDoc_Class_test( app ):
  filepath = PathToTestFile( 'GetDoc.py' )
  contents = ReadFile( filepath )

  command_data = BuildRequest( filepath = filepath,
                               filetype = 'python',
                               line_num = 19,
                               column_num = 6,
                               contents = contents,
                               command_arguments = [ 'GetDoc' ] )

  response = app.post_json( '/run_completer_command', command_data ).json

  assert_that( response, has_entry(
    'detailed_info', 'TestClass()\n\nClass Documentation',
  ) )


@SharedYcmd
def Subcommands_GetDoc_WhitespaceOnly_test( app ):
  filepath = PathToTestFile( 'GetDoc.py' )
  contents = ReadFile( filepath )

  command_data = BuildRequest( filepath = filepath,
                               filetype = 'python',
                               line_num = 27,
                               column_num = 10,
                               contents = contents,
                               command_arguments = [ 'GetDoc' ] )

  response = app.post_json( '/run_completer_command',
                            command_data,
                            expect_errors = True ).json

  assert_that( response,
               ErrorMatcher( RuntimeError, 'No documentation available.' ) )



@SharedYcmd
def Subcommands_GetDoc_NoDocumentation_test( app ):
  filepath = PathToTestFile( 'GetDoc.py' )
  contents = ReadFile( filepath )

  command_data = BuildRequest( filepath = filepath,
                               filetype = 'python',
                               line_num = 8,
                               column_num = 23,
                               contents = contents,
                               command_arguments = [ 'GetDoc' ] )

  response = app.post_json( '/run_completer_command',
                            command_data,
                            expect_errors = True ).json

  assert_that( response,
               ErrorMatcher( RuntimeError, 'No documentation available.' ) )


@pytest.mark.parametrize( 'test', [
    { 'request':  ( 'basic.py', 2, 1 ), 'response': ( TYPESHED_PATH, 947, 7 ) },
    { 'request':  ( 'basic.py', 8, 1 ), 'response': ( 'basic.py', 4, 7 ) },
    { 'request':  ( 'basic.py', 3, 1 ),
      'response': 'Can\'t jump to type definition.' },
  ] )
@SharedYcmd
def Subcommands_GoToType_test( app, test ):
  Subcommands_GoTo( app, test, 'GoToType' )


@SharedYcmd
def Subcommands_GoToReferences_Function_test( app ):
  filepath = PathToTestFile( 'goto', 'references.py' )
  contents = ReadFile( filepath )

  command_data = BuildRequest( filepath = filepath,
                               filetype = 'python',
                               line_num = 4,
                               column_num = 5,
                               contents = contents,
                               command_arguments = [ 'GoToReferences' ] )

  assert_that(
    app.post_json( '/run_completer_command', command_data ).json,
    contains_exactly(
      has_entries( {
        'filepath': filepath,
        'line_num': 1,
        'column_num': 5,
        'description': 'def f'
      } ),
      has_entries( {
        'filepath': filepath,
        'line_num': 4,
        'column_num': 5,
        'description': 'f'
      } ),
      has_entries( {
        'filepath': filepath,
        'line_num': 5,
        'column_num': 5,
        'description': 'f'
      } ),
      has_entries( {
        'filepath': filepath,
        'line_num': 6,
        'column_num': 5,
        'description': 'f'
      } )
    )
  )


@SharedYcmd
def Subcommands_GoToReferences_Builtin_test( app ):
  filepath = PathToTestFile( 'goto', 'references.py' )
  contents = ReadFile( filepath )

  command_data = BuildRequest( filepath = filepath,
                               filetype = 'python',
                               line_num = 8,
                               column_num = 1,
                               contents = contents,
                               command_arguments = [ 'GoToReferences' ] )

  assert_that(
    app.post_json( '/run_completer_command', command_data ).json,
    has_item(
      has_entries( {
        'filepath': filepath,
        'line_num': 8,
        'column_num': 1,
        'description': 'str'
      } )
    )
  )


@SharedYcmd
def Subcommands_GoToReferences_NoReferences_test( app ):
  filepath = PathToTestFile( 'goto', 'references.py' )
  contents = ReadFile( filepath )

  command_data = BuildRequest( filepath = filepath,
                               filetype = 'python',
                               line_num = 2,
                               column_num = 5,
                               contents = contents,
                               command_arguments = [ 'GoToReferences' ] )

  response = app.post_json( '/run_completer_command',
                            command_data,
                            expect_errors = True ).json

  assert_that( response,
               ErrorMatcher( RuntimeError, 'Can\'t find references.' ) )


@SharedYcmd
def Subcommands_GoToReferences_InvalidJediReferences_test( app ):
  with patch( 'ycmd.completers.python.python_completer.'
              'jedi.Script.get_references',
              return_value = [ JediDef(),
                               JediDef( 1, 1, PathToTestFile( 'foo.py' ) ) ] ):

    filepath = PathToTestFile( 'goto', 'references.py' )
    contents = ReadFile( filepath )

    command_data = BuildRequest( filepath = filepath,
                                 filetype = 'python',
                                 line_num = 2,
                                 column_num = 5,
                                 contents = contents,
                                 command_arguments = [ 'GoToReferences' ] )

    response = app.post_json( '/run_completer_command',
                              command_data,
                              expect_errors = True ).json

    assert_that( response, contains_exactly( has_entries( {
      'line_num': 1,
      'column_num': 2, # Jedi columns are 0 based
      'filepath': PathToTestFile( 'foo.py' ) } ) ) )



@SharedYcmd
def Subcommands_RefactorRename_NoNewName_test( app ):
  filepath = PathToTestFile( 'basic.py' )
  contents = ReadFile( filepath )
  command_data = BuildRequest( filepath = filepath,
                               filetype = 'python',
                               line_num = 3,
                               column_num = 10,
                               contents = contents,
                               command_arguments = [ 'RefactorRename' ] )

  response = app.post_json( '/run_completer_command',
                            command_data,
                            expect_errors = True )

  assert_that( response.status_code,
               equal_to( requests.codes.internal_server_error ) )
  assert_that( response.json,
               ErrorMatcher( RuntimeError, 'Must specify a new name' ) )


@SharedYcmd
def Subcommands_RefactorRename_Same_test( app ):
  filepath = PathToTestFile( 'basic.py' )
  contents = ReadFile( filepath )

  command_data = BuildRequest( filepath = filepath,
                               filetype = 'python',
                               line_num = 3,
                               column_num = 10,
                               contents = contents,
                               command_arguments = [ 'RefactorRename',
                                                     'c' ] )

  response = app.post_json( '/run_completer_command',
                            command_data ).json

  assert_that( response, has_entries( {
    'fixits': contains_exactly(
      has_entries( {
        'text': '',
        'chunks': contains_exactly(
          ChunkMatcher( 'c',
                        LocationMatcher( filepath, 3, 10 ),
                        LocationMatcher( filepath, 3, 11 ) ),
          ChunkMatcher( 'c',
                        LocationMatcher( filepath, 7, 3 ),
                        LocationMatcher( filepath, 7, 4 ) )
        )
      } )
    )
  } ) )


@SharedYcmd
def Subcommands_RefactorRename_Longer_test( app ):
  filepath = PathToTestFile( 'basic.py' )
  contents = ReadFile( filepath )

  command_data = BuildRequest( filepath = filepath,
                               filetype = 'python',
                               line_num = 3,
                               column_num = 10,
                               contents = contents,
                               command_arguments = [ 'RefactorRename',
                                                     'booo' ] )

  response = app.post_json( '/run_completer_command',
                            command_data ).json

  assert_that( response, has_entries( {
    'fixits': contains_exactly(
      has_entries( {
        'text': '',
        'chunks': contains_exactly(
          ChunkMatcher( 'booo',
                        LocationMatcher( filepath, 3, 10 ),
                        LocationMatcher( filepath, 3, 11 ) ),
          ChunkMatcher( 'booo',
                        LocationMatcher( filepath, 7, 3 ),
                        LocationMatcher( filepath, 7, 4 ) )
        )
      } )
    )
  } ) )


@SharedYcmd
def Subcommands_RefactorRename_ShortenDelete_test( app ):
  filepath = PathToTestFile( 'basic.py' )
  contents = ReadFile( filepath )

  command_data = BuildRequest( filepath = filepath,
                               filetype = 'python',
                               line_num = 1,
                               column_num = 8,
                               contents = contents,
                               command_arguments = [ 'RefactorRename',
                                                     'F' ] )

  response = app.post_json( '/run_completer_command',
                            command_data ).json

  assert_that( response, has_entries( {
    'fixits': contains_exactly(
      has_entries( {
        'text': '',
        'chunks': contains_exactly(
          ChunkMatcher( '',
                        LocationMatcher( filepath, 1, 8 ),
                        LocationMatcher( filepath, 1, 10 ) ),
          ChunkMatcher( '',
                        LocationMatcher( filepath, 6, 6 ),
                        LocationMatcher( filepath, 6, 8 ) )
        )
      } )
    )
  } ) )


@SharedYcmd
def Subcommands_RefactorRename_Shorten_test( app ):
  filepath = PathToTestFile( 'basic.py' )
  contents = ReadFile( filepath )

  command_data = BuildRequest( filepath = filepath,
                               filetype = 'python',
                               line_num = 1,
                               column_num = 8,
                               contents = contents,
                               command_arguments = [ 'RefactorRename',
                                                     'G' ] )

  response = app.post_json( '/run_completer_command',
                            command_data ).json

  assert_that( response, has_entries( {
    'fixits': contains_exactly(
      has_entries( {
        'text': '',
        'chunks': contains_exactly(
          ChunkMatcher( 'G',
                        LocationMatcher( filepath, 1, 7 ),
                        LocationMatcher( filepath, 1, 10 ) ),
          ChunkMatcher( 'G',
                        LocationMatcher( filepath, 6, 5 ),
                        LocationMatcher( filepath, 6, 8 ) )
        )
      } )
    )
  } ) )


@SharedYcmd
def Subcommands_RefactorRename_StartOfFile_test( app ):
  one = PathToTestFile( 'rename', 'one.py' )
  contents = ReadFile( one )

  command_data = BuildRequest( filepath = one,
                               filetype = 'python',
                               line_num = 8,
                               column_num = 44,
                               contents = contents,
                               command_arguments = [ 'RefactorRename',
                                                     'myvariable' ] )

  response = app.post_json( '/run_completer_command',
                            command_data ).json

  assert_that( response, has_entries( {
    'fixits': contains_exactly(
      has_entries( {
        'text': '',
        'chunks': contains_exactly(
          ChunkMatcher( 'myvariable',
                        LocationMatcher( one, 1, 1 ),
                        LocationMatcher( one, 1, 13 ) ),
          ChunkMatcher( 'myvariable',
                        LocationMatcher( one, 8, 33 ),
                        LocationMatcher( one, 8, 45 ) ),
          ChunkMatcher( 'myvariable',
                        LocationMatcher( one, 16, 32 ),
                        LocationMatcher( one, 16, 44 ) )
        )
      } )
    )
  } ) )


@SharedYcmd
def Subcommands_RefactorRename_MultiFIle_test( app ):
  one = PathToTestFile( 'rename', 'one.py' )
  two = PathToTestFile( 'rename', 'two.py' )
  contents = ReadFile( one )

  command_data = BuildRequest( filepath = one,
                               filetype = 'python',
                               line_num = 4,
                               column_num = 7,
                               contents = contents,
                               command_arguments = [ 'RefactorRename',
                                                     'OneLove' ] )

  response = app.post_json( '/run_completer_command',
                            command_data ).json

  assert_that( response, has_entries( {
    'fixits': contains_exactly(
      has_entries( {
        'text': '',
        'chunks': contains_exactly(
          ChunkMatcher( 'eLov',
                        LocationMatcher( one, 4, 9 ),
                        LocationMatcher( one, 4, 9 ) ),
          ChunkMatcher( 'eLov',
                        LocationMatcher( one, 9, 24 ),
                        LocationMatcher( one, 9, 24 ) ),
          ChunkMatcher( 'Love',
                        LocationMatcher( one, 16, 15 ),
                        LocationMatcher( one, 16, 15 ) ),
          ChunkMatcher( 'eLov',
                        LocationMatcher( two, 4, 18 ),
                        LocationMatcher( two, 4, 18 ) ),
          ChunkMatcher( 'Love',
                        LocationMatcher( two, 11, 14 ),
                        LocationMatcher( two, 11, 14 ) )
        )
      } )
    )
  } ) )


@ExpectedFailure( 'file renames not implemented yet' )
@SharedYcmd
def Subcommands_RefactorRename_Module_test( app ):
  one = PathToTestFile( 'rename', 'one.py' )
  two = PathToTestFile( 'rename', 'two.py' )
  contents = ReadFile( two )

  command_data = BuildRequest( filepath = two,
                               filetype = 'python',
                               line_num = 1,
                               column_num = 8,
                               contents = contents,
                               command_arguments = [ 'RefactorRename',
                                                     'pfivr' ] )

  response = app.post_json( '/run_completer_command',
                            command_data ).json

  assert_that( response, has_entries( {
    'fixits': contains_exactly(
      has_entries( {
        'text': '',
        'chunks': contains_exactly(
          ChunkMatcher( 'pfivr',
                        LocationMatcher( two, 1, 8 ),
                        LocationMatcher( two, 1, 11 ) ),
          ChunkMatcher( 'pfivr',
                        LocationMatcher( two, 4, 12 ),
                        LocationMatcher( two, 4, 15 ) )
        ),
        'files': contains_exactly(
          has_entries( {
            'operation': 'RENAME',
            'old_file': one,
            'new_file': PathToTestFile( 'rename', 'pfivr.py' )
          } )
        )
      } )
    )
  } ) )


def Dummy_test():
  # Workaround for https://github.com/pytest-dev/pytest-rerunfailures/issues/51
  assert True
