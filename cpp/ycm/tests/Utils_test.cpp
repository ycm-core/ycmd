// Copyright (C) 2017 ycmd contributors
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
#include "Utils.h"

namespace YouCompleteMe {

TEST( UtilsTest, IsAcii ) {
  EXPECT_TRUE( IsAscii( '\x00' ) );
  EXPECT_TRUE( IsAscii( '\x7f' ) );

  EXPECT_FALSE( IsAscii( '\x80' ) );
  EXPECT_FALSE( IsAscii( '\xff' ) );
}

TEST( UtilsTest, IsAlpha ) {
  EXPECT_TRUE( IsAlpha( 'a' ) );
  EXPECT_TRUE( IsAlpha( 'm' ) );
  EXPECT_TRUE( IsAlpha( 'z' ) );
  EXPECT_TRUE( IsAlpha( 'A' ) );
  EXPECT_TRUE( IsAlpha( 'M' ) );
  EXPECT_TRUE( IsAlpha( 'Z' ) );

  EXPECT_FALSE( IsAlpha( '/' ) );
  EXPECT_FALSE( IsAlpha( '*' ) );
  EXPECT_FALSE( IsAlpha( '.' ) );
}

TEST( UtilsTest, IsPrintable ) {
  EXPECT_TRUE( IsPrintable( 'b' ) );
  EXPECT_TRUE( IsPrintable( 'R' ) );
  EXPECT_TRUE( IsPrintable( '&' ) );
  EXPECT_TRUE( IsPrintable( '(' ) );

  EXPECT_FALSE( IsPrintable( '\b' ) );
  EXPECT_FALSE( IsPrintable( '\n' ) );
  EXPECT_FALSE( IsPrintable( '\r' ) );
  EXPECT_FALSE( IsPrintable( '\f' ) );

  EXPECT_TRUE( IsPrintable( "Is Printable" ) );

  EXPECT_FALSE( IsPrintable( "Not\nPrintable" ) );
}

TEST( UtilsTest, IsPunctuation ) {
  EXPECT_TRUE( IsPunctuation( '-' ) );
  EXPECT_TRUE( IsPunctuation( '_' ) );
  EXPECT_TRUE( IsPunctuation( '!' ) );
  EXPECT_TRUE( IsPunctuation( '<' ) );

  EXPECT_FALSE( IsPunctuation( 'c' ) );
  EXPECT_FALSE( IsPunctuation( 'I' ) );
  EXPECT_FALSE( IsPunctuation( '0' ) );
  EXPECT_FALSE( IsPunctuation( '\t' ) );
}

TEST( UtilsTest, IsLowercase ) {
  EXPECT_TRUE( IsLowercase( 'a' ) );
  EXPECT_TRUE( IsLowercase( 'm' ) );
  EXPECT_TRUE( IsLowercase( 'z' ) );

  EXPECT_FALSE( IsLowercase( 'A' ) );
  EXPECT_FALSE( IsLowercase( 'M' ) );
  EXPECT_FALSE( IsLowercase( 'Z' ) );

  EXPECT_FALSE( IsLowercase( ']' ) );
  EXPECT_FALSE( IsLowercase( '+' ) );
  EXPECT_FALSE( IsLowercase( '\a' ) );

  EXPECT_TRUE( IsLowercase( "is-lowercase" ) );

  EXPECT_FALSE( IsLowercase( "NotLowerCase" ) );
}

TEST( UtilsTest, IsUppercase ) {
  EXPECT_TRUE( IsUppercase( 'A' ) );
  EXPECT_TRUE( IsUppercase( 'B' ) );
  EXPECT_TRUE( IsUppercase( 'Z' ) );

  EXPECT_FALSE( IsUppercase( 'a' ) );
  EXPECT_FALSE( IsUppercase( 'b' ) );
  EXPECT_FALSE( IsUppercase( 'z' ) );

  EXPECT_FALSE( IsUppercase( '$' ) );
  EXPECT_FALSE( IsUppercase( '@' ) );
  EXPECT_FALSE( IsUppercase( '~' ) );
}

TEST( UtilsTest, Lowercase ) {
  EXPECT_EQ( Lowercase( 'a' ), 'a' );
  EXPECT_EQ( Lowercase( 'z' ), 'z' );
  EXPECT_EQ( Lowercase( 'A' ), 'a' );
  EXPECT_EQ( Lowercase( 'Z' ), 'z' );
  EXPECT_EQ( Lowercase( ';' ), ';' );
}

TEST( UtilsTest, Uppercase ) {
  EXPECT_EQ( Uppercase( 'a' ), 'A' );
  EXPECT_EQ( Uppercase( 'z' ), 'Z' );
  EXPECT_EQ( Uppercase( 'A' ), 'A' );
  EXPECT_EQ( Uppercase( 'Z' ), 'Z' );
  EXPECT_EQ( Uppercase( '`' ), '`' );
}

TEST( UtilsTest, HasUppercase ) {
  EXPECT_TRUE( HasUppercase( "HasUppercase" ) );

  EXPECT_FALSE( HasUppercase( "has_uppercase" ) );
}

TEST( UtilsTest, SwapCase ) {
  EXPECT_EQ( SwapCase( 'a' ), 'A' );
  EXPECT_EQ( SwapCase( 'z' ), 'Z' );
  EXPECT_EQ( SwapCase( 'A' ), 'a' );
  EXPECT_EQ( SwapCase( 'Z' ), 'z' );
  EXPECT_EQ( SwapCase( '/' ), '/' );

  EXPECT_EQ( SwapCase( "SwAp_CasE" ), "sWaP_cASe" );
}

} // namespace YouCompleteMe
