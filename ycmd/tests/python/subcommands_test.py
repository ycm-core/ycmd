# Copyright (C) 2015-2018 ycmd contributors
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
                       has_entries,
                       has_entry,
                       matches_regexp )
import os.path

from ycmd.utils import ReadFile
from ycmd.tests.python import PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import BuildRequest, LocationMatcher, ErrorMatcher


@SharedYcmd
def RunGoToTest( app, test ):
  filepath = PathToTestFile( test[ 'request' ][ 'filename' ] )
  command_data = BuildRequest( command_arguments = [ 'GoTo' ],
                               line_num = test[ 'request' ][ 'line_num' ],
                               contents = ReadFile( filepath ),
                               filetype = 'python',
                               filepath = filepath )

  assert_that(
    app.post_json( '/run_completer_command', command_data ).json,
    test[ 'response' ]
  )


def Subcommands_GoTo_test():
  # Tests taken from https://github.com/Valloric/YouCompleteMe/issues/1236
  tests = [
    {
      'request': { 'filename': 'goto_file1.py', 'line_num': 2 },
      'response': LocationMatcher( PathToTestFile( 'goto_file3.py' ), 1, 5 )
    },
    {
      'request': { 'filename': 'goto_file4.py', 'line_num': 2 },
      'response': LocationMatcher( PathToTestFile( 'goto_file4.py' ), 1, 18 )
    }
  ]

  for test in tests:
    yield RunGoToTest, test


@SharedYcmd
def RunGoToTest_Variation_ZeroBasedLineAndColumn( app, test ):
  # Example taken directly from jedi docs
  # http://jedi.jedidjah.ch/en/latest/docs/plugin-api.html#examples
  contents = """
def my_func():
  print 'called'

alias = my_func
my_list = [1, None, alias]
inception = my_list[2]

inception()
"""

  command_data = BuildRequest( command_arguments = test[ 'command_arguments' ],
                               line_num = 9,
                               contents = contents,
                               filetype = 'python',
                               filepath = '/foo.py' )

  assert_that(
    app.post_json( '/run_completer_command', command_data ).json,
    test[ 'response' ]
  )


def Subcommands_GoTo_Variation_ZeroBasedLineAndColumn_test():
  tests = [
    {
      'command_arguments': [ 'GoToDefinition' ],
      'response': LocationMatcher( os.path.abspath( '/foo.py' ), 2, 5 )
    },
    {
      'command_arguments': [ 'GoToDeclaration' ],
      'response': LocationMatcher( os.path.abspath( '/foo.py' ), 7, 1 )
    }
  ]

  for test in tests:
    yield RunGoToTest_Variation_ZeroBasedLineAndColumn, test


@SharedYcmd
def Subcommands_GoTo_CannotJump_test( app ):
  filepath = PathToTestFile( 'goto_file5.py' )
  command_data = BuildRequest( command_arguments = [ 'GoTo' ],
                               line_num = 3,
                               column_num = 1,
                               contents = ReadFile( filepath ),
                               filetype = 'python',
                               filepath = filepath )

  response = app.post_json( '/run_completer_command',
                            command_data,
                            expect_errors = True ).json
  assert_that( response,
               ErrorMatcher( RuntimeError,
                             "Can\'t jump to definition or declaration." ) )


@SharedYcmd
def Subcommands_GoToDefinition_Keyword_test( app ):
  filepath = PathToTestFile( 'goto_file5.py' )
  command_data = BuildRequest( command_arguments = [ 'GoToDefinition' ],
                               line_num = 2,
                               column_num = 4,
                               contents = ReadFile( filepath ),
                               filetype = 'python',
                               filepath = filepath )

  response = app.post_json( '/run_completer_command',
                            command_data,
                            expect_errors = True ).json
  assert_that( response,
               ErrorMatcher( RuntimeError, "Can\'t jump to definition." ) )


@SharedYcmd
def Subcommands_GoToDefinition_CannotJump_test( app ):
  filepath = PathToTestFile( 'goto_file5.py' )
  command_data = BuildRequest( command_arguments = [ 'GoToDefinition' ],
                               line_num = 4,
                               column_num = 2,
                               contents = ReadFile( filepath ),
                               filetype = 'python',
                               filepath = filepath )

  response = app.post_json( '/run_completer_command',
                            command_data,
                            expect_errors = True ).json
  assert_that( response,
               ErrorMatcher( RuntimeError, "Can\'t jump to definition." ) )


@SharedYcmd
def Subcommands_GoToDeclaration_CannotJump_test( app ):
  filepath = PathToTestFile( 'goto_file5.py' )
  command_data = BuildRequest( command_arguments = [ 'GoToDeclaration' ],
                               line_num = 2,
                               column_num = 5,
                               contents = ReadFile( filepath ),
                               filetype = 'python',
                               filepath = filepath )

  response = app.post_json( '/run_completer_command',
                            command_data,
                            expect_errors = True ).json
  assert_that( response,
               ErrorMatcher( RuntimeError, "Can\'t jump to declaration." ) )


@SharedYcmd
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


def Subcommands_GetType_test():
  tests = (
    ( ( 11,  7 ), 'instance int' ),
    ( ( 11, 20 ), 'def some_function()' ),
    ( ( 12, 15 ), 'class SomeClass(*args, **kwargs)' ),
    ( ( 13,  8 ), 'instance SomeClass' ),
    ( ( 13, 17 ), 'def SomeMethod(first_param, second_param)' ),
    ( ( 19,  4 ), matches_regexp( '^(instance str, instance int|'
                                  'instance int, instance str)$' ) )
  )
  for test in tests:
    yield Subcommands_GetType, test[ 0 ], test[ 1 ]


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
                               column_num = 2,
                               contents = contents,
                               command_arguments = [ 'GetDoc' ] )

  response = app.post_json( '/run_completer_command', command_data ).json

  assert_that( response, has_entry(
    'detailed_info', 'Class Documentation',
  ) )


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


@SharedYcmd
def Subcommands_GoToReferences_Function_test( app ):
  filepath = PathToTestFile( 'goto_references.py' )
  contents = ReadFile( filepath )

  command_data = BuildRequest( filepath = filepath,
                               filetype = 'python',
                               line_num = 4,
                               column_num = 5,
                               contents = contents,
                               command_arguments = [ 'GoToReferences' ] )

  assert_that(
    app.post_json( '/run_completer_command', command_data ).json,
    contains(
      has_entries( {
        'filepath': PathToTestFile( 'goto_references.py' ),
        'line_num': 1,
        'column_num': 5,
        'description': 'def f'
      } ),
      has_entries( {
        'filepath': PathToTestFile( 'goto_references.py' ),
        'line_num': 4,
        'column_num': 5,
        'description': 'f'
      } ),
      has_entries( {
        'filepath': PathToTestFile( 'goto_references.py' ),
        'line_num': 5,
        'column_num': 5,
        'description': 'f'
      } ),
      has_entries( {
        'filepath': PathToTestFile( 'goto_references.py' ),
        'line_num': 6,
        'column_num': 5,
        'description': 'f'
      } )
    )
  )


@SharedYcmd
def Subcommands_GoToReferences_Builtin_test( app ):
  filepath = PathToTestFile( 'goto_references.py' )
  contents = ReadFile( filepath )

  command_data = BuildRequest( filepath = filepath,
                               filetype = 'python',
                               line_num = 8,
                               column_num = 1,
                               contents = contents,
                               command_arguments = [ 'GoToReferences' ] )

  assert_that(
    app.post_json( '/run_completer_command', command_data ).json,
    contains(
      has_entries( {
        'description': 'Builtin class str',
      } ),
      has_entries( {
        'filepath': PathToTestFile( 'goto_references.py' ),
        'line_num': 8,
        'column_num': 1,
        'description': 'str'
      } )
    )
  )


@SharedYcmd
def Subcommands_GoToReferences_NoReferences_test( app ):
  filepath = PathToTestFile( 'goto_references.py' )
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
