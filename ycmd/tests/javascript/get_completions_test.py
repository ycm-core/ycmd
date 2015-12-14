#
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

from nose.tools import eq_
from hamcrest import ( assert_that, contains, contains_inanyorder, empty,
                       has_entries )
from javascript_handlers_test import Javascript_Handlers_test
from pprint import pformat
import httplib

# The following properties/methods are in Object.prototype, so are present
# on all objects:
#
# toString()
# toLocaleString()
# valueOf()
# hasOwnProperty()
# propertyIsEnumerable()
# isPrototypeOf()


class Javascript_GetCompletions_test( Javascript_Handlers_test ):

  def _RunTest( self, test ):
    """
    Method to run a simple completion test and verify the result

    test is a dictionary containing:
      'request': kwargs for BuildRequest
      'expect': {
         'response': server response code (e.g. httplib.OK)
         'data': matcher for the server response json
      }
    """

    contents = open( test[ 'request' ][ 'filepath' ] ).read()

    def CombineRequest( request, data ):
      kw = request
      request.update( data )
      return self._BuildRequest( **kw )

    self._app.post_json( '/event_notification',
                         CombineRequest( test[ 'request' ], {
                                         'event_name': 'FileReadyToParse',
                                         'contents': contents,
                                         } ),
                         expect_errors = True )

    # We ignore errors here and we check the response code ourself.
    # This is to allow testing of requests returning errors.
    response = self._app.post_json( '/completions',
                                    CombineRequest( test[ 'request' ], {
                                      'contents': contents
                                    } ),
                                    expect_errors = True )

    print( 'completer response: {0}'.format( pformat( response.json ) ) )

    eq_( response.status_code, test[ 'expect' ][ 'response' ] )

    assert_that( response.json, test[ 'expect' ][ 'data' ] )


  def NoQuery_test( self ):
    self._RunTest( {
      'description': 'semantic completion works for simple object no query',
      'request': {
        'filetype'  : 'javascript',
        'filepath'  : self._PathToTestFile( 'simple_test.js' ),
        'line_num'  : 13,
        'column_num': 43,
      },
      'expect': {
        'response': httplib.OK,
        'data': has_entries( {
          'completions': contains_inanyorder(
            self._CompletionEntryMatcher( 'a_simple_function',
                                          'fn(param: ?) -> string' ),
            self._CompletionEntryMatcher( 'basic_type', 'number' ),
            self._CompletionEntryMatcher( 'object', 'object' ),
            self._CompletionEntryMatcher( 'toString', 'fn() -> string' ),
            self._CompletionEntryMatcher( 'toLocaleString', 'fn() -> string' ),
            self._CompletionEntryMatcher( 'valueOf', 'fn() -> number' ),
            self._CompletionEntryMatcher( 'hasOwnProperty',
                                          'fn(prop: string) -> bool' ),
            self._CompletionEntryMatcher( 'isPrototypeOf',
                                          'fn(obj: ?) -> bool' ),
            self._CompletionEntryMatcher( 'propertyIsEnumerable',
                                          'fn(prop: string) -> bool' ),
          ),
          'errors': empty(),
        } )
      },
    } )


  def Query_test( self ):
    self._RunTest( {
      'description': 'semantic completion works for simple object with query',
      'request': {
        'filetype'  : 'javascript',
        'filepath'  : self._PathToTestFile( 'simple_test.js' ),
        'line_num'  : 14,
        'column_num': 45,
      },
      'expect': {
        'response': httplib.OK,
        'data': has_entries( {
          'completions': contains(
            self._CompletionEntryMatcher( 'basic_type', 'number' ),
            self._CompletionEntryMatcher( 'isPrototypeOf',
                                          'fn(obj: ?) -> bool' ),
          ),
          'errors': empty(),
        } )
      },
    } )


  def Require_NoQuery_test( self ):
    self._RunTest( {
      'description': 'semantic completion works for simple object no query',
      'request': {
        'filetype'  : 'javascript',
        'filepath'  : self._PathToTestFile( 'requirejs_test.js' ),
        'line_num'  : 2,
        'column_num': 15,
      },
      'expect': {
        'response': httplib.OK,
        'data': has_entries( {
          'completions': contains_inanyorder(
            self._CompletionEntryMatcher( 'mine_bitcoin',
                                          'fn(how_much: ?) -> number' ),
            self._CompletionEntryMatcher( 'get_number', 'number' ),
            self._CompletionEntryMatcher( 'get_string', 'string' ),
            self._CompletionEntryMatcher( 'get_thing',
                                          'fn(a: ?) -> number|string' ),
            self._CompletionEntryMatcher( 'toString', 'fn() -> string' ),
            self._CompletionEntryMatcher( 'toLocaleString', 'fn() -> string' ),
            self._CompletionEntryMatcher( 'valueOf', 'fn() -> number' ),
            self._CompletionEntryMatcher( 'hasOwnProperty',
                                          'fn(prop: string) -> bool' ),
            self._CompletionEntryMatcher( 'isPrototypeOf',
                                          'fn(obj: ?) -> bool' ),
            self._CompletionEntryMatcher( 'propertyIsEnumerable',
                                          'fn(prop: string) -> bool' ),
          ),
          'errors': empty(),
        } )
      },
    } )


  def Require_Query_test( self ):
    self._RunTest( {
      'description': 'semantic completion works for require object with query',
      'request': {
        'filetype'  : 'javascript',
        'filepath'  : self._PathToTestFile( 'requirejs_test.js' ),
        'line_num'  : 3,
        'column_num': 17,
      },
      'expect': {
        'response': httplib.OK,
        'data': has_entries( {
          'completions': contains(
            self._CompletionEntryMatcher( 'mine_bitcoin',
                                          'fn(how_much: ?) -> number' ),
          ),
          'errors': empty(),
        } )
      },
    } )


  def Require_Query_LCS_test( self ):
    self._RunTest( {
      'description': ( 'completion works for require object '
                       'with query not prefix' ),
      'request': {
        'filetype'  : 'javascript',
        'filepath'  : self._PathToTestFile( 'requirejs_test.js' ),
        'line_num'  : 4,
        'column_num': 17,
      },
      'expect': {
        'response': httplib.OK,
        'data': has_entries( {
          'completions': contains(
            self._CompletionEntryMatcher( 'get_number', 'number' ),
            self._CompletionEntryMatcher( 'get_thing',
                                          'fn(a: ?) -> number|string' ),
            self._CompletionEntryMatcher( 'get_string', 'string' ),
          ),
          'errors': empty(),
        } )
      },
    } )


  def DirtyNamedBuffers_test( self ):
    # This tests that when we have dirty buffers in our editor, tern actually
    # uses them correctly
    self._RunTest( {
      'description': ( 'completion works for require object '
                       'with query not prefix' ),
      'request': {
        'filetype'  : 'javascript',
        'filepath'  : self._PathToTestFile( 'requirejs_test.js' ),
        'line_num'  : 18,
        'column_num': 11,
        'file_data': {
          self._PathToTestFile( 'no_such_lib', 'no_such_file.js' ): {
            'contents': (
              'define( [], function() { return { big_endian_node: 1 } } )' ),
            'filetypes': [ 'javascript' ]
          }
        },
      },
      'expect': {
        'response': httplib.OK,
        'data': has_entries( {
          'completions': contains_inanyorder(
            self._CompletionEntryMatcher( 'big_endian_node', 'number' ),
            self._CompletionEntryMatcher( 'toString', 'fn() -> string' ),
            self._CompletionEntryMatcher( 'toLocaleString', 'fn() -> string' ),
            self._CompletionEntryMatcher( 'valueOf', 'fn() -> number' ),
            self._CompletionEntryMatcher( 'hasOwnProperty',
                                          'fn(prop: string) -> bool' ),
            self._CompletionEntryMatcher( 'isPrototypeOf',
                                          'fn(obj: ?) -> bool' ),
            self._CompletionEntryMatcher( 'propertyIsEnumerable',
                                          'fn(prop: string) -> bool' ),
          ),
          'errors': empty(),
        } )
      },
    } )


  def ReturnsDocsInCompletions_test( self ):
    # This tests that we supply docs for completions
    self._RunTest( {
      'description': 'completions supply docs',
      'request': {
        'filetype'  : 'javascript',
        'filepath'  : self._PathToTestFile( 'requirejs_test.js' ),
        'line_num'  : 8,
        'column_num': 15,
      },
      'expect': {
        'response': httplib.OK,
        'data': has_entries( {
          'completions': contains_inanyorder(
            self._CompletionEntryMatcher(
              'a_function',
              'fn(bar: ?) -> {a_value: string}', {
                'detailed_info': ( 'fn(bar: ?) -> {a_value: string}\n'
                                   'This is a short documentation string'),
              } ),
            self._CompletionEntryMatcher( 'options', 'options' ),
            self._CompletionEntryMatcher( 'toString', 'fn() -> string' ),
            self._CompletionEntryMatcher( 'toLocaleString', 'fn() -> string' ),
            self._CompletionEntryMatcher( 'valueOf', 'fn() -> number' ),
            self._CompletionEntryMatcher( 'hasOwnProperty',
                                          'fn(prop: string) -> bool' ),
            self._CompletionEntryMatcher( 'isPrototypeOf',
                                          'fn(obj: ?) -> bool' ),
            self._CompletionEntryMatcher( 'propertyIsEnumerable',
                                          'fn(prop: string) -> bool' ),
          ),
          'errors': empty(),
        } )
      },
    } )
