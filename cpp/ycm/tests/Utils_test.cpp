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

#include "TestUtils.h"
#include "Utils.h"

#include <gtest/gtest.h>

namespace YouCompleteMe {

class UtilsTest : public ::testing::Test {
protected:
  virtual void SetUp() {
    // The returned temporary path is a symlink on macOS.
    tmp_dir = fs::canonical( fs::temp_directory_path() ) / fs::unique_path();
    existing_path = tmp_dir / "existing_path";
    symlink = tmp_dir / "symlink";
    fs::create_directories( existing_path );
    fs::create_directory_symlink( existing_path, symlink );
  }

  virtual void TearDown() {
    fs::remove_all( tmp_dir );
  }

  fs::path tmp_dir;
  fs::path existing_path;
  fs::path symlink;
};


TEST_F( UtilsTest, IsUppercase ) {
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

TEST_F( UtilsTest, Lowercase ) {
  EXPECT_EQ( Lowercase( 'a' ), 'a' );
  EXPECT_EQ( Lowercase( 'z' ), 'z' );
  EXPECT_EQ( Lowercase( 'A' ), 'a' );
  EXPECT_EQ( Lowercase( 'Z' ), 'z' );
  EXPECT_EQ( Lowercase( ';' ), ';' );

  EXPECT_EQ( Lowercase( "lOwER_CasE" ), "lower_case" );
}


TEST_F( UtilsTest, NormalizePath ) {
  EXPECT_THAT( NormalizePath( "" ),   Equals( fs::current_path() ) );
  EXPECT_THAT( NormalizePath( "." ),  Equals( fs::current_path() ) );
  EXPECT_THAT( NormalizePath( "./" ), Equals( fs::current_path() ) );
  EXPECT_THAT( NormalizePath( existing_path ),       Equals( existing_path ) );
  EXPECT_THAT( NormalizePath( "", existing_path ),   Equals( existing_path ) );
  EXPECT_THAT( NormalizePath( ".", existing_path ),  Equals( existing_path ) );
  EXPECT_THAT( NormalizePath( "./", existing_path ), Equals( existing_path ) );
  EXPECT_THAT( NormalizePath( symlink ),             Equals( existing_path ) );
  EXPECT_THAT( NormalizePath( "", symlink ),         Equals( existing_path ) );
  EXPECT_THAT( NormalizePath( ".", symlink ),        Equals( existing_path ) );
  EXPECT_THAT( NormalizePath( "./", symlink ),       Equals( existing_path ) );
  EXPECT_THAT( NormalizePath( existing_path / "foo/../bar/./xyz//" ),
               Equals( existing_path / "bar" / "xyz" ) );
  EXPECT_THAT( NormalizePath( "foo/../bar/./xyz//", existing_path ),
               Equals( existing_path / "bar" / "xyz" ) );
  EXPECT_THAT( NormalizePath( symlink / "foo/../bar/./xyz//" ),
               Equals( existing_path / "bar" / "xyz" ) );
  EXPECT_THAT( NormalizePath( "foo/../bar/./xyz//", symlink ),
               Equals( existing_path / "bar" / "xyz" ) );
}


} // namespace YouCompleteMe
