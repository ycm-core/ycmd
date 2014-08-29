#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2014 Google Inc.
#
# YouCompleteMe is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# YouCompleteMe is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with YouCompleteMe.  If not, see <http://www.gnu.org/licenses/>.

from nose.tools import eq_
from ..request_wrap import RequestWrap

def PrepareJson( contents = '', line_num = 1, column_num = 1, filetype = '' ):
  return {
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
                                 contents = 'foo.') )[ 'start_column' ] )


def StartColumn_Dot_test():
  eq_( 5,
       RequestWrap( PrepareJson( column_num = 8,
                                 contents = 'foo.bar') )[ 'start_column' ] )

def StartColumn_DotWithUnicode_test():
  eq_( 7,
       RequestWrap( PrepareJson( column_num = 11,
                                 contents = 'fäö.bär') )[ 'start_column' ] )


def StartColumn_Paren_test():
  eq_( 5,
       RequestWrap( PrepareJson( column_num = 8,
                                 contents = 'foo(bar') )[ 'start_column' ] )


def StartColumn_AfterWholeWord_test():
  eq_( 1,
       RequestWrap( PrepareJson( column_num = 7,
                                 contents = 'foobar') )[ 'start_column' ] )


def StartColumn_AfterWholeWord_Html_test():
  eq_( 1,
       RequestWrap( PrepareJson( column_num = 7,
                                 filetype = 'html',
                                 contents = 'fo-bar') )[ 'start_column' ] )


def StartColumn_AfterWholeUnicodeWord_test():
  eq_( 1,
       RequestWrap( PrepareJson( column_num = 6,
                                 contents = u'fäö') )[ 'start_column' ] )


def StartColumn_InMiddleOfWholeWord_test():
  eq_( 1,
       RequestWrap( PrepareJson( column_num = 4,
                                 contents = 'foobar') )[ 'start_column' ] )


def StartColumn_ColumnOne_test():
  eq_( 1,
       RequestWrap( PrepareJson( column_num = 1,
                                 contents = 'foobar') )[ 'start_column' ] )


def Query_AtWordEnd_test():
  eq_( 'foo',
       RequestWrap( PrepareJson( column_num = 4,
                                 contents = 'foo') )[ 'query' ] )


def Query_InWordMiddle_test():
  eq_( 'foo',
       RequestWrap( PrepareJson( column_num = 4,
                                 contents = 'foobar') )[ 'query' ] )


def Query_StartOfLine_test():
  eq_( '',
       RequestWrap( PrepareJson( column_num = 1,
                                 contents = 'foobar') )[ 'query' ] )


def Query_StopsAtParen_test():
  eq_( 'bar',
       RequestWrap( PrepareJson( column_num = 8,
                                 contents = 'foo(bar') )[ 'query' ] )


def Query_InWhiteSpace_test():
  eq_( '',
       RequestWrap( PrepareJson( column_num = 8,
                                 contents = 'foo       ') )[ 'query' ] )
