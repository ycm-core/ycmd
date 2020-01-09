# Copyright (C) 2018-2020 ycmd contributors
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

from hamcrest import assert_that, equal_to


from ycmd.tests.clangd.conftest import * # noqa
from ycmd.tests.test_utils import ( CombineRequest,
                                    WaitUntilCompleterServerReady )
from ycmd.utils import ReadFile

shared_app = None


def RunAfterInitialized( app, test ):
  """Performs initialization of clangd server for the file contents specified in
  the |test| and optionally can run a test and check for its response.
  Since LSP servers do not start until initialization we need to send a
  FileReadyToParse request prior to any other request we will make.

  |test| consists of two parts a 'request' to be made and an optional 'expect'
  to perform a check on server's response.
  Request part must contain either a 'content' or 'filepath' element which
  either contains or points to the source code that will be sent to the server.
  In addition to that, if |test| also contain a 'route' element, then a
  follow-up request will be made to the server, with the same file contents and
  response of that request will be returned.
  Expect part, if specified, must contain two elements named 'response' and
  'data' which are used to check status code and data of the result received
  from server before returning them to the caller.

  Example usage:
    filepath = PathToTestFile( 'foo.cc' )
    request = { 'filepath': filepath,
                'filetype': 'cpp' }

    test = { 'request': request }
    RunAfterInitialized( app, test )
    ...
  """
  request = test[ 'request' ]
  contents = ( request[ 'contents' ] if 'contents' in request else
               ReadFile( request[ 'filepath' ] ) )
  response = app.post_json( '/event_notification',
                 CombineRequest( request, {
                   'event_name': 'FileReadyToParse',
                   'contents': contents,
                 } ),
                 expect_errors = True )
  WaitUntilCompleterServerReady( app, 'cpp' )

  if 'route' in test:
    expect_errors = 'expect' in test
    response = app.post_json( test[ 'route' ],
                              CombineRequest( request, {
                                'contents': contents
                              } ),
                              expect_errors = expect_errors )

  if 'expect' in test:
    print( "Completer response: {}".format( json.dumps( response.json,
                                                        indent = 2 ) ) )
    assert_that( response.status_code,
                 equal_to( test[ 'expect' ][ 'response' ] ) )
    assert_that( response.json, test[ 'expect' ][ 'data' ] )
  return response.json
