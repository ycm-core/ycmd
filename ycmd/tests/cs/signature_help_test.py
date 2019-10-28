# coding: utf-8
#
# Copyright (C) 2019 ycmd contributors
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

from hamcrest import ( assert_that,
                       contains,
                       empty,
                       has_entries )
from mock import patch
from ycmd import handlers
from ycmd.utils import ReadFile, LOGGER
from ycmd.tests.cs import PathToTestFile, SharedYcmd, WrapOmniSharpServer
from ycmd.tests.test_utils import ( BuildRequest,
                                    ParameterMatcher,
                                    SignatureMatcher,
                                    SignatureAvailableMatcher )


@SharedYcmd
def Signature_Help_Available_test( app ):
  response = app.get( '/signature_help_available',
                      { 'subserver': 'cs' } ).json
  assert_that( response, SignatureAvailableMatcher( 'YES' ) )


@SharedYcmd
def Signature_Help_Available_Server_Not_Ready_test( app ):
  completer = handlers._server_state.GetFiletypeCompleter( [ 'cs' ] )
  with patch.object( completer, 'ServerIsHealthy', return_value = False ):
    response = app.get( '/signature_help_available',
                        { 'subserver': 'cs' } ).json
    assert_that( response, SignatureAvailableMatcher( 'PENDING' ) )


@SharedYcmd
def SignatureHelp_TriggerComma_test( app ):
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
        'signatures': contains(
          SignatureMatcher( 'void ContinuousTest.MultiArg(int i, string s)',
                            [ ParameterMatcher( 29, 34 ),
                              ParameterMatcher( 36, 44 ) ] )
        )
      } )
    } ) )


@SharedYcmd
def SignatureHelp_TriggerParen_test( app ):
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
        'signatures': contains(
          SignatureMatcher( 'void ContinuousTest.Main(string[] args)',
                            [ ParameterMatcher( 25, 38 ) ] )
        )
      } )
    } ) )


@SharedYcmd
def SignatureHelp_MultipleSignatures_test( app ):
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
        'signatures': contains(
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
        'signatures': contains(
          SignatureMatcher( 'void ContinuousTest.Overloaded(int i, int a)',
                            [ ParameterMatcher( 31, 36 ),
                              ParameterMatcher( 38, 43 ) ] ),
          SignatureMatcher( 'void ContinuousTest.Overloaded(string s)',
                            [ ParameterMatcher( 31, 39 ) ] ),
        )
      } )
    } ) )


@SharedYcmd
def SignatureHelp_NotAFunction_NoError_test( app ):
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
