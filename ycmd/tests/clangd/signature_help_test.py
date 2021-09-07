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

import json
import requests
from unittest.mock import patch
from unittest import TestCase
from hamcrest import assert_that, contains_exactly, empty, equal_to, has_entries

from ycmd import handlers
from ycmd.tests.clangd import setUpModule, tearDownModule # noqa
from ycmd.tests.clangd import PathToTestFile, SharedYcmd, IsolatedYcmd
from ycmd.tests.test_utils import ( EMPTY_SIGNATURE_HELP,
                                    BuildRequest,
                                    CombineRequest,
                                    ParameterMatcher,
                                    SignatureMatcher,
                                    SignatureAvailableMatcher,
                                    WaitUntilCompleterServerReady )
from ycmd.utils import ReadFile


def RunTest( app, test ):
  """
  Method to run a simple completion test and verify the result

  Note: Compile commands are extracted from a compile_flags.txt file by clangd
  by iteratively looking at the directory containing the source file and its
  ancestors.

  test is a dictionary containing:
    'request': kwargs for BuildRequest
    'expect': {
       'response': server response code (e.g. requests.codes.ok)
       'data': matcher for the server response json
    }
  """

  request = test[ 'request' ]
  filetype = request.get( 'filetype', 'cpp' )
  if 'contents' not in request:
    contents = ReadFile( request[ 'filepath' ] )
    request[ 'contents' ] = contents
    request[ 'filetype' ] = filetype

  # Because we aren't testing this command, we *always* ignore errors. This
  # is mainly because we (may) want to test scenarios where the completer
  # throws an exception and the easiest way to do that is to throw from
  # within the Settings function.
  app.post_json( '/event_notification',
                 CombineRequest( request, {
                   'event_name': 'FileReadyToParse',
                   'filetype': filetype
                 } ),
                 expect_errors = True )
  WaitUntilCompleterServerReady( app, filetype )

  # We also ignore errors here, but then we check the response code ourself.
  # This is to allow testing of requests returning errors.
  response = app.post_json( '/signature_help',
                            BuildRequest( **request ),
                            expect_errors = True )

  assert_that( response.status_code,
               equal_to( test[ 'expect' ][ 'response' ] ) )

  print( f'Completer response: { json.dumps( response.json, indent = 2 ) }' )

  assert_that( response.json, test[ 'expect' ][ 'data' ] )


class SignatureHelpTest( TestCase ):
  @SharedYcmd
  def test_Signature_Help_Trigger( self, app ):
    RunTest( app, {
      'description': 'trigger after (',
      'request': {
        'filetype'  : 'cpp',
        'filepath'  : PathToTestFile( 'general_fallback',
                                      'make_drink.cc' ),
        'line_num'  : 7,
        'column_num': 14,
        'signature_help_state': 'INACTIVE',
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'errors': empty(),
          'signature_help': has_entries( {
            'activeSignature': 0,
            'activeParameter': 0,
            'signatures': contains_exactly(
              SignatureMatcher( 'make_drink(TypeOfDrink type, '
                                'Temperature temp, '
                                'int sugargs) -> Drink &', [
                                  ParameterMatcher( 11, 27 ),
                                  ParameterMatcher( 29, 45 ),
                                  ParameterMatcher( 47, 58 ),
                                ] ),
              SignatureMatcher( 'make_drink(TypeOfDrink type, '
                                'double fizziness, '
                                'Flavour Flavour) -> Drink &', [
                                  ParameterMatcher( 11, 27 ),
                                  ParameterMatcher( 29, 45 ),
                                  ParameterMatcher( 47, 62 ),
                                ] ),
            )
          } ),
        } )
      },
    } )


  @IsolatedYcmd( { 'disable_signature_help': 1 } )
  def test_Signature_Help_Disabled( self, app ):
    RunTest( app, {
      'description': 'trigger after (',
      'request': {
        'filetype'  : 'cpp',
        'filepath'  : PathToTestFile( 'general_fallback',
                                      'make_drink.cc' ),
        'line_num'  : 7,
        'column_num': 14,
        'signature_help_state': 'INACTIVE',
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'errors': empty(),
          'signature_help': EMPTY_SIGNATURE_HELP,
        } )
      },
    } )


  @SharedYcmd
  def test_Signature_Help_NoTrigger( self, app ):
    RunTest( app, {
      'description': 'do not trigger before (',
      'request': {
        'filetype'  : 'cpp',
        'filepath'  : PathToTestFile( 'general_fallback',
                                      'make_drink.cc' ),
        'line_num'  : 7,
        'column_num': 13,
        'signature_help_state': 'INACTIVE',
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'errors': empty(),
          'signature_help': EMPTY_SIGNATURE_HELP,
        } ),
      },
    } )


  @SharedYcmd
  def test_Signature_Help_NoTrigger_After_Trigger( self, app ):
    RunTest( app, {
      'description': 'do not trigger too far after (',
      'request': {
        'filetype'  : 'cpp',
        'filepath'  : PathToTestFile( 'general_fallback',
                                      'make_drink.cc' ),
        'line_num'  : 7,
        'column_num': 15,
        'signature_help_state': 'INACTIVE',
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'errors': empty(),
          'signature_help': EMPTY_SIGNATURE_HELP,
        } ),
      },
    } )


  @SharedYcmd
  def test_Signature_Help_Trigger_After_Trigger( self, app ):
    RunTest( app, {
      'description': 'Auto trigger due to state of existing request',
      'request': {
        'filetype'  : 'cpp',
        'filepath'  : PathToTestFile( 'general_fallback',
                                      'make_drink.cc' ),
        'line_num'  : 7,
        'column_num': 15,
        'signature_help_state': 'ACTIVE',
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'errors': empty(),
          'signature_help': has_entries( {
            'activeSignature': 0,
            'activeParameter': 0,
            'signatures': contains_exactly(
              SignatureMatcher( 'make_drink(TypeOfDrink type, '
                                'Temperature temp, '
                                'int sugargs) -> Drink &', [
                                  ParameterMatcher( 11, 27 ),
                                  ParameterMatcher( 29, 45 ),
                                  ParameterMatcher( 47, 58 ),
                                ] ),
              SignatureMatcher( 'make_drink(TypeOfDrink type, '
                                'double fizziness, '
                                'Flavour Flavour) -> Drink &', [
                                  ParameterMatcher( 11, 27 ),
                                  ParameterMatcher( 29, 45 ),
                                  ParameterMatcher( 47, 62 ),
                                ] ),
            )
          } ),
        } ),
      },
    } )


  @IsolatedYcmd( { 'disable_signature_help': 1 } )
  def test_Signature_Help_Trigger_After_Trigger_Disabled( self, app ):
    RunTest( app, {
      'description': 'Auto trigger due to state of existing request',
      'request': {
        'filetype'  : 'cpp',
        'filepath'  : PathToTestFile( 'general_fallback',
                                      'make_drink.cc' ),
        'line_num'  : 7,
        'column_num': 15,
        'signature_help_state': 'ACTIVE',
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'errors': empty(),
          'signature_help': EMPTY_SIGNATURE_HELP,
        } ),
      },
    } )


  @SharedYcmd
  def test_Signature_Help_Trigger_After_Trigger_PlusText( self, app ):
    RunTest( app, {
      'description': 'Triggering after additional text beyond (',
      'request': {
        'filetype'  : 'cpp',
        'filepath'  : PathToTestFile( 'general_fallback',
                                      'make_drink.cc' ),
        'line_num'  : 7,
        'column_num': 17,
        'signature_help_state': 'ACTIVE',
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'errors': empty(),
          'signature_help': has_entries( {
            'activeSignature': 0,
            'activeParameter': 0,
            'signatures': contains_exactly(
              SignatureMatcher( 'make_drink(TypeOfDrink type, '
                                'Temperature temp, '
                                'int sugargs) -> Drink &', [
                                  ParameterMatcher( 11, 27 ),
                                  ParameterMatcher( 29, 45 ),
                                  ParameterMatcher( 47, 58 ),
                                ] ),
              SignatureMatcher( 'make_drink(TypeOfDrink type, '
                                'double fizziness, '
                                'Flavour Flavour) -> Drink &', [
                                  ParameterMatcher( 11, 27 ),
                                  ParameterMatcher( 29, 45 ),
                                  ParameterMatcher( 47, 62 ),
                                ] ),
            )
          } ),
        } ),
      },
    } )


  @SharedYcmd
  def test_Signature_Help_Trigger_After_Trigger_PlusCompletion( self, app ):
    RunTest( app, {
      'description': 'Triggering after semantic trigger after (',
      'request': {
        'filetype'  : 'cpp',
        'filepath'  : PathToTestFile( 'general_fallback',
                                      'make_drink.cc' ),
        'line_num'  : 7,
        'column_num': 28,
        'signature_help_state': 'ACTIVE',
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'errors': empty(),
          'signature_help': has_entries( {
            'activeSignature': 0,
            'activeParameter': 0,
            'signatures': contains_exactly(
              SignatureMatcher( 'make_drink(TypeOfDrink type, '
                                'Temperature temp, '
                                'int sugargs) -> Drink &', [
                                  ParameterMatcher( 11, 27 ),
                                  ParameterMatcher( 29, 45 ),
                                  ParameterMatcher( 47, 58 ),
                                ] ),
              SignatureMatcher( 'make_drink(TypeOfDrink type, '
                                'double fizziness, '
                                'Flavour Flavour) -> Drink &', [
                                  ParameterMatcher( 11, 27 ),
                                  ParameterMatcher( 29, 45 ),
                                  ParameterMatcher( 47, 62 ),
                                ] ),
            )
          } ),
        } ),
      },
    } )


  @SharedYcmd
  def test_Signature_Help_Trigger_After_OtherTrigger( self, app ):
    RunTest( app, {
      'description': 'Triggering after ,',
      'request': {
        'filetype'  : 'cpp',
        'filepath'  : PathToTestFile( 'general_fallback',
                                      'make_drink.cc' ),
        'line_num'  : 7,
        'column_num': 35,
        'signature_help_state': 'INACTIVE',
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'errors': empty(),
          'signature_help': has_entries( {
            'activeSignature': 0,
            'activeParameter': 1,
            'signatures': contains_exactly(
              SignatureMatcher( 'make_drink(TypeOfDrink type, '
                                'Temperature temp, '
                                'int sugargs) -> Drink &', [
                                  ParameterMatcher( 11, 27 ),
                                  ParameterMatcher( 29, 45 ),
                                  ParameterMatcher( 47, 58 ),
                                ] ),
              SignatureMatcher( 'make_drink(TypeOfDrink type, '
                                'double fizziness, '
                                'Flavour Flavour) -> Drink &', [
                                  ParameterMatcher( 11, 27 ),
                                  ParameterMatcher( 29, 45 ),
                                  ParameterMatcher( 47, 62 ),
                                ] ),
            )
          } ),
        } ),
      },
    } )


  @SharedYcmd
  def test_Signature_Help_Trigger_After_Arguments_Narrow( self, app ):
    RunTest( app, {
      'description': 'After resolution of overload',
      'request': {
        'filetype'  : 'cpp',
        'filepath'  : PathToTestFile( 'general_fallback',
                                      'make_drink.cc' ),
        'line_num'  : 7,
        'column_num': 41,
        'signature_help_state': 'ACTIVE',
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'errors': empty(),
          'signature_help': has_entries( {
            'activeSignature': 0,
            'activeParameter': 2,
            'signatures': contains_exactly(
              SignatureMatcher( 'make_drink(TypeOfDrink type, '
                                'double fizziness, '
                                'Flavour Flavour) -> Drink &', [
                                  ParameterMatcher( 11, 27 ),
                                  ParameterMatcher( 29, 45 ),
                                  ParameterMatcher( 47, 62 ),
                                ] )
            )
          } ),
        } ),
      },
    } )


  @SharedYcmd
  def test_Signature_Help_Trigger_After_Arguments_Narrow2( self, app ):
    RunTest( app, {
      'description': 'After resolution of overload not the first one',
      'request': {
        'filetype'  : 'cpp',
        'filepath'  : PathToTestFile( 'general_fallback',
                                      'make_drink.cc' ),
        'line_num'  : 8,
        'column_num': 53,
        'signature_help_state': 'ACTIVE',
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'errors': empty(),
          'signature_help': has_entries( {
            'activeSignature': 0,
            'activeParameter': 2,
            'signatures': contains_exactly(
              SignatureMatcher( 'make_drink(TypeOfDrink type, '
                                'Temperature temp, '
                                'int sugargs) -> Drink &', [
                                  ParameterMatcher( 11, 27 ),
                                  ParameterMatcher( 29, 45 ),
                                  ParameterMatcher( 47, 58 ),
                                ] )
            )
          } ),
        } ),
      },
    } )


  @SharedYcmd
  def test_Signature_Help_Trigger_After_OtherTrigger_ReTrigger( self, app ):
    RunTest( app, {
      'description': 'Triggering after , but already ACTIVE',
      'request': {
        'filetype'  : 'cpp',
        'filepath'  : PathToTestFile( 'general_fallback',
                                      'make_drink.cc' ),
        'line_num'  : 7,
        'column_num': 35,
        'signature_help_state': 'ACTIVE',
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'errors': empty(),
          'signature_help': has_entries( {
            'activeSignature': 0,
            'activeParameter': 1,
            'signatures': contains_exactly(
              SignatureMatcher( 'make_drink(TypeOfDrink type, '
                                'Temperature temp, '
                                'int sugargs) -> Drink &', [
                                  ParameterMatcher( 11, 27 ),
                                  ParameterMatcher( 29, 45 ),
                                  ParameterMatcher( 47, 58 ),
                                ] ),
              SignatureMatcher( 'make_drink(TypeOfDrink type, '
                                'double fizziness, '
                                'Flavour Flavour) -> Drink &', [
                                  ParameterMatcher( 11, 27 ),
                                  ParameterMatcher( 29, 45 ),
                                  ParameterMatcher( 47, 62 ),
                                ] ),
            )
          } ),
        } ),
      },
    } )


  @SharedYcmd
  def test_Signature_Help_Trigger_JustBeforeClose( self, app ):
    RunTest( app, {
      'description': 'Last argument, before )',
      'request': {
        'filetype'  : 'cpp',
        'filepath'  : PathToTestFile( 'general_fallback',
                                      'make_drink.cc' ),
        'line_num'  : 8,
        'column_num': 33,
        'signature_help_state': 'ACTIVE',
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'errors': empty(),
          'signature_help': has_entries( {
            'activeSignature': 0,
            'activeParameter': 0,
            'signatures': contains_exactly(
              SignatureMatcher( 'make_drink(TypeOfDrink type, '
                                'Temperature temp, '
                                'int sugargs) -> Drink &', [
                                  ParameterMatcher( 11, 27 ),
                                  ParameterMatcher( 29, 45 ),
                                  ParameterMatcher( 47, 58 ),
                                ] ),
              SignatureMatcher( 'make_drink(TypeOfDrink type, '
                                'double fizziness, '
                                'Flavour Flavour) -> Drink &', [
                                  ParameterMatcher( 11, 27 ),
                                  ParameterMatcher( 29, 45 ),
                                  ParameterMatcher( 47, 62 ),
                                ] ),
            )
          } ),
        } ),
      },
    } )


  @SharedYcmd
  def test_Signature_Help_Clears_After_EndFunction( self, app ):
    RunTest( app, {
      'description': 'Empty response on )',
      'request': {
        'filetype'  : 'cpp',
        'filepath'  : PathToTestFile( 'general_fallback',
                                      'make_drink.cc' ),
        'line_num'  : 7,
        'column_num': 70,
        'signature_help_state': 'ACTIVE',
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'errors': empty(),
          'signature_help': EMPTY_SIGNATURE_HELP,
        } ),
      },
    } )


  @SharedYcmd
  def test_Signature_Help_Clears_After_Function_Call( self, app ):
    RunTest( app, {
      'description': 'Empty response after )',
      'request': {
        'filetype'  : 'cpp',
        'filepath'  : PathToTestFile( 'general_fallback',
                                      'make_drink.cc' ),
        'line_num'  : 7,
        'column_num': 71,
        'signature_help_state': 'ACTIVE',
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'errors': empty(),
          'signature_help': EMPTY_SIGNATURE_HELP,
        } ),
      },
    } )


  @patch( 'ycmd.completers.completer.Completer.ShouldUseSignatureHelpNow',
          return_value = True )
  @patch( 'ycmd.completers.language_server.language_server_completer.'
          'LanguageServerCompleter._ServerIsInitialized', return_value = False )
  @IsolatedYcmd()
  def test_Signature_Help_Server_Not_Initialized( self, app, *args ):
    filepath = PathToTestFile( 'general_fallback', 'make_drink.cc' )
    request = {
      'filetype'  : 'cpp',
      'filepath'  : filepath,
      'line_num'  : 7,
      'column_num': 71,
      'signature_help_state': 'INACTIVE',
      'contents': ReadFile( filepath )
    }
    response = app.post_json( '/signature_help',
                              BuildRequest( **request ),
                              expect_errors = True )
    assert_that( response.json, has_entries( {
          'errors': empty(),
          'signature_help': EMPTY_SIGNATURE_HELP,
        } ) )


  def test_Signature_Help_Available_Server_Not_Initialized( self ):
    completer = handlers._server_state.GetFiletypeCompleter( [ 'cpp' ] )

    @SharedYcmd
    @patch.object( completer, '_ServerIsInitialized', return_value = False )
    def Test( self, app ):
      response = app.get( '/signature_help_available',
                          { 'subserver': 'cpp' } ).json
      assert_that( response, SignatureAvailableMatcher( 'PENDING' ) )


  @SharedYcmd
  def test_Signature_Help_Supported( self, app ):
    request = { 'filepath' : PathToTestFile( 'goto.cc' ) }
    app.post_json( '/event_notification',
                   CombineRequest( request, {
                     'event_name': 'FileReadyToParse',
                     'filetype': 'cpp'
                   } ),
                   expect_errors = True )
    WaitUntilCompleterServerReady( app, 'cpp' )

    response = app.get( '/signature_help_available',
                        { 'subserver': 'cpp' } ).json
    assert_that( response, SignatureAvailableMatcher( 'YES' ) )


  @IsolatedYcmd( { 'disable_signature_help': 1 } )
  def test_Signature_Help_Available_Disabled_By_User( self, app, *args ):
    request = { 'filepath' : PathToTestFile( 'goto.cc' ) }
    app.post_json( '/event_notification',
                   CombineRequest( request, {
                     'event_name': 'FileReadyToParse',
                     'filetype': 'cpp'
                   } ),
                   expect_errors = True )
    WaitUntilCompleterServerReady( app, 'cpp' )

    response = app.get( '/signature_help_available',
                        { 'subserver': 'cpp' } ).json
    assert_that( response, SignatureAvailableMatcher( 'NO' ) )
