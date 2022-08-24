# Copyright (C) 2022 ycmd contributors
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
from hamcrest import assert_that, is_not, empty, equal_to, has_entries

from ycmd.tests.go import setUpModule, tearDownModule # noqa
from ycmd.tests.go import PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import ( BuildRequest,
                                    CombineRequest,
                                    WaitUntilCompleterServerReady )
from ycmd.utils import ReadFile


def RunTest( app, test ):
  """
  Method to run a simple completion test and verify the result

  test is a dictionary containing:
    'request': kwargs for BuildRequest
    'expect': {
       'response': server response code (e.g. requests.codes.ok)
       'data': matcher for the server response json
    }
  """

  request = test[ 'request' ]
  filetype = request.get( 'filetype', 'go' )
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
  @SharedYcmd
  def test_none( self, app ):
    RunTest( app, {
      'request': {
        'filetype': 'go',
        'filepath': PathToTestFile( 'thing.go' )
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'errors': empty(),
          'semantic_tokens': is_not( empty() )
        } )
      },
    } )
