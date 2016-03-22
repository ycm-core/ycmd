# Copyright (C) 2015 ycmd contributors
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
from future import standard_library
standard_library.install_aliases()
from builtins import *  # noqa

from hamcrest import ( assert_that, contains, contains_inanyorder, empty,
                       has_entries )
from nose.tools import eq_
from pprint import pformat
import http.client

from ycmd.tests.javascript import PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import BuildRequest, CompletionEntryMatcher
from ycmd.utils import ReadFile

# The following properties/methods are in Object.prototype, so are present
# on all objects:
#
# toString()
# toLocaleString()
# valueOf()
# hasOwnProperty()
# propertyIsEnumerable()
# isPrototypeOf()


def RunTest( app, test ):
  """
  Method to run a simple completion test and verify the result

  test is a dictionary containing:
    'request': kwargs for BuildRequest
    'expect': {
       'response': server response code (e.g. httplib.OK)
       'data': matcher for the server response json
    }
  """

  contents = ReadFile( test[ 'request' ][ 'filepath' ] )

  def CombineRequest( request, data ):
    kw = request
    request.update( data )
    return BuildRequest( **kw )

  app.post_json( '/event_notification',
                 CombineRequest( test[ 'request' ], {
                                 'event_name': 'FileReadyToParse',
                                 'contents': contents,
                                 } ),
                 expect_errors = True )

  # We ignore errors here and we check the response code ourself.
  # This is to allow testing of requests returning errors.
  response = app.post_json( '/completions',
                            CombineRequest( test[ 'request' ], {
                              'contents': contents
                            } ),
                            expect_errors = True )

  print( 'completer response: {0}'.format( pformat( response.json ) ) )

  eq_( response.status_code, test[ 'expect' ][ 'response' ] )

  assert_that( response.json, test[ 'expect' ][ 'data' ] )


@SharedYcmd
def GetCompletions_NoQuery_test( app ):
  RunTest( app, {
    'description': 'semantic completion works for simple object no query',
    'request': {
      'filetype'  : 'javascript',
      'filepath'  : PathToTestFile( 'simple_test.js' ),
      'line_num'  : 13,
      'column_num': 43,
    },
    'expect': {
      'response': http.client.OK,
      'data': has_entries( {
        'completions': contains_inanyorder(
          CompletionEntryMatcher( 'a_simple_function',
                                  'fn(param: ?) -> string' ),
          CompletionEntryMatcher( 'basic_type', 'number' ),
          CompletionEntryMatcher( 'object', 'object' ),
          CompletionEntryMatcher( 'toString', 'fn() -> string' ),
          CompletionEntryMatcher( 'toLocaleString', 'fn() -> string' ),
          CompletionEntryMatcher( 'valueOf', 'fn() -> number' ),
          CompletionEntryMatcher( 'hasOwnProperty',
                                  'fn(prop: string) -> bool' ),
          CompletionEntryMatcher( 'isPrototypeOf',
                                  'fn(obj: ?) -> bool' ),
          CompletionEntryMatcher( 'propertyIsEnumerable',
                                  'fn(prop: string) -> bool' ),
        ),
        'errors': empty(),
      } )
    },
  } )


@SharedYcmd
def GetCompletions_Query_test( app ):
  RunTest( app, {
    'description': 'semantic completion works for simple object with query',
    'request': {
      'filetype'  : 'javascript',
      'filepath'  : PathToTestFile( 'simple_test.js' ),
      'line_num'  : 14,
      'column_num': 45,
    },
    'expect': {
      'response': http.client.OK,
      'data': has_entries( {
        'completions': contains(
          CompletionEntryMatcher( 'basic_type', 'number' ),
          CompletionEntryMatcher( 'isPrototypeOf',
                                  'fn(obj: ?) -> bool' ),
        ),
        'errors': empty(),
      } )
    },
  } )


@SharedYcmd
def GetCompletions_Require_NoQuery_test( app ):
  RunTest( app, {
    'description': 'semantic completion works for simple object no query',
    'request': {
      'filetype'  : 'javascript',
      'filepath'  : PathToTestFile( 'requirejs_test.js' ),
      'line_num'  : 2,
      'column_num': 15,
    },
    'expect': {
      'response': http.client.OK,
      'data': has_entries( {
        'completions': contains_inanyorder(
          CompletionEntryMatcher( 'mine_bitcoin',
                                  'fn(how_much: ?) -> number' ),
          CompletionEntryMatcher( 'get_number', 'number' ),
          CompletionEntryMatcher( 'get_string', 'string' ),
          CompletionEntryMatcher( 'get_thing',
                                  'fn(a: ?) -> number|string' ),
          CompletionEntryMatcher( 'toString', 'fn() -> string' ),
          CompletionEntryMatcher( 'toLocaleString', 'fn() -> string' ),
          CompletionEntryMatcher( 'valueOf', 'fn() -> number' ),
          CompletionEntryMatcher( 'hasOwnProperty',
                                  'fn(prop: string) -> bool' ),
          CompletionEntryMatcher( 'isPrototypeOf',
                                  'fn(obj: ?) -> bool' ),
          CompletionEntryMatcher( 'propertyIsEnumerable',
                                  'fn(prop: string) -> bool' ),
        ),
        'errors': empty(),
      } )
    },
  } )


@SharedYcmd
def GetCompletions_Require_Query_test( app ):
  RunTest( app, {
    'description': 'semantic completion works for require object with query',
    'request': {
      'filetype'  : 'javascript',
      'filepath'  : PathToTestFile( 'requirejs_test.js' ),
      'line_num'  : 3,
      'column_num': 17,
    },
    'expect': {
      'response': http.client.OK,
      'data': has_entries( {
        'completions': contains(
          CompletionEntryMatcher( 'mine_bitcoin',
                                  'fn(how_much: ?) -> number' ),
        ),
        'errors': empty(),
      } )
    },
  } )


@SharedYcmd
def GetCompletions_Require_Query_LCS_test( app ):
  RunTest( app, {
    'description': ( 'completion works for require object '
                     'with query not prefix' ),
    'request': {
      'filetype'  : 'javascript',
      'filepath'  : PathToTestFile( 'requirejs_test.js' ),
      'line_num'  : 4,
      'column_num': 17,
    },
    'expect': {
      'response': http.client.OK,
      'data': has_entries( {
        'completions': contains(
          CompletionEntryMatcher( 'get_number', 'number' ),
          CompletionEntryMatcher( 'get_thing',
                                  'fn(a: ?) -> number|string' ),
          CompletionEntryMatcher( 'get_string', 'string' ),
        ),
        'errors': empty(),
      } )
    },
  } )


@SharedYcmd
def GetCompletions_DirtyNamedBuffers_test( app ):
  # This tests that when we have dirty buffers in our editor, tern actually
  # uses them correctly
  RunTest( app, {
    'description': ( 'completion works for require object '
                     'with query not prefix' ),
    'request': {
      'filetype'  : 'javascript',
      'filepath'  : PathToTestFile( 'requirejs_test.js' ),
      'line_num'  : 18,
      'column_num': 11,
      'file_data': {
        PathToTestFile( 'no_such_lib', 'no_such_file.js' ): {
          'contents': (
            'define( [], function() { return { big_endian_node: 1 } } )' ),
          'filetypes': [ 'javascript' ]
        }
      },
    },
    'expect': {
      'response': http.client.OK,
      'data': has_entries( {
        'completions': contains_inanyorder(
          CompletionEntryMatcher( 'big_endian_node', 'number' ),
          CompletionEntryMatcher( 'toString', 'fn() -> string' ),
          CompletionEntryMatcher( 'toLocaleString', 'fn() -> string' ),
          CompletionEntryMatcher( 'valueOf', 'fn() -> number' ),
          CompletionEntryMatcher( 'hasOwnProperty',
                                  'fn(prop: string) -> bool' ),
          CompletionEntryMatcher( 'isPrototypeOf',
                                  'fn(obj: ?) -> bool' ),
          CompletionEntryMatcher( 'propertyIsEnumerable',
                                  'fn(prop: string) -> bool' ),
        ),
        'errors': empty(),
      } )
    },
  } )


@SharedYcmd
def GetCompletions_ReturnsDocsInCompletions_test( app ):
  # This tests that we supply docs for completions
  RunTest( app, {
    'description': 'completions supply docs',
    'request': {
      'filetype'  : 'javascript',
      'filepath'  : PathToTestFile( 'requirejs_test.js' ),
      'line_num'  : 8,
      'column_num': 15,
    },
    'expect': {
      'response': http.client.OK,
      'data': has_entries( {
        'completions': contains_inanyorder(
          CompletionEntryMatcher(
            'a_function',
            'fn(bar: ?) -> {a_value: string}', extra_params = {
              'doc_string': 'This is a short documentation string',
            } ),
          CompletionEntryMatcher( 'options', 'options' ),
          CompletionEntryMatcher( 'toString', 'fn() -> string' ),
          CompletionEntryMatcher( 'toLocaleString', 'fn() -> string' ),
          CompletionEntryMatcher( 'valueOf', 'fn() -> number' ),
          CompletionEntryMatcher( 'hasOwnProperty',
                                  'fn(prop: string) -> bool' ),
          CompletionEntryMatcher( 'isPrototypeOf',
                                  'fn(obj: ?) -> bool' ),
          CompletionEntryMatcher( 'propertyIsEnumerable',
                                  'fn(prop: string) -> bool' ),
        ),
        'errors': empty(),
      } )
    },
  } )
