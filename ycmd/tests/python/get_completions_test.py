#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 ycmd contributors.
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
from hamcrest import ( assert_that, has_item, has_items, has_entry,
                       has_entries, contains, empty, contains_string )
from python_handlers_test import Python_Handlers_test
import httplib


class Python_GetCompletions_test( Python_Handlers_test ):

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
                                         } ) )


    # We ignore errors here and we check the response code ourself.
    # This is to allow testing of requests returning errors.
    response = self._app.post_json( '/completions',
                                    CombineRequest( test[ 'request' ], {
                                      'contents': contents
                                    } ),
                                    expect_errors = True )

    eq_( response.status_code, test[ 'expect' ][ 'response' ] )

    assert_that( response.json, test[ 'expect' ][ 'data' ] )


  def Basic_test( self ):
    filepath = self._PathToTestFile( 'basic.py' )
    completion_data = self._BuildRequest( filepath = filepath,
                                          filetype = 'python',
                                          contents = open( filepath ).read(),
                                          line_num = 7,
                                          column_num = 3)

    results = self._app.post_json( '/completions',
                                   completion_data ).json[ 'completions' ]

    assert_that( results,
                 has_items(
                   self._CompletionEntryMatcher( 'a' ),
                   self._CompletionEntryMatcher( 'b' ),
                   self._CompletionLocationMatcher( 'line_num', 3 ),
                   self._CompletionLocationMatcher( 'line_num', 4 ),
                   self._CompletionLocationMatcher( 'column_num', 10 ),
                   self._CompletionLocationMatcher( 'filepath', filepath ) ) )


  def UnicodeDescription_test( self ):
    filepath = self._PathToTestFile( 'unicode.py' )
    completion_data = self._BuildRequest( filepath = filepath,
                                          filetype = 'python',
                                          contents = open( filepath ).read(),
                                          force_semantic = True,
                                          line_num = 5,
                                          column_num = 3)

    results = self._app.post_json( '/completions',
                                   completion_data ).json[ 'completions' ]
    assert_that( results, has_item(
      has_entry( 'detailed_info', contains_string( u'aafäö' ) ) ) )


  def NoSuggestions_Fallback_test( self ):
    # Python completer doesn't raise NO_COMPLETIONS_MESSAGE, so this is a
    # different code path to the Clang completer cases

    # TESTCASE2 (general_fallback/lang_python.py)
    self._RunTest( {
      'description': 'param jedi does not know about (id). query="a_p"',
      'request': {
        'filetype'  : 'python',
        'filepath'  : self._PathToTestFile( 'general_fallback',
                                            'lang_python.py' ),
        'line_num'  : 28,
        'column_num': 20,
        'force_semantic': False,
      },
      'expect': {
        'response': httplib.OK,
        'data': has_entries( {
          'completions': contains(
            self._CompletionEntryMatcher( 'a_parameter', '[ID]' ),
            self._CompletionEntryMatcher( 'another_parameter', '[ID]' ),
          ),
          'errors': empty(),
        } )
      },
    } )
