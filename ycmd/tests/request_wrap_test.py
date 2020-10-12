# Copyright (C) 2020 ycmd contributors
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

import pytest
from hamcrest import ( assert_that, calling, contains_exactly, empty, equal_to,
                       has_entry, has_string, raises )

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


@pytest.mark.parametrize( 'line,col,prefix', [
    ( 'abc.def', 5, 'abc.' ),
    ( 'abc.def', 6, 'abc.' ),
    ( 'abc.def', 8, 'abc.' ),
    ( 'abc.def', 4, '' ),
    ( 'abc.', 5, 'abc.' ),
    ( 'abc.', 4, '' ),
    ( '', 1, '' ),
  ] )
def Prefix_test( line, col, prefix ):
  assert_that( prefix,
               equal_to( RequestWrap(
                 PrepareJson( line_num = 1,
                              contents = line,
                              column_num = col ) )[ 'prefix' ] ) )


def LineValue_OneLine_test():
  assert_that( 'zoo',
               equal_to( RequestWrap(
                 PrepareJson( line_num = 1,
                              contents = 'zoo' ) )[ 'line_value' ] ) )


def LineValue_LastLine_test():
  assert_that( 'zoo',
               equal_to( RequestWrap(
                 PrepareJson( line_num = 3,
                              contents = 'goo\nbar\nzoo' ) )[ 'line_value' ] ) )


def LineValue_MiddleLine_test():
  assert_that( 'zoo',
               equal_to( RequestWrap(
                 PrepareJson( line_num = 2,
                              contents = 'goo\nzoo\nbar' ) )[ 'line_value' ] ) )


def LineValue_WindowsLines_test():
  assert_that( 'zoo',
               equal_to( RequestWrap(
                 PrepareJson(
                   line_num = 3,
                   contents = 'goo\r\nbar\r\nzoo' ) )[ 'line_value' ] ) )


def LineValue_MixedFormatLines_test():
  assert_that( 'zoo',
               equal_to( RequestWrap(
                 PrepareJson(
                   line_num = 3,
                   contents = 'goo\nbar\r\nzoo' ) )[ 'line_value' ] ) )


def LineValue_EmptyContents_test():
  assert_that( '',
               equal_to( RequestWrap(
                 PrepareJson( line_num = 1,
                              contents = '' ) )[ 'line_value' ] ) )


def StartColumn_RightAfterDot_test():
  assert_that( 5,
               equal_to( RequestWrap(
                 PrepareJson( column_num = 5,
                              contents = 'foo.' ) )[ 'start_column' ] ) )


def StartColumn_Dot_test():
  assert_that( 5,
               equal_to( RequestWrap(
                 PrepareJson( column_num = 8,
                              contents = 'foo.bar' ) )[ 'start_column' ] ) )


def StartColumn_DotWithUnicode_test():
  assert_that( 7,
               equal_to( RequestWrap(
                 PrepareJson( column_num = 11,
                              contents = 'fäö.bär' ) )[ 'start_column' ] ) )


def StartColumn_UnicodeNotIdentifier_test():
  contents = "var x = '†es†ing'."

  # † not considered an identifier character

  for i in range( 13, 15 ):
    print( ToBytes( contents )[ i - 1 : i ] )
    assert_that( 13,
                 equal_to( RequestWrap(
                   PrepareJson( column_num = i,
                                contents = contents ) )[ 'start_column' ] ) )

  assert_that( 13,
               equal_to( RequestWrap(
                 PrepareJson( column_num = 15,
                              contents = contents ) )[ 'start_column' ] ) )

  for i in range( 18, 20 ):
    print( ToBytes( contents )[ i - 1 : i ] )
    assert_that( 18,
                 equal_to( RequestWrap(
                   PrepareJson( column_num = i,
                                contents = contents ) )[ 'start_column' ] ) )


def StartColumn_QueryIsUnicode_test():
  contents = "var x = ålpha.alphå"
  assert_that( 16,
               equal_to( RequestWrap(
                 PrepareJson( column_num = 16,
                              contents = contents ) )[ 'start_column' ] ) )
  assert_that( 16,
               equal_to( RequestWrap(
                 PrepareJson( column_num = 19,
                              contents = contents ) )[ 'start_column' ] ) )


def StartColumn_QueryStartsWithUnicode_test():
  contents = "var x = ålpha.ålpha"
  assert_that( 16,
               equal_to( RequestWrap(
                 PrepareJson( column_num = 16,
                              contents = contents ) )[ 'start_column' ] ) )
  assert_that( 16,
               equal_to( RequestWrap(
                 PrepareJson( column_num = 19,
                              contents = contents ) )[ 'start_column' ] ) )


def StartColumn_ThreeByteUnicode_test():
  contents = "var x = '†'."
  assert_that( 15,
               equal_to( RequestWrap(
                 PrepareJson( column_num = 15,
                              contents = contents ) )[ 'start_column' ] ) )


def StartColumn_Paren_test():
  assert_that( 5,
               equal_to( RequestWrap(
                 PrepareJson( column_num = 8,
                              contents = 'foo(bar' ) )[ 'start_column' ] ) )


def StartColumn_AfterWholeWord_test():
  assert_that( 1,
               equal_to( RequestWrap(
                 PrepareJson( column_num = 7,
                              contents = 'foobar' ) )[ 'start_column' ] ) )


def StartColumn_AfterWholeWord_Html_test():
  assert_that( 1,
               equal_to( RequestWrap(
                 PrepareJson( column_num = 7, filetype = 'html',
                              contents = 'fo-bar' ) )[ 'start_column' ] ) )


def StartColumn_AfterWholeUnicodeWord_test():
  assert_that( 1, equal_to( RequestWrap(
                   PrepareJson( column_num = 6,
                                contents = u'fäö' ) )[ 'start_column' ] ) )


def StartColumn_InMiddleOfWholeWord_test():
  assert_that( 1, equal_to( RequestWrap(
                   PrepareJson( column_num = 4,
                                contents = 'foobar' ) )[ 'start_column' ] ) )


def StartColumn_ColumnOne_test():
  assert_that( 1, equal_to( RequestWrap(
                     PrepareJson( column_num = 1,
                                  contents = 'foobar' ) )[ 'start_column' ] ) )


def Query_AtWordEnd_test():
  assert_that( 'foo', equal_to( RequestWrap(
                        PrepareJson( column_num = 4,
                                     contents = 'foo' ) )[ 'query' ] ) )


def Query_InWordMiddle_test():
  assert_that( 'foo', equal_to( RequestWrap(
                        PrepareJson( column_num = 4,
                                     contents = 'foobar' ) )[ 'query' ] ) )


def Query_StartOfLine_test():
  assert_that( '', equal_to( RequestWrap(
                     PrepareJson( column_num = 1,
                                   contents = 'foobar' ) )[ 'query' ] ) )


def Query_StopsAtParen_test():
  assert_that( 'bar', equal_to( RequestWrap(
                        PrepareJson( column_num = 8,
                                     contents = 'foo(bar' ) )[ 'query' ] ) )


def Query_InWhiteSpace_test():
  assert_that( '', equal_to( RequestWrap(
                     PrepareJson( column_num = 8,
                                   contents = 'foo       ' ) )[ 'query' ] ) )


def Query_UnicodeSinglecharInclusive_test():
  assert_that( 'ø', equal_to( RequestWrap(
                      PrepareJson( column_num = 7,
                                   contents = 'abc.ø' ) )[ 'query' ] ) )


def Query_UnicodeSinglecharExclusive_test():
  assert_that( '', equal_to( RequestWrap(
                     PrepareJson( column_num = 5,
                                  contents = 'abc.ø' ) )[ 'query' ] ) )


def StartColumn_Set_test():
  wrap = RequestWrap( PrepareJson( column_num = 11,
                                   contents = 'this \'test',
                                   filetype = 'javascript' ) )
  assert_that( wrap[ 'start_column' ], equal_to( 7 ) )
  assert_that( wrap[ 'start_codepoint' ], equal_to( 7 ) )
  assert_that( wrap[ 'query' ], equal_to( "test" ) )
  assert_that( wrap[ 'prefix' ], equal_to( "this '" ) )

  wrap[ 'start_column' ] = 6
  assert_that( wrap[ 'start_column' ], equal_to( 6 ) )
  assert_that( wrap[ 'start_codepoint' ], equal_to( 6 ) )
  assert_that( wrap[ 'query' ], equal_to( "'test" ) )
  assert_that( wrap[ 'prefix' ], equal_to( "this " ) )


def StartColumn_SetUnicode_test():
  wrap = RequestWrap( PrepareJson( column_num = 14,
                                   contents = '†eß† \'test',
                                   filetype = 'javascript' ) )
  assert_that( 7, equal_to( wrap[ 'start_codepoint' ] ) )
  assert_that( 12, equal_to( wrap[ 'start_column' ] ) )
  assert_that( wrap[ 'query' ], equal_to( "te" ) )
  assert_that( wrap[ 'prefix' ], equal_to( "†eß† \'" ) )

  wrap[ 'start_column' ] = 11
  assert_that( wrap[ 'start_column' ], equal_to( 11 ) )
  assert_that( wrap[ 'start_codepoint' ], equal_to( 6 ) )
  assert_that( wrap[ 'query' ], equal_to( "'te" ) )
  assert_that( wrap[ 'prefix' ], equal_to( "†eß† " ) )


def StartCodepoint_Set_test():
  wrap = RequestWrap( PrepareJson( column_num = 11,
                                   contents = 'this \'test',
                                   filetype = 'javascript' ) )
  assert_that( wrap[ 'start_column' ], equal_to( 7 ) )
  assert_that( wrap[ 'start_codepoint' ], equal_to( 7 ) )
  assert_that( wrap[ 'query' ], equal_to( "test" ) )
  assert_that( wrap[ 'prefix' ], equal_to( "this '" ) )

  wrap[ 'start_codepoint' ] = 6
  assert_that( wrap[ 'start_column' ], equal_to( 6 ) )
  assert_that( wrap[ 'start_codepoint' ], equal_to( 6 ) )
  assert_that( wrap[ 'query' ], equal_to( "'test" ) )
  assert_that( wrap[ 'prefix' ], equal_to( "this " ) )


def StartCodepoint_SetUnicode_test():
  wrap = RequestWrap( PrepareJson( column_num = 14,
                                   contents = '†eß† \'test',
                                   filetype = 'javascript' ) )
  assert_that( 7, equal_to( wrap[ 'start_codepoint' ] ) )
  assert_that( 12, equal_to( wrap[ 'start_column' ] ) )
  assert_that( wrap[ 'query' ], equal_to( "te" ) )
  assert_that( wrap[ 'prefix' ], equal_to( "†eß† \'" ) )

  wrap[ 'start_codepoint' ] = 6
  assert_that( wrap[ 'start_column' ], equal_to( 11 ) )
  assert_that( wrap[ 'start_codepoint' ], equal_to( 6 ) )
  assert_that( wrap[ 'query' ], equal_to( "'te" ) )
  assert_that( wrap[ 'prefix' ], equal_to( "†eß† " ) )


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
  assert_that( extra_conf_data,
               has_entry( 'key', contains_exactly( 'value' ) ) )
  assert_that(
    extra_conf_data,
    has_string(
      equal_to( "<HashableDict {'key': ['value']}>" )
    )
  )

  # Check that extra_conf_data can be used as a dictionary's key.
  assert_that( { extra_conf_data: 'extra conf data' },
               has_entry( extra_conf_data, 'extra conf data' ) )

  # Check that extra_conf_data's values are immutable.
  extra_conf_data[ 'key' ].append( 'another_value' )
  assert_that( extra_conf_data,
               has_entry( 'key', contains_exactly( 'value' ) ) )


def Dummy_test():
  # Workaround for https://github.com/pytest-dev/pytest-rerunfailures/issues/51
  assert True
