#!/usr/bin/env python
#
# Copyright (C) 2013  Google Inc.
#
# This file is part of YouCompleteMe.
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
from ycmd.completers.all import identifier_completer as ic
from ycmd.request_wrap import RequestWrap
from ycmd.tests.test_utils import BuildRequest

def BuildRequestWrap( contents, column_num, line_num = 1 ):
  return RequestWrap( BuildRequest( column_num = column_num,
                                    line_num = line_num,
                                    contents = contents ) )


def GetCursorIdentifier_StartOfLine_test():
  eq_( 'foo', ic._GetCursorIdentifier( BuildRequestWrap( 'foo', 1 ) ) )
  eq_( 'fooBar', ic._GetCursorIdentifier( BuildRequestWrap( 'fooBar', 1 ) ) )


def GetCursorIdentifier_EndOfLine_test():
  eq_( 'foo', ic._GetCursorIdentifier( BuildRequestWrap( 'foo', 3 ) ) )


def GetCursorIdentifier_PastEndOfLine_test():
  eq_( '', ic._GetCursorIdentifier( BuildRequestWrap( 'foo', 11 ) ) )


def GetCursorIdentifier_NegativeColumn_test():
  eq_( 'foo', ic._GetCursorIdentifier( BuildRequestWrap( 'foo', -10 ) ) )


def GetCursorIdentifier_StartOfLine_StopsAtNonIdentifierChar_test():
  eq_( 'foo', ic._GetCursorIdentifier( BuildRequestWrap( 'foo(goo)', 1 ) ) )


def GetCursorIdentifier_AtNonIdentifier_test():
  eq_( 'goo', ic._GetCursorIdentifier( BuildRequestWrap( 'foo(goo)', 4 ) ) )


def GetCursorIdentifier_WalksForwardForIdentifier_test():
  eq_( 'foo', ic._GetCursorIdentifier( BuildRequestWrap( '       foo', 1 ) ) )


def GetCursorIdentifier_FindsNothingForward_test():
  eq_( '', ic._GetCursorIdentifier( BuildRequestWrap( 'foo   ()***()', 5 ) ) )


def GetCursorIdentifier_SingleCharIdentifier_test():
  eq_( 'f', ic._GetCursorIdentifier( BuildRequestWrap( '    f    ', 1 ) ) )


def GetCursorIdentifier_StartsInMiddleOfIdentifier_test():
  eq_( 'foobar', ic._GetCursorIdentifier( BuildRequestWrap( 'foobar', 4 ) ) )


def GetCursorIdentifier_LineEmpty_test():
  eq_( '', ic._GetCursorIdentifier( BuildRequestWrap( '', 12 ) ) )


def PreviousIdentifier_Simple_test():
  eq_( 'foo', ic._PreviousIdentifier( 2, BuildRequestWrap( 'foo', 4 ) ) )


def PreviousIdentifier_ColumnInMiddleStillWholeIdent_test():
  eq_( 'foobar', ic._PreviousIdentifier( 2, BuildRequestWrap( 'foobar', 4 ) ) )


def PreviousIdentifier_IgnoreForwardIdents_test():
  eq_( 'foo',
       ic._PreviousIdentifier( 2, BuildRequestWrap( 'foo bar zoo', 4 ) ) )


def PreviousIdentifier_IgnoreTooSmallIdent_test():
  eq_( '', ic._PreviousIdentifier( 4, BuildRequestWrap( 'foo', 4 ) ) )


def PreviousIdentifier_IgnoreTooSmallIdent_DontContinueLooking_test():
  eq_( '', ic._PreviousIdentifier( 4, BuildRequestWrap( 'abcde foo', 10 ) ) )


def PreviousIdentifier_WhitespaceAfterIdent_test():
  eq_( 'foo', ic._PreviousIdentifier( 2, BuildRequestWrap( 'foo     ', 6 ) ) )


def PreviousIdentifier_JunkAfterIdent_test():
  eq_( 'foo',
       ic._PreviousIdentifier( 2, BuildRequestWrap( 'foo  ;;()**   ', 13 ) ) )


def PreviousIdentifier_IdentInMiddleOfJunk_test():
  eq_( 'aa',
       ic._PreviousIdentifier( 2, BuildRequestWrap( 'foo  ;;(aa)**   ', 13 ) ) )


def PreviousIdentifier_IdentOnPreviousLine_test():
  eq_( 'foo',
       ic._PreviousIdentifier( 2, BuildRequestWrap( 'foo\n   ',
                                                    column_num = 3,
                                                    line_num = 2 ) ) )

  eq_( 'foo',
       ic._PreviousIdentifier( 2, BuildRequestWrap( 'foo\n',
                                                    column_num = 1,
                                                    line_num = 2 ) ) )


def PreviousIdentifier_IdentOnPreviousLine_JunkAfterIdent_test():
  eq_( 'foo',
       ic._PreviousIdentifier( 2, BuildRequestWrap( 'foo **;()\n   ',
                                                    column_num = 3,
                                                    line_num = 2 ) ) )
