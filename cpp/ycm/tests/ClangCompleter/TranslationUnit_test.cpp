// Copyright (C) 2011-2018 ycmd contributors
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

#include "CompletionData.h"
#include "TranslationUnitStore.h"
#include "Utils.h"
#include "../TestUtils.h"

#include <gtest/gtest.h>
#include <gmock/gmock.h>

#include <clang-c/Index.h>

using ::testing::ElementsAre;
using ::testing::WhenSorted;

namespace YouCompleteMe {

class TranslationUnitTest : public ::testing::Test {
protected:
  virtual void SetUp() {
    clang_index_ = clang_createIndex( 0, 0 );
  }

  virtual void TearDown() {
    clang_disposeIndex( clang_index_ );
  }

  CXIndex clang_index_;
};


TEST_F( TranslationUnitTest, ExceptionThrownOnParseFailure ) {
  // Create a translation unit for a C++ file that is not saved on disk.
  std::string filename = PathToTestFile( "unsaved_file.cpp" ).string();
  UnsavedFile unsaved_file;
  unsaved_file.filename_ = filename;

  try {
    // libclang requires a valid index to parse a file.
    TranslationUnit( filename,
                     std::vector< UnsavedFile >{ unsaved_file },
                     std::vector< std::string >(),
                     nullptr );
    FAIL() << "Expected ClangParseError exception.";
  } catch ( const ClangParseError &error ) {
    EXPECT_STREQ( error.what(), "Invalid arguments supplied "
                                "when parsing the translation unit." );
  } catch ( ... ) {
    FAIL() << "Expected ClangParseError exception.";
  }
}

TEST_F( TranslationUnitTest, GoToDefinitionWorks ) {
  auto test_file = PathToTestFile( "goto.cpp" ).string();
  TranslationUnit unit( test_file,
                        std::vector< UnsavedFile >(),
                        std::vector< std::string >(),
                        clang_index_ );

  Location location = unit.GetDefinitionLocation(
                        test_file,
                        17,
                        3,
                        std::vector< UnsavedFile >() );

  EXPECT_EQ( 1, location.line_number_ );
  EXPECT_EQ( 8, location.column_number_ );
  EXPECT_TRUE( !location.filename_.empty() );
}

TEST_F( TranslationUnitTest, GoToDefinitionFails ) {
  auto test_file = PathToTestFile( "goto.cpp" ).string();
  TranslationUnit unit( test_file,
                        std::vector< UnsavedFile >(),
                        std::vector< std::string >(),
                        clang_index_ );

  Location location = unit.GetDefinitionLocation(
                        test_file,
                        19,
                        3,
                        std::vector< UnsavedFile >() );

  EXPECT_FALSE( location.IsValid() );
}

TEST_F( TranslationUnitTest, GoToDeclarationWorks ) {
  auto test_file = PathToTestFile( "goto.cpp" ).string();
  TranslationUnit unit( test_file,
                        std::vector< UnsavedFile >(),
                        std::vector< std::string >(),
                        clang_index_ );

  Location location = unit.GetDeclarationLocation(
                        test_file,
                        19,
                        3,
                        std::vector< UnsavedFile >() );

  EXPECT_EQ( 12, location.line_number_ );
  EXPECT_EQ( 8, location.column_number_ );
  EXPECT_TRUE( !location.filename_.empty() );
}

TEST_F( TranslationUnitTest, GoToDeclarationWorksOnDefinition ) {
  auto test_file = PathToTestFile( "goto.cpp" ).string();
  TranslationUnit unit( test_file,
                        std::vector< UnsavedFile >(),
                        std::vector< std::string >(),
                        clang_index_ );

  Location location = unit.GetDeclarationLocation(
                        test_file,
                        16,
                        6,
                        std::vector< UnsavedFile >() );

  EXPECT_EQ( 14, location.line_number_ );
  EXPECT_EQ( 6, location.column_number_ );
  EXPECT_TRUE( !location.filename_.empty() );
}


TEST_F( TranslationUnitTest, GoToWorks ) {
  auto test_file = PathToTestFile( "goto.cpp" ).string();
  TranslationUnit unit( test_file,
                        std::vector< UnsavedFile >(),
                        std::vector< std::string >(),
                        clang_index_ );

  Location location = unit.GetDefinitionOrDeclarationLocation(
                        test_file,
                        16,
                        8,
                        std::vector< UnsavedFile >() );

  EXPECT_EQ( 14, location.line_number_ );
  EXPECT_EQ( 6, location.column_number_ );
  EXPECT_TRUE( !location.filename_.empty() );

  location = unit.GetDefinitionOrDeclarationLocation(
               test_file,
               14,
               9,
               std::vector< UnsavedFile >() );

  EXPECT_EQ( 16, location.line_number_ );
  EXPECT_EQ( 6, location.column_number_ );
  EXPECT_TRUE( !location.filename_.empty() );
}


TEST_F( TranslationUnitTest, InvalidTranslationUnitStore ) {
  // libclang fails to parse a file with no extension and no language flag -x
  // given.
  TranslationUnitStore translation_unit_store{ clang_index_ };
  try {
    translation_unit_store.GetOrCreate(
      PathToTestFile( "file_without_extension" ).string(),
      std::vector< UnsavedFile >(),
      std::vector< std::string >() );
    FAIL() << "Expected ClangParseError exception.";
  } catch ( const ClangParseError &error ) {
    EXPECT_STREQ( error.what(),
                  "An AST deserialization error occurred while parsing "
                  "the translation unit." );
  } catch ( ... ) {
    FAIL() << "Expected ClangParseError exception.";
  }
}


TEST_F( TranslationUnitTest, InvalidTranslationUnit ) {

  TranslationUnit unit;

  EXPECT_TRUE( unit.IsCurrentlyUpdating() );

  std::vector< CompletionData > completion_data_vector =
      unit.CandidatesForLocation( "", 1, 1, std::vector< UnsavedFile >() );
  EXPECT_TRUE( completion_data_vector.empty() );

  EXPECT_EQ( Location(),
             unit.GetDeclarationLocation( "",
                                          1,
                                          1,
                                          std::vector< UnsavedFile >() ) );

  EXPECT_EQ( Location(),
             unit.GetDefinitionLocation( "",
                                         1,
                                         1,
                                         std::vector< UnsavedFile >() ) );

  EXPECT_EQ( Location(),
             unit.GetDefinitionOrDeclarationLocation(
               "",
               1,
               1,
               std::vector< UnsavedFile >() ) );

  EXPECT_EQ( std::string( "Internal error: no translation unit" ),
             unit.GetTypeAtLocation( "",
                                     1,
                                     1,
                                     std::vector< UnsavedFile >() ) );

  EXPECT_EQ( std::string( "Internal error: no translation unit" ),
             unit.GetEnclosingFunctionAtLocation(
               "",
               1,
               1,
               std::vector< UnsavedFile >() ) );

  EXPECT_EQ( DocumentationData(),
             unit.GetDocsForLocation( Location(),
                                      std::vector< UnsavedFile >(),
                                      false ) );
}

} // namespace YouCompleteMe
