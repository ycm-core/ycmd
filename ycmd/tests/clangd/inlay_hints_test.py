# Copyright (C) 2024 ycmd contributors
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
from ycmd.tests.clangd import PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import ( BuildRequest,
                                    CombineRequest,
                                    LocationMatcher,
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
  response = app.post_json( '/inlay_hints',
                            BuildRequest( **request ),
                            expect_errors = True )

  assert_that( response.status_code,
               equal_to( test[ 'expect' ][ 'response' ] ) )

  print( f'Completer response: { json.dumps( response.json, indent = 2 ) }' )

  assert_that( response.json, test[ 'expect' ][ 'data' ] )


class SignatureHelpTest( TestCase ):
  @SharedYcmd
  def test_none( self, app ):
    filepath = PathToTestFile( 'template.cc' )
    RunTest( app, {
      'request': {
        'filetype': 'cpp',
        'filepath': filepath,
        'range': {
          'start': {
            'line_num': 0,
            'column_num': 0,
            'filepath': filepath
          },
          'end': {
            'line_num': 2,
            'column_num': 0,
            'filepath': filepath
          },
        }
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'errors': empty(),
          'inlay_hints': empty(),
        } )
      },
    } )


  @SharedYcmd
  def test_basic( self, app ):
    filepath = PathToTestFile( 'inlay_hints_basic.cpp' )
    RunTest( app, {
      'request': {
        'filetype'  : 'cpp',
        'filepath': filepath,
        'range': {
          'start': {
            'line_num': 0,
            'column_num': 0,
            'filepath': filepath
          },
          'end': {
            'line_num': 2,
            'column_num': 0,
            'filepath': filepath
          },
        }
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'errors': empty(),
          'inlay_hints': contains(
            has_entries( {
              'kind': 'Parameter',
              'position': LocationMatcher( filepath, 2, 16 ),
              'label': 'b:'
            } ),
          ),
        } )
      },
    } )


  @SharedYcmd
  def test_multiple( self, app ):
    filepath = PathToTestFile( 'inlay_hints_multiple.cpp' )
    RunTest( app, {
      'request': {
        'filetype'  : 'cpp',
        'filepath': filepath,
        'range': {
          'start': {
            'line_num': 0,
            'column_num': 0,
            'filepath': filepath
          },
          'end': {
            'line_num': 2,
            'column_num': 0,
            'filepath': filepath
          },
        }
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'errors': empty(),
          'inlay_hints': contains(
            has_entries( {
              'kind': 'Parameter',
              'position': LocationMatcher( filepath, 2, 16 ),
              'label': 'a:'
            } ),
            has_entries( {
              'kind': 'Parameter',
              'position': LocationMatcher( filepath, 2, 19 ),
              'label': 'b:'
            } )
          ),
        } )
      },
    } )
