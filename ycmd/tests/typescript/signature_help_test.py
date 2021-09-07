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

from hamcrest import assert_that, contains_exactly, empty, equal_to, has_entries
from unittest import TestCase
import requests

from ycmd.tests.typescript import setUpModule, tearDownModule # noqa
from ycmd.tests.typescript import PathToTestFile, IsolatedYcmd, SharedYcmd
from ycmd.tests.test_utils import ( CombineRequest,
                                    ParameterMatcher,
                                    SignatureMatcher,
                                    SignatureAvailableMatcher,
                                    WaitUntilCompleterServerReady )
from ycmd.utils import ReadFile


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

  WaitUntilCompleterServerReady( app, 'typescript' )

  app.post_json( '/event_notification',
                 CombineRequest( test[ 'request' ], {
                   'event_name': 'BufferVisit',
                   'contents': contents,
                   'filetype': 'typescript',
                 } ),
                 expect_errors = True )

  # We ignore errors here and we check the response code ourself.
  # This is to allow testing of requests returning errors.
  response = app.post_json( '/signature_help',
                            CombineRequest( test[ 'request' ], {
                              'contents': contents,
                              'filetype': 'typescript',
                            } ),
                            expect_errors = True )

  assert_that( response.status_code,
               equal_to( test[ 'expect' ][ 'response' ] ) )

  print( response.json )
  assert_that( response.json, test[ 'expect' ][ 'data' ] )


class SignatureHelpTest( TestCase ):
  @SharedYcmd
  def test_Signature_Help_Available( self, app ):
    response = app.get( '/signature_help_available',
                        { 'subserver': 'typescript' } ).json
    assert_that( response, SignatureAvailableMatcher( 'YES' ) )


  # Triggering on '(', ',' and '<'
  @SharedYcmd
  def test_Signature_Help_Trigger_Paren( self, app ):
    RunTest( app, {
      'description': 'Trigger after (',
      'request': {
        'filetype'  : 'typescript',
        'filepath'  : PathToTestFile( 'signatures.ts' ),
        'line_num'  : 27,
        'column_num': 29,
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'errors': empty(),
          'signature_help': has_entries( {
            'activeSignature': 0,
            'activeParameter': 0,
            'signatures': contains_exactly(
              SignatureMatcher(
                'single_argument_with_return(a: string): string',
                [ ParameterMatcher( 28, 37, '' ) ],
                '' )
            ),
          } ),
        } )
      }
    } )


  @IsolatedYcmd( { 'disable_signature_help': True } )
  def test_Signature_Help_Trigger_Paren_Disabled( self, app ):
    RunTest( app, {
      'description': 'Trigger after (',
      'request': {
        'filetype'  : 'typescript',
        'filepath'  : PathToTestFile( 'signatures.ts' ),
        'line_num'  : 27,
        'column_num': 29,
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'errors': empty(),
          'signature_help': has_entries( {
            'activeSignature': 0,
            'activeParameter': 0,
            'signatures': empty()
          } ),
        } )
      }
    } )


  @SharedYcmd
  def test_Signature_Help_Trigger_Comma( self, app ):
    RunTest( app, {
      'description': 'Trigger after ,',
      'request': {
        'filetype'  : 'typescript',
        'filepath'  : PathToTestFile( 'signatures.ts' ),
        'line_num'  : 60,
        'column_num': 32,
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'errors': empty(),
          'signature_help': has_entries( {
            'activeSignature': 0,
            'activeParameter': 1,
            'signatures': contains_exactly(
              SignatureMatcher(
                ( 'multi_argument_no_return(løng_våriable_name: number, '
                                            'untyped_argument: any): number' ),
                [ ParameterMatcher( 25, 53, '' ),
                  ParameterMatcher( 55, 76, '' ) ],
                '' )
            ),
          } ),
        } )
      }
    } )


  @SharedYcmd
  def test_Signature_Help_Trigger_AngleBracket( self, app ):
    RunTest( app, {
      'description': 'Trigger after <',
      'request': {
        'filetype'  : 'typescript',
        'filepath'  : PathToTestFile( 'signatures.ts' ),
        'line_num'  : 68,
        'column_num': 9,
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'errors': empty(),
          'signature_help': has_entries( {
            'activeSignature': 0,
            'activeParameter': 0,
            'signatures': contains_exactly(
              SignatureMatcher(
                'generic<TYPE extends ReturnValue>(t: SomeClass): string',
                [ ParameterMatcher( 8, 32, '' ) ],
                '' )
            ),
          } ),
        } )
      }
    } )


  @SharedYcmd
  def test_Signature_Help_Multiple_Signatures( self, app ):
    RunTest( app, {
      'description': 'Test overloaded methods',
      'request': {
        'filetype'  : 'typescript',
        'filepath'  : PathToTestFile( 'signatures.ts' ),
        'line_num'  : 89,
        'column_num': 18,
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'errors': empty(),
          'signature_help': has_entries( {
            'activeSignature': 1,
            'activeParameter': 1,
            'signatures': contains_exactly(
              SignatureMatcher( 'øverløåd(a: number): string',
                                [ ParameterMatcher( 12, 21, '' ) ],
                                '' ),
              SignatureMatcher( 'øverløåd(a: string, b: number): string',
                                [ ParameterMatcher( 12, 21, '' ),
                                  ParameterMatcher( 23, 32, '' ) ],
                                '' )
            ),
          } ),
        } )
      }
    } )


  @SharedYcmd
  def test_Signature_Help_NoSignatures( self, app ):
    RunTest( app, {
      'description': 'Test overloaded methods',
      'request': {
        'filetype'  : 'typescript',
        'filepath'  : PathToTestFile( 'signatures.ts' ),
        'line_num'  : 68,
        'column_num': 22,
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'errors': empty(),
          'signature_help': has_entries( {
            'activeSignature': 0,
            'activeParameter': 0,
            'signatures': empty(),
          } ),
        } )
      }
    } )


  @SharedYcmd
  def test_Signature_Help_WithDoc( self, app ):
    RunTest( app, {
      'description': 'Test parameter documentation',
      'request': {
        'filetype': 'typescript',
        'filepath': PathToTestFile( 'signatures.ts' ),
        'line_num': 101,
        'column_num': 26,
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'errors': empty(),
          'signature_help': has_entries( {
            'activeSignature': 0,
            'activeParameter': 0,
            'signatures': contains_exactly(
              SignatureMatcher(
                'single_argument_with_doc(a: string): string',
                [ ParameterMatcher( 25, 34, '- The argument' ) ],
                'A function with a single argument' ) )
          } ),
        } )
      }
    } )


  @SharedYcmd
  def test_Signature_Help_NoErrorWhenNoSignatureInfo( self, app ):
    RunTest( app, {
      'description': 'Test dodgy (',
      'request': {
        'filetype'  : 'typescript',
        'filepath'  : PathToTestFile( 'signatures.ts' ),
        'line_num'  : 103,
        'column_num': 5,
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'errors': empty(),
          'signature_help': has_entries( {
            'activeSignature': 0,
            'activeParameter': 0,
            'signatures': empty(),
          } ),
        } )
      }
    } )
