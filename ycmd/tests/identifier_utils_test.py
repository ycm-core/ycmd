# coding: utf-8
#
# Copyright (C) 2013-2018 ycmd contributors
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

from nose.tools import eq_, ok_
from ycmd import identifier_utils as iu
from hamcrest import assert_that, has_item


def RemoveIdentifierFreeText_CppComments_test():
  eq_( "foo \nbar \nqux",
       iu.RemoveIdentifierFreeText( "foo \nbar //foo \nqux" ) )


def RemoveIdentifierFreeText_PythonComments_test():
  eq_( "foo \nbar \nqux",
       iu.RemoveIdentifierFreeText( "foo \nbar #foo \nqux" ) )


def RemoveIdentifierFreeText_CstyleComments_test():
  eq_( "\n bar",
       iu.RemoveIdentifierFreeText( "/* foo\n */ bar" ) )

  eq_( "foo \nbar \nqux",
       iu.RemoveIdentifierFreeText( "foo \nbar /* foo */\nqux" ) )

  eq_( "foo \nbar \n\nqux",
       iu.RemoveIdentifierFreeText( "foo \nbar /* foo \n foo2 */\nqux" ) )


def RemoveIdentifierFreeText_SimpleSingleQuoteString_test():
  eq_( "foo \nbar \nqux",
       iu.RemoveIdentifierFreeText( "foo \nbar 'foo'\nqux" ) )


def RemoveIdentifierFreeText_SimpleDoubleQuoteString_test():
  eq_( "foo \nbar \nqux",
       iu.RemoveIdentifierFreeText( 'foo \nbar "foo"\nqux' ) )


def RemoveIdentifierFreeText_EscapedQuotes_test():
  eq_( "foo \nbar \nqux",
       iu.RemoveIdentifierFreeText( "foo \nbar 'fo\\'oz\\nfoo'\nqux" ) )

  eq_( "foo \nbar \nqux",
       iu.RemoveIdentifierFreeText( 'foo \nbar "fo\\"oz\\nfoo"\nqux' ) )


def RemoveIdentifierFreeText_SlashesInStrings_test():
  eq_( "foo \nbar baz\nqux ",
       iu.RemoveIdentifierFreeText( 'foo \nbar "fo\\\\"baz\nqux "qwe"' ) )

  eq_( "foo \nbar \nqux ",
       iu.RemoveIdentifierFreeText( "foo '\\\\'\nbar '\\\\'\nqux '\\\\'" ) )


def RemoveIdentifierFreeText_EscapedQuotesStartStrings_test():
  eq_( "\\\"foo\\\" zoo",
       iu.RemoveIdentifierFreeText( "\\\"foo\\\"'\"''bar' zoo'test'" ) )

  eq_( "\\'foo\\' zoo",
       iu.RemoveIdentifierFreeText( "\\'foo\\'\"'\"\"bar\" zoo\"test\"" ) )


def RemoveIdentifierFreeText_NoMultilineString_test():
  eq_( "'\nlet x = \nlet y = ",
       iu.RemoveIdentifierFreeText( "'\nlet x = 'foo'\nlet y = 'bar'" ) )

  eq_( "\"\nlet x = \nlet y = ",
       iu.RemoveIdentifierFreeText( "\"\nlet x = \"foo\"\nlet y = \"bar\"" ) )


def RemoveIdentifierFreeText_PythonMultilineString_test():
  eq_( "\n\n\nzoo",
       iu.RemoveIdentifierFreeText( "\"\"\"\nfoobar\n\"\"\"\nzoo" ) )

  eq_( "\n\n\nzoo",
       iu.RemoveIdentifierFreeText( "'''\nfoobar\n'''\nzoo" ) )


def RemoveIdentifierFreeText_GoBackQuoteString_test():
  eq_( "foo \nbar `foo`\nqux",
       iu.RemoveIdentifierFreeText( "foo \nbar `foo`\nqux" ) )
  eq_( "foo \nbar \nqux",
       iu.RemoveIdentifierFreeText( "foo \nbar `foo`\nqux", filetype = 'go' ) )


def ExtractIdentifiersFromText_test():
  eq_( [ "foo", "_bar", "BazGoo", "FOO", "_", "x", "one", "two", "moo", "qqq" ],
       iu.ExtractIdentifiersFromText(
           "foo $_bar \n&BazGoo\n FOO= !!! '-' - _ (x) one-two !moo [qqq]" ) )


def ExtractIdentifiersFromText_Css_test():
  eq_( [ "foo", "-zoo", "font-size", "px", "a99" ],
       iu.ExtractIdentifiersFromText(
           "foo -zoo {font-size: 12px;} a99", "css" ) )


def ExtractIdentifiersFromText_Html_test():
  eq_( [ "foo", "goo-foo", "zoo", "bar", "aa", "z", "b@g", "fo", "ba" ],
       iu.ExtractIdentifiersFromText(
           '<foo> <goo-foo zoo=bar aa="" z=\'\'/> b@g fo.ba', "html" ) )


def ExtractIdentifiersFromText_Html_TemplateChars_test():
  assert_that( iu.ExtractIdentifiersFromText( '<foo>{{goo}}</foo>', 'html' ),
               has_item( 'goo' ) )


def ExtractIdentifiersFromText_JavaScript_test():
  eq_( [ "var", "foo", "require", "bar" ],
       iu.ExtractIdentifiersFromText( "var foo = require('bar');",
                                      'javascript' ) )


def IsIdentifier_Default_test():
  ok_( iu.IsIdentifier( 'foo' ) )
  ok_( iu.IsIdentifier( 'foo129' ) )
  ok_( iu.IsIdentifier( 'f12' ) )
  ok_( iu.IsIdentifier( 'f12' ) )

  ok_( iu.IsIdentifier( '_foo' ) )
  ok_( iu.IsIdentifier( '_foo129' ) )
  ok_( iu.IsIdentifier( '_f12' ) )
  ok_( iu.IsIdentifier( '_f12' ) )

  ok_( iu.IsIdentifier( 'uniçode' ) )
  ok_( iu.IsIdentifier( 'uç' ) )
  ok_( iu.IsIdentifier( 'ç' ) )
  ok_( iu.IsIdentifier( 'çode' ) )

  ok_( not iu.IsIdentifier( '1foo129' ) )
  ok_( not iu.IsIdentifier( '-foo' ) )
  ok_( not iu.IsIdentifier( 'foo-' ) )
  ok_( not iu.IsIdentifier( 'font-face' ) )
  ok_( not iu.IsIdentifier( None ) )
  ok_( not iu.IsIdentifier( '' ) )


def IsIdentifier_JavaScript_test():
  ok_( iu.IsIdentifier( '_føo1', 'javascript' ) )
  ok_( iu.IsIdentifier( 'fø_o1', 'javascript' ) )
  ok_( iu.IsIdentifier( '$føo1', 'javascript' ) )
  ok_( iu.IsIdentifier( 'fø$o1', 'javascript' ) )

  ok_( not iu.IsIdentifier( '1føo', 'javascript' ) )


def IsIdentifier_TypeScript_test():
  ok_( iu.IsIdentifier( '_føo1', 'typescript' ) )
  ok_( iu.IsIdentifier( 'fø_o1', 'typescript' ) )
  ok_( iu.IsIdentifier( '$føo1', 'typescript' ) )
  ok_( iu.IsIdentifier( 'fø$o1', 'typescript' ) )

  ok_( not iu.IsIdentifier( '1føo', 'typescript' ) )


def IsIdentifier_Css_test():
  ok_( iu.IsIdentifier( 'foo'      , 'css' ) )
  ok_( iu.IsIdentifier( 'a'        , 'css' ) )
  ok_( iu.IsIdentifier( 'a1'       , 'css' ) )
  ok_( iu.IsIdentifier( 'a-'       , 'css' ) )
  ok_( iu.IsIdentifier( 'a-b'      , 'css' ) )
  ok_( iu.IsIdentifier( '_b'       , 'css' ) )
  ok_( iu.IsIdentifier( '-ms-foo'  , 'css' ) )
  ok_( iu.IsIdentifier( '-_o'      , 'css' ) )
  ok_( iu.IsIdentifier( 'font-face', 'css' ) )
  ok_( iu.IsIdentifier( 'αβγ'      , 'css' ) )

  ok_( not iu.IsIdentifier( '-3b', 'css' ) )
  ok_( not iu.IsIdentifier( '-3' , 'css' ) )
  ok_( not iu.IsIdentifier( '--' , 'css' ) )
  ok_( not iu.IsIdentifier( '3'  , 'css' ) )
  ok_( not iu.IsIdentifier( ''   , 'css' ) )
  ok_( not iu.IsIdentifier( '€'  , 'css' ) )


def IsIdentifier_R_test():
  ok_( iu.IsIdentifier( 'a'    , 'r' ) )
  ok_( iu.IsIdentifier( 'a.b'  , 'r' ) )
  ok_( iu.IsIdentifier( 'a.b.c', 'r' ) )
  ok_( iu.IsIdentifier( 'a_b'  , 'r' ) )
  ok_( iu.IsIdentifier( 'a1'   , 'r' ) )
  ok_( iu.IsIdentifier( 'a_1'  , 'r' ) )
  ok_( iu.IsIdentifier( '.a'   , 'r' ) )
  ok_( iu.IsIdentifier( '.a_b' , 'r' ) )
  ok_( iu.IsIdentifier( '.a1'  , 'r' ) )
  ok_( iu.IsIdentifier( '...'  , 'r' ) )
  ok_( iu.IsIdentifier( '..1'  , 'r' ) )

  ok_( not iu.IsIdentifier( '.1a', 'r' ) )
  ok_( not iu.IsIdentifier( '.1' , 'r' ) )
  ok_( not iu.IsIdentifier( '1a' , 'r' ) )
  ok_( not iu.IsIdentifier( '123', 'r' ) )
  ok_( not iu.IsIdentifier( '_1a', 'r' ) )
  ok_( not iu.IsIdentifier( '_a' , 'r' ) )
  ok_( not iu.IsIdentifier( ''   , 'r' ) )


def IsIdentifier_Clojure_test():
  ok_( iu.IsIdentifier( 'foo'  , 'clojure' ) )
  ok_( iu.IsIdentifier( 'f9'   , 'clojure' ) )
  ok_( iu.IsIdentifier( 'a.b.c', 'clojure' ) )
  ok_( iu.IsIdentifier( 'a.c'  , 'clojure' ) )
  ok_( iu.IsIdentifier( 'a/c'  , 'clojure' ) )
  ok_( iu.IsIdentifier( '*'    , 'clojure' ) )
  ok_( iu.IsIdentifier( 'a*b'  , 'clojure' ) )
  ok_( iu.IsIdentifier( '?'    , 'clojure' ) )
  ok_( iu.IsIdentifier( 'a?b'  , 'clojure' ) )
  ok_( iu.IsIdentifier( ':'    , 'clojure' ) )
  ok_( iu.IsIdentifier( 'a:b'  , 'clojure' ) )
  ok_( iu.IsIdentifier( '+'    , 'clojure' ) )
  ok_( iu.IsIdentifier( 'a+b'  , 'clojure' ) )
  ok_( iu.IsIdentifier( '-'    , 'clojure' ) )
  ok_( iu.IsIdentifier( 'a-b'  , 'clojure' ) )
  ok_( iu.IsIdentifier( '!'    , 'clojure' ) )
  ok_( iu.IsIdentifier( 'a!b'  , 'clojure' ) )

  ok_( not iu.IsIdentifier( '9f'   , 'clojure' ) )
  ok_( not iu.IsIdentifier( '9'    , 'clojure' ) )
  ok_( not iu.IsIdentifier( 'a/b/c', 'clojure' ) )
  ok_( not iu.IsIdentifier( '(a)'  , 'clojure' ) )
  ok_( not iu.IsIdentifier( ''     , 'clojure' ) )


def IsIdentifier_Elisp_test():
  # elisp is using the clojure regexes, so we're testing this more lightly
  ok_( iu.IsIdentifier( 'foo'  , 'elisp' ) )
  ok_( iu.IsIdentifier( 'f9'   , 'elisp' ) )
  ok_( iu.IsIdentifier( 'a.b.c', 'elisp' ) )
  ok_( iu.IsIdentifier( 'a/c'  , 'elisp' ) )

  ok_( not iu.IsIdentifier( '9f'   , 'elisp' ) )
  ok_( not iu.IsIdentifier( '9'    , 'elisp' ) )
  ok_( not iu.IsIdentifier( 'a/b/c', 'elisp' ) )
  ok_( not iu.IsIdentifier( '(a)'  , 'elisp' ) )
  ok_( not iu.IsIdentifier( ''     , 'elisp' ) )


def IsIdentifier_Haskell_test():
  ok_( iu.IsIdentifier( 'foo' , 'haskell' ) )
  ok_( iu.IsIdentifier( "foo'", 'haskell' ) )
  ok_( iu.IsIdentifier( "x'"  , 'haskell' ) )
  ok_( iu.IsIdentifier( "_x'" , 'haskell' ) )
  ok_( iu.IsIdentifier( "_x"  , 'haskell' ) )
  ok_( iu.IsIdentifier( "x9"  , 'haskell' ) )

  ok_( not iu.IsIdentifier( "'x", 'haskell' ) )
  ok_( not iu.IsIdentifier( "9x", 'haskell' ) )
  ok_( not iu.IsIdentifier( "9" , 'haskell' ) )
  ok_( not iu.IsIdentifier( ''  , 'haskell' ) )


def IsIdentifier_Tex_test():
  ok_( iu.IsIdentifier( 'foo'        , 'tex' ) )
  ok_( iu.IsIdentifier( 'fig:foo'    , 'tex' ) )
  ok_( iu.IsIdentifier( 'fig:foo-bar', 'tex' ) )
  ok_( iu.IsIdentifier( 'sec:summary', 'tex' ) )
  ok_( iu.IsIdentifier( 'eq:bar_foo' , 'tex' ) )
  ok_( iu.IsIdentifier( 'fōo'        , 'tex' ) )
  ok_( iu.IsIdentifier( 'some8'      , 'tex' ) )

  ok_( not iu.IsIdentifier( '\\section', 'tex' ) )
  ok_( not iu.IsIdentifier( 'foo:'    , 'tex' ) )
  ok_( not iu.IsIdentifier( '-bar'    , 'tex' ) )
  ok_( not iu.IsIdentifier( ''        , 'tex' ) )


def IsIdentifier_Perl6_test():
  ok_( iu.IsIdentifier( 'foo'  , 'perl6' ) )
  ok_( iu.IsIdentifier( "f-o"  , 'perl6' ) )
  ok_( iu.IsIdentifier( "x'y"  , 'perl6' ) )
  ok_( iu.IsIdentifier( "_x-y" , 'perl6' ) )
  ok_( iu.IsIdentifier( "x-y'a", 'perl6' ) )
  ok_( iu.IsIdentifier( "x-_"  , 'perl6' ) )
  ok_( iu.IsIdentifier( "x-_7" , 'perl6' ) )
  ok_( iu.IsIdentifier( "_x"   , 'perl6' ) )
  ok_( iu.IsIdentifier( "x9"   , 'perl6' ) )

  ok_( not iu.IsIdentifier( "'x"  , 'perl6' ) )
  ok_( not iu.IsIdentifier( "x'"  , 'perl6' ) )
  ok_( not iu.IsIdentifier( "-x"  , 'perl6' ) )
  ok_( not iu.IsIdentifier( "x-"  , 'perl6' ) )
  ok_( not iu.IsIdentifier( "x-1" , 'perl6' ) )
  ok_( not iu.IsIdentifier( "x--" , 'perl6' ) )
  ok_( not iu.IsIdentifier( "x--a", 'perl6' ) )
  ok_( not iu.IsIdentifier( "x-'" , 'perl6' ) )
  ok_( not iu.IsIdentifier( "x-'a", 'perl6' ) )
  ok_( not iu.IsIdentifier( "x-a-", 'perl6' ) )
  ok_( not iu.IsIdentifier( "x+"  , 'perl6' ) )
  ok_( not iu.IsIdentifier( "9x"  , 'perl6' ) )
  ok_( not iu.IsIdentifier( "9"   , 'perl6' ) )
  ok_( not iu.IsIdentifier( ''    , 'perl6' ) )


def IsIdentifier_Scheme_test():
  ok_( iu.IsIdentifier( 'λ'         , 'scheme' ) )
  ok_( iu.IsIdentifier( '_'         , 'scheme' ) )
  ok_( iu.IsIdentifier( '+'         , 'scheme' ) )
  ok_( iu.IsIdentifier( '-'         , 'scheme' ) )
  ok_( iu.IsIdentifier( '...'       , 'scheme' ) )
  ok_( iu.IsIdentifier( r'\x01;'    , 'scheme' ) )
  ok_( iu.IsIdentifier( r'h\x65;lle', 'scheme' ) )
  ok_( iu.IsIdentifier( 'foo'       , 'scheme' ) )
  ok_( iu.IsIdentifier( 'foo+-*/1-1', 'scheme' ) )
  ok_( iu.IsIdentifier( 'call/cc'   , 'scheme' ) )

  ok_( not iu.IsIdentifier( '.'            , 'scheme' ) )
  ok_( not iu.IsIdentifier( '..'           , 'scheme' ) )
  ok_( not iu.IsIdentifier( '--'           , 'scheme' ) )
  ok_( not iu.IsIdentifier( '++'           , 'scheme' ) )
  ok_( not iu.IsIdentifier( '+1'           , 'scheme' ) )
  ok_( not iu.IsIdentifier( '-1'           , 'scheme' ) )
  ok_( not iu.IsIdentifier( '-abc'         , 'scheme' ) )
  ok_( not iu.IsIdentifier( '-<abc'        , 'scheme' ) )
  ok_( not iu.IsIdentifier( '@'            , 'scheme' ) )
  ok_( not iu.IsIdentifier( '@a'           , 'scheme' ) )
  ok_( not iu.IsIdentifier( '-@a'          , 'scheme' ) )
  ok_( not iu.IsIdentifier( '-12a'         , 'scheme' ) )
  ok_( not iu.IsIdentifier( '12a'          , 'scheme' ) )
  ok_( not iu.IsIdentifier( '\\'           , 'scheme' ) )
  ok_( not iu.IsIdentifier( r'\x'          , 'scheme' ) )
  ok_( not iu.IsIdentifier( r'\x123'       , 'scheme' ) )
  ok_( not iu.IsIdentifier( r'aa\x123;cc\x', 'scheme' ) )


def StartOfLongestIdentifierEndingAtIndex_Simple_test():
  eq_( 0, iu.StartOfLongestIdentifierEndingAtIndex( 'foo', 3 ) )
  eq_( 0, iu.StartOfLongestIdentifierEndingAtIndex( 'f12', 3 ) )


def StartOfLongestIdentifierEndingAtIndex_BadInput_test():
  eq_( 0, iu.StartOfLongestIdentifierEndingAtIndex( '', 0 ) )
  eq_( 1, iu.StartOfLongestIdentifierEndingAtIndex( '', 1 ) )
  eq_( 5, iu.StartOfLongestIdentifierEndingAtIndex( None, 5 ) )
  eq_( -1, iu.StartOfLongestIdentifierEndingAtIndex( 'foo', -1 ) )
  eq_( 10, iu.StartOfLongestIdentifierEndingAtIndex( 'foo', 10 ) )


def StartOfLongestIdentifierEndingAtIndex_Punctuation_test():
  eq_( 1, iu.StartOfLongestIdentifierEndingAtIndex( '(foo', 4 ) )
  eq_( 6, iu.StartOfLongestIdentifierEndingAtIndex( '      foo', 9 ) )
  eq_( 4, iu.StartOfLongestIdentifierEndingAtIndex( 'gar;foo', 7 ) )
  eq_( 2, iu.StartOfLongestIdentifierEndingAtIndex( '...', 2 ) )


def StartOfLongestIdentifierEndingAtIndex_PunctuationWithUnicode_test():
  eq_( 1, iu.StartOfLongestIdentifierEndingAtIndex( u'(fäö', 4 ) )
  eq_( 2, iu.StartOfLongestIdentifierEndingAtIndex( u'  fäö', 5 ) )


# Not a test, but a test helper function
def LoopExpectLongestIdentifier( ident, expected, end_index ):
  eq_( expected, iu.StartOfLongestIdentifierEndingAtIndex( ident, end_index ) )


def StartOfLongestIdentifierEndingAtIndex_Entire_Simple_test():
  ident = 'foobar'
  for i in range( len( ident ) ):
    yield LoopExpectLongestIdentifier, ident, 0, i


def StartOfLongestIdentifierEndingAtIndex_Entire_AllBad_test():
  ident = '....'
  for i in range( len( ident ) ):
    yield LoopExpectLongestIdentifier, ident, i, i


def StartOfLongestIdentifierEndingAtIndex_Entire_FirstCharNotNumber_test():
  ident = 'f12341234'
  for i in range( len( ident ) ):
    yield LoopExpectLongestIdentifier, ident, 0, i


def StartOfLongestIdentifierEndingAtIndex_Entire_SubIdentifierValid_test():
  ident = 'f123f1234'
  for i in range( len( ident ) ):
    yield LoopExpectLongestIdentifier, ident, 0, i


def StartOfLongestIdentifierEndingAtIndex_Entire_Unicode_test():
  ident = u'fäöttccoö'
  for i in range( len( ident ) ):
    yield LoopExpectLongestIdentifier, ident, 0, i


# Not a test, but a test helper function
def LoopExpectIdentfierAtIndex( ident, index, expected ):
  eq_( expected, iu.IdentifierAtIndex( ident, index ) )


def IdentifierAtIndex_Entire_Simple_test():
  ident = u'foobar'
  for i in range( len( ident ) ):
    yield LoopExpectIdentfierAtIndex, ident, i, ident


def IdentifierAtIndex_Entire_Unicode_test():
  ident = u'fäöttccoö'
  for i in range( len( ident ) ):
    yield LoopExpectIdentfierAtIndex, ident, i, ident


def IdentifierAtIndex_BadInput_test():
  eq_( '', iu.IdentifierAtIndex( '', 0 ) )
  eq_( '', iu.IdentifierAtIndex( '', 5 ) )
  eq_( '', iu.IdentifierAtIndex( 'foo', 5 ) )
  eq_( 'foo', iu.IdentifierAtIndex( 'foo', -5 ) )


def IdentifierAtIndex_IndexPastIdent_test():
  eq_( '', iu.IdentifierAtIndex( 'foo    ', 5 ) )


def IdentifierAtIndex_StopsAtNonIdentifier_test():
  eq_( 'foo', iu.IdentifierAtIndex( 'foo(goo)', 0 ) )
  eq_( 'goo', iu.IdentifierAtIndex( 'foo(goo)', 5 ) )


def IdentifierAtIndex_LooksAhead_Success_test():
  eq_( 'goo', iu.IdentifierAtIndex( 'foo(goo)', 3 ) )
  eq_( 'goo', iu.IdentifierAtIndex( '   goo', 0 ) )


def IdentifierAtIndex_LooksAhead_Failure_test():
  eq_( '', iu.IdentifierAtIndex( 'foo    ()***()', 5 ) )


def IdentifierAtIndex_SingleCharIdent_test():
  eq_( 'f', iu.IdentifierAtIndex( '    f    ', 1 ) )


def IdentifierAtIndex_Css_test():
  eq_( 'font-face', iu.IdentifierAtIndex( 'font-face', 0, 'css' ) )
