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
#include "LetterNodeListMap.h"

namespace YouCompleteMe {

TEST( IsUppercaseTest, Basic ) {
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

} // namespace YouCompleteMe

