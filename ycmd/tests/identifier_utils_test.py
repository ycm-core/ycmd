# Copyright (C) 2013-2021 ycmd contributors
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

from ycmd import identifier_utils as iu
from hamcrest import assert_that, equal_to, has_item
from unittest import TestCase


def LoopExpectIdentfierAtIndex( ident, index, expected ):
  assert_that( expected, equal_to( iu.IdentifierAtIndex( ident, index ) ) )


def LoopExpectLongestIdentifier( ident, expected, end_index ):
  assert_that( expected, equal_to(
    iu.StartOfLongestIdentifierEndingAtIndex( ident, end_index ) ) )


class IdentifierUtilsTest( TestCase ):
  def test_RemoveIdentifierFreeText_CppComments( self ):
    assert_that( "foo \nbar \nqux",
                 equal_to( iu.RemoveIdentifierFreeText(
                   "foo \nbar //foo \nqux" ) ) )


  def test_RemoveIdentifierFreeText_PythonComments( self ):
    assert_that( "foo \nbar \nqux",
                 equal_to( iu.RemoveIdentifierFreeText(
                   "foo \nbar #foo \nqux" ) ) )


  def test_RemoveIdentifierFreeText_CstyleComments( self ):
    assert_that( "\n bar",
                 equal_to( iu.RemoveIdentifierFreeText(
                   "/* foo\n */ bar" ) ) )
    assert_that( "foo \nbar \nqux",
                 equal_to( iu.RemoveIdentifierFreeText(
                   "foo \nbar /* foo */\nqux" ) ) )
    assert_that( "foo \nbar \n\nqux",
                 equal_to( iu.RemoveIdentifierFreeText(
                   "foo \nbar /* foo \n foo2 */\nqux" ) ) )


  def test_RemoveIdentifierFreeText_SimpleSingleQuoteString( self ):
    assert_that( "foo \nbar \nqux",
                 equal_to( iu.RemoveIdentifierFreeText(
                   "foo \nbar 'foo'\nqux" ) ) )


  def test_RemoveIdentifierFreeText_SimpleDoubleQuoteString( self ):
    assert_that( "foo \nbar \nqux",
                 equal_to( iu.RemoveIdentifierFreeText(
                   'foo \nbar "foo"\nqux' ) ) )


  def test_RemoveIdentifierFreeText_EscapedQuotes( self ):
    assert_that( "foo \nbar \nqux",
                 equal_to( iu.RemoveIdentifierFreeText(
                   "foo \nbar 'fo\\'oz\\nfoo'\nqux" ) ) )
    assert_that( "foo \nbar \nqux",
                 equal_to( iu.RemoveIdentifierFreeText(
                   'foo \nbar "fo\\"oz\\nfoo"\nqux' ) ) )


  def test_RemoveIdentifierFreeText_SlashesInStrings( self ):
    assert_that( "foo \nbar baz\nqux ",
                 equal_to( iu.RemoveIdentifierFreeText(
                   'foo \nbar "fo\\\\"baz\nqux "qwe"' ) ) )
    assert_that( "foo \nbar \nqux ",
                 equal_to( iu.RemoveIdentifierFreeText(
                   "foo '\\\\'\nbar '\\\\'\nqux '\\\\'" ) ) )


  def test_RemoveIdentifierFreeText_EscapedQuotesStartStrings( self ):
    assert_that( "\\\"foo\\\" zoo",
                 equal_to( iu.RemoveIdentifierFreeText(
                   "\\\"foo\\\"'\"''bar' zoo'test'" ) ) )
    assert_that( "\\'foo\\' zoo",
                 equal_to( iu.RemoveIdentifierFreeText(
                   "\\'foo\\'\"'\"\"bar\" zoo\"test\"" ) ) )


  def test_RemoveIdentifierFreeText_NoMultilineString( self ):
    assert_that( "'\nlet x = \nlet y = ",
                 equal_to( iu.RemoveIdentifierFreeText(
                   "'\nlet x = 'foo'\nlet y = 'bar'" ) ) )
    assert_that( "\"\nlet x = \nlet y = ",
                 equal_to( iu.RemoveIdentifierFreeText(
                   "\"\nlet x = \"foo\"\nlet y = \"bar\"" ) ) )


  def test_RemoveIdentifierFreeText_PythonMultilineString( self ):
    assert_that( "\n\n\nzoo",
                 equal_to( iu.RemoveIdentifierFreeText(
                   "\"\"\"\nfoobar\n\"\"\"\nzoo" ) ) )
    assert_that( "\n\n\nzoo",
                 equal_to( iu.RemoveIdentifierFreeText(
                   "'''\nfoobar\n'''\nzoo" ) ) )


  def test_RemoveIdentifierFreeText_GoBackQuoteString( self ):
    assert_that( "foo \nbar `foo`\nqux",
                 equal_to( iu.RemoveIdentifierFreeText(
                   "foo \nbar `foo`\nqux" ) ) )
    assert_that( "foo \nbar \nqux",
                 equal_to( iu.RemoveIdentifierFreeText(
                   "foo \nbar `foo`\nqux", filetype = 'go' ) ) )


  def test_ExtractIdentifiersFromText( self ):
    assert_that( [ "foo", "_bar", "BazGoo", "FOO", "_", "x",
                   "one", "two", "moo", "qqq" ],
                 equal_to( iu.ExtractIdentifiersFromText(
                   "foo $_bar \n&BazGoo\n FOO= !!! '-' "
                   "- _ (x) one-two !moo [qqq]" ) ) )


  def test_ExtractIdentifiersFromText_Css( self ):
    assert_that( [ "foo", "-zoo", "font-size", "px", "a99" ],
                 equal_to( iu.ExtractIdentifiersFromText(
                   "foo -zoo {font-size: 12px;} a99", "css" ) ) )


  def test_ExtractIdentifiersFromText_Html( self ):
    assert_that(
      [ "foo", "goo-foo", "zoo", "bar", "aa", "z", "b@g", "fo", "ba" ],
      equal_to(
        iu.ExtractIdentifiersFromText(
          '<foo> <goo-foo zoo=bar aa="" z=\'\'/> b@g fo.ba', "html" ) ) )


  def test_ExtractIdentifiersFromText_Html_TemplateChars( self ):
    assert_that( iu.ExtractIdentifiersFromText( '<foo>{{goo}}</foo>', 'html' ),
                 has_item( 'goo' ) )


  def test_ExtractIdentifiersFromText_JavaScript( self ):
    assert_that( [ "var", "foo", "require", "bar" ],
                 equal_to( iu.ExtractIdentifiersFromText(
                   "var foo = require('bar');", 'javascript' ) ) )


  def test_IsIdentifier_Default( self ):
    assert_that( iu.IsIdentifier( 'foo' ) )
    assert_that( iu.IsIdentifier( 'foo129' ) )
    assert_that( iu.IsIdentifier( 'f12' ) )
    assert_that( iu.IsIdentifier( 'f12' ) )

    assert_that( iu.IsIdentifier( '_foo' ) )
    assert_that( iu.IsIdentifier( '_foo129' ) )
    assert_that( iu.IsIdentifier( '_f12' ) )
    assert_that( iu.IsIdentifier( '_f12' ) )

    assert_that( iu.IsIdentifier( 'uniçode' ) )
    assert_that( iu.IsIdentifier( 'uç' ) )
    assert_that( iu.IsIdentifier( 'ç' ) )
    assert_that( iu.IsIdentifier( 'çode' ) )

    assert_that( not iu.IsIdentifier( '1foo129' ) )
    assert_that( not iu.IsIdentifier( '-foo' ) )
    assert_that( not iu.IsIdentifier( 'foo-' ) )
    assert_that( not iu.IsIdentifier( 'font-face' ) )
    assert_that( not iu.IsIdentifier( None ) )
    assert_that( not iu.IsIdentifier( '' ) )


  def test_IsIdentifier_JavaScript( self ):
    assert_that( iu.IsIdentifier( '_føo1', 'javascript' ) )
    assert_that( iu.IsIdentifier( 'fø_o1', 'javascript' ) )
    assert_that( iu.IsIdentifier( '$føo1', 'javascript' ) )
    assert_that( iu.IsIdentifier( 'fø$o1', 'javascript' ) )

    assert_that( not iu.IsIdentifier( '1føo', 'javascript' ) )


  def test_IsIdentifier_TypeScript( self ):
    assert_that( iu.IsIdentifier( '_føo1', 'typescript' ) )
    assert_that( iu.IsIdentifier( 'fø_o1', 'typescript' ) )
    assert_that( iu.IsIdentifier( '$føo1', 'typescript' ) )
    assert_that( iu.IsIdentifier( 'fø$o1', 'typescript' ) )

    assert_that( not iu.IsIdentifier( '1føo', 'typescript' ) )


  def test_IsIdentifier_Css( self ):
    assert_that( iu.IsIdentifier( 'foo'      , 'css' ) )
    assert_that( iu.IsIdentifier( 'a'        , 'css' ) )
    assert_that( iu.IsIdentifier( 'a1'       , 'css' ) )
    assert_that( iu.IsIdentifier( 'a-'       , 'css' ) )
    assert_that( iu.IsIdentifier( 'a-b'      , 'css' ) )
    assert_that( iu.IsIdentifier( '_b'       , 'css' ) )
    assert_that( iu.IsIdentifier( '-ms-foo'  , 'css' ) )
    assert_that( iu.IsIdentifier( '-_o'      , 'css' ) )
    assert_that( iu.IsIdentifier( 'font-face', 'css' ) )
    assert_that( iu.IsIdentifier( 'αβγ'      , 'css' ) )

    assert_that( not iu.IsIdentifier( '-3b', 'css' ) )
    assert_that( not iu.IsIdentifier( '-3' , 'css' ) )
    assert_that( not iu.IsIdentifier( '--' , 'css' ) )
    assert_that( not iu.IsIdentifier( '3'  , 'css' ) )
    assert_that( not iu.IsIdentifier( ''   , 'css' ) )
    assert_that( not iu.IsIdentifier( '€'  , 'css' ) )


  def test_IsIdentifier_R( self ):
    assert_that( iu.IsIdentifier( 'a'    , 'r' ) )
    assert_that( iu.IsIdentifier( 'a.b'  , 'r' ) )
    assert_that( iu.IsIdentifier( 'a.b.c', 'r' ) )
    assert_that( iu.IsIdentifier( 'a_b'  , 'r' ) )
    assert_that( iu.IsIdentifier( 'a1'   , 'r' ) )
    assert_that( iu.IsIdentifier( 'a_1'  , 'r' ) )
    assert_that( iu.IsIdentifier( '.a'   , 'r' ) )
    assert_that( iu.IsIdentifier( '.a_b' , 'r' ) )
    assert_that( iu.IsIdentifier( '.a1'  , 'r' ) )
    assert_that( iu.IsIdentifier( '...'  , 'r' ) )
    assert_that( iu.IsIdentifier( '..1'  , 'r' ) )

    assert_that( not iu.IsIdentifier( '.1a', 'r' ) )
    assert_that( not iu.IsIdentifier( '.1' , 'r' ) )
    assert_that( not iu.IsIdentifier( '1a' , 'r' ) )
    assert_that( not iu.IsIdentifier( '123', 'r' ) )
    assert_that( not iu.IsIdentifier( '_1a', 'r' ) )
    assert_that( not iu.IsIdentifier( '_a' , 'r' ) )
    assert_that( not iu.IsIdentifier( ''   , 'r' ) )


  def test_IsIdentifier_Clojure( self ):
    assert_that( iu.IsIdentifier( 'foo'  , 'clojure' ) )
    assert_that( iu.IsIdentifier( 'f9'   , 'clojure' ) )
    assert_that( iu.IsIdentifier( 'a.b.c', 'clojure' ) )
    assert_that( iu.IsIdentifier( 'a.c'  , 'clojure' ) )
    assert_that( iu.IsIdentifier( 'a/c'  , 'clojure' ) )
    assert_that( iu.IsIdentifier( '*'    , 'clojure' ) )
    assert_that( iu.IsIdentifier( 'a*b'  , 'clojure' ) )
    assert_that( iu.IsIdentifier( '?'    , 'clojure' ) )
    assert_that( iu.IsIdentifier( 'a?b'  , 'clojure' ) )
    assert_that( iu.IsIdentifier( ':'    , 'clojure' ) )
    assert_that( iu.IsIdentifier( 'a:b'  , 'clojure' ) )
    assert_that( iu.IsIdentifier( '+'    , 'clojure' ) )
    assert_that( iu.IsIdentifier( 'a+b'  , 'clojure' ) )
    assert_that( iu.IsIdentifier( '-'    , 'clojure' ) )
    assert_that( iu.IsIdentifier( 'a-b'  , 'clojure' ) )
    assert_that( iu.IsIdentifier( '!'    , 'clojure' ) )
    assert_that( iu.IsIdentifier( 'a!b'  , 'clojure' ) )

    assert_that( not iu.IsIdentifier( '9f'   , 'clojure' ) )
    assert_that( not iu.IsIdentifier( '9'    , 'clojure' ) )
    assert_that( not iu.IsIdentifier( 'a/b/c', 'clojure' ) )
    assert_that( not iu.IsIdentifier( '(a)'  , 'clojure' ) )
    assert_that( not iu.IsIdentifier( ''     , 'clojure' ) )


  def test_IsIdentifier_Elisp( self ):
    # elisp is using the clojure regexes, so we're testing this more lightly
    assert_that( iu.IsIdentifier( 'foo'  , 'elisp' ) )
    assert_that( iu.IsIdentifier( 'f9'   , 'elisp' ) )
    assert_that( iu.IsIdentifier( 'a.b.c', 'elisp' ) )
    assert_that( iu.IsIdentifier( 'a/c'  , 'elisp' ) )

    assert_that( not iu.IsIdentifier( '9f'   , 'elisp' ) )
    assert_that( not iu.IsIdentifier( '9'    , 'elisp' ) )
    assert_that( not iu.IsIdentifier( 'a/b/c', 'elisp' ) )
    assert_that( not iu.IsIdentifier( '(a)'  , 'elisp' ) )
    assert_that( not iu.IsIdentifier( ''     , 'elisp' ) )


  def test_IsIdentifier_Haskell( self ):
    assert_that( iu.IsIdentifier( 'foo' , 'haskell' ) )
    assert_that( iu.IsIdentifier( "foo'", 'haskell' ) )
    assert_that( iu.IsIdentifier( "x'"  , 'haskell' ) )
    assert_that( iu.IsIdentifier( "_x'" , 'haskell' ) )
    assert_that( iu.IsIdentifier( "_x"  , 'haskell' ) )
    assert_that( iu.IsIdentifier( "x9"  , 'haskell' ) )

    assert_that( not iu.IsIdentifier( "'x", 'haskell' ) )
    assert_that( not iu.IsIdentifier( "9x", 'haskell' ) )
    assert_that( not iu.IsIdentifier( "9" , 'haskell' ) )
    assert_that( not iu.IsIdentifier( ''  , 'haskell' ) )


  def test_IsIdentifier_Tex( self ):
    assert_that( iu.IsIdentifier( 'foo'        , 'tex' ) )
    assert_that( iu.IsIdentifier( 'fig:foo'    , 'tex' ) )
    assert_that( iu.IsIdentifier( 'fig:foo-bar', 'tex' ) )
    assert_that( iu.IsIdentifier( 'sec:summary', 'tex' ) )
    assert_that( iu.IsIdentifier( 'eq:bar_foo' , 'tex' ) )
    assert_that( iu.IsIdentifier( 'fōo'        , 'tex' ) )
    assert_that( iu.IsIdentifier( 'some8'      , 'tex' ) )

    assert_that( not iu.IsIdentifier( '\\section', 'tex' ) )
    assert_that( not iu.IsIdentifier( 'foo:'    , 'tex' ) )
    assert_that( not iu.IsIdentifier( '-bar'    , 'tex' ) )
    assert_that( not iu.IsIdentifier( ''        , 'tex' ) )


  def test_IsIdentifier_Perl6( self ):
    assert_that( iu.IsIdentifier( 'foo'  , 'perl6' ) )
    assert_that( iu.IsIdentifier( "f-o"  , 'perl6' ) )
    assert_that( iu.IsIdentifier( "x'y"  , 'perl6' ) )
    assert_that( iu.IsIdentifier( "_x-y" , 'perl6' ) )
    assert_that( iu.IsIdentifier( "x-y'a", 'perl6' ) )
    assert_that( iu.IsIdentifier( "x-_"  , 'perl6' ) )
    assert_that( iu.IsIdentifier( "x-_7" , 'perl6' ) )
    assert_that( iu.IsIdentifier( "_x"   , 'perl6' ) )
    assert_that( iu.IsIdentifier( "x9"   , 'perl6' ) )

    assert_that( not iu.IsIdentifier( "'x"  , 'perl6' ) )
    assert_that( not iu.IsIdentifier( "x'"  , 'perl6' ) )
    assert_that( not iu.IsIdentifier( "-x"  , 'perl6' ) )
    assert_that( not iu.IsIdentifier( "x-"  , 'perl6' ) )
    assert_that( not iu.IsIdentifier( "x-1" , 'perl6' ) )
    assert_that( not iu.IsIdentifier( "x--" , 'perl6' ) )
    assert_that( not iu.IsIdentifier( "x--a", 'perl6' ) )
    assert_that( not iu.IsIdentifier( "x-'" , 'perl6' ) )
    assert_that( not iu.IsIdentifier( "x-'a", 'perl6' ) )
    assert_that( not iu.IsIdentifier( "x-a-", 'perl6' ) )
    assert_that( not iu.IsIdentifier( "x+"  , 'perl6' ) )
    assert_that( not iu.IsIdentifier( "9x"  , 'perl6' ) )
    assert_that( not iu.IsIdentifier( "9"   , 'perl6' ) )
    assert_that( not iu.IsIdentifier( ''    , 'perl6' ) )


  def test_IsIdentifier_Scheme( self ):
    assert_that( iu.IsIdentifier( 'λ'         , 'scheme' ) )
    assert_that( iu.IsIdentifier( '_'         , 'scheme' ) )
    assert_that( iu.IsIdentifier( '+'         , 'scheme' ) )
    assert_that( iu.IsIdentifier( '-'         , 'scheme' ) )
    assert_that( iu.IsIdentifier( '...'       , 'scheme' ) )
    assert_that( iu.IsIdentifier( r'\x01;'    , 'scheme' ) )
    assert_that( iu.IsIdentifier( r'h\x65;lle', 'scheme' ) )
    assert_that( iu.IsIdentifier( 'foo'       , 'scheme' ) )
    assert_that( iu.IsIdentifier( 'foo+-*/1-1', 'scheme' ) )
    assert_that( iu.IsIdentifier( 'call/cc'   , 'scheme' ) )

    assert_that( not iu.IsIdentifier( '.'            , 'scheme' ) )
    assert_that( not iu.IsIdentifier( '..'           , 'scheme' ) )
    assert_that( not iu.IsIdentifier( '--'           , 'scheme' ) )
    assert_that( not iu.IsIdentifier( '++'           , 'scheme' ) )
    assert_that( not iu.IsIdentifier( '+1'           , 'scheme' ) )
    assert_that( not iu.IsIdentifier( '-1'           , 'scheme' ) )
    assert_that( not iu.IsIdentifier( '-abc'         , 'scheme' ) )
    assert_that( not iu.IsIdentifier( '-<abc'        , 'scheme' ) )
    assert_that( not iu.IsIdentifier( '@'            , 'scheme' ) )
    assert_that( not iu.IsIdentifier( '@a'           , 'scheme' ) )
    assert_that( not iu.IsIdentifier( '-@a'          , 'scheme' ) )
    assert_that( not iu.IsIdentifier( '-12a'         , 'scheme' ) )
    assert_that( not iu.IsIdentifier( '12a'          , 'scheme' ) )
    assert_that( not iu.IsIdentifier( '\\'           , 'scheme' ) )
    assert_that( not iu.IsIdentifier( r'\x'          , 'scheme' ) )
    assert_that( not iu.IsIdentifier( r'\x123'       , 'scheme' ) )
    assert_that( not iu.IsIdentifier( r'aa\x123;cc\x', 'scheme' ) )


  def test_StartOfLongestIdentifierEndingAtIndex_Simple( self ):
    assert_that( 0, equal_to(
      iu.StartOfLongestIdentifierEndingAtIndex( 'foo', 3 ) ) )
    assert_that( 0, equal_to(
      iu.StartOfLongestIdentifierEndingAtIndex( 'f12', 3 ) ) )


  def test_StartOfLongestIdentifierEndingAtIndex_BadInput( self ):
    assert_that( 0, equal_to(
      iu.StartOfLongestIdentifierEndingAtIndex( '', 0 ) ) )
    assert_that( 1, equal_to(
      iu.StartOfLongestIdentifierEndingAtIndex( '', 1 ) ) )
    assert_that( 5, equal_to(
      iu.StartOfLongestIdentifierEndingAtIndex( None, 5 ) ) )
    assert_that( -1, equal_to(
      iu.StartOfLongestIdentifierEndingAtIndex( 'foo', -1 ) ) )
    assert_that( 10, equal_to(
      iu.StartOfLongestIdentifierEndingAtIndex( 'foo', 10 ) ) )


  def test_StartOfLongestIdentifierEndingAtIndex_Punctuation( self ):
    assert_that( 1, equal_to(
      iu.StartOfLongestIdentifierEndingAtIndex( '(foo', 4 ) ) )
    assert_that( 6, equal_to(
      iu.StartOfLongestIdentifierEndingAtIndex( '      foo', 9 ) ) )
    assert_that( 4, equal_to(
      iu.StartOfLongestIdentifierEndingAtIndex( 'gar;foo', 7 ) ) )
    assert_that( 2, equal_to(
      iu.StartOfLongestIdentifierEndingAtIndex( '...', 2 ) ) )


  def test_StartOfLongestIdentifierEndingAtIndex_PunctuationWithUnicode( self ):
    assert_that( 1, equal_to(
      iu.StartOfLongestIdentifierEndingAtIndex( u'(fäö', 4 ) ) )
    assert_that( 2, equal_to(
      iu.StartOfLongestIdentifierEndingAtIndex( u'  fäö', 5 ) ) )


  def test_StartOfLongestIdentifierEndingAtIndex_Entire( self ):
    zipped = zip(
        [ 'foobar', 'f12341234', 'f123f1234', 'fäöttccoö' ],
        [ 'Simple', '1stNonNumber', 'Subidentifier', 'Unicode' ] )
    for i, args in enumerate( zipped ):
      with self.subTest( args[ 1 ], ident = args[ 0 ], i = i ):
        LoopExpectLongestIdentifier( args[ 0 ], 0, i )


  def test_StartOfLongestIdentifierEndingAtIndex_Entire_AllBad( self ):
    ident = '....'
    for i in range( len( ident ) ):
      LoopExpectLongestIdentifier( ident, i, i )


  def test_IdentifierAtIndex_Entire( self ):
    zipped = zip(
        [ 'foobar', 'fäöttccoö' ],
        [ 'Simple', 'Unicode' ] )
    for i, args in enumerate( zipped ):
      with self.subTest( args[ 1 ], i = i, ident = args[ 0 ] ):
        LoopExpectIdentfierAtIndex( args[ 0 ], i, args[ 0 ] )


  def test_IdentifierAtIndex_BadInput( self ):
    assert_that( '', equal_to( iu.IdentifierAtIndex( '', 0 ) ) )
    assert_that( '', equal_to( iu.IdentifierAtIndex( '', 5 ) ) )
    assert_that( '', equal_to( iu.IdentifierAtIndex( 'foo', 5 ) ) )
    assert_that( 'foo', equal_to( iu.IdentifierAtIndex( 'foo', -5 ) ) )


  def test_IdentifierAtIndex_IndexPastIdent( self ):
    assert_that( '', equal_to( iu.IdentifierAtIndex( 'foo    ', 5 ) ) )


  def test_IdentifierAtIndex_StopsAtNonIdentifier( self ):
    assert_that( 'foo', equal_to( iu.IdentifierAtIndex( 'foo(goo)', 0 ) ) )
    assert_that( 'goo', equal_to( iu.IdentifierAtIndex( 'foo(goo)', 5 ) ) )


  def test_IdentifierAtIndex_LooksAhead_Success( self ):
    assert_that( 'goo', equal_to( iu.IdentifierAtIndex( 'foo(goo)', 3 ) ) )
    assert_that( 'goo', equal_to( iu.IdentifierAtIndex( '   goo', 0 ) ) )


  def test_IdentifierAtIndex_LooksAhead_Failure( self ):
    assert_that( '', equal_to( iu.IdentifierAtIndex( 'foo    ()***()', 5 ) ) )


  def test_IdentifierAtIndex_SingleCharIdent( self ):
    assert_that( 'f', equal_to( iu.IdentifierAtIndex( '    f    ', 1 ) ) )


  def test_IdentifierAtIndex_Css( self ):
    assert_that( 'font-face', equal_to(
      iu.IdentifierAtIndex( 'font-face', 0, 'css' ) ) )
