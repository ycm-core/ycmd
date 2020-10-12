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

import pprint
import requests
from hamcrest import assert_that, equal_to, has_entries, has_item
from ycmd.tests.javascriptreact import PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import CombineRequest
from ycmd.utils import ReadFile


def RunTest( app, test ):
  contents = ReadFile( test[ 'request' ][ 'filepath' ] )
  filetype = test[ 'request' ].get( 'filetype', 'javascriptreact' )
  app.post_json(
    '/event_notification',
    CombineRequest( test[ 'request' ], {
      'contents': contents,
      'filetype': filetype,
      'event_name': 'BufferVisit'
    } )
  )

  response = app.post_json(
    '/completions',
    CombineRequest( test[ 'request' ], {
      'contents': contents,
      'filetype': 'javascriptreact',
      'force_semantic': True
    } )
  )

  print( f'completer response: { pprint.pformat( response.json ) }' )

  assert_that( response.status_code,
               equal_to( test[ 'expect' ][ 'response' ] ) )

  assert_that( response.json, test[ 'expect' ][ 'data' ] )


@SharedYcmd
def GetCompletions_JavaScriptReact_DefaultTriggers_test( app ):
  filepath = PathToTestFile( 'test.jsx' )
  RunTest( app, {
    'description': 'No need to force after a semantic trigger',
    'request': {
      'line_num': 7,
      'column_num': 12,
      'filepath': filepath,
      'filetype': 'javascriptreact'
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': has_item( has_entries( {
          'insertion_text':  'alinkColor',
          'extra_menu_info': '(property) Document.alinkColor: string',
          'detailed_info':   '(property) Document.alinkColor: string',
          'kind':            'property',
        } ) )
      } )
    }
  } )


def Dummy_test():
  # Workaround for https://github.com/pytest-dev/pytest-rerunfailures/issues/51
  assert True
