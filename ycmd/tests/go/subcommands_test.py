# Copyright (C) 2016-2018 ycmd contributors
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

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa

from hamcrest import assert_that, contains, has_entries, has_entry
from mock import patch
from nose.tools import eq_
from pprint import pformat
import requests

from ycmd.tests.go import IsolatedYcmd, PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import ( BuildRequest,
                                    CombineRequest,
                                    ErrorMatcher,
                                    MockProcessTerminationTimingOut,
                                    WaitUntilCompleterServerReady )
from ycmd.utils import ReadFile


@SharedYcmd
def Subcommands_DefinedSubcommands_test( app ):
  subcommands_data = BuildRequest( completer_target = 'go' )
  eq_( sorted( [ 'RestartServer',
                 'GoTo',
                 'GoToDefinition',
                 'GoToDeclaration' ] ),
       app.post_json( '/defined_subcommands',
                      subcommands_data ).json )


def RunTest( app, test ):
  contents = ReadFile( test[ 'request' ][ 'filepath' ] )

  # We ignore errors here and check the response code ourself.
  # This is to allow testing of requests returning errors.
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

  print( 'completer response: {0}'.format( pformat( response.json ) ) )

  eq_( response.status_code, test[ 'expect' ][ 'response' ] )

  assert_that( response.json, test[ 'expect' ][ 'data' ] )


@SharedYcmd
def Subcommands_GoTo_Basic( app, goto_command ):
  RunTest( app, {
    'description': goto_command + ' works within file',
    'request': {
      'command': goto_command,
      'line_num': 8,
      'column_num': 8,
      'filepath': PathToTestFile( 'goto.go' ),
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'filepath': PathToTestFile( 'goto.go' ),
        'line_num': 3,
        'column_num': 6,
      } )
    }
  } )


def Subcommands_GoTo_Basic_test():
  for command in [ 'GoTo', 'GoToDefinition', 'GoToDeclaration' ]:
    yield Subcommands_GoTo_Basic, command


@SharedYcmd
def Subcommands_GoTo_Keyword( app, goto_command ):
  RunTest( app, {
    'description': goto_command + ' can\'t jump on keyword',
    'request': {
      'command': goto_command,
      'line_num': 3,
      'column_num': 3,
      'filepath': PathToTestFile( 'goto.go' ),
    },
    'expect': {
      'response': requests.codes.internal_server_error,
      'data': ErrorMatcher( RuntimeError, 'Can\'t find a definition.' )
    }
  } )


def Subcommands_GoTo_Keyword_test():
  for command in [ 'GoTo', 'GoToDefinition', 'GoToDeclaration' ]:
    yield Subcommands_GoTo_Keyword, command


@SharedYcmd
def Subcommands_GoTo_WindowsNewlines( app, goto_command ):
  RunTest( app, {
    'description': goto_command + ' works with Windows newlines',
    'request': {
      'command': goto_command,
      'line_num': 4,
      'column_num': 7,
      'filepath': PathToTestFile( 'win.go' ),
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'filepath': PathToTestFile( 'win.go' ),
        'line_num': 2,
        'column_num': 6,
      } )
    }
  } )


def Subcommands_GoTo_WindowsNewlines_test():
  for command in [ 'GoTo', 'GoToDefinition', 'GoToDeclaration' ]:
    yield Subcommands_GoTo_WindowsNewlines, command


@IsolatedYcmd
@patch( 'ycmd.utils.WaitUntilProcessIsTerminated',
        MockProcessTerminationTimingOut )
def Subcommands_StopServer_Timeout_test( app ):
  WaitUntilCompleterServerReady( app, 'go' )

  app.post_json(
    '/run_completer_command',
    BuildRequest(
      filetype = 'go',
      command_arguments = [ 'StopServer' ]
    )
  )

  request_data = BuildRequest( filetype = 'go' )
  assert_that( app.post_json( '/debug_info', request_data ).json,
               has_entry(
                 'completer',
                 has_entry( 'servers', contains(
                   has_entry( 'is_running', False )
                 ) )
               ) )
