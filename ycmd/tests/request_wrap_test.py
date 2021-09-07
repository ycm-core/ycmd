# Copyright (C) 2021 ycmd contributors
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

from hamcrest import ( assert_that, calling, contains_exactly, empty, equal_to,
                       has_entry, has_string, raises )

from ycmd.utils import ToBytes
from ycmd.request_wrap import RequestWrap
from unittest import TestCase


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


class RequestWrapTest( TestCase ):
  def test_Prefix( self ):
    for line, col, prefix in [
      ( 'abc.def', 5, 'abc.' ),
      ( 'abc.def', 6, 'abc.' ),
      ( 'abc.def', 8, 'abc.' ),
      ( 'abc.def', 4, '' ),
      ( 'abc.', 5, 'abc.' ),
      ( 'abc.', 4, '' ),
      ( '', 1, '' ),
    ]:
      with self.subTest( line = line, col = col, prefix = prefix ):
        assert_that( prefix,
                     equal_to( RequestWrap(
                       PrepareJson( line_num = 1,
                                    contents = line,
                                    column_num = col ) )[ 'prefix' ] ) )


  def test_LineValue_OneLine( self ):
    assert_that( 'zoo',
                 equal_to( RequestWrap(
                   PrepareJson( line_num = 1,
                                contents = 'zoo' ) )[ 'line_value' ] ) )


  def test_LineValue_LastLine( self ):
    assert_that(
      'zoo',
      equal_to(
        RequestWrap(
          PrepareJson( line_num = 3,
                       contents = 'goo\nbar\nzoo' ) )[ 'line_value' ] ) )


  def test_LineValue_MiddleLine( self ):
    assert_that(
      'zoo',
      equal_to(
        RequestWrap(
          PrepareJson( line_num = 2,
                       contents = 'goo\nzoo\nbar' ) )[ 'line_value' ] ) )


  def test_LineValue_WindowsLines( self ):
    assert_that( 'zoo',
                 equal_to( RequestWrap(
                   PrepareJson(
                     line_num = 3,
                     contents = 'goo\r\nbar\r\nzoo' ) )[ 'line_value' ] ) )


  def test_LineValue_MixedFormatLines( self ):
    assert_that( 'zoo',
                 equal_to( RequestWrap(
                   PrepareJson(
                     line_num = 3,
                     contents = 'goo\nbar\r\nzoo' ) )[ 'line_value' ] ) )


  def test_LineValue_EmptyContents( self ):
    assert_that( '',
                 equal_to( RequestWrap(
                   PrepareJson( line_num = 1,
                                contents = '' ) )[ 'line_value' ] ) )


  def test_StartColumn_RightAfterDot( self ):
    assert_that( 5,
                 equal_to( RequestWrap(
                   PrepareJson( column_num = 5,
                                contents = 'foo.' ) )[ 'start_column' ] ) )


  def test_StartColumn_Dot( self ):
    assert_that( 5,
                 equal_to( RequestWrap(
                   PrepareJson( column_num = 8,
                                contents = 'foo.bar' ) )[ 'start_column' ] ) )


  def test_StartColumn_DotWithUnicode( self ):
    assert_that( 7,
                 equal_to( RequestWrap(
                   PrepareJson( column_num = 11,
                                contents = 'fäö.bär' ) )[ 'start_column' ] ) )


  def test_StartColumn_UnicodeNotIdentifier( self ):
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


  def test_StartColumn_QueryIsUnicode( self ):
    contents = "var x = ålpha.alphå"
    assert_that( 16,
                 equal_to( RequestWrap(
                   PrepareJson( column_num = 16,
                                contents = contents ) )[ 'start_column' ] ) )
    assert_that( 16,
                 equal_to( RequestWrap(
                   PrepareJson( column_num = 19,
                                contents = contents ) )[ 'start_column' ] ) )


  def test_StartColumn_QueryStartsWithUnicode( self ):
    contents = "var x = ålpha.ålpha"
    assert_that( 16,
                 equal_to( RequestWrap(
                   PrepareJson( column_num = 16,
                                contents = contents ) )[ 'start_column' ] ) )
    assert_that( 16,
                 equal_to( RequestWrap(
                   PrepareJson( column_num = 19,
                                contents = contents ) )[ 'start_column' ] ) )


  def test_StartColumn_ThreeByteUnicode( self ):
    contents = "var x = '†'."
    assert_that( 15,
                 equal_to( RequestWrap(
                   PrepareJson( column_num = 15,
                                contents = contents ) )[ 'start_column' ] ) )


  def test_StartColumn_Paren( self ):
    assert_that( 5,
                 equal_to( RequestWrap(
                   PrepareJson( column_num = 8,
                                contents = 'foo(bar' ) )[ 'start_column' ] ) )


  def test_StartColumn_AfterWholeWord( self ):
    assert_that( 1,
                 equal_to( RequestWrap(
                   PrepareJson( column_num = 7,
                                contents = 'foobar' ) )[ 'start_column' ] ) )


  def test_StartColumn_AfterWholeWord_Html( self ):
    assert_that( 1,
                 equal_to( RequestWrap(
                   PrepareJson( column_num = 7, filetype = 'html',
                                contents = 'fo-bar' ) )[ 'start_column' ] ) )


  def test_StartColumn_AfterWholeUnicodeWord( self ):
    assert_that( 1, equal_to( RequestWrap(
                     PrepareJson( column_num = 6,
                                  contents = u'fäö' ) )[ 'start_column' ] ) )


  def test_StartColumn_InMiddleOfWholeWord( self ):
    assert_that( 1, equal_to( RequestWrap(
                     PrepareJson( column_num = 4,
                                  contents = 'foobar' ) )[ 'start_column' ] ) )


  def test_StartColumn_ColumnOne( self ):
    assert_that( 1,
                 equal_to( RequestWrap(
                   PrepareJson( column_num = 1,
                                contents = 'foobar' ) )[ 'start_column' ] ) )


  def test_Query_AtWordEnd( self ):
    assert_that( 'foo', equal_to( RequestWrap(
                          PrepareJson( column_num = 4,
                                       contents = 'foo' ) )[ 'query' ] ) )


  def test_Query_InWordMiddle( self ):
    assert_that( 'foo', equal_to( RequestWrap(
                          PrepareJson( column_num = 4,
                                       contents = 'foobar' ) )[ 'query' ] ) )


  def test_Query_StartOfLine( self ):
    assert_that( '', equal_to( RequestWrap(
                       PrepareJson( column_num = 1,
                                     contents = 'foobar' ) )[ 'query' ] ) )


  def test_Query_StopsAtParen( self ):
    assert_that( 'bar', equal_to( RequestWrap(
                          PrepareJson( column_num = 8,
                                       contents = 'foo(bar' ) )[ 'query' ] ) )


  def test_Query_InWhiteSpace( self ):
    assert_that( '', equal_to( RequestWrap(
                       PrepareJson( column_num = 8,
                                     contents = 'foo       ' ) )[ 'query' ] ) )


  def test_Query_UnicodeSinglecharInclusive( self ):
    assert_that( 'ø', equal_to( RequestWrap(
                        PrepareJson( column_num = 7,
                                     contents = 'abc.ø' ) )[ 'query' ] ) )


  def test_Query_UnicodeSinglecharExclusive( self ):
    assert_that( '', equal_to( RequestWrap(
                       PrepareJson( column_num = 5,
                                    contents = 'abc.ø' ) )[ 'query' ] ) )


  def test_StartColumn_Set( self ):
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


  def test_StartColumn_SetUnicode( self ):
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


  def test_StartCodepoint_Set( self ):
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


  def test_StartCodepoint_SetUnicode( self ):
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


  def test_Calculated_SetMethod( self ):
    assert_that(
      calling( RequestWrap( PrepareJson() ).__setitem__ ).with_args(
        'line_value', '' ),
      raises( ValueError, 'Key "line_value" is read-only' ) )


  def test_Calculated_SetOperator( self ):
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


  def test_NonCalculated_Set( self ):
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


  def test_ForceSemanticCompletion( self ):
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


  def test_ExtraConfData( self ):
    wrap = RequestWrap( PrepareJson() )
    assert_that( wrap[ 'extra_conf_data' ], empty() )

    wrap = RequestWrap(
             PrepareJson( extra_conf_data = { 'key': [ 'value' ] } ) )
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
