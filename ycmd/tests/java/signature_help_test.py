# Copyright (C) 2021 ycmd contributors
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
                       empty,
                       equal_to,
                       has_entries )
from unittest import TestCase
import requests

from ycmd.utils import ReadFile
from ycmd.tests.java import setUpModule, tearDownModule # noqa
from ycmd.tests.java import PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import ( CombineRequest,
                                    ParameterMatcher,
                                    SignatureMatcher,
                                    SignatureAvailableMatcher,
                                    WaitUntilCompleterServerReady,
                                    WithRetry )


def ProjectPath( *args ):
  return PathToTestFile( 'extra_confs',
                         'simple_extra_conf_project',
                         'src',
                         *args )


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

  print( response.json )
  assert_that( response.json, test[ 'expect' ][ 'data' ] )


class SignatureHelpTest( TestCase ):
  @WithRetry()
  @SharedYcmd
  def test_SignatureHelp_MethodTrigger( self, app ):
    RunTest( app, {
      'description': 'Trigger after (',
      'request': {
        'filetype'  : 'java',
        'filepath'  : ProjectPath( 'SignatureHelp.java' ),
        'line_num'  : 9,
        'column_num': 17,
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'errors': empty(),
          'signature_help': has_entries( {
            'activeSignature': 0,
            'activeParameter': 0,
            'signatures': contains_exactly(
              SignatureMatcher( 'unique(double d) : void',
                                [ ParameterMatcher( 7, 15 ) ] )
            ),
          } ),
        } )
      }
    } )


  @WithRetry()
  @SharedYcmd
  def test_SignatureHelp_ArgTrigger( self, app ):
    RunTest( app, {
      'description': 'Trigger after ,',
      'request': {
        'filetype'  : 'java',
        'filepath'  : ProjectPath( 'SignatureHelp.java' ),
        'line_num'  : 5,
        'column_num': 23,
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'errors': empty(),
          'signature_help': has_entries( {
            'activeSignature': 1,
            'activeParameter': 1,
            'signatures': contains_exactly(
              SignatureMatcher( 'test(int i, String s) : void',
                                [ ParameterMatcher( 5, 10 ),
                                  ParameterMatcher( 12, 20 ) ] ),
              SignatureMatcher( 'test(String s, String s1) : void',
                                [ ParameterMatcher( 5, 13 ),
                                  ParameterMatcher( 15, 24 ) ] )
            ),
          } ),
        } )
      }
    } )


  @WithRetry()
  @SharedYcmd
  def test_SignatureHelp_Constructor( self, app ):
    RunTest( app, {
      'description': 'Constructor',
      'request': {
        'filetype'  : 'java',
        'filepath'  : ProjectPath( 'SignatureHelp.java' ),
        'line_num'  : 17,
        'column_num': 41,
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'errors': empty(),
          'signature_help': has_entries( {
            'activeSignature': 0,
            'activeParameter': 0,
            'signatures': contains_exactly(
              SignatureMatcher( 'SignatureHelp(String signature)',
                                [ ParameterMatcher( 14, 30 ) ] )
            ),
          } ),
        } )
      }
    } )


  @SharedYcmd
  def test_Signature_Help_Available( self, app ):
    request = { 'filepath' : ProjectPath( 'SignatureHelp.java' ) }
    app.post_json( '/event_notification',
                   CombineRequest( request, {
                     'event_name': 'FileReadyToParse',
                     'filetype': 'java'
                   } ),
                   expect_errors = True )
    WaitUntilCompleterServerReady( app, 'java' )

    response = app.get( '/signature_help_available',
                        { 'subserver': 'java' } ).json
    assert_that( response, SignatureAvailableMatcher( 'YES' ) )
