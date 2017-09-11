# Copyright (C) 2017 ycmd contributors
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

from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import division
# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa

from hamcrest import ( assert_that, contains, has_entries )
from nose.tools import eq_

from ycmd.tests.java import ( PathToTestFile, SharedYcmd, DEFAULT_PROJECT_DIR )
from ycmd.tests.test_utils import ( BuildRequest )
from ycmd.utils import ReadFile

import time
from pprint import pformat


# TODO: Replace with ChunkMatcher, LocationMatcher, etc.
def PositionMatch( line, column ):
  return has_entries( {
    'line_num': line,
    'column_num': column
  } )


def RangeMatch( start, end ):
  return has_entries( {
    'start': PositionMatch( *start ),
    'end': PositionMatch( *end ),
  } )


def Merge( request, data ):
  kw = dict( request )
  kw.update( data )
  return kw


def PollForMessages( app, request_data, drain=True ):
  expiration = time.time() + 5
  while True:
    if time.time() > expiration:
      raise RuntimeError( 'Waited for diagnostics to be ready for '
                          '10 seconds, aborting.' )

    response = app.post_json( '/receive_messages', BuildRequest( **Merge ( {
      'filetype'  : 'java',
      'line_num'  : 1,
      'column_num': 1,
    }, request_data ) ) ).json

    print( 'poll response: {0}'.format( pformat( response ) ) )

    if isinstance( response, bool ):
      if not response:
        raise RuntimeError( 'The message poll was aborted by the server' )
      elif drain:
        return
    elif isinstance( response, list ):
      for message in response:
        yield message
    else:
      raise AssertionError( 'Message poll response was wrong type' )

    time.sleep( 0.25 )


@SharedYcmd
def FileReadyToParse_Diagnostics_Simple_test( app ):
  filepath = PathToTestFile( DEFAULT_PROJECT_DIR,
                             'src',
                             'com',
                             'test',
                             'TestFactory.java' )
  contents = ReadFile( filepath )

  # During server initialisation, jdtls reads the project files off the disk.
  # This means that when the test module initialised (waiting for the /ready
  # response), we actually already handled the messages, so they should be in
  # the diagnostics cache.
  event_data = BuildRequest( event_name = 'FileReadyToParse',
                             contents = contents,
                             filepath = filepath,
                             filetype = 'java' )

  results = app.post_json( '/event_notification', event_data ).json

  print( 'completer response: {0}'.format( pformat( results ) ) )

  assert_that(
    results,
    contains(
      has_entries( {
        'kind': 'WARNING',
        'text': 'The value of the field TestFactory.Bar.testString is not used',
        'location': PositionMatch( 15, 19 ),
        'location_extent': RangeMatch( ( 15, 19 ), ( 15, 29 ) ),
        'ranges': contains( RangeMatch( ( 15, 19 ), ( 15, 29 ) ) ),
        'fixit_available': False
      } ),
      has_entries( {
        'kind': 'ERROR',
        'text': 'Wibble cannot be resolved to a type',
        'location': PositionMatch( 18, 24 ),
        'location_extent': RangeMatch( ( 18, 24 ), ( 18, 30 ) ),
        'ranges': contains( RangeMatch( ( 18, 24 ), ( 18, 30 ) ) ),
        'fixit_available': False
      } ),
      has_entries( {
        'kind': 'ERROR',
        'text': 'Wibble cannot be resolved to a variable',
        'location': PositionMatch( 19, 15 ),
        'location_extent': RangeMatch( ( 19, 15 ), ( 19, 21 ) ),
        'ranges': contains( RangeMatch( ( 19, 15 ), ( 19, 21 ) ) ),
        'fixit_available': False
      } ),
      has_entries( {
        'kind': 'ERROR',
        'text': 'Type mismatch: cannot convert from int to boolean',
        'location': PositionMatch( 27, 10 ),
        'location_extent': RangeMatch( ( 27, 10 ), ( 27, 16 ) ),
        'ranges': contains( RangeMatch( ( 27, 10 ), ( 27, 16 ) ) ),
        'fixit_available': False
      } ),
    )
  )


@SharedYcmd
def FileReadyToParse_Diagnostics_FileNotOnDisk_test( app ):
  contents = '''
    package com.test;
    class Test {
      public String test
    }
  '''
  filepath = PathToTestFile( DEFAULT_PROJECT_DIR,
                             'src',
                             'com',
                             'test',
                             'Test.java' )

  # During server initialisation, jdtls reads the project files off the disk.
  # This means that when the test module initialised (waiting for the /ready
  # response), we actually already handled the messages, so they should be in
  # the diagnostics cache.
  event_data = BuildRequest( event_name = 'FileReadyToParse',
                             contents = contents,
                             filepath = filepath,
                             filetype = 'java' )

  results = app.post_json( '/event_notification', event_data ).json

  # This is a new file, so the diagnostics can't possibly be available.
  eq_( results, {} )

  diag_matcher = contains( has_entries( {
    'kind': 'ERROR',
    'text': 'Syntax error, insert ";" to complete ClassBodyDeclarations',
    'location': PositionMatch( 4, 21 ),
    'location_extent': RangeMatch( ( 4, 21 ), ( 4, 25 ) ),
    'ranges': contains( RangeMatch( ( 4, 21 ), ( 4, 25 ) ) ),
    'fixit_available': False
  } ) )

  # Poll until we receive the diags asynchronously
  for message in PollForMessages( app,
                                  { 'filepath': filepath,
                                    'contents': contents },
                                  drain=True ):
    print( 'Message {0}'.format( pformat( message ) ) )
    if 'diagnostics' in message:
      assert_that( message, has_entries( {
        'diagnostics': diag_matcher
      } ) )
      break

  # Now confirm that we _also_ get these from the FileReadyToParse request
  results = app.post_json( '/event_notification', event_data ).json
  print( 'completer response: {0}'.format( pformat( results ) ) )

  assert_that( results, diag_matcher )
