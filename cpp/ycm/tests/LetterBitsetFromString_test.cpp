// Copyright (C) 2011, 2012 Google Inc.
//
// This file is part of ycmd.
//
// ycmd is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// ycmd is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with ycmd.  If not, see <http://www.gnu.org/licenses/>.

#include <gtest/gtest.h>
#include "Candidate.h"

namespace YouCompleteMe {

TEST( LetterBitsetFromStringTest, Basic ) {
  Bitset expected;
  expected.set( IndexForLetter( 'a' ) );
  expected.set( IndexForLetter( 'o' ) );
  expected.set( IndexForLetter( 'c' ) );
  expected.set( IndexForLetter( 'f' ) );
  expected.set( IndexForLetter( 'b' ) );

  std::string text = "abcfoof";
  EXPECT_EQ( expected, LetterBitsetFromString( text ) );
}


TEST( LetterBitsetFromStringTest, Boundaries ) {
  Bitset expected;
  // While the null character (0) is the lower bound, we cannot check it
  // because it is used to terminate a string.
  expected.set( IndexForLetter( 1 ) );
  expected.set( IndexForLetter( 127 ) );

  // \x01 is the start of heading character.
  // \x7f (127) is the delete character.
  // \x80 (-128) and \xff (-1) are out of ASCII characters range and are
  // ignored.
  std::string text = "\x01\x7f\x80\xff";
  EXPECT_EQ( expected, LetterBitsetFromString( text ) );
}


TEST( LetterBitsetFromStringTest, IgnoreNonAsciiCharacters ) {
  Bitset expected;
  expected.set( IndexForLetter( 'u' ) );
  expected.set( IndexForLetter( 'n' ) );
  expected.set( IndexForLetter( 'i' ) );
  expected.set( IndexForLetter( 'd' ) );

  // UTF-8 characters representation:
  //   ¢: \xc2\xa2
  //   €: \xe2\x82\xac
  //   𐍈: \xf0\x90\x8d\x88
  std::string text = "uni¢𐍈d€";
  EXPECT_EQ( expected, LetterBitsetFromString( text ) );
}

} // namespace YouCompleteMe
