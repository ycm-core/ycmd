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

from nose.tools import eq_
from hamcrest import assert_that, contains_inanyorder, has_entries
from javascript_handlers_test import Javascript_Handlers_test
from pprint import pformat
import httplib


class Javascript_Subcommands_test( Javascript_Handlers_test ):

  def _RunTest( self, test ):
    contents = open( test[ 'request' ][ 'filepath' ] ).read()

    def CombineRequest( request, data ):
      kw = request
      request.update( data )
      return self._BuildRequest( **kw )

    # Because we aren't testing this command, we *always* ignore errors. This
    # is mainly because we (may) want to test scenarios where the completer
    # throws an exception and the easiest way to do that is to throw from
    # within the FlagsForFile function.
    self._app.post_json( '/event_notification',
                         CombineRequest( test[ 'request' ], {
                                         'event_name': 'FileReadyToParse',
                                         'contents': contents,
                                         } ),
                         expect_errors = True )

    # We also ignore errors here, but then we check the response code
    # ourself. This is to allow testing of requests returning errors.
    response = self._app.post_json(
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

    print( 'completer response: {0}'.format( pformat( response.json ) ) )

    eq_( response.status_code, test[ 'expect' ][ 'response' ] )

    assert_that( response.json, test[ 'expect' ][ 'data' ] )


  def DefinedSubcommands_test( self ):
    subcommands_data = self._BuildRequest( completer_target = 'javascript' )

    self._WaitUntilTernServerReady()

    eq_( sorted( [ 'GoToDefinition',
                   'GoTo',
                   'GetDoc',
                   'GetType',
                   'StartServer',
                   'StopServer',
                   'GoToReferences' ] ),
         self._app.post_json( '/defined_subcommands',
                              subcommands_data ).json )


  def GoToDefinition_test( self ):
    self._RunTest( {
      'description': 'GoToDefinition works within file',
      'request': {
        'command': 'GoToDefinition',
        'line_num': 13,
        'column_num': 25,
        'filepath': self._PathToTestFile( 'simple_test.js' ),
      },
      'expect': {
        'response': httplib.OK,
        'data': has_entries( {
          'filepath': self._PathToTestFile( 'simple_test.js' ),
          'line_num': 1,
          'column_num': 5,
        } )
      }
    } )


  def GoTo_test( self ):
    self._RunTest( {
      'description': 'GoTo works the same as GoToDefinition within file',
      'request': {
        'command': 'GoTo',
        'line_num': 13,
        'column_num': 25,
        'filepath': self._PathToTestFile( 'simple_test.js' ),
      },
      'expect': {
        'response': httplib.OK,
        'data': has_entries( {
          'filepath': self._PathToTestFile( 'simple_test.js' ),
          'line_num': 1,
          'column_num': 5,
        } )
      }
    } )


  def GetDoc_test( self ):
    self._RunTest( {
      'description': 'GetDoc works within file',
      'request': {
        'command': 'GetDoc',
        'line_num': 7,
        'column_num': 16,
        'filepath': self._PathToTestFile( 'coollib', 'cool_object.js' ),
      },
      'expect': {
        'response': httplib.OK,
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


  def GetType_test( self ):
    self._RunTest( {
      'description': 'GetType works within file',
      'request': {
        'command': 'GetType',
        'line_num': 11,
        'column_num': 14,
        'filepath': self._PathToTestFile( 'coollib', 'cool_object.js' ),
      },
      'expect': {
        'response': httplib.OK,
        'data': has_entries( {
          'message': 'number'
        } )
      }
    } )


  def GoToReferences_test( self ):
    self._RunTest( {
      'description': 'GoToReferences works within file',
      'request': {
        'command': 'GoToReferences',
        'line_num': 17,
        'column_num': 29,
        'filepath': self._PathToTestFile( 'coollib', 'cool_object.js' ),
      },
      'expect': {
        'response': httplib.OK,
        'data': contains_inanyorder(
          has_entries( {
            'filepath': self._PathToTestFile( 'coollib', 'cool_object.js' ),
            'line_num':  17,
            'column_num': 29,
          } ),
          has_entries( {
            'filepath': self._PathToTestFile( 'coollib', 'cool_object.js' ),
            'line_num': 12,
            'column_num': 9,
          } )
        )
      }
    } )


  def GetDocWithNoItendifier_test( self ):
    self._RunTest( {
      'description': 'GetDoc works when no identifier',
      'request': {
        'command': 'GetDoc',
        'filepath': self._PathToTestFile( 'simple_test.js' ),
        'line_num': 12,
        'column_num': 1,
      },
      'expect': {
        'response': httplib.INTERNAL_SERVER_ERROR,
        'data': self._ErrorMatcher( RuntimeError, 'TernError: No type found '
                                                  'at the given position.' ),
      }
    } )
