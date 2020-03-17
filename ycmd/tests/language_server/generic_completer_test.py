# Copyright (C) 2015-2020 ycmd contributors
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
from hamcrest import ( assert_that,
                       contains_exactly,
                       empty,
                       equal_to,
                       has_entries,
                       has_entry,
                       has_items,
                       instance_of )
from unittest.mock import patch
from os import path as p

from ycmd.completers.language_server.language_server_completer import (
  ResponseFailedException
)
from ycmd import handlers
from ycmd.tests.language_server import IsolatedYcmd, PathToTestFile
from ycmd.tests.test_utils import ( BuildRequest,
                                    CompletionEntryMatcher,
                                    ErrorMatcher,
                                    LocationMatcher,
                                    RangeMatcher,
                                    SignatureAvailableMatcher,
                                    WaitUntilCompleterServerReady )
from ycmd.utils import ReadFile

DIR_OF_THIS_SCRIPT = p.dirname( p.abspath( __file__ ) )
PATH_TO_GENERIC_COMPLETER = p.join( DIR_OF_THIS_SCRIPT,
                                    '..',
                                    '..',
                                    '..',
                                    'third_party',
                                    'generic_server',
                                    'out',
                                    'server.js' )
TEST_FILE = PathToTestFile( 'generic_server', 'test_file' )
TEST_FILE_CONTENT = ReadFile( TEST_FILE )


@IsolatedYcmd( { 'language_server':
  [ { 'name': 'foo',
      'filetypes': [ 'foo' ],
      'cmdline': [ 'node', PATH_TO_GENERIC_COMPLETER, '--stdio' ] } ] } )
def GenericLSPCompleter_GetCompletions_NotACompletionProvider_test( app ):
  completer = handlers._server_state.GetFiletypeCompleter( [ 'foo' ] )
  with patch.object( completer, '_is_completion_provider', False ):
    request = BuildRequest( filepath = TEST_FILE,
                          filetype = 'foo',
                          line_num = 1,
                          column_num = 3,
                          contents = 'Java',
                          event_name = 'FileReadyToParse' )
    app.post_json( '/event_notification', request )
    WaitUntilCompleterServerReady( app, 'foo' )
    request.pop( 'event_name' )
    response = app.post_json( '/completions', BuildRequest( **request ) )
    assert_that( response.json, has_entries( { 'completions': contains_exactly(
      CompletionEntryMatcher( 'Java', '[ID]' ) ) } ) )


@IsolatedYcmd( { 'semantic_triggers': { 'foo': [ 're!.' ] },
  'language_server':
  [ { 'name': 'foo',
      'filetypes': [ 'foo' ],
      'cmdline': [ 'node', PATH_TO_GENERIC_COMPLETER, '--stdio' ] } ] } )
def GenericLSPCompleter_GetCompletions_FilteredNoForce_test( app ):
  request = BuildRequest( filepath = TEST_FILE,
                          filetype = 'foo',
                          line_num = 1,
                          column_num = 3,
                          contents = 'Java',
                          event_name = 'FileReadyToParse' )
  app.post_json( '/event_notification', request )
  WaitUntilCompleterServerReady( app, 'foo' )
  request.pop( 'event_name' )
  response = app.post_json( '/completions', BuildRequest( **request ) )
  assert_that( response.status_code, equal_to( 200 ) )
  print( 'Completer response: {}'.format( json.dumps(
    response.json, indent = 2 ) ) )
  assert_that( response.json, has_entries( {
    'completions': contains_exactly(
      CompletionEntryMatcher( 'JavaScript', 'JavaScript details' ),
    )
  } ) )


@IsolatedYcmd( { 'language_server':
  [ { 'name': 'foo',
      'filetypes': [ 'foo' ],
      'cmdline': [ 'node', PATH_TO_GENERIC_COMPLETER, '--stdio' ] } ] } )
def GenericLSPCompleter_GetCompletions_test( app ):
  request = BuildRequest( filepath = TEST_FILE,
                          filetype = 'foo',
                          line_num = 1,
                          column_num = 1,
                          contents = TEST_FILE_CONTENT,
                          event_name = 'FileReadyToParse' )
  app.post_json( '/event_notification', request )
  WaitUntilCompleterServerReady( app, 'foo' )
  request[ 'force_semantic' ] = True
  request.pop( 'event_name' )
  response = app.post_json( '/completions', BuildRequest( **request ) )
  assert_that( response.status_code, equal_to( 200 ) )
  print( 'Completer response: {}'.format( json.dumps(
    response.json, indent = 2 ) ) )
  assert_that( response.json, has_entries( {
    'completions': contains_exactly(
      CompletionEntryMatcher( 'JavaScript', 'JavaScript details' ),
      CompletionEntryMatcher( 'TypeScript', 'TypeScript details' ),
    )
  } ) )


@IsolatedYcmd( { 'language_server':
  [ { 'name': 'foo',
      'filetypes': [ 'foo' ],
      'cmdline': [ 'node', PATH_TO_GENERIC_COMPLETER, '--stdio' ] } ] } )
def GenericLSPCompleter_Diagnostics_test( app ):
  request = BuildRequest( filepath = TEST_FILE,
                          filetype = 'foo',
                          line_num = 1,
                          column_num = 1,
                          contents = TEST_FILE_CONTENT,
                          event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', request )
  WaitUntilCompleterServerReady( app, 'foo' )
  request.pop( 'event_name' )
  response = app.post_json( '/receive_messages', request )
  assert_that( response.json, has_items(
    has_entries( { 'diagnostics': has_items(
      has_entries( {
        'kind': equal_to( 'WARNING' ),
        'location': LocationMatcher( TEST_FILE, 2, 1 ),
        'location_extent': RangeMatcher( TEST_FILE, ( 2, 1 ), ( 2, 4 ) ),
        'text': equal_to( 'FOO is all uppercase.' ),
        'fixit_available': False
      } )
    ) } )
  ) )


@IsolatedYcmd( { 'language_server':
  [ { 'name': 'foo',
      'filetypes': [ 'foo' ],
      'cmdline': [ 'node', PATH_TO_GENERIC_COMPLETER, '--stdio' ] } ] } )
def GenericLSPCompleter_Hover_RequestFails_test( app ):
  request = BuildRequest( filepath = TEST_FILE,
                          filetype = 'foo',
                          line_num = 1,
                          column_num = 1,
                          contents = TEST_FILE_CONTENT,
                          event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', request )
  WaitUntilCompleterServerReady( app, 'foo' )
  request.pop( 'event_name' )
  request[ 'command_arguments' ] = [ 'GetHover' ]
  response = app.post_json( '/run_completer_command',
                            request,
                            expect_errors = True )
  assert_that( response.status_code,
               equal_to( requests.codes.internal_server_error ) )

  assert_that( response.json, ErrorMatcher( ResponseFailedException,
    'Request failed: -32601: Unhandled method textDocument/hover' ) )


@IsolatedYcmd( { 'language_server':
  [ { 'name': 'foo',
      'filetypes': [ 'foo' ],
      'cmdline': [ 'node', PATH_TO_GENERIC_COMPLETER, '--stdio' ] } ] } )
@patch( 'ycmd.completers.language_server.generic_lsp_completer.'
        'GenericLSPCompleter.GetHoverResponse', return_value = 'asd' )
def GenericLSPCompleter_HoverIsString_test( get_hover, app ):
  request = BuildRequest( filepath = TEST_FILE,
                          filetype = 'foo',
                          line_num = 1,
                          column_num = 1,
                          contents = TEST_FILE_CONTENT,
                          event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', request )
  WaitUntilCompleterServerReady( app, 'foo' )
  request.pop( 'event_name' )
  request[ 'command_arguments' ] = [ 'GetHover' ]
  response = app.post_json( '/run_completer_command', request ).json
  assert_that( response, has_entry( 'detailed_info', 'asd' ) )


@IsolatedYcmd( { 'language_server':
  [ { 'name': 'foo',
      'filetypes': [ 'foo' ],
      'cmdline': [ 'node', PATH_TO_GENERIC_COMPLETER, '--stdio' ] } ] } )
@patch( 'ycmd.completers.language_server.generic_lsp_completer.'
        'GenericLSPCompleter.GetHoverResponse',
        return_value = { 'whatever': 'blah', 'value': 'asd' } )
def GenericLSPCompleter_HoverIsDict_test( get_hover, app ):
  request = BuildRequest( filepath = TEST_FILE,
                          filetype = 'foo',
                          line_num = 1,
                          column_num = 1,
                          contents = TEST_FILE_CONTENT,
                          event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', request )
  WaitUntilCompleterServerReady( app, 'foo' )
  request.pop( 'event_name' )
  request[ 'command_arguments' ] = [ 'GetHover' ]
  response = app.post_json( '/run_completer_command', request ).json
  assert_that( response, has_entry( 'detailed_info', 'asd' ) )


@IsolatedYcmd( { 'language_server':
  [ { 'name': 'foo',
      'filetypes': [ 'foo' ],
      'cmdline': [ 'node', PATH_TO_GENERIC_COMPLETER, '--stdio' ] } ] } )
@patch( 'ycmd.completers.language_server.generic_lsp_completer.'
        'GenericLSPCompleter.GetHoverResponse',
        return_value = [ { 'whatever': 'blah', 'value': 'asd' },
                         'qe',
                         { 'eh?': 'hover_sucks', 'value': 'yes, it does' } ] )
def GenericLSPCompleter_HoverIsList_test( get_hover, app ):
  request = BuildRequest( filepath = TEST_FILE,
                          filetype = 'foo',
                          line_num = 1,
                          column_num = 1,
                          contents = TEST_FILE_CONTENT,
                          event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', request )
  WaitUntilCompleterServerReady( app, 'foo' )
  request.pop( 'event_name' )
  request[ 'command_arguments' ] = [ 'GetHover' ]
  response = app.post_json( '/run_completer_command', request ).json
  assert_that( response, has_entry( 'detailed_info', 'asd\nqe\nyes, it does' ) )



@IsolatedYcmd( { 'language_server':
  [ { 'name': 'foo',
      'filetypes': [ 'foo' ],
      'project_root_files': [ 'proj_root' ],
      'cmdline': [ 'node', PATH_TO_GENERIC_COMPLETER, '--stdio' ] } ] } )
def GenericLSPCompleter_DebugInfo_CustomRoot_test( app, *args ):
  test_file = PathToTestFile(
      'generic_server', 'foo', 'bar', 'baz', 'test_file' )
  request = BuildRequest( filepath = test_file,
                          filetype = 'foo',
                          line_num = 1,
                          column_num = 1,
                          contents = '',
                          event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', request )
  WaitUntilCompleterServerReady( app, 'foo' )
  request.pop( 'event_name' )
  response = app.post_json( '/debug_info', request ).json
  assert_that(
    response,
    has_entry( 'completer', has_entries( {
      'name': 'GenericLSP',
      'servers': contains_exactly( has_entries( {
        'name': 'fooCompleter',
        'is_running': instance_of( bool ),
        'executable': contains_exactly( instance_of( str ),
                                instance_of( str ),
                                instance_of( str ) ),
        'address': None,
        'port': None,
        'pid': instance_of( int ),
        'logfiles': contains_exactly( instance_of( str ) ),
        'extras': contains_exactly(
          has_entries( {
            'key': 'Server State',
            'value': instance_of( str ),
          } ),
          has_entries( {
            'key': 'Project Directory',
            'value': PathToTestFile( 'generic_server', 'foo' ),
          } ),
          has_entries( {
            'key': 'Settings',
            'value': '{}'
          } ),
        )
      } ) ),
    } ) )
  )


@IsolatedYcmd( { 'language_server':
  [ { 'name': 'foo',
      'filetypes': [ 'foo' ],
      'project_root_files': [ 'proj_root' ],
      'cmdline': [ 'node', PATH_TO_GENERIC_COMPLETER, '--stdio' ] } ] } )
def GenericLSPCompleter_SignatureHelp_NoTriggers_test( app ):
  test_file = PathToTestFile(
      'generic_server', 'foo', 'bar', 'baz', 'test_file' )
  request = BuildRequest( filepath = test_file,
                          filetype = 'foo',
                          line_num = 1,
                          column_num = 1,
                          contents = '',
                          event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', request )
  WaitUntilCompleterServerReady( app, 'foo' )
  request.pop( 'event_name' )
  response = app.post_json( '/signature_help', request ).json
  assert_that( response, has_entries( {
    'signature_help': has_entries( {
      'activeSignature': 0,
      'activeParameter': 0,
      'signatures': empty()
    } ),
    'errors': empty()
  } ) )


@IsolatedYcmd( { 'language_server':
  [ { 'name': 'foo',
      'filetypes': [ 'foo' ],
      'project_root_files': [ 'proj_root' ],
      'cmdline': [ 'node', PATH_TO_GENERIC_COMPLETER, '--stdio' ] } ] } )
@patch( 'ycmd.completers.completer.Completer.ShouldUseSignatureHelpNow',
        return_value = True )
def GenericLSPCompleter_SignatureHelp_NotASigHelpProvider_test( should_use_sig,
                                                                app ):
  test_file = PathToTestFile(
      'generic_server', 'foo', 'bar', 'baz', 'test_file' )
  request = BuildRequest( filepath = test_file,
                          filetype = 'foo',
                          line_num = 1,
                          column_num = 1,
                          contents = '',
                          event_name = 'FileReadyToParse' )
  app.post_json( '/event_notification', request )
  WaitUntilCompleterServerReady( app, 'foo' )
  request.pop( 'event_name' )
  response = app.post_json( '/signature_help', request ).json
  assert_that( response, has_entries( {
    'signature_help': has_entries( {
      'activeSignature': 0,
      'activeParameter': 0,
      'signatures': empty()
    } ),
    'errors': empty()
  } ) )


@IsolatedYcmd( { 'language_server':
  [ { 'name': 'foo',
      'filetypes': [ 'foo' ],
      'project_root_files': [ 'proj_root' ],
      'cmdline': [ 'node', PATH_TO_GENERIC_COMPLETER, '--stdio' ] } ] } )
def GenericLSPCompleter_SignatureHelp_NotSupported_test( app ):
  test_file = PathToTestFile(
      'generic_server', 'foo', 'bar', 'baz', 'test_file' )
  app.post_json( '/event_notification',
                 BuildRequest( **{
                   'filepath': test_file,
                   'event_name': 'FileReadyToParse',
                   'filetype': 'foo'
                 } ),
                 expect_errors = True )
  WaitUntilCompleterServerReady( app, 'foo' )

  response = app.get( '/signature_help_available',
                      { 'subserver': 'foo' } ).json
  assert_that( response, SignatureAvailableMatcher( 'NO' ) )
