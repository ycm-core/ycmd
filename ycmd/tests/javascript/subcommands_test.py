#
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

from ycmd.server_utils import SetUpPythonPath
SetUpPythonPath()

import bottle, httplib, pprint

from webtest import TestApp
from nose.tools import ( eq_, with_setup )
from hamcrest import ( assert_that, contains_inanyorder, has_entries )

from ycmd import handlers
from ycmd.tests.test_utils import ( BuildRequest, ErrorMatcher, Setup )

from .test_utils import ( TEST_DATA_DIR,
                          PathToTestFile,
                          StopTernServer,
                          with_cwd,
                          WaitForTernServerReady  )

bottle.debug( True )

@with_setup( Setup )
@with_cwd( TEST_DATA_DIR )
def Subcommands_TernCompleter_Defined_Subcommands_test():
  app = TestApp( handlers.app )

  try:
    subcommands_data = BuildRequest( completer_target = 'javascript' )

    WaitForTernServerReady( app )

    eq_( sorted ( [ 'GoToDefinition',
                    'GoTo',
                    'GetDoc',
                    'GetType',
                    'StartServer',
                    'StopServer',
                    'GoToReferences' ] ),
          app.post_json( '/defined_subcommands', subcommands_data ).json )
  finally:
    StopTernServer( app )


def Subcommand_RunTest( test ):
  app = TestApp( handlers.app )

  try:
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
  finally:
    StopTernServer( app )


@with_setup( Setup )
@with_cwd( TEST_DATA_DIR )
def SubCommands_TernCompleter_GoToDefinition_Works_test():
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
def SubCommands_TernCompleter_GoTo_Works_test():
  Subcommand_RunTest( {
    'description': 'GoTo works the same as GoToDefinition within file',
    'request': {
      'command': 'GoTo',
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
def SubCommands_TernCompleter_GetDoc_Works_test():
  Subcommand_RunTest( {
    'description': 'GetDoc works within file',
    'request': {
      'command': 'GetDoc',
      'line_num': 7,
      'column_num': 16,
      'filepath': PathToTestFile( 'coollib/cool_object.js' ),
    },
    'expect': {
      'response': httplib.OK,
      'data': has_entries( {
        'detailed_info': (
          'Name: mine_bitcoin\n' +
          'Type: fn(how_much: ?) -> number\n\n' +
          'This function takes a number and invests it in bitcoin. ' +
          'It returns\nthe expected value (in notional currency) after 1 year.'
        )
      } )
    }
  } )


@with_setup( Setup )
@with_cwd( TEST_DATA_DIR )
def SubCommands_TernCompleter_GetType_Works_test():
  Subcommand_RunTest( {
    'description': 'GetType works within file',
    'request': {
      'command': 'GetType',
      'line_num': 11,
      'column_num': 14,
      'filepath': PathToTestFile( 'coollib/cool_object.js' ),
    },
    'expect': {
      'response': httplib.OK,
      'data': has_entries( {
        'message': 'number'
      } )
    }
  } )


@with_setup( Setup )
@with_cwd( TEST_DATA_DIR )
def SubCommands_TernCompleter_GoToReferences_Works_test():
  Subcommand_RunTest( {
    'description': 'GoToReferences works within file',
    'request': {
      'command': 'GoToReferences',
      'line_num': 17,
      'column_num': 29,
      'filepath': PathToTestFile( 'coollib/cool_object.js' ),
    },
    'expect': {
      'response': httplib.OK,
      'data': contains_inanyorder(
        has_entries( {
          'filepath': PathToTestFile( 'coollib/cool_object.js' ),
          'line_num':  17,
          'column_num': 29,
        } ),
        has_entries( {
          'filepath': PathToTestFile( 'coollib/cool_object.js' ),
          'line_num': 12,
          'column_num': 9,
        } )
      )
    }
  } )


@with_setup( Setup )
@with_cwd( TEST_DATA_DIR )
def SubCommands_TernCompleter_DetDoc_With_No_Itendifier_test():
  Subcommand_RunTest( {
    'description': 'GetDoc works when no identifier',
    'request': {
      'command': 'GetDoc',
      'filepath': PathToTestFile( 'simple_test.js' ),
      'line_num': 12,
      'column_num': 1,
    },
    'expect': {
      'response': httplib.INTERNAL_SERVER_ERROR,
      'data': ErrorMatcher( RuntimeError,
                            'TernError: No type found at the given position.'),
    }
  } )
