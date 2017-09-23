// Copyright (C) 2017-2018 ycmd contributors
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

  EXPECT_EQ( Lowercase( "lOwER_CasE" ), "lower_case" );
}

} // namespace YouCompleteMe
