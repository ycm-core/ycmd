# Copyright (C) 2020 ycmd contributors
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

from hamcrest import assert_that, contains_exactly, empty, equal_to, has_entries
import requests

from ycmd.utils import ReadFile
from ycmd.tests.rust import PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import ( CombineRequest,
                                    SignatureMatcher,
                                    SignatureAvailableMatcher,
                                    WaitUntilCompleterServerReady,
                                    WithRetry )


def RunTest( app, test ):
  """
  Method to run a simple signature help test and verify the result

  test is a dictionary containing:
    'request': kwargs for BuildRequest
    'expect': {
       'response': server response code (e.g. httplib.OK)
       'data': matcher for the server response json
    }
  """
  contents = ReadFile( test[ 'request' ][ 'filepath' ] )

  app.post_json( '/event_notification',
                 CombineRequest( test[ 'request' ], {
                                 'event_name': 'FileReadyToParse',
                                 'contents': contents,
                                 } ),
                 expect_errors = True )

  # We ignore errors here and we check the response code ourself.
  # This is to allow testing of requests returning errors.
  response = app.post_json( '/signature_help',
                            CombineRequest( test[ 'request' ], {
                              'contents': contents
                            } ),
                            expect_errors = True )

  assert_that( response.status_code,
               equal_to( test[ 'expect' ][ 'response' ] ) )

  assert_that( response.json, test[ 'expect' ][ 'data' ] )


@WithRetry
@SharedYcmd
def SignatureHelp_NoParams_test( app ):
  RunTest( app, {
    'description': 'Trigger after (',
    'request': {
      'filetype'  : 'rust',
      'filepath'  : PathToTestFile( 'common', 'src', 'test.rs' ),
      'line_num'  : 14,
      'column_num': 14,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'errors': empty(),
        'signature_help': has_entries( {
          'activeSignature': 0,
          'activeParameter': 0,
          'signatures': contains_exactly(
            SignatureMatcher( 'fn sig_test()', [] )
          ),
        } ),
      } )
    }
  } )


@WithRetry
@SharedYcmd
def SignatureHelp_MethodTrigger_test( app ):
  RunTest( app, {
    'description': 'Trigger after (',
    'request': {
      'filetype'  : 'rust',
      'filepath'  : PathToTestFile( 'common', 'src', 'test.rs' ),
      'line_num'  : 13,
      'column_num': 20,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'errors': empty(),
        'signature_help': has_entries( {
          'activeSignature': 0,
          'activeParameter': 0,
          'signatures': contains_exactly(
            SignatureMatcher( 'fn build_rocket(&self)', [] )
          ),
        } ),
      } )
    }
  } )



@WithRetry
@SharedYcmd
def Signature_Help_Available_test( app ):
  request = { 'filepath' : PathToTestFile( 'common', 'src', 'main.rs' ) }
  app.post_json( '/event_notification',
                 CombineRequest( request, {
                   'event_name': 'FileReadyToParse',
                   'filetype': 'rust'
                 } ),
                 expect_errors = True )
  WaitUntilCompleterServerReady( app, 'rust' )

  response = app.get( '/signature_help_available',
                      { 'subserver': 'rust' } ).json
  assert_that( response, SignatureAvailableMatcher( 'YES' ) )


def Dummy_test():
  # Workaround for https://github.com/pytest-dev/pytest-rerunfailures/issues/51
  assert True
