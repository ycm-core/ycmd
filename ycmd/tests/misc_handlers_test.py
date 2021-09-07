# Copyright (C) 2015-2021 ycmd contributors
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

from hamcrest import ( any_of, assert_that, contains_exactly, empty, equal_to,
                       has_entries, instance_of )
from unittest.mock import patch
from unittest import TestCase
import requests

from ycmd.tests import IsolatedYcmd, PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import ( BuildRequest,
                                    DummyCompleter,
                                    PatchCompleter,
                                    SignatureAvailableMatcher,
                                    ErrorMatcher )


class MiscHandlersTest( TestCase ):
  @SharedYcmd
  def test_MiscHandlers_Healthy( self, app ):
    assert_that( app.get( '/healthy' ).json, equal_to( True ) )


  @SharedYcmd
  def test_MiscHandlers_Healthy_Subserver( self, app ):
    with PatchCompleter( DummyCompleter, filetype = 'dummy_filetype' ):
      assert_that( app.get( '/healthy',
                            { 'subserver': 'dummy_filetype' } ).json,
                   equal_to( True ) )


  @SharedYcmd
  def test_MiscHandlers_SignatureHelpAvailable( self, app ):
    response = app.get( '/signature_help_available', expect_errors = True ).json
    assert_that( response,
                 ErrorMatcher( RuntimeError, 'Subserver not specified' ) )


  @SharedYcmd
  def test_MiscHandlers_SignatureHelpAvailable_Subserver( self, app ):
    with PatchCompleter( DummyCompleter, filetype = 'dummy_filetype' ):
      assert_that( app.get( '/signature_help_available',
                            { 'subserver': 'dummy_filetype' } ).json,
                   SignatureAvailableMatcher( 'NO' ) )


  @SharedYcmd
  def test_MiscHandlers_SignatureHelpAvailable_NoSemanticCompleter( self, app ):
    assert_that( app.get( '/signature_help_available',
                          { 'subserver': 'dummy_filetype' } ).json,
                 SignatureAvailableMatcher( 'NO' ) )


  @SharedYcmd
  def test_MiscHandlers_Ready( self, app ):
    assert_that( app.get( '/ready' ).json, equal_to( True ) )


  @SharedYcmd
  def test_MiscHandlers_Ready_Subserver( self, app ):
    with PatchCompleter( DummyCompleter, filetype = 'dummy_filetype' ):
      assert_that( app.get( '/ready', { 'subserver': 'dummy_filetype' } ).json,
                   equal_to( True ) )


  @SharedYcmd
  def test_MiscHandlers_SemanticCompletionAvailable( self, app ):
    with PatchCompleter( DummyCompleter, filetype = 'dummy_filetype' ):
      request_data = BuildRequest( filetype = 'dummy_filetype' )
      assert_that( app.post_json( '/semantic_completion_available',
                                  request_data ).json,
                   equal_to( True ) )


  @SharedYcmd
  def test_MiscHandlers_EventNotification_AlwaysJsonResponse( self, app ):
    event_data = BuildRequest( contents = 'foo foogoo ba',
                               event_name = 'FileReadyToParse' )

    assert_that( app.post_json( '/event_notification', event_data ).json,
                 empty() )


  @SharedYcmd
  def test_MiscHandlers_EventNotification_ReturnJsonOnBigFileError( self, app ):
    # We generate a content greater than Bottle.MEMFILE_MAX (10MB)
    contents = "foo " * 5000000
    event_data = BuildRequest( contents = contents,
                               event_name = 'FileReadyToParse' )

    response = app.post_json( '/event_notification',
                              event_data,
                              expect_errors = True )
    assert_that( response.status_code,
                 equal_to( requests.codes.request_entity_too_large ) )
    assert_that( response.json,
                 has_entries( { 'traceback': None,
                                'message': 'None',
                                'exception': None } ) )


  @SharedYcmd
  def test_MiscHandlers_FilterAndSortCandidates_Basic( self, app ):
    candidate1 = { 'prop1': 'aoo', 'prop2': 'bar' }
    candidate2 = { 'prop1': 'bfo', 'prop2': 'zoo' }
    candidate3 = { 'prop1': 'cfo', 'prop2': 'moo' }

    data = {
      'candidates': [ candidate3, candidate1, candidate2 ],
      'sort_property': 'prop1',
      'query': 'fo'
    }

    response_data = app.post_json( '/filter_and_sort_candidates', data ).json

    assert_that( response_data, contains_exactly( candidate2, candidate3 ) )


  @SharedYcmd
  def test_MiscHandlers_LoadExtraConfFile_AlwaysJsonResponse( self, app ):
    filepath = PathToTestFile( 'extra_conf', 'project', '.ycm_extra_conf.py' )
    extra_conf_data = BuildRequest( filepath = filepath )

    assert_that( app.post_json( '/load_extra_conf_file', extra_conf_data ).json,
                 equal_to( True ) )


  @SharedYcmd
  def test_MiscHandlers_IgnoreExtraConfFile_AlwaysJsonResponse( self, app ):
    filepath = PathToTestFile( 'extra_conf', 'project', '.ycm_extra_conf.py' )
    extra_conf_data = BuildRequest( filepath = filepath )

    assert_that( app.post_json( '/ignore_extra_conf_file',
                                extra_conf_data ).json,
                 equal_to( True ) )


  @IsolatedYcmd()
  def test_MiscHandlers_DebugInfo_ExtraConfLoaded( self, app ):
    filepath = PathToTestFile( 'extra_conf', 'project', '.ycm_extra_conf.py' )
    app.post_json( '/load_extra_conf_file', { 'filepath': filepath } )

    request_data = BuildRequest( filepath = filepath )
    assert_that(
      app.post_json( '/debug_info', request_data ).json,
      has_entries( {
        'python': has_entries( {
          'executable': instance_of( str ),
          'version': instance_of( str ),
        } ),
        'clang': has_entries( {
          'has_support': instance_of( bool ),
          'version': any_of( None, instance_of( str ) )
        } ),
        'extra_conf': has_entries( {
          'path': instance_of( str ),
          'is_loaded': True
        } ),
        'completer': None
      } )
    )


  @SharedYcmd
  def test_MiscHandlers_DebugInfo_NoExtraConfFound( self, app ):
    request_data = BuildRequest()
    assert_that(
      app.post_json( '/debug_info', request_data ).json,
      has_entries( {
        'python': has_entries( {
          'executable': instance_of( str ),
          'version': instance_of( str ),
        } ),
        'clang': has_entries( {
          'has_support': instance_of( bool ),
          'version': any_of( None, instance_of( str ) )
        } ),
        'extra_conf': has_entries( {
          'path': None,
          'is_loaded': False
        } ),
        'completer': None
      } )
    )


  @IsolatedYcmd()
  def test_MiscHandlers_DebugInfo_ExtraConfFoundButNotLoaded( self, app ):
    filepath = PathToTestFile( 'extra_conf', 'project', '.ycm_extra_conf.py' )
    request_data = BuildRequest( filepath = filepath )
    assert_that(
      app.post_json( '/debug_info', request_data ).json,
      has_entries( {
        'python': has_entries( {
          'executable': instance_of( str ),
          'version': instance_of( str ),
        } ),
        'clang': has_entries( {
          'has_support': instance_of( bool ),
          'version': any_of( None, instance_of( str ) )
        } ),
        'extra_conf': has_entries( {
          'path': instance_of( str ),
          'is_loaded': False
        } ),
        'completer': None
      } )
    )


  @SharedYcmd
  def test_MiscHandlers_ReceiveMessages_NoCompleter( self, app ):
    request_data = BuildRequest()
    assert_that( app.post_json( '/receive_messages', request_data ).json,
                 equal_to( False ) )


  @SharedYcmd
  def test_MiscHandlers_ReceiveMessages_NotSupportedByCompleter( self, app ):
    with PatchCompleter( DummyCompleter, filetype = 'dummy_filetype' ):
      request_data = BuildRequest( filetype = 'dummy_filetype' )
      assert_that( app.post_json( '/receive_messages', request_data ).json,
                   equal_to( False ) )


  @SharedYcmd
  @patch( 'ycmd.completers.completer.Completer.ShouldUseSignatureHelpNow',
          return_value = True )
  def test_MiscHandlers_SignatureHelp_DefaultEmptyResponse( self, app, *args ):
    with PatchCompleter( DummyCompleter, filetype = 'dummy_filetype' ):
      request_data = BuildRequest( filetype = 'dummy_filetype' )
      response = app.post_json( '/signature_help', request_data ).json
      assert_that( response, has_entries( {
        'signature_help': has_entries( {
          'activeSignature': 0,
          'activeParameter': 0,
          'signatures': empty()
        } ),
        'errors': empty()
      } ) )


  @SharedYcmd
  @patch( 'ycmd.completers.completer.Completer.ComputeSignatures',
          side_effect = RuntimeError )
  def test_MiscHandlers_SignatureHelp_ComputeSignatureThrows(
      self, app, *args ):
    with PatchCompleter( DummyCompleter, filetype = 'dummy_filetype' ):
      request_data = BuildRequest( filetype = 'dummy_filetype' )
      response = app.post_json( '/signature_help', request_data ).json
      print( response )
      assert_that( response, has_entries( {
        'signature_help': has_entries( {
          'activeSignature': 0,
          'activeParameter': 0,
          'signatures': empty()
        } ),
        'errors': contains_exactly(
          ErrorMatcher( RuntimeError, '' )
        )
      } ) )
