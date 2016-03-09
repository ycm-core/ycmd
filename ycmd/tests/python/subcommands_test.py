# Copyright (C) 2015 ycmd contributors
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
from future import standard_library
standard_library.install_aliases()
from builtins import *  # noqa

from hamcrest import assert_that, contains, contains_inanyorder, has_entries
from nose.tools import eq_
from pprint import pformat
import http.client

from ycmd.utils import ReadFile
from ycmd.tests.python import PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import ( BuildRequest, ChunkMatcher, ErrorMatcher,
                                    LocationMatcher )


def RunTest( app, test ):
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
                                 } ),
                 expect_errors = True )

  # We also ignore errors here, but then we check the response code
  # ourself. This is to allow testing of requests returning errors.
  response = app.post_json(
    '/run_completer_command',
    CombineRequest( test[ 'request' ], {
      'completer_target': 'filetype_default',
      'contents': contents,
      'filetype': 'python',
      'command_arguments': ( [ test[ 'request' ][ 'command' ] ]
                             + test[ 'request' ].get( 'arguments', [] ) )
    } ),
    expect_errors = True
  )

  print( 'completer response: {0}'.format( pformat( response.json ) ) )

  eq_( response.status_code, test[ 'expect' ][ 'response' ] )

  assert_that( response.json, test[ 'expect' ][ 'data' ] )


@SharedYcmd
def Subcommands_GoToDefinition_test( app ):
  # Example taken directly from jedi docs
  # http://jedi.jedidjah.ch/en/latest/docs/plugin-api.html#examples
  filepath = PathToTestFile( 'goto.py' )
  RunTest( app, {
    'description': 'GoToDefinition jumps to definition',
    'request': {
      'command': 'GoToDefinition',
      'line_num': 8,
      'filepath': filepath,
    },
    'expect': {
      'response': http.client.OK,
      'data': has_entries( {
        'filepath': filepath,
        'line_num': 1,
        'column_num': 5,
      } )
    }
  } )


@SharedYcmd
def Subcommands_GoToDeclaration_test( app ):
  # Example taken directly from jedi docs
  # http://jedi.jedidjah.ch/en/latest/docs/plugin-api.html#examples
  filepath = PathToTestFile( 'goto.py' )
  RunTest( app, {
    'description': 'GoToDeclaration jumps to assignment',
    'request': {
      'command': 'GoToDeclaration',
      'line_num': 8,
      'filepath': filepath,
    },
    'expect': {
      'response': http.client.OK,
      'data': has_entries( {
        'filepath': filepath,
        'line_num': 6,
        'column_num': 1,
      } )
    }
  } )


@SharedYcmd
def Subcommands_GoTo_DefinitionBeforeDeclaration_test( app ):
  RunTest( app, {
    'description': 'GoTo jumps to definition before declaration',
    'request': {
      'command': 'GoTo',
      'line_num': 2,
      'filepath': PathToTestFile( 'goto_file1.py' ),
    },
    'expect': {
      'response': http.client.OK,
      'data': has_entries( {
        'filepath': PathToTestFile( 'goto_file3.py' ),
        'line_num': 1,
        'column_num': 5,
      } )
    }
  } )


@SharedYcmd
def Subcommands_GoTo_FallbackToDeclaration_test( app ):
  filepath = PathToTestFile( 'goto_file4.py' )
  RunTest( app, {
    'description': 'GoTo jumps to declaration if definition is a builtin',
    'request': {
      'command': 'GoTo',
      'line_num': 2,
      'filepath': filepath,
    },
    'expect': {
      'response': http.client.OK,
      'data': has_entries( {
        'filepath': filepath,
        'line_num': 1,
        'column_num': 18,
      } )
    }
  } )


@SharedYcmd
def Subcommands_GoToDefinition_NotFound_test( app ):
  RunTest( app, {
    'description': 'GoToDefinition raises an error when no definition found',
    'request': {
      'command': 'GoToDefinition',
      'line_num': 4,
      'filepath': PathToTestFile( 'goto_file5.py' )
    },
    'expect': {
      'response': http.client.INTERNAL_SERVER_ERROR,
      'data': ErrorMatcher( RuntimeError, "Can\'t jump to definition." )
    }
  } )


@SharedYcmd
def Subcommands_GetDoc_Method_test( app ):
  RunTest( app, {
    'description': 'GetDoc works for method',
    'request': {
      'command': 'GetDoc',
      'line_num': 17,
      'column_num': 9,
      'filepath': PathToTestFile( 'GetDoc.py' ),
    },
    'expect': {
      'response': http.client.OK,
      'data': has_entries( {
        'detailed_info': '_ModuleMethod()\n\n'
                         'Module method docs\n'
                         'Are dedented, like you might expect',
      } )
    }
  } )


@SharedYcmd
def Subcommands_GetDoc_Class_test( app ):
  RunTest( app, {
    'description': 'GetDoc works for class',
    'request': {
      'command': 'GetDoc',
      'line_num': 19,
      'column_num': 2,
      'filepath': PathToTestFile( 'GetDoc.py' ),
    },
    'expect': {
      'response': http.client.OK,
      'data': has_entries( {
        'detailed_info': 'Class Documentation',
      } )
    }
  } )


@SharedYcmd
def Subcommands_GoToReferences_test( app ):
  filepath = PathToTestFile( 'goto_references.py' )
  RunTest( app, {
    'description': 'GoToReferences works within a single file',
    'request': {
      'command': 'GoToReferences',
      'filepath': filepath,
      'line_num': 4,
      'column_num': 5,
    },
    'expect': {
      'response': http.client.OK,
      'data': contains_inanyorder(
        {
          'filepath': filepath,
          'column_num': 5,
          'description': 'def f',
          'line_num': 1
        },
        {
          'filepath': filepath,
          'column_num': 5,
          'description': 'a = f()',
          'line_num': 4
        },
        {
          'filepath': filepath,
          'column_num': 5,
          'description': 'b = f()',
          'line_num': 5
        },
        {
          'filepath': filepath,
          'column_num': 5,
          'description': 'c = f()',
          'line_num': 6
        }
      )
    }
  } )


@SharedYcmd
def Subcommands_RefactorRename_MissingNewName_test( app ):
  filepath = PathToTestFile( 'refactor_rename1.py' )
  RunTest( app, {
    'description': 'RefactorRename raises an error without new name',
    'request': {
      'command': 'RefactorRename',
      'arguments': [],
      'filepath': filepath,
      'line_num': 7,
      'column_num': 14,
    },
    'expect': {
      'response': http.client.INTERNAL_SERVER_ERROR,
      'data': ErrorMatcher( ValueError,
                            'Please specify a new name to rename it to.\n'
                            'Usage: RefactorRename <new name>' ),
    }
  } )


@SharedYcmd
def Subcommands_RefactorRename_NotPossible_test( app ):
  filepath = PathToTestFile( 'refactor_rename1.py' )
  RunTest( app, {
    'description': 'RefactorRename raises an error '
                   'when there is no reference',
    'request': {
      'command': 'RefactorRename',
      'arguments': [ 'whatever' ],
      'filepath': filepath,
      'line_num': 1,
      'column_num': 17,
    },
    'expect': {
      'response': http.client.INTERNAL_SERVER_ERROR,
      'data': ErrorMatcher( RuntimeError, 'Can\'t find references.' ),
    }
  } )


@SharedYcmd
def Subcommands_RefactorRename_SingleFile_test( app ):
  filepath = PathToTestFile( 'refactor_rename1.py' )
  RunTest( app, {
    'description': 'RefactorRename works within a single file',
    'request': {
      'command': 'RefactorRename',
      'arguments': [ 'a_new_variable_name' ],
      'filepath': filepath,
      'line_num': 7,
      'column_num': 14,
    },
    'expect': {
      'response': http.client.OK,
      'data': has_entries( {
        'fixits': contains( has_entries( {
          'chunks': contains(
              ChunkMatcher( 'a_new_variable_name',
                            LocationMatcher( filepath, 1, 1 ),
                            LocationMatcher( filepath, 1, 14 ) ),
              ChunkMatcher( 'a_new_variable_name',
                            LocationMatcher( filepath, 5, 10 ),
                            LocationMatcher( filepath, 5, 23 ) ),
              ChunkMatcher( 'a_new_variable_name',
                            LocationMatcher( filepath, 7, 10 ),
                            LocationMatcher( filepath, 7, 23 ) ),
              # On the same line, ensuring offsets are as expected (as
              # unmodified source, similar to clang)
              ChunkMatcher( 'a_new_variable_name',
                            LocationMatcher( filepath, 7, 26 ),
                            LocationMatcher( filepath, 7, 39 ) ),
          ),
          'location': LocationMatcher( filepath, 7, 14 )
        } ) )
      } )
    }
  } )


@SharedYcmd
def Subcommands_RefactorRename_MultipleFiles_test( app ):
  current_filepath = PathToTestFile( 'refactor_rename1.py' )
  filepath2 = PathToTestFile( 'refactor_rename2.py' )
  filepath3 = PathToTestFile( 'refactor_rename3.py' )
  RunTest( app, {
    'description': 'RefactorRename works across files',
    'request': {
      'command': 'RefactorRename',
      'arguments': [ 'a_new_function_name' ],
      'filepath': current_filepath,
      'line_num': 4,
      'column_num': 5,
    },
    'expect': {
      'response': http.client.OK,
      'data': has_entries( {
        'fixits': contains( has_entries( {
          'chunks': contains(
            ChunkMatcher(
              'a_new_function_name',
              LocationMatcher( current_filepath, 4, 5 ),
              LocationMatcher( current_filepath, 4, 18 ) ),
            ChunkMatcher(
              'a_new_function_name',
              LocationMatcher( filepath2, 1, 30 ),
              LocationMatcher( filepath2, 1, 43 ) ),
            ChunkMatcher(
              'a_new_function_name',
              LocationMatcher( filepath2, 3, 1 ),
              LocationMatcher( filepath2, 3, 14 ) ),
            ChunkMatcher(
              'a_new_function_name',
              LocationMatcher( filepath3, 5, 20 ),
              LocationMatcher( filepath3, 5, 33 ) ),
          ),
          'location': LocationMatcher( current_filepath, 4, 5 )
        } ) )
      } )
    }
  } )
