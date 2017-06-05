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

#include "ClangCompleter.h"
#include "CompletionData.h"
#include "../TestUtils.h"

#include <gtest/gtest.h>
#include <gmock/gmock.h>

#include <boost/filesystem.hpp>

namespace YouCompleteMe {

using ::testing::ElementsAre;
using ::testing::WhenSorted;
using ::testing::StrEq;
using ::testing::Property;
using ::testing::Contains;

TEST( ClangCompleterTest, CandidatesForLocationInFile ) {
  ClangCompleter completer;
  std::vector< CompletionData > completions_class =
    completer.CandidatesForLocationInFile(
      PathToTestFile( "basic.cpp" ).string(),
      29,
      7,
      std::vector< UnsavedFile >(),
      std::vector< std::string >() );
  std::vector< CompletionData > completions_struct =
    completer.CandidatesForLocationInFile(
      PathToTestFile( "basic.cpp" ).string(),
      30,
      7,
      std::vector< UnsavedFile >(),
      std::vector< std::string >() );

  ASSERT_TRUE( !completions_struct.empty() );
  ASSERT_TRUE( !completions_class.empty() );
}


TEST( ClangCompleterTest, BufferTextNoParens ) {
  ClangCompleter completer;
  std::vector< CompletionData > completions =
    completer.CandidatesForLocationInFile(
      PathToTestFile( "basic.cpp" ).string(),
      29,
      7,
      std::vector< UnsavedFile >(),
      std::vector< std::string >() );

  ASSERT_TRUE( !completions.empty() );
  EXPECT_THAT( completions,
               Contains(
                 Property( &CompletionData::TextToInsertInBuffer,
                           StrEq( "barbar" ) ) ) );
}


TEST( ClangCompleterTest, MemberFunctionWithDefaults ) {
  ClangCompleter completer;
  std::vector< CompletionData > completions =
    completer.CandidatesForLocationInFile(
      PathToTestFile( "basic.cpp" ).string(),
      30,
      7,
      std::vector< UnsavedFile >(),
      std::vector< std::string >() );

  for ( size_t i = 0; i < completions.size(); ++i ) {
    if ( completions[i].TextToInsertInBuffer() == "foobar" ) {
      EXPECT_STREQ( "foobar( int a, float b, char c )",
                    completions[i].MainCompletionText().c_str() );
      break;
    }
  }
}


TEST( ClangCompleterTest, CandidatesObjCForLocationInFile ) {
  ClangCompleter completer;
  std::vector< std::string > flags;
  flags.push_back( "-x" );
  flags.push_back( "objective-c" );
  std::vector< CompletionData > completions =
    completer.CandidatesForLocationInFile(
      PathToTestFile( "SWObject.m" ).string(),
      6,
      16,
      std::vector< UnsavedFile >(),
      flags );

  ASSERT_TRUE( !completions.empty() );
  EXPECT_THAT( completions[0].TextToInsertInBuffer(), StrEq( "withArg2:" ) );
}


TEST( ClangCompleterTest, CandidatesObjCFuncForLocationInFile ) {
  ClangCompleter completer;
  std::vector< std::string > flags;
  flags.push_back( "-x" );
  flags.push_back( "objective-c" );
  std::vector< CompletionData > completions =
    completer.CandidatesForLocationInFile(
      PathToTestFile( "SWObject.m" ).string(),
      9,
      3,
      std::vector< UnsavedFile >(),
      flags );

  ASSERT_TRUE( !completions.empty() );
  EXPECT_THAT(
    completions[0].TextToInsertInBuffer(),
    StrEq( "(void)test:(int)arg1 withArg2:(int)arg2 withArg3:(int)arg3" ) );
}



TEST( ClangCompleterTest, GetDefinitionLocation ) {
  ClangCompleter completer;
  std::string filename = PathToTestFile( "basic.cpp" ).string();

  // Clang operates on the reasonable assumption that line and column numbers
  // are 1-based.
  Location actual_location_struct =
    completer.GetDefinitionLocation(
      filename,
      26,
      3,
      std::vector< UnsavedFile >(),
      std::vector< std::string >() );

  Location actual_location_class_method =
    completer.GetDefinitionLocation(
      filename,
      29,
      7,
      std::vector< UnsavedFile >(),
      std::vector< std::string >() );

  Location actual_location_class =
    completer.GetDefinitionLocation(
      filename,
      27,
      3,
      std::vector< UnsavedFile >(),
      std::vector< std::string >() );

  Location actual_location_enum_value =
    completer.GetDefinitionLocation(
      filename,
      31,
      25,
      std::vector< UnsavedFile >(),
      std::vector< std::string >() );

  Location actual_location_enum =
    completer.GetDefinitionLocation(
      filename,
      31,
      3,
      std::vector< UnsavedFile >(),
      std::vector< std::string >() );

  EXPECT_EQ( Location( filename, 12, 8 ), actual_location_struct );
  EXPECT_EQ( Location( filename, 1, 7 ), actual_location_class );
  EXPECT_EQ( Location( filename, 22, 35 ), actual_location_enum );
  EXPECT_EQ( Location( filename, 22, 16 ), actual_location_enum_value );
  EXPECT_EQ( Location( filename, 7, 8 ), actual_location_class_method );
}


TEST( ClangCompleterTest, GetDocString ) {
  ClangCompleter completer;

  std::vector< CompletionData > completions =
    completer.CandidatesForLocationInFile(
      PathToTestFile( "basic.cpp" ).string(),
      30,
      7,
      std::vector< UnsavedFile >(),
      std::vector< std::string >() );

  for ( size_t i = 0; i < completions.size(); ++i ) {
    if ( completions[i].TextToInsertInBuffer() == "x" ) {
      EXPECT_STREQ( "A docstring.", completions[i].DocString().c_str() );
      break;
    }
  }
}


TEST( ClangCompleterTest, NoTranslationUnit ) {
  ClangCompleter completer;

  const std::string filename;
  const std::vector< UnsavedFile > unsaved_files;
  const std::vector< std::string > flags;

  EXPECT_EQ( std::vector< Diagnostic >(),
             completer.UpdateTranslationUnit( filename, unsaved_files, flags) );

  EXPECT_EQ( std::vector< CompletionData >(),
             completer.CandidatesForLocationInFile( filename,
                                                    1,
                                                    1,
                                                    unsaved_files,
                                                    flags ) );

  EXPECT_EQ( Location(), completer.GetDeclarationLocation( filename,
                                                           1,
                                                           1,
                                                           unsaved_files,
                                                           flags ) );
  EXPECT_EQ( Location(), completer.GetDefinitionLocation( filename,
                                                          1,
                                                          1,
                                                          unsaved_files,
                                                          flags ) );
  EXPECT_EQ( std::string( "no unit" ),
             completer.GetTypeAtLocation( filename,
                                          1,
                                          1,
                                          unsaved_files,
                                          flags ) );
  EXPECT_EQ( std::string( "no unit" ),
             completer.GetEnclosingFunctionAtLocation( filename,
                                                       1,
                                                       1,
                                                       unsaved_files,
                                                       flags ) );
  EXPECT_EQ( std::vector< FixIt >(),
             completer.GetFixItsForLocationInFile( filename,
                                                   1,
                                                   1,
                                                   unsaved_files,
                                                   flags ) );

  EXPECT_EQ( DocumentationData(),
             completer.GetDocsForLocationInFile( filename,
                                                 1,
                                                 1,
                                                 unsaved_files,
                                                 flags ) );
}

} // namespace YouCompleteMe
