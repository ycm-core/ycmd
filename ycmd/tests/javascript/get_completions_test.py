# encoding: utf-8
#
# Copyright (C) 2018 ycmd contributors
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
                       contains_inanyorder,
                       has_entries,
                       has_item,
                       matches_regexp )
from nose.tools import eq_
import pprint
import requests

from ycmd.tests.javascript import IsolatedYcmd, PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import ( BuildRequest, ChunkMatcher,
                                    CompletionEntryMatcher, LocationMatcher )
from ycmd.utils import ReadFile


def RunTest( app, test ):
  contents = ReadFile( test[ 'request' ][ 'filepath' ] )

  def CombineRequest( request, data ):
    kw = request
    request.update( data )
    return BuildRequest( **kw )

  app.post_json(
    '/event_notification',
    CombineRequest( test[ 'request' ], {
      'contents': contents,
      'filetype': 'javascript',
      'event_name': 'BufferVisit'
    } )
  )

  response = app.post_json(
    '/completions',
    CombineRequest( test[ 'request' ], {
      'contents': contents,
      'filetype': 'javascript',
      'force_semantic': True
    } )
  )

  print( 'completer response: {0}'.format( pprint.pformat( response.json ) ) )

  eq_( response.status_code, test[ 'expect' ][ 'response' ] )

  assert_that( response.json, test[ 'expect' ][ 'data' ] )


@SharedYcmd
def GetCompletions_Basic_test( app ):
  RunTest( app, {
    'description': 'Extra and detailed info when completions are methods',
    'request': {
      'line_num': 14,
      'column_num': 6,
      'filepath': PathToTestFile( 'test.js' )
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': contains_inanyorder(
          CompletionEntryMatcher(
            'methodA',
            '(method) Foo.methodA(): void',
            extra_params = {
              'kind': 'method',
              'detailed_info': '(method) Foo.methodA(): void\n\n'
                               'Unicode string: 说话'
            }
          ),
          CompletionEntryMatcher(
            'methodB',
            '(method) Foo.methodB(): void',
            extra_params = {
              'kind': 'method',
              'detailed_info': '(method) Foo.methodB(): void'
            }
          ),
          CompletionEntryMatcher(
            'methodC',
            '(method) Foo.methodC(foo: any, bar: any): void',
            extra_params = {
              'kind': 'method',
              'detailed_info': '(method) Foo.methodC(foo: any, bar: any): void'
            }
          )
        )
      } )
    }
  } )


@SharedYcmd
def GetCompletions_Keyword_test( app ):
  RunTest( app, {
    'description': 'No extra and detailed info when completion is a keyword',
    'request': {
      'line_num': 1,
      'column_num': 5,
      'filepath': PathToTestFile( 'test.js' ),
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': has_item( {
          'insertion_text': 'class',
          'kind':           'keyword',
          'extra_data':     {}
        } )
      } )
    }
  } )


@SharedYcmd
def GetCompletions_AutoImport_test( app ):
  filepath = PathToTestFile( 'test.js' )
  RunTest( app, {
    'description': 'Symbol from external module can be completed and '
                   'its completion contains fixits to automatically import it',
    'request': {
      'line_num': 36,
      'column_num': 5,
      'filepath': filepath,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': has_item( has_entries( {
          'insertion_text':  'Bår',
          'extra_menu_info': 'class Bår',
          'detailed_info':   'class Bår',
          'kind':            'class',
          'extra_data': has_entries( {
            'fixits': contains_inanyorder(
              has_entries( {
                'text': 'Import \'Bår\' from module "./unicode"',
                'chunks': contains(
                  ChunkMatcher(
                    matches_regexp( '^import { Bår } from "./unicode";\r?\n'
                                    '\r?\n' ),
                    LocationMatcher( filepath, 1, 1 ),
                    LocationMatcher( filepath, 1, 1 )
                  )
                ),
                'location': LocationMatcher( filepath, 36, 5 )
              } )
            )
          } )
        } ) )
      } )
    }
  } )


@IsolatedYcmd
def GetCompletions_IgnoreIdentifiers_test( app ):
  RunTest( app, {
    'description': 'Identifier "test" is not returned as a suggestion',
    'request': {
      'line_num': 5,
      'column_num': 6,
      'filepath': PathToTestFile( 'identifier', 'test.js' ),
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': contains(
          CompletionEntryMatcher(
            'foo',
            '(property) foo: string',
            extra_params = {
              'kind': 'property',
              'detailed_info': '(property) foo: string'
            }
          )
        )
      } )
    }
  } )
