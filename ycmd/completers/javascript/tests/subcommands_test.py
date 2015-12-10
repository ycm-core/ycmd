#
# Copyright (C) 2015 ycmd contributors
#
# This file is part of YouCompleteMe.
#
# YouCompleteMe is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# YouCompleteMe is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with YouCompleteMe.  If not, see <http://www.gnu.org/licenses/>.

from ycmd.server_utils import SetUpPythonPath
SetUpPythonPath()

import bottle, httplib, pprint

from webtest import TestApp
from nose.tools import ( eq_, with_setup )
from hamcrest import ( assert_that, has_entries )

from ycmd import handlers
from ycmd.tests.test_utils import ( BuildRequest, Setup )

from .test_utils import ( with_cwd,
                          TEST_DATA_DIR,
                          PathToTestFile,
                          WaitForTernServerReady  )

bottle.debug( True )

@with_setup( Setup )
@with_cwd( TEST_DATA_DIR )
def Subcommands_TernCompleter_Defined_Subcommands_test():
  app = TestApp( handlers.app )
  subcommands_data = BuildRequest( completer_target = 'javascript' )

  WaitForTernServerReady( app )

  eq_( sorted ( [ 'ConnectToServer',
                  'GoToDefinition',
                  'GoTo',
                  'GetDoc',
                  'GetType',
                  'StartServer',
                  'StopServer'] ),
        app.post_json( '/defined_subcommands', subcommands_data ).json )


def Subcommand_RunTest( test ):
  app = TestApp( handlers.app )
  WaitForTernServerReady( app )

  contents = open( test[ 'request' ][ 'filepath' ] ).read()

  def CombineRequest( request, data ):
    kw = request
    request.update( data )
    return BuildRequest( **kw )

  # Because we aren't testing this command, we *always* ignore errors. This is
  # mainly because we (may) want to test scenarios where the completer throws
  # an exception and the easiest way to do that is to throw from within the
  # FlagsForFile function.
  app.post_json( '/event_notification',
                 CombineRequest( test[ 'request' ], {
                                   'event_name': 'FileReadyToParse',
                                   'contents': contents,
                                 } ),
                 expect_errors = True )

  # We also ignore errors here, but then we check the response code ourself.
  # This is to allow testing of requests returning errors.
  response = app.post_json( '/run_completer_command',
                            CombineRequest( test[ 'request' ], {
                              'completer_target': 'filetype_default',
                              'contents': contents,
                              'filetype': 'javascript',
                              'command_arguments': (
                                [ test['request' ][ 'command' ] ]
                                + test[ 'request'].get( 'arguments', [] ) )
                            } ),
                            expect_errors = True )

  print 'completer response: ' + pprint.pformat( response.json )

  eq_( response.status_code, test[ 'expect' ][ 'response' ] )

  assert_that( response.json, test[ 'expect' ][ 'data' ] )

@with_setup( Setup )
@with_cwd( TEST_DATA_DIR )
def SubCommands_TernCompleter_GoToDefinition_test():
  Subcommand_RunTest( {
    'description': 'GoToDefinition works within file',
    'request': {
      'command': 'GoToDefinition',
      'line_num': 13,
      'column_num': 25,
      'filepath': PathToTestFile( 'simple_test.js' ),
    },
    'expect': {
      'response': httplib.OK,
      'data': has_entries( {
        'filepath': PathToTestFile( 'simple_test.js' ),
        'line_num': 1,
        'column_num': 5,
      } )
    }
  } )


@with_setup( Setup )
@with_cwd( TEST_DATA_DIR )
def SubCommands_TernCompleter_GoTo_test():
  pass


@with_setup( Setup )
@with_cwd( TEST_DATA_DIR )
def SubCommands_TernCompleter_GetDoc_test():
  pass


@with_setup( Setup )
@with_cwd( TEST_DATA_DIR )
def SubCommands_TernCompleter_GetType_test():
  pass

