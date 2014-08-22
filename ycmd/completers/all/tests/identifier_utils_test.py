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
from ycmd.completers.all import identifier_utils


def RemoveIdentifierFreeText_CppComments_test():
  eq_( "foo \nbar \nqux",
       identifier_utils.RemoveIdentifierFreeText(
          "foo \nbar //foo \nqux" ) )


def RemoveIdentifierFreeText_PythonComments_test():
  eq_( "foo \nbar \nqux",
       identifier_utils.RemoveIdentifierFreeText(
          "foo \nbar #foo \nqux" ) )


def RemoveIdentifierFreeText_CstyleComments_test():
  eq_( "foo \nbar \nqux",
       identifier_utils.RemoveIdentifierFreeText(
          "foo \nbar /* foo */\nqux" ) )

  eq_( "foo \nbar \nqux",
       identifier_utils.RemoveIdentifierFreeText(
          "foo \nbar /* foo \n foo2 */\nqux" ) )


def RemoveIdentifierFreeText_SimpleSingleQuoteString_test():
  eq_( "foo \nbar \nqux",
       identifier_utils.RemoveIdentifierFreeText(
          "foo \nbar 'foo'\nqux" ) )


def RemoveIdentifierFreeText_SimpleDoubleQuoteString_test():
  eq_( "foo \nbar \nqux",
       identifier_utils.RemoveIdentifierFreeText(
          'foo \nbar "foo"\nqux' ) )


def RemoveIdentifierFreeText_EscapedQuotes_test():
  eq_( "foo \nbar \nqux",
       identifier_utils.RemoveIdentifierFreeText(
          "foo \nbar 'fo\\'oz\\nfoo'\nqux" ) )

  eq_( "foo \nbar \nqux",
       identifier_utils.RemoveIdentifierFreeText(
          'foo \nbar "fo\\"oz\\nfoo"\nqux' ) )


def RemoveIdentifierFreeText_SlashesInStrings_test():
  eq_( "foo \nbar baz\nqux ",
       identifier_utils.RemoveIdentifierFreeText(
           'foo \nbar "fo\\\\"baz\nqux "qwe"' ) )

  eq_( "foo \nbar \nqux ",
       identifier_utils.RemoveIdentifierFreeText(
           "foo '\\\\'\nbar '\\\\'\nqux '\\\\'" ) )


def RemoveIdentifierFreeText_EscapedQuotesStartStrings_test():
  eq_( "\\\"foo\\\" zoo",
       identifier_utils.RemoveIdentifierFreeText(
           "\\\"foo\\\"'\"''bar' zoo'test'" ) )

  eq_( "\\'foo\\' zoo",
       identifier_utils.RemoveIdentifierFreeText(
           "\\'foo\\'\"'\"\"bar\" zoo\"test\"" ) )


def RemoveIdentifierFreeText_NoMultilineString_test():
  eq_( "'\nlet x = \nlet y = ",
       identifier_utils.RemoveIdentifierFreeText(
           "'\nlet x = 'foo'\nlet y = 'bar'" ) )

  eq_( "\"\nlet x = \nlet y = ",
       identifier_utils.RemoveIdentifierFreeText(
           "\"\nlet x = \"foo\"\nlet y = \"bar\"" ) )


def RemoveIdentifierFreeText_PythonMultilineString_test():
  eq_( "\nzoo",
       identifier_utils.RemoveIdentifierFreeText(
           "\"\"\"\nfoobar\n\"\"\"\nzoo" ) )

  eq_( "\nzoo",
       identifier_utils.RemoveIdentifierFreeText(
           "'''\nfoobar\n'''\nzoo" ) )


def ExtractIdentifiersFromText_test():
  eq_( [ "foo", "_bar", "BazGoo", "FOO", "_", "x", "one", "two", "moo", "qqq" ],
       identifier_utils.ExtractIdentifiersFromText(
           "foo $_bar \n&BazGoo\n FOO= !!! '-' - _ (x) one-two !moo [qqq]" ) )
