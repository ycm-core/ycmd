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

from hamcrest import assert_that, contains, has_entry
from mock import patch
from nose.tools import eq_

from ycmd.tests.rust import IsolatedYcmd, PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import ( BuildRequest,
                                    MockProcessTerminationTimingOut,
                                    WaitUntilCompleterServerReady )
from ycmd.utils import ReadFile


@SharedYcmd
def RunGoToTest( app, params ):
  filepath = PathToTestFile( 'test.rs' )
  contents = ReadFile( filepath )

  command = params[ 'command' ]
  goto_data = BuildRequest( completer_target = 'filetype_default',
                            command_arguments = [ command ],
                            line_num = 7,
                            column_num = 12,
                            contents = contents,
                            filetype = 'rust',
                            filepath = filepath )

  results = app.post_json( '/run_completer_command',
                           goto_data )

  eq_( {
    'line_num': 1, 'column_num': 8, 'filepath': filepath
  }, results.json )


def Subcommands_GoTo_all_test():
  tests = [
    { 'command': 'GoTo' },
    { 'command': 'GoToDefinition' },
    { 'command': 'GoToDeclaration' }
  ]

  for test in tests:
    yield RunGoToTest, test


@SharedYcmd
def Subcommands_GetDoc_Method_test( app ):
  filepath = PathToTestFile( 'docs.rs' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'rust',
                             line_num = 7,
                             column_num = 9,
                             contents = contents,
                             command_arguments = [ 'GetDoc' ],
                             completer_target = 'filetype_default' )

  response = app.post_json( '/run_completer_command', event_data ).json

  eq_( response, {
    'detailed_info': 'pub fn fun()\n---\n'
                     'some docs on a function'
  } )


@SharedYcmd
def Subcommands_GetDoc_Fail_Method_test( app ):
  filepath = PathToTestFile( 'docs.rs' )
  contents = ReadFile( filepath )

  # no docs exist for this function
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'rust',
                             line_num = 8,
                             column_num = 9,
                             contents = contents,
                             command_arguments = [ 'GetDoc' ],
                             completer_target = 'filetype_default' )

  response = app.post_json(
          '/run_completer_command',
          event_data,
          expect_errors=True ).json

  eq_( response[ 'exception' ][ 'TYPE' ], 'RuntimeError' )
  eq_( response[ 'message' ], 'Can\'t lookup docs.' )


@IsolatedYcmd()
@patch( 'ycmd.utils.WaitUntilProcessIsTerminated',
        MockProcessTerminationTimingOut )
def Subcommands_StopServer_Timeout_test( app ):
  WaitUntilCompleterServerReady( app, 'rust' )

  app.post_json(
    '/run_completer_command',
    BuildRequest(
      filetype = 'rust',
      command_arguments = [ 'StopServer' ]
    )
  )

  request_data = BuildRequest( filetype = 'rust' )
  assert_that( app.post_json( '/debug_info', request_data ).json,
               has_entry(
                 'completer',
                 has_entry( 'servers', contains(
                   has_entry( 'is_running', False )
                 ) )
               ) )
