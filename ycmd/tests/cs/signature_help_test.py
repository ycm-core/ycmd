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
                       has_entries,
                       has_items )
from unittest.mock import patch
from unittest import TestCase
from ycmd import handlers
from ycmd.utils import ReadFile, LOGGER
from ycmd.tests.cs import setUpModule, tearDownModule # noqa
from ycmd.tests.cs import ( PathToTestFile, # noqa
                            IsolatedYcmd,
                            SharedYcmd,
                            WrapOmniSharpServer )
from ycmd.tests.test_utils import ( BuildRequest,
                                    ParameterMatcher,
                                    SignatureMatcher,
                                    SignatureAvailableMatcher,
                                    CompletionEntryMatcher )


class SignatureHelpTest( TestCase ):
  @SharedYcmd
  def test_Signature_Help_Available( self, app ):
    response = app.get( '/signature_help_available',
                        { 'subserver': 'cs' } ).json
    assert_that( response, SignatureAvailableMatcher( 'YES' ) )


  @SharedYcmd
  def test_Signature_Help_Available_Server_Not_Ready( self, app ):
    completer = handlers._server_state.GetFiletypeCompleter( [ 'cs' ] )
    with patch.object( completer, 'ServerIsHealthy', return_value = False ):
      response = app.get( '/signature_help_available',
                          { 'subserver': 'cs' } ).json
      assert_that( response, SignatureAvailableMatcher( 'PENDING' ) )


  @SharedYcmd
  def test_SignatureHelp_TriggerComma( self, app ):
    filepath = PathToTestFile( 'testy', 'ContinuousTest.cs' )
    contents = ReadFile( filepath )
    request = BuildRequest(
      line_num = 17,
      column_num = 16,
      filetypes = [ 'cs' ],
      filepath = filepath,
      contents = contents )
    with WrapOmniSharpServer( app, filepath ):
      response = app.post_json( '/signature_help', request ).json
      LOGGER.debug( 'response = %s', response )
      assert_that( response, has_entries( {
        'errors': empty(),
        'signature_help': has_entries( {
          'activeSignature': 0,
          'activeParameter': 1,
          'signatures': contains_exactly(
            SignatureMatcher( 'void ContinuousTest.MultiArg(int i, string s)',
                              [ ParameterMatcher( 29, 34 ),
                                ParameterMatcher( 36, 44 ) ] )
          )
        } )
      } ) )


  @SharedYcmd
  def test_SignatureHelp_TriggerParen( self, app ):
    filepath = PathToTestFile( 'testy', 'ContinuousTest.cs' )
    contents = ReadFile( filepath )
    request = BuildRequest(
      line_num = 10,
      column_num = 9,
      filetypes = [ 'cs' ],
      filepath = filepath,
      contents = contents )
    with WrapOmniSharpServer( app, filepath ):
      response = app.post_json( '/signature_help', request ).json
      LOGGER.debug( 'response = %s', response )
      assert_that( response, has_entries( {
        'errors': empty(),
        'signature_help': has_entries( {
          'activeSignature': 0,
          'activeParameter': 0,
          'signatures': contains_exactly(
            SignatureMatcher( 'void ContinuousTest.Main(string[] args)',
                              [ ParameterMatcher( 25, 38 ) ] )
          )
        } )
      } ) )


  @IsolatedYcmd( { 'disable_signature_help': True } )
  def test_SignatureHelp_TriggerParen_Disabled( self, app ):
    filepath = PathToTestFile( 'testy', 'ContinuousTest.cs' )
    contents = ReadFile( filepath )
    request = BuildRequest(
      line_num = 10,
      column_num = 9,
      filetypes = [ 'cs' ],
      filepath = filepath,
      contents = contents )
    with WrapOmniSharpServer( app, filepath ):
      response = app.post_json( '/signature_help', request ).json
      LOGGER.debug( 'response = %s', response )
      assert_that( response, has_entries( {
        'errors': empty(),
        'signature_help': has_entries( {
          'activeSignature': 0,
          'activeParameter': 0,
          'signatures': empty()
        } )
      } ) )


  @SharedYcmd
  def test_SignatureHelp_MultipleSignatures( self, app ):
    filepath = PathToTestFile( 'testy', 'ContinuousTest.cs' )
    contents = ReadFile( filepath )
    request = BuildRequest(
      line_num = 18,
      column_num = 15,
      filetypes = [ 'cs' ],
      filepath = filepath,
      contents = contents )
    with WrapOmniSharpServer( app, filepath ):
      response = app.post_json( '/signature_help', request ).json
      LOGGER.debug( 'response = %s', response )
      assert_that( response, has_entries( {
        'errors': empty(),
        'signature_help': has_entries( {
          'activeSignature': 0,
          'activeParameter': 0,
          'signatures': contains_exactly(
            SignatureMatcher( 'void ContinuousTest.Overloaded(int i, int a)',
                              [ ParameterMatcher( 31, 36 ),
                                ParameterMatcher( 38, 43 ) ] ),
            SignatureMatcher( 'void ContinuousTest.Overloaded(string s)',
                              [ ParameterMatcher( 31, 39 ) ] ),
          )
        } )
      } ) )
    request[ 'column_num' ] = 20
    with WrapOmniSharpServer( app, filepath ):
      response = app.post_json( '/signature_help', request ).json
      LOGGER.debug( 'response = %s', response )
      assert_that( response, has_entries( {
        'errors': empty(),
        'signature_help': has_entries( {
          'activeSignature': 0,
          'activeParameter': 1,
          'signatures': contains_exactly(
            SignatureMatcher( 'void ContinuousTest.Overloaded(int i, int a)',
                              [ ParameterMatcher( 31, 36 ),
                                ParameterMatcher( 38, 43 ) ] ),
            SignatureMatcher( 'void ContinuousTest.Overloaded(string s)',
                              [ ParameterMatcher( 31, 39 ) ] ),
          )
        } )
      } ) )


  @SharedYcmd
  def test_SignatureHelp_NotAFunction_NoError( self, app ):
    filepath = PathToTestFile( 'testy', 'ContinuousTest.cs' )
    contents = ReadFile( filepath )
    request = BuildRequest(
      line_num = 19,
      column_num = 7,
      filetypes = [ 'cs' ],
      filepath = filepath,
      contents = contents )
    with WrapOmniSharpServer( app, filepath ):
      response = app.post_json( '/signature_help', request ).json
      LOGGER.debug( 'response = %s', response )
      assert_that( response, has_entries( {
        'errors': empty(),
        'signature_help': has_entries( {
          'activeSignature': 0,
          'activeParameter': 0,
          'signatures': empty()
        } )
      } ) )


  @IsolatedYcmd( { 'disable_signature_help': True } )
  def test_GetCompletions_Basic_NoSigHelp( self, app ):
    filepath = PathToTestFile( 'testy', 'Program.cs' )
    with WrapOmniSharpServer( app, filepath ):
      contents = ReadFile( filepath )

      completion_data = BuildRequest( filepath = filepath,
                                      filetype = 'cs',
                                      contents = contents,
                                      line_num = 10,
                                      column_num = 12 )
      response_data = app.post_json( '/completions', completion_data ).json
      print( 'Response: ', response_data )
      assert_that(
        response_data,
        has_entries( {
          'completion_start_column': 12,
          'completions': has_items(
            CompletionEntryMatcher( 'CursorLeft',
                                    'CursorLeft',
                                    { 'kind': 'Property' } ),
            CompletionEntryMatcher( 'CursorSize',
                                    'CursorSize',
                                    { 'kind': 'Property' } ),
          ),
          'errors': empty(),
        } ) )
