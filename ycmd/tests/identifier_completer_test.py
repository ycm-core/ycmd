# Copyright (C) 2013 Google Inc.
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

import os
from nose.tools import eq_
from ycmd.user_options_store import DefaultOptions
from ycmd.completers.all import identifier_completer as ic
from ycmd.completers.all.identifier_completer import IdentifierCompleter
from ycmd.request_wrap import RequestWrap
from ycmd.tests import PathToTestFile
from ycmd.tests.test_utils import BuildRequest


def BuildRequestWrap( contents, column_num, line_num = 1 ):
  return RequestWrap( BuildRequest( column_num = column_num,
                                    line_num = line_num,
                                    contents = contents ) )


def GetCursorIdentifier_StartOfLine_test():
  eq_( 'foo', ic._GetCursorIdentifier( False, BuildRequestWrap( 'foo', 1 ) ) )
  eq_( 'fooBar', ic._GetCursorIdentifier( False,
                                          BuildRequestWrap( 'fooBar', 1 ) ) )


def GetCursorIdentifier_EndOfLine_test():
  eq_( 'foo', ic._GetCursorIdentifier( False, BuildRequestWrap( 'foo', 3 ) ) )


def GetCursorIdentifier_PastEndOfLine_test():
  eq_( '', ic._GetCursorIdentifier( False, BuildRequestWrap( 'foo', 11 ) ) )


def GetCursorIdentifier_NegativeColumn_test():
  eq_( 'foo', ic._GetCursorIdentifier( False, BuildRequestWrap( 'foo', -10 ) ) )


def GetCursorIdentifier_StartOfLine_StopsAtNonIdentifierChar_test():
  eq_( 'foo', ic._GetCursorIdentifier( False,
                                       BuildRequestWrap( 'foo(goo)', 1 ) ) )


def GetCursorIdentifier_AtNonIdentifier_test():
  eq_( 'goo', ic._GetCursorIdentifier( False,
                                       BuildRequestWrap( 'foo(goo)', 4 ) ) )


def GetCursorIdentifier_WalksForwardForIdentifier_test():
  eq_( 'foo', ic._GetCursorIdentifier( False,
                                       BuildRequestWrap( '       foo', 1 ) ) )


def GetCursorIdentifier_FindsNothingForward_test():
  eq_( '', ic._GetCursorIdentifier( False,
                                    BuildRequestWrap( 'foo   ()***()', 5 ) ) )


def GetCursorIdentifier_SingleCharIdentifier_test():
  eq_( 'f', ic._GetCursorIdentifier( False,
                                     BuildRequestWrap( '    f    ', 1 ) ) )


def GetCursorIdentifier_StartsInMiddleOfIdentifier_test():
  eq_( 'foobar', ic._GetCursorIdentifier( False,
                                          BuildRequestWrap( 'foobar', 4 ) ) )


def GetCursorIdentifier_LineEmpty_test():
  eq_( '', ic._GetCursorIdentifier( False, BuildRequestWrap( '', 12 ) ) )


def GetCursorIdentifier_IgnoreIdentifierFromCommentsAndStrings_test():
  eq_( '', ic._GetCursorIdentifier( False, BuildRequestWrap( '"foobar"', 4 ) ) )
  eq_( '', ic._GetCursorIdentifier( False,
                                    BuildRequestWrap( '/*\n'
                                                      ' * foobar\n'
                                                      ' */', 5, 2 ) ) )


def GetCursorIdentifier_CollectIdentifierFromCommentsAndStrings_test():
  eq_( 'foobar', ic._GetCursorIdentifier( True,
                                          BuildRequestWrap( '"foobar"', 4 ) ) )
  eq_( 'foobar', ic._GetCursorIdentifier( True,
                                          BuildRequestWrap( '/*\n'
                                                            ' * foobar\n'
                                                            ' */', 5, 2 ) ) )


def PreviousIdentifier_Simple_test():
  eq_( 'foo', ic._PreviousIdentifier( 2, False, BuildRequestWrap( 'foo', 4 ) ) )


def PreviousIdentifier_WholeIdentShouldBeBeforeColumn_test():
  eq_( '',
       ic._PreviousIdentifier( 2, False, BuildRequestWrap( 'foobar',
                                                           column_num = 4 ) ) )


def PreviousIdentifier_DoNotWrap_test():
  eq_( '',
       ic._PreviousIdentifier( 2, False, BuildRequestWrap( 'foobar\n bar',
                                                           column_num = 4 ) ) )


def PreviousIdentifier_IgnoreForwardIdents_test():
  eq_( 'foo',
       ic._PreviousIdentifier( 2, False, BuildRequestWrap( 'foo bar zoo',
                                                           4 ) ) )


def PreviousIdentifier_IgnoreTooSmallIdent_test():
  eq_( '', ic._PreviousIdentifier( 4, False, BuildRequestWrap( 'foo', 4 ) ) )


def PreviousIdentifier_IgnoreTooSmallIdent_DontContinueLooking_test():
  eq_( '', ic._PreviousIdentifier( 4, False, BuildRequestWrap( 'abcde foo',
                                                               10 ) ) )


def PreviousIdentifier_WhitespaceAfterIdent_test():
  eq_( 'foo', ic._PreviousIdentifier( 2, False, BuildRequestWrap( 'foo     ',
                                                                  6 ) ) )


def PreviousIdentifier_JunkAfterIdent_test():
  eq_( 'foo',
       ic._PreviousIdentifier( 2, False, BuildRequestWrap( 'foo  ;;()**   ',
                                                           13 ) ) )


def PreviousIdentifier_IdentInMiddleOfJunk_test():
  eq_( 'aa',
       ic._PreviousIdentifier( 2, False, BuildRequestWrap( 'foo  ;;(aa)**   ',
                                                           13 ) ) )


def PreviousIdentifier_IdentOnPreviousLine_test():
  eq_( 'foo',
       ic._PreviousIdentifier( 2, False, BuildRequestWrap( 'foo\n   ',
                                                           column_num = 3,
                                                           line_num = 2 ) ) )

  eq_( 'foo',
       ic._PreviousIdentifier( 2, False, BuildRequestWrap( 'foo\n',
                                                           column_num = 1,
                                                           line_num = 2 ) ) )


def PreviousIdentifier_IdentOnPreviousLine_JunkAfterIdent_test():
  eq_( 'foo',
       ic._PreviousIdentifier( 2, False, BuildRequestWrap( 'foo **;()\n   ',
                                                           column_num = 3,
                                                           line_num = 2 ) ) )


def PreviousIdentifier_NoGoodIdentFound_test():
  eq_( '',
       ic._PreviousIdentifier( 5, False, BuildRequestWrap( 'foo\n ',
                                                           column_num = 2,
                                                           line_num = 2 ) ) )


def PreviousIdentifier_IgnoreIdentifierFromCommentsAndStrings_test():
  eq_( '',
       ic._PreviousIdentifier( 2, False, BuildRequestWrap( '"foo"\n',
                                                           column_num = 1,
                                                           line_num = 2 ) ) )
  eq_( '',
       ic._PreviousIdentifier( 2, False, BuildRequestWrap( '/*\n'
                                                           ' * foo\n'
                                                           ' */',
                                                           column_num = 2,
                                                           line_num = 3 ) ) )


def PreviousIdentifier_CollectIdentifierFromCommentsAndStrings_test():
  eq_( 'foo',
       ic._PreviousIdentifier( 2, True, BuildRequestWrap( '"foo"\n',
                                                          column_num = 1,
                                                          line_num = 2 ) ) )
  eq_( 'foo',
       ic._PreviousIdentifier( 2, True, BuildRequestWrap( '/*\n'
                                                          ' * foo\n'
                                                          ' */',
                                                          column_num = 2,
                                                          line_num = 3 ) ) )


def FilterUnchangedTagFiles_NoFiles_test():
  ident_completer = IdentifierCompleter( DefaultOptions() )
  eq_( [], list( ident_completer._FilterUnchangedTagFiles( [] ) ) )


def FilterUnchangedTagFiles_SkipBadFiles_test():
  ident_completer = IdentifierCompleter( DefaultOptions() )
  eq_( [],
       list( ident_completer._FilterUnchangedTagFiles( [ '/some/tags' ] ) ) )


def FilterUnchangedTagFiles_KeepGoodFiles_test():
  ident_completer = IdentifierCompleter( DefaultOptions() )
  tag_file = PathToTestFile( 'basic.tags' )
  eq_( [ tag_file ],
       list( ident_completer._FilterUnchangedTagFiles( [ tag_file ] ) ) )


def FilterUnchangedTagFiles_SkipUnchangesFiles_test():
  ident_completer = IdentifierCompleter( DefaultOptions() )

  # simulate an already open tags file that didn't change in the meantime.
  tag_file = PathToTestFile( 'basic.tags' )
  ident_completer._tags_file_last_mtime[ tag_file ] = os.path.getmtime(
      tag_file )

  eq_( [], list( ident_completer._FilterUnchangedTagFiles( [ tag_file ] ) ) )
