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

"""This tests the comment "sanitisation" which is done on C/C++/ObjC
method/variable,etc. headers in order to remove non-data-ink from the raw
comment"""


# flake8: noqa
from hamcrest import assert_that, equal_to
from unittest import TestCase
from ycmd.completers.cpp import clang_completer


def _Check_FormatRawComment( comment, expected ):
  try:
    result = clang_completer._FormatRawComment( comment )
    assert_that( result, equal_to( expected ) )
  except:
    print( "Failed while parsing:\n"
           "'" + comment + "'\n"
           "Expecting:\n"
           "'" + expected + "'\n"
           "But found:\n"
           "'" + result + "'" )
    raise


class CommentStripTest( TestCase ):
  def test_ClangCompleter_FormatRawComment_SingleLine_Doxygen( self ):
    # - <whitespace>///

    # Indent + /// +
    _Check_FormatRawComment( '    /// Single line comment',
                             'Single line comment' )

    # No indent, Internal indent removed, trailing whitespace removed
    _Check_FormatRawComment( '///      Single line comment    ',
                             'Single line comment' )

    # Extra / prevents initial indent being removed
    _Check_FormatRawComment( '////      Single line comment    ',
                             '/      Single line comment' )
    _Check_FormatRawComment( '////* Test	', '/* Test' )


  def test_ClangCompleter_FormatRawComment_SingleLine_InlineDoxygen( self ):
    # Inline-style comments with and without leading/trailing tokens
    # - <whitespace>///<
    _Check_FormatRawComment( '///<Test', 'Test' )
    _Check_FormatRawComment( '  ///<Test */', 'Test' )
    _Check_FormatRawComment( '///<Test  ', 'Test' )
    _Check_FormatRawComment( '///< Test  ', 'Test' )
    _Check_FormatRawComment( ' ///<< Test  ', '< Test' )
    _Check_FormatRawComment( ' ///<! Test  ', '! Test' )


  def test_ClangCompleter_FormatRawComment_SingleLine_InlineShort( self ):
    # - <whitespace>//<
    _Check_FormatRawComment( '//<Test', 'Test' )
    _Check_FormatRawComment( '	//<Test', 'Test' )
    _Check_FormatRawComment( '//<Test', 'Test' )
    _Check_FormatRawComment( '//< Test', 'Test' )
    _Check_FormatRawComment( '//<< Test  ', '< Test' )


  def test_ClangCompleter_FormatRawComment_SingleLine_InlineShortBang( self ):
    # - <whitespace>//!
    _Check_FormatRawComment( '//!Test', 'Test' )
    _Check_FormatRawComment( '	//<Test */	', 'Test' )
    _Check_FormatRawComment( '//!Test  ', 'Test' )
    _Check_FormatRawComment( '//! Test	', 'Test' )
    _Check_FormatRawComment( '//!! Test  ', '! Test' )


  def test_ClangCompleter_FormatRawComment_SingleLine_JavaDoc( self ):
    # - <whitespace>/*
    # - <whitespace>/**
    # - <whitespace>*/
    _Check_FormatRawComment( '/*Test', 'Test' )
    _Check_FormatRawComment( '	/** Test */    ', 'Test' )
    _Check_FormatRawComment( '/*** Test', '* Test' )


  def test_ClangCompleter_FormatRawComment_MultiOneLine_JavaDoc( self ):
    # sic: This one isn't ideal, but it is (probably) uncommon
    _Check_FormatRawComment( '/** Test */ /** Test2 */',
                             'Test */ /** Test2' )


  def test_ClangCompleter_FormatRawComment_MultiLine_Doxygen_Inbalance( self ):
    # The dedenting only applies to consistent indent
    # Note trailing whitespace is intentional
    _Check_FormatRawComment(
  """
      /// This is
      ///    a
      ///Multi-line
    /// Comment	
/// 	 With many different */ 	
      ///< Doxygen-like    
      ///!   comment   ****/ Entries
      
  """,
  """
 This is
    a
Multi-line
 Comment
 	 With many different
 Doxygen-like
   comment   ****/ Entries

""" ) # noqa

  def test_ClangCompleter_FormatRawComment_MultiLine_JavaDoc_Inconsistent( self ):
    # The dedenting only applies to consistent indent, and leaves any subsequent
    # indent intact
    # Note trailing whitespace is intentional
    _Check_FormatRawComment(
  """
      /**  All of the 
    *  Lines in this	
  	Comment consistently
           *  * Have a 2-space indent */  
  """,
  """
All of the
Lines in this
	Comment consistently
* Have a 2-space indent
""" ) # noqa

  def test_ClangCompleter_FormatRawComment_ZeroLine( self ):
    _Check_FormatRawComment( '', '' )


  def test_ClangCompleter_FormatRawComment_MultiLine_empty( self ):
    # Note trailing whitespace is intentional
    _Check_FormatRawComment(
  """
    

  *
///   
  */
  """,
  """





""" ) # noqa
