// Copyright (C) 2011, 2012  Google Inc.
//
// This file is part of YouCompleteMe.
//
// YouCompleteMe is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// YouCompleteMe is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with YouCompleteMe.  If not, see <http://www.gnu.org/licenses/>.

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

// These two functions override the output for readability when gmock
// prints CompletionData and CompletionChunk objects.
std::ostream &operator<<( std::ostream &os, CompletionChunk const &part ) {
  os << "\"" << part.Chunk() << "\"";
  if ( part.placeholder_ ) os << "(placeholder)";
  return os;
}

std::ostream &operator<<( std::ostream &os, CompletionData const &data ) {
  os << "\"" << data.TypedString() << "\"" << " ( " ;
  for ( size_t i = 0; i < data.CompletionChunks().size(); i++ ) {
    if ( i > 0 ) os << " ";
    os << data.CompletionChunks()[i];
  }
  os << " )";
  return os;
}

TEST( ClangCompleterTest, CandidatesForLocationInFile ) {
  ClangCompleter completer;
  std::vector< CompletionData > completions =
    completer.CandidatesForLocationInFile(
      PathToTestFile( "basic.cpp" ).string(),
      15,
      7,
      std::vector< UnsavedFile >(),
      std::vector< std::string >() );

  EXPECT_TRUE( !completions.empty() );
  EXPECT_THAT( completions,
               Contains(
                 AllOf(
                   Property( &CompletionData::TypedString,
                             StrEq( "foobar" ) ),
                   Property( &CompletionData::CompletionChunks,
                             ElementsAre(
                               CompletionChunk( "foobar()" )
                             ) )
                 ) ) );
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

  EXPECT_TRUE( !completions.empty() );
  EXPECT_THAT( completions,
               Contains(
                 AllOf(
                   Property( &CompletionData::TypedString,
                             StrEq( "withArg2:withArg3:" ) ),
                   Property( &CompletionData::CompletionChunks,
                             ElementsAre(
                               CompletionChunk( "withArg2:" ),
                               CompletionChunk( "(int)", true ),
                               CompletionChunk( " withArg3:" ),
                               CompletionChunk( "(int)", true )
                             ) )
                 ) ) );
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

  EXPECT_TRUE( !completions.empty() );
  EXPECT_THAT( completions,
               Contains(
                 AllOf(
                   Property( &CompletionData::TypedString,
                             StrEq( "test:withArg2:withArg3:" ) ),
                   Property( &CompletionData::CompletionChunks,
                             ElementsAre(
                               CompletionChunk( "(void)test:(int)arg1 withArg2:(int)arg2 withArg3:(int)arg3" )
                             ) )
                 ) ) );
}



TEST( ClangCompleterTest, GetDefinitionLocation ) {
  ClangCompleter completer;
  std::string filename = PathToTestFile( "basic.cpp" ).string();

  // Clang operates on the reasonable assumption that line and column numbers
  // are 1-based.
  Location actual_location =
    completer.GetDefinitionLocation(
      filename,
      13,
      3,
      std::vector< UnsavedFile >(),
      std::vector< std::string >() );

  EXPECT_EQ( Location( filename, 1, 8 ), actual_location );
}


TEST( ClangCompleterTest, GetDocString ) {
  ClangCompleter completer;

  std::vector< CompletionData > completions =
    completer.CandidatesForLocationInFile(
      PathToTestFile( "basic.cpp" ).string(),
      11,
      7,
      std::vector< UnsavedFile >(),
      std::vector< std::string >() );

  for ( size_t i = 0; i < completions.size(); ++i ) {
    if ( completions[i].DisplayString() == "x" ) {
      EXPECT_STREQ( "A docstring.", completions[i].DocString().c_str() );
      break;
    }
  }
}

} // namespace YouCompleteMe
