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

from hamcrest import assert_that
from nose.tools import eq_
import os.path

from ycmd.utils import ReadFile
from ycmd.tests.python import PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import BuildRequest, ErrorMatcher


@SharedYcmd
def RunGoToTest( app, test ):
  filepath = PathToTestFile( test[ 'request' ][ 'filename' ] )
  goto_data = BuildRequest( completer_target = 'filetype_default',
                            command_arguments = [ 'GoTo' ],
                            line_num = test[ 'request' ][ 'line_num' ],
                            contents = ReadFile( filepath ),
                            filetype = 'python',
                            filepath = filepath )

  eq_( test[ 'response' ],
       app.post_json( '/run_completer_command', goto_data ).json )


def Subcommands_GoTo_test():
  # Tests taken from https://github.com/Valloric/YouCompleteMe/issues/1236
  tests = [
    {
      'request': { 'filename': 'goto_file1.py', 'line_num': 2 },
      'response': {
          'filepath': PathToTestFile( 'goto_file3.py' ),
          'line_num': 1,
          'column_num': 5
      }
    },
    {
      'request': { 'filename': 'goto_file4.py', 'line_num': 2 },
      'response': {
          'filepath': PathToTestFile( 'goto_file4.py' ),
          'line_num': 1,
          'column_num': 18
      }
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

  goto_data = BuildRequest(
      completer_target = 'filetype_default',
      command_arguments = test[ 'command_arguments' ],
      line_num = 9,
      contents = contents,
      filetype = 'python',
      filepath = '/foo.py'
  )

  eq_( test[ 'response' ],
       app.post_json( '/run_completer_command', goto_data ).json )


def Subcommands_GoTo_Variation_ZeroBasedLineAndColumn_test():
  tests = [
    {
      'command_arguments': [ 'GoToDefinition' ],
      'response': {
        'filepath': os.path.abspath( '/foo.py' ),
        'line_num': 2,
        'column_num': 5
      }
    },
    {
      'command_arguments': [ 'GoToDeclaration' ],
      'response': {
        'filepath': os.path.abspath( '/foo.py' ),
        'line_num': 7,
        'column_num': 1
      }
    }
  ]

  for test in tests:
    yield RunGoToTest_Variation_ZeroBasedLineAndColumn, test


@SharedYcmd
def Subcommands_GoToDefinition_NotFound_test( app ):
  filepath = PathToTestFile( 'goto_file5.py' )
  goto_data = BuildRequest( command_arguments = [ 'GoToDefinition' ],
                            line_num = 4,
                            contents = ReadFile( filepath ),
                            filetype = 'python',
                            filepath = filepath )

  response = app.post_json( '/run_completer_command',
                            goto_data,
                            expect_errors = True  ).json
  assert_that( response,
               ErrorMatcher( RuntimeError,
                             "Can\'t jump to definition." ) )


@SharedYcmd
def Subcommands_GetDoc_Method_test( app ):
  # Testcase1
  filepath = PathToTestFile( 'GetDoc.py' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'python',
                             line_num = 17,
                             column_num = 9,
                             contents = contents,
                             command_arguments = [ 'GetDoc' ],
                             completer_target = 'filetype_default' )

  response = app.post_json( '/run_completer_command', event_data ).json

  eq_( response, {
    'detailed_info': '_ModuleMethod()\n\n'
                     'Module method docs\n'
                     'Are dedented, like you might expect',
  } )


@SharedYcmd
def Subcommands_GetDoc_Class_test( app ):
  # Testcase1
  filepath = PathToTestFile( 'GetDoc.py' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'python',
                             line_num = 19,
                             column_num = 2,
                             contents = contents,
                             command_arguments = [ 'GetDoc' ],
                             completer_target = 'filetype_default' )

  response = app.post_json( '/run_completer_command', event_data ).json

  eq_( response, {
    'detailed_info': 'Class Documentation',
  } )


@SharedYcmd
def Subcommands_GoToReferences_test( app ):
  filepath = PathToTestFile( 'goto_references.py' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'python',
                             line_num = 4,
                             column_num = 5,
                             contents = contents,
                             command_arguments = [ 'GoToReferences' ],
                             completer_target = 'filetype_default' )

  response = app.post_json( '/run_completer_command', event_data ).json

  eq_( response, [
    {
      'filepath': PathToTestFile( 'goto_references.py' ),
      'column_num': 5,
      'description': 'def f',
      'line_num': 1
    },
    {
      'filepath': PathToTestFile( 'goto_references.py' ),
      'column_num': 5,
      'description': 'a = f()',
      'line_num': 4
    },
    {
      'filepath': PathToTestFile( 'goto_references.py' ),
      'column_num': 5,
      'description': 'b = f()',
      'line_num': 5
    },
    {
      'filepath': PathToTestFile( 'goto_references.py' ),
      'column_num': 5,
      'description': 'c = f()',
      'line_num': 6
    } ] )
