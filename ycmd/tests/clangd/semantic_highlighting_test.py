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
from unittest import TestCase
from hamcrest import assert_that, contains, empty, equal_to, has_entries

from ycmd.tests.clangd import setUpModule, tearDownModule # noqa
from ycmd.tests.clangd import PathToTestFile, SharedYcmd, IsolatedYcmd
from ycmd.tests.test_utils import ( BuildRequest,
                                    CombineRequest,
                                    RangeMatcher,
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
  response = app.post_json( '/semantic_tokens',
                            BuildRequest( **request ),
                            expect_errors = True )

  assert_that( response.status_code,
               equal_to( test[ 'expect' ][ 'response' ] ) )

  print( f'Completer response: { json.dumps( response.json, indent = 2 ) }' )

  assert_that( response.json, test[ 'expect' ][ 'data' ] )


class SignatureHelpTest( TestCase ):
  @IsolatedYcmd
  def test_none( self, app ):
    RunTest( app, {
      'request': {
        'filetype': 'cpp',
        'filepath': PathToTestFile( 'tokens.manual.cpp' ),
        'contents': ''
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'errors': empty(),
          'semantic_tokens': has_entries( {
            'tokens': empty()
          } ),
        } )
      },
    } )


  @SharedYcmd
  def test_basic( self, app ):
    RunTest( app, {
      'request': {
        'filetype'  : 'cpp',
        'filepath'  : PathToTestFile( 'tokens.manual.cpp' ),
        'contents': '#define MACRO( x, y ) do { ( x ) = ( y ); } while (0)'
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'errors': empty(),
          'semantic_tokens': has_entries( {
            'tokens': contains(
              has_entries( {
                'range': RangeMatcher( PathToTestFile( 'tokens.manual.cpp' ),
                                       ( 1, 9 ),
                                       ( 1, 14 ) ),
                'type': 'macro',
                'modifiers': contains( 'declaration', 'globalScope' )
              } )
            )
          } ),
        } )
      },
    } )


  @SharedYcmd
  def test_multiple( self, app ):
    RunTest( app, {
      'request': {
        'filetype'  : 'cpp',
        'filepath'  : PathToTestFile( 'tokens.manual.cpp' ),
        'contents':
            '#define MACRO( x, y ) ( x );\n\nnamespace Test {}'
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'errors': empty(),
          'semantic_tokens': has_entries( {
            'tokens': contains(
              has_entries( {
                'range': RangeMatcher( PathToTestFile( 'tokens.manual.cpp' ),
                                       ( 1, 9 ),
                                       ( 1, 14 ) ),
                'type': 'macro',
                'modifiers': contains( 'declaration', 'globalScope' )
              } ),
              has_entries( {
                'range': RangeMatcher( PathToTestFile( 'tokens.manual.cpp' ),
                                       ( 3, 11 ),
                                       ( 3, 15 ) ),
                'type': 'namespace',
                'modifiers': contains( 'declaration', 'globalScope' )
              } )
            )
          } ),
        } )
      },
    } )
