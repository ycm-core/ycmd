# encoding: utf-8
#
# Copyright (C) 2015-2018 ycmd contributors
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

import json
import requests
from hamcrest import ( assert_that,
                       contains,
                       equal_to,
                       has_entries,
                       has_items )
from mock import patch
from nose.tools import eq_
from os import path as p

from ycmd.completers.language_server.language_server_completer import (
  ResponseFailedException
)
from ycmd.tests.language_server import IsolatedYcmd, PathToTestFile
from ycmd.tests.test_utils import ( BuildRequest,
                                    CompletionEntryMatcher,
                                    ErrorMatcher,
                                    LocationMatcher,
                                    RangeMatcher,
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
  eq_( response.status_code, 200 )
  print( 'Completer response: {}'.format( json.dumps(
    response.json, indent = 2 ) ) )
  assert_that( response.json, has_entries( {
    'completions': contains(
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
  eq_( response.status_code, requests.codes.internal_server_error )

  assert_that( response.json, ErrorMatcher( ResponseFailedException,
    'Request failed: -32601: Unhandled method textDocument/hover' ) )


@IsolatedYcmd( { 'language_server':
  [ { 'name': 'foo',
      'filetypes': [ 'foo' ],
      'cmdline': [ 'node', PATH_TO_GENERIC_COMPLETER, '--stdio' ] } ] } )
@patch( 'ycmd.completers.language_server.generic_lsp_completer.'
        'GenericLSPCompleter.GetHoverResponse', return_value = 'asd' )
def GenericLSPCompleter_Hover_HasResponse_test( app, *args ):
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
  eq_( response, {
    'message': 'asd'
  } )
