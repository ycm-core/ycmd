# coding: utf-8
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

from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from future import standard_library
standard_library.install_aliases()
from builtins import *  # noqa

from nose.tools import eq_
from hamcrest import ( assert_that, has_item, has_items, has_entry,
                       has_entries, contains, empty, contains_string )
import requests

from ycmd.utils import ReadFile
from ycmd.tests.python import PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import ( BuildRequest, CompletionEntryMatcher,
                                    CompletionLocationMatcher )


@SharedYcmd
def GetCompletions_Basic_test( app ):
  filepath = PathToTestFile( 'basic.py' )
  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'python',
                                  contents = ReadFile( filepath ),
                                  line_num = 7,
                                  column_num = 3)

  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]

  assert_that( results,
               has_items(
                 CompletionEntryMatcher( 'a' ),
                 CompletionEntryMatcher( 'b' ),
                 CompletionLocationMatcher( 'line_num', 3 ),
                 CompletionLocationMatcher( 'line_num', 4 ),
                 CompletionLocationMatcher( 'column_num', 10 ),
                 CompletionLocationMatcher( 'filepath', filepath ) ) )


@SharedYcmd
def GetCompletions_UnicodeDescription_test( app ):
  filepath = PathToTestFile( 'unicode.py' )
  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'python',
                                  contents = ReadFile( filepath ),
                                  force_semantic = True,
                                  line_num = 5,
                                  column_num = 3)

  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]
  assert_that( results, has_item(
    has_entry( 'detailed_info', contains_string( u'aafäö' ) ) ) )


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
                                 } ) )

  # We ignore errors here and we check the response code ourself.
  # This is to allow testing of requests returning errors.
  response = app.post_json( '/completions',
                            CombineRequest( test[ 'request' ], {
                              'contents': contents
                            } ),
                            expect_errors = True )

  eq_( response.status_code, test[ 'expect' ][ 'response' ] )

  assert_that( response.json, test[ 'expect' ][ 'data' ] )


@SharedYcmd
def GetCompletions_NoSuggestions_Fallback_test( app ):
  # Python completer doesn't raise NO_COMPLETIONS_MESSAGE, so this is a
  # different code path to the Clang completer cases

  # TESTCASE2 (general_fallback/lang_python.py)
  RunTest( app, {
    'description': 'param jedi does not know about (id). query="a_p"',
    'request': {
      'filetype'  : 'python',
      'filepath'  : PathToTestFile( 'general_fallback',
                                    'lang_python.py' ),
      'line_num'  : 28,
      'column_num': 20,
      'force_semantic': False,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': contains(
          CompletionEntryMatcher( 'a_parameter', '[ID]' ),
          CompletionEntryMatcher( 'another_parameter', '[ID]' ),
        ),
        'errors': empty(),
      } )
    },
  } )


@SharedYcmd
def GetCompletions_Unicode_InLine_test( app ):
  RunTest( app, {
    'description': 'return completions for strings with multi-byte chars',
    'request': {
      'filetype'  : 'python',
      'filepath'  : PathToTestFile( 'unicode.py' ),
      'line_num'  : 7,
      'column_num': 14
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': contains(
          CompletionEntryMatcher( 'center', 'function: builtins.str.center' )
        ),
        'errors': empty(),
      } )
    },
  } )
