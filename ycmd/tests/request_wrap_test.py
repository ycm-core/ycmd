# coding: utf-8
#
# Copyright (C) 2014 Google Inc.
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

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa

from hamcrest import ( assert_that, calling, contains, empty, equal_to,
                       has_entry, has_string, matches_regexp, raises )
from nose.tools import eq_

from ycmd.utils import ToBytes
from ycmd.request_wrap import RequestWrap


def PrepareJson( contents = '',
                 line_num = 1,
                 column_num = 1,
                 filetype = '',
                 force_semantic = None,
                 extra_conf_data = None ):
  message = {
    'line_num': line_num,
    'column_num': column_num,
    'filepath': '/foo',
    'file_data': {
      '/foo': {
        'filetypes': [ filetype ],
        'contents': contents
      }
    }
  }
  if force_semantic is not None:
    message[ 'force_semantic' ] = force_semantic
  if extra_conf_data is not None:
    message[ 'extra_conf_data' ] = extra_conf_data

  return message


def Prefix_test():
  tests = [
    ( 'abc.def', 5, 'abc.' ),
    ( 'abc.def', 6, 'abc.' ),
    ( 'abc.def', 8, 'abc.' ),
    ( 'abc.def', 4, '' ),
    ( 'abc.', 5, 'abc.' ),
    ( 'abc.', 4, '' ),
    ( '', 1, '' ),
  ]

  def Test( line, col, prefix ):
    eq_( prefix,
         RequestWrap( PrepareJson( line_num = 1,
                                   contents = line,
                                   column_num = col ) )[ 'prefix' ] )

  for test in tests:
    yield Test, test[ 0 ], test[ 1 ], test[ 2 ]


def LineValue_OneLine_test():
  eq_( 'zoo',
       RequestWrap( PrepareJson( line_num = 1,
                                 contents = 'zoo' ) )[ 'line_value' ] )


def LineValue_LastLine_test():
  eq_( 'zoo',
       RequestWrap(
          PrepareJson( line_num = 3,
                       contents = 'goo\nbar\nzoo' ) )[ 'line_value' ] )


def LineValue_MiddleLine_test():
  eq_( 'zoo',
       RequestWrap(
          PrepareJson( line_num = 2,
                       contents = 'goo\nzoo\nbar' ) )[ 'line_value' ] )


def LineValue_WindowsLines_test():
  eq_( 'zoo',
       RequestWrap(
          PrepareJson( line_num = 3,
                       contents = 'goo\r\nbar\r\nzoo' ) )[ 'line_value' ] )


def LineValue_MixedFormatLines_test():
  eq_( 'zoo',
       RequestWrap(
          PrepareJson( line_num = 3,
                       contents = 'goo\nbar\r\nzoo' ) )[ 'line_value' ] )


def LineValue_EmptyContents_test():
  eq_( '',
       RequestWrap( PrepareJson( line_num = 1,
                                 contents = '' ) )[ 'line_value' ] )


def StartColumn_RightAfterDot_test():
  eq_( 5,
       RequestWrap( PrepareJson( column_num = 5,
                                 contents = 'foo.' ) )[ 'start_column' ] )


def StartColumn_Dot_test():
  eq_( 5,
       RequestWrap( PrepareJson( column_num = 8,
                                 contents = 'foo.bar' ) )[ 'start_column' ] )


def StartColumn_DotWithUnicode_test():
  eq_( 7,
       RequestWrap( PrepareJson( column_num = 11,
                                 contents = 'fäö.bär' ) )[ 'start_column' ] )


def StartColumn_UnicodeNotIdentifier_test():
  contents = "var x = '†es†ing'."

  # † not considered an identifier character

  for i in range( 13, 15 ):
    print( ToBytes( contents )[ i - 1 : i ] )
    eq_( 13,
         RequestWrap( PrepareJson( column_num = i,
                                   contents = contents ) )[ 'start_column' ] )

  eq_( 13,
       RequestWrap( PrepareJson( column_num = 15,
                                 contents = contents ) )[ 'start_column' ] )

  for i in range( 18, 20 ):
    print( ToBytes( contents )[ i - 1 : i ] )
    eq_( 18,
         RequestWrap( PrepareJson( column_num = i,
                                   contents = contents ) )[ 'start_column' ] )


def StartColumn_QueryIsUnicode_test():
  contents = "var x = ålpha.alphå"
  eq_( 16,
       RequestWrap( PrepareJson( column_num = 16,
                                 contents = contents ) )[ 'start_column' ] )
  eq_( 16,
       RequestWrap( PrepareJson( column_num = 19,
                                 contents = contents ) )[ 'start_column' ] )


def StartColumn_QueryStartsWithUnicode_test():
  contents = "var x = ålpha.ålpha"
  eq_( 16,
       RequestWrap( PrepareJson( column_num = 16,
                                 contents = contents ) )[ 'start_column' ] )
  eq_( 16,
       RequestWrap( PrepareJson( column_num = 19,
                                 contents = contents ) )[ 'start_column' ] )


def StartColumn_ThreeByteUnicode_test():
  contents = "var x = '†'."
  eq_( 15,
       RequestWrap( PrepareJson( column_num = 15,
                                 contents = contents ) )[ 'start_column' ] )


def StartColumn_Paren_test():
  eq_( 5,
       RequestWrap( PrepareJson( column_num = 8,
                                 contents = 'foo(bar' ) )[ 'start_column' ] )


def StartColumn_AfterWholeWord_test():
  eq_( 1,
       RequestWrap( PrepareJson( column_num = 7,
                                 contents = 'foobar' ) )[ 'start_column' ] )


def StartColumn_AfterWholeWord_Html_test():
  eq_( 1,
       RequestWrap( PrepareJson( column_num = 7,
                                 filetype = 'html',
                                 contents = 'fo-bar' ) )[ 'start_column' ] )


def StartColumn_AfterWholeUnicodeWord_test():
  eq_( 1,
       RequestWrap( PrepareJson( column_num = 6,
                                 contents = u'fäö' ) )[ 'start_column' ] )


def StartColumn_InMiddleOfWholeWord_test():
  eq_( 1,
       RequestWrap( PrepareJson( column_num = 4,
                                 contents = 'foobar' ) )[ 'start_column' ] )


def StartColumn_ColumnOne_test():
  eq_( 1,
       RequestWrap( PrepareJson( column_num = 1,
                                 contents = 'foobar' ) )[ 'start_column' ] )


def Query_AtWordEnd_test():
  eq_( 'foo',
       RequestWrap( PrepareJson( column_num = 4,
                                 contents = 'foo' ) )[ 'query' ] )


def Query_InWordMiddle_test():
  eq_( 'foo',
       RequestWrap( PrepareJson( column_num = 4,
                                 contents = 'foobar' ) )[ 'query' ] )


def Query_StartOfLine_test():
  eq_( '',
       RequestWrap( PrepareJson( column_num = 1,
                                 contents = 'foobar' ) )[ 'query' ] )


def Query_StopsAtParen_test():
  eq_( 'bar',
       RequestWrap( PrepareJson( column_num = 8,
                                 contents = 'foo(bar' ) )[ 'query' ] )


def Query_InWhiteSpace_test():
  eq_( '',
       RequestWrap( PrepareJson( column_num = 8,
                                 contents = 'foo       ' ) )[ 'query' ] )


def Query_UnicodeSinglecharInclusive_test():
  eq_( 'ø',
       RequestWrap( PrepareJson( column_num = 7,
                                 contents = 'abc.ø' ) )[ 'query' ] )


def Query_UnicodeSinglecharExclusive_test():
  eq_( '',
       RequestWrap( PrepareJson( column_num = 5,
                                 contents = 'abc.ø' ) )[ 'query' ] )


def StartColumn_Set_test():
  wrap = RequestWrap( PrepareJson( column_num = 11,
                                   contents = 'this \'test',
                                   filetype = 'javascript' ) )
  eq_( wrap[ 'start_column' ], 7 )
  eq_( wrap[ 'start_codepoint' ], 7 )
  eq_( wrap[ 'query' ], "test" )
  eq_( wrap[ 'prefix' ], "this '" )

  wrap[ 'start_column' ] = 6
  eq_( wrap[ 'start_column' ], 6 )
  eq_( wrap[ 'start_codepoint' ], 6 )
  eq_( wrap[ 'query' ], "'test" )
  eq_( wrap[ 'prefix' ], "this " )


def StartColumn_SetUnicode_test():
  wrap = RequestWrap( PrepareJson( column_num = 14,
                                   contents = '†eß† \'test',
                                   filetype = 'javascript' ) )
  eq_( 7,  wrap[ 'start_codepoint' ] )
  eq_( 12, wrap[ 'start_column' ] )
  eq_( wrap[ 'query' ], "te" )
  eq_( wrap[ 'prefix' ], "†eß† \'" )

  wrap[ 'start_column' ] = 11
  eq_( wrap[ 'start_column' ], 11 )
  eq_( wrap[ 'start_codepoint' ], 6 )
  eq_( wrap[ 'query' ], "'te" )
  eq_( wrap[ 'prefix' ], "†eß† " )


def StartCodepoint_Set_test():
  wrap = RequestWrap( PrepareJson( column_num = 11,
                                   contents = 'this \'test',
                                   filetype = 'javascript' ) )
  eq_( wrap[ 'start_column' ], 7 )
  eq_( wrap[ 'start_codepoint' ], 7 )
  eq_( wrap[ 'query' ], "test" )
  eq_( wrap[ 'prefix' ], "this '" )

  wrap[ 'start_codepoint' ] = 6
  eq_( wrap[ 'start_column' ], 6 )
  eq_( wrap[ 'start_codepoint' ], 6 )
  eq_( wrap[ 'query' ], "'test" )
  eq_( wrap[ 'prefix' ], "this " )


def StartCodepoint_SetUnicode_test():
  wrap = RequestWrap( PrepareJson( column_num = 14,
                                   contents = '†eß† \'test',
                                   filetype = 'javascript' ) )
  eq_( 7,  wrap[ 'start_codepoint' ] )
  eq_( 12, wrap[ 'start_column' ] )
  eq_( wrap[ 'query' ], "te" )
  eq_( wrap[ 'prefix' ], "†eß† \'" )

  wrap[ 'start_codepoint' ] = 6
  eq_( wrap[ 'start_column' ], 11 )
  eq_( wrap[ 'start_codepoint' ], 6 )
  eq_( wrap[ 'query' ], "'te" )
  eq_( wrap[ 'prefix' ], "†eß† " )


def Calculated_SetMethod_test():
  assert_that(
    calling( RequestWrap( PrepareJson() ).__setitem__ ).with_args(
      'line_value', '' ),
    raises( ValueError, 'Key "line_value" is read-only' ) )


def Calculated_SetOperator_test():
  # Differs from the above in that it use [] operator rather than __setitem__
  # directly. And it uses a different property for extra credit.
  wrap = RequestWrap( PrepareJson() )
  try:
    wrap[ 'query' ] = 'test'
  except ValueError as error:
    assert_that( str( error ),
                 equal_to( 'Key "query" is read-only' ) )
  else:
    raise AssertionError( 'Expected setting "query" to fail' )


def NonCalculated_Set_test():
  # Differs from the above in that it use [] operator rather than __setitem__
  # directly. And it uses a different property for extra credit.
  wrap = RequestWrap( PrepareJson() )
  try:
    wrap[ 'column_num' ] = 10
  except ValueError as error:
    assert_that( str( error ),
                 equal_to( 'Key "column_num" is read-only' ) )
  else:
    raise AssertionError( 'Expected setting "column_num" to fail' )


def ForceSemanticCompletion_test():
  wrap = RequestWrap( PrepareJson() )
  assert_that( wrap[ 'force_semantic' ], equal_to( False ) )

  wrap = RequestWrap( PrepareJson( force_semantic = True ) )
  assert_that( wrap[ 'force_semantic' ], equal_to( True ) )

  wrap = RequestWrap( PrepareJson( force_semantic = 1 ) )
  assert_that( wrap[ 'force_semantic' ], equal_to( True ) )

  wrap = RequestWrap( PrepareJson( force_semantic = 0 ) )
  assert_that( wrap[ 'force_semantic' ], equal_to( False ) )

  wrap = RequestWrap( PrepareJson( force_semantic = 'No' ) )
  assert_that( wrap[ 'force_semantic' ], equal_to( True ) )


def ExtraConfData_test():
  wrap = RequestWrap( PrepareJson() )
  assert_that( wrap[ 'extra_conf_data' ], empty() )

  wrap = RequestWrap( PrepareJson( extra_conf_data = { 'key': [ 'value' ] } ) )
  extra_conf_data = wrap[ 'extra_conf_data' ]
  assert_that( extra_conf_data, has_entry( 'key', contains( 'value' ) ) )
  assert_that(
    extra_conf_data,
    has_string(
      matches_regexp( "^<HashableDict {u?'key': \\[u?'value'\\]}>$" )
    )
  )

  # Check that extra_conf_data can be used as a dictionary's key.
  assert_that( { extra_conf_data: 'extra conf data' },
               has_entry( extra_conf_data, 'extra conf data' ) )

  # Check that extra_conf_data's values are immutable.
  extra_conf_data[ 'key' ].append( 'another_value' )
  assert_that( extra_conf_data, has_entry( 'key', contains( 'value' ) ) )
