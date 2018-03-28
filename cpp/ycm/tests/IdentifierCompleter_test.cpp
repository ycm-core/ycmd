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

#include <gtest/gtest.h>
#include <gmock/gmock.h>
#include "IdentifierCompleter.h"
#include "Utils.h"
#include "TestUtils.h"

using ::testing::ElementsAre;
using ::testing::IsEmpty;
using ::testing::WhenSorted;

namespace YouCompleteMe {

TEST( IdentifierCompleterTest, SortOnEmptyQuery ) {
  EXPECT_THAT( IdentifierCompleter( {
                 "foo",
                 "bar" } ).CandidatesForQuery( "" ),
               ElementsAre( "bar",
                            "foo" ) );
}

TEST( IdentifierCompleterTest, IgnoreEmptyCandidate ) {
  EXPECT_THAT( IdentifierCompleter( {
                 "" } ).CandidatesForQuery( "" ),
               IsEmpty() );
}

TEST( IdentifierCompleterTest, IgnoreCandidatesShorterThanQuery ) {
  EXPECT_THAT( IdentifierCompleter( {
                 "fo",
                 "foo" } ).CandidatesForQuery( "fooo" ),
               IsEmpty() );
}

TEST( IdentifierCompleterTest, NoDuplicatesReturned ) {
  EXPECT_THAT( IdentifierCompleter( {
                 "foobar",
                 "foobar",
                 "foobar" } ).CandidatesForQuery( "foo" ),
               ElementsAre( "foobar" ) );
}


TEST( IdentifierCompleterTest, OneCandidate ) {
  EXPECT_THAT( IdentifierCompleter( {
                 "foobar" } ).CandidatesForQuery( "fbr" ),
               ElementsAre( "foobar" ) );
}

TEST( IdentifierCompleterTest, ManyCandidateSimple ) {
  EXPECT_THAT( IdentifierCompleter( {
                 "foobar",
                 "foobartest",
                 "Foobartest" } ).CandidatesForQuery( "fbr" ),
               WhenSorted( ElementsAre( "Foobartest",
                                        "foobar",
                                        "foobartest" ) ) );
}

TEST( IdentifierCompleterTest, SmartCaseFiltering ) {
  EXPECT_THAT( IdentifierCompleter( {
                 "fooBar",
                 "fooBaR" } ).CandidatesForQuery( "fBr" ),
               ElementsAre( "fooBaR",
                            "fooBar" ) );
}

TEST( IdentifierCompleterTest, FirstCharSameAsQueryWins ) {
  EXPECT_THAT( IdentifierCompleter( {
                 "foobar",
                 "afoobar" } ).CandidatesForQuery( "fbr" ),
               ElementsAre( "foobar",
                            "afoobar" ) );
}

TEST( IdentifierCompleterTest, CompleteMatchForWordBoundaryCharsWins ) {
  EXPECT_THAT( IdentifierCompleter( {
                 "FooBarQux",
                 "FBaqux" } ).CandidatesForQuery( "fbq" ),
               ElementsAre( "FooBarQux",
                            "FBaqux" ) );

  EXPECT_THAT( IdentifierCompleter( {
                 "CompleterTest",
                 "CompleteMatchForWordBoundaryCharsWins" } )
               .CandidatesForQuery( "ct" ),
               ElementsAre( "CompleterTest",
                            "CompleteMatchForWordBoundaryCharsWins" ) );

  EXPECT_THAT( IdentifierCompleter( {
                 "FooBar",
                 "FooBarRux" } ).CandidatesForQuery( "fbr" ),
               ElementsAre( "FooBarRux",
                            "FooBar" ) );

  EXPECT_THAT( IdentifierCompleter( {
                 "foo-bar",
                 "foo-bar-rux" } ).CandidatesForQuery( "fbr" ),
               ElementsAre( "foo-bar-rux",
                            "foo-bar" ) );

  EXPECT_THAT( IdentifierCompleter( {
                 "foo.bar",
                 "foo.bar.rux" } ).CandidatesForQuery( "fbr" ),
               ElementsAre( "foo.bar.rux",
                            "foo.bar" ) );
}

TEST( IdentifierCompleterTest, RatioUtilizationTieBreak ) {
  EXPECT_THAT( IdentifierCompleter( {
                 "aGaaFooBarQux",
                 "aBaafbq" } ).CandidatesForQuery( "fbq" ),
               ElementsAre( "aGaaFooBarQux",
                            "aBaafbq" ) );

  EXPECT_THAT( IdentifierCompleter( {
                 "aFooBarQux",
                 "afbq" } ).CandidatesForQuery( "fbq" ),
               ElementsAre( "aFooBarQux",
                            "afbq" ) );

  EXPECT_THAT( IdentifierCompleter( {
                 "acaaCaaFooGxx",
                 "aCaafoog" } ).CandidatesForQuery( "caafoo" ),
               ElementsAre( "acaaCaaFooGxx",
                            "aCaafoog" ) );

  EXPECT_THAT( IdentifierCompleter( {
                 "FooBarQux",
                 "FooBarQuxZaa" } ).CandidatesForQuery( "fbq" ),
               ElementsAre( "FooBarQux",
                            "FooBarQuxZaa" ) );

  EXPECT_THAT( IdentifierCompleter( {
                 "FooBar",
                 "FooBarRux" } ).CandidatesForQuery( "fba" ),
               ElementsAre( "FooBar",
                            "FooBarRux" ) );
}

TEST( IdentifierCompleterTest, QueryPrefixOfCandidateWins ) {
  EXPECT_THAT( IdentifierCompleter( {
                 "foobar",
                 "fbaroo" } ).CandidatesForQuery( "foo" ),
               ElementsAre( "foobar",
                            "fbaroo" ) );
}

TEST( IdentifierCompleterTest, LowerMatchCharIndexSumWins ) {
  EXPECT_THAT( IdentifierCompleter( {
                 "ratio_of_word_boundary_chars_in_query_",
                 "first_char_same_in_query_and_text_"
               } ).CandidatesForQuery( "charinq" ),
               ElementsAre( "first_char_same_in_query_and_text_",
                            "ratio_of_word_boundary_chars_in_query_" ) );

  EXPECT_THAT( IdentifierCompleter( {
                 "barfooq",
                 "barquxfoo" } ).CandidatesForQuery( "foo" ),
               ElementsAre( "barfooq",
                            "barquxfoo" ) );

  EXPECT_THAT( IdentifierCompleter( {
                 "xxxxxxabc",
                 "xxabcxxxx" } ).CandidatesForQuery( "abc" ),
               ElementsAre( "xxabcxxxx",
                            "xxxxxxabc" ) );

  EXPECT_THAT( IdentifierCompleter( {
                 "FooBarQux",
                 "FaBarQux" } ).CandidatesForQuery( "fbq" ),
               ElementsAre( "FaBarQux",
                            "FooBarQux" ) );
}

TEST( IdentifierCompleterTest, ShorterCandidateWins ) {
  EXPECT_THAT( IdentifierCompleter( {
                 "CompleterT",
                 "CompleterTest" } ).CandidatesForQuery( "co" ),
               ElementsAre( "CompleterT",
                            "CompleterTest" ) );

  EXPECT_THAT( IdentifierCompleter( {
                 "CompleterT",
                 "CompleterTest" } ).CandidatesForQuery( "plet" ),
               ElementsAre( "CompleterT",
                            "CompleterTest" ) );
}

TEST( IdentifierCompleterTest, SameLowercaseCandidateWins ) {
  EXPECT_THAT( IdentifierCompleter( {
                 "foobar",
                 "Foobar" } ).CandidatesForQuery( "foo" ),
               ElementsAre( "foobar",
                            "Foobar" ) );

}

TEST( IdentifierCompleterTest, PreferLowercaseCandidate ) {
  EXPECT_THAT( IdentifierCompleter( {
                 "chatContentExtension",
                 "ChatContentExtension"
               } ).CandidatesForQuery( "chatContent" ),
               ElementsAre( "chatContentExtension",
                            "ChatContentExtension" ) );

  EXPECT_THAT( IdentifierCompleter( {
                 "fooBar",
                 "FooBar" } ).CandidatesForQuery( "oba" ),
               ElementsAre( "fooBar",
                            "FooBar" ) );
}

TEST( IdentifierCompleterTest, ShorterAndLowercaseWins ) {
  EXPECT_THAT( IdentifierCompleter( {
                 "STDIN_FILENO",
                 "stdin" } ).CandidatesForQuery( "std" ),
               ElementsAre( "stdin",
                            "STDIN_FILENO" ) );
}


TEST( IdentifierCompleterTest, NonAlnumChars ) {
  EXPECT_THAT( IdentifierCompleter( {
                 "font-family",
                 "font-face" } ).CandidatesForQuery( "fo" ),
               ElementsAre( "font-face",
                            "font-family" ) );
}


TEST( IdentifierCompleterTest, NonAlnumStartChar ) {
  EXPECT_THAT( IdentifierCompleter( {
                 "-zoo-foo" } ).CandidatesForQuery( "-z" ),
               ElementsAre( "-zoo-foo" ) );
}


TEST( IdentifierCompleterTest, UnicodeCandidates ) {
  EXPECT_THAT( IdentifierCompleter( {
                 "uni¢𐍈d€" } ).CandidatesForQuery( "¢" ),
               ElementsAre( "uni¢𐍈d€" ) );
}


TEST( IdentifierCompleterTest, NonPrintableCandidates ) {
  EXPECT_THAT( IdentifierCompleter( {
                 "\x01\x1f\x7f" } ).CandidatesForQuery( "\x1f" ),
               ElementsAre( "\x01\x1f\x7f" ) );
}


TEST( IdentifierCompleterTest, LotOfCandidates ) {
  // Generate a lot of candidates of the form [a-z]{5} in reverse order.
  std::vector< std::string > candidates;
  for ( int i = 0; i < 2048; ++i ) {
    std::string candidate = "";
    int letter = i;
    for ( int pos = 0; pos < 5; letter /= 26, ++pos ) {
      candidate = std::string( 1, letter % 26 + 'a' ) + candidate;
    }
    candidates.insert( candidates.begin(), candidate );
  }

  IdentifierCompleter completer( candidates );

  std::reverse( candidates.begin(), candidates.end() );

  EXPECT_THAT( completer.CandidatesForQuery( "aa" ),
               candidates );

  EXPECT_THAT( completer.CandidatesForQuery( "aa", 2 ),
               ElementsAre( "aaaaa",
                            "aaaab" ) );
}


TEST( IdentifierCompleterTest, TagsEndToEndWorks ) {
  IdentifierCompleter completer;
  std::vector< std::string > tag_files;
  tag_files.push_back( PathToTestFile( "basic.tags" ).string() );

  completer.AddIdentifiersToDatabaseFromTagFiles( tag_files );

  EXPECT_THAT( completer.CandidatesForQueryAndType( "fo", "cpp" ),
               ElementsAre( "foosy",
                            "fooaaa" ) );

}


// Filetype checking
TEST( IdentifierCompleterTest, ManyCandidateSimpleFileType ) {
  IdentifierCompleter completer;
  EXPECT_THAT( IdentifierCompleter( {
                 "foobar",
                 "foobartest",
                 "Foobartest"
               }, "c", "foo" ).CandidatesForQueryAndType( "fbr", "c" ),
               WhenSorted( ElementsAre( "Foobartest",
                                        "foobar",
                                        "foobartest" ) ) );
}


TEST( IdentifierCompleterTest, ManyCandidateSimpleWrongFileType ) {
  IdentifierCompleter completer;
  EXPECT_THAT( IdentifierCompleter( {
                 "foobar",
                 "foobartest",
                 "Foobartest"
               }, "c", "foo" ).CandidatesForQueryAndType( "fbr", "cpp" ),
               IsEmpty() );
}

} // namespace YouCompleteMe

