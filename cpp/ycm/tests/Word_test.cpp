// Copyright (C) 2018 ycmd contributors
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

#include "Character.h"
#include "CharacterRepository.h"
#include "TestUtils.h"
#include "Word.h"

#include <array>
#include <gtest/gtest.h>
#include <gmock/gmock.h>

using ::testing::TestWithParam;
using ::testing::ValuesIn;

namespace YouCompleteMe {

class WordTest : public TestWithParam< WordTuple > {
protected:
  WordTest()
    : repo_( CharacterRepository::Instance() ) {
  }

  virtual void SetUp() {
    repo_.ClearCharacters();
    word_ = WordTuple( GetParam() );
  }

  CharacterRepository &repo_;
  WordTuple word_;
};


std::ostream& operator<<( std::ostream& os,
                          const CharacterSequence &characters ) {
  os << PrintToString( characters );
  return os;
}


TEST_P( WordTest, BreakIntoCharacters ) {
  std::vector< std::string > characters;
  for ( const auto &character : word_.characters_ ) {
    characters.push_back( character );
  }
  EXPECT_THAT( Word( word_.text_ ).Characters(),
               ContainsPointees( repo_.GetCharacters(
                                 std::move( characters ) ) ) );
}


// Tests generated from
// https://www.unicode.org/Public/UCD/latest/ucd/auxiliary/GraphemeBreakTest.txt
const WordTuple tests[] = {
#include "GraphemeBreakCases.inc"
};


INSTANTIATE_TEST_SUITE_P( UnicodeTest, WordTest, ValuesIn( tests ) );


TEST( WordTest, MatchesBytes ) {
  Word word( "f𐍈oβaＡaR" );

  EXPECT_TRUE( word.ContainsBytes( Word( "f𐍈oβaＡar" ) ) );
  EXPECT_TRUE( word.ContainsBytes( Word( "F𐍈oβaａaR" ) ) );
  EXPECT_TRUE( word.ContainsBytes( Word( "foΒar"    ) ) );
  EXPECT_TRUE( word.ContainsBytes( Word( "RＡβof"    ) ) );
  EXPECT_TRUE( word.ContainsBytes( Word( "βfr𐍈ａ"    ) ) );
  EXPECT_TRUE( word.ContainsBytes( Word( "fβr"      ) ) );
  EXPECT_TRUE( word.ContainsBytes( Word( "r"        ) ) );
  EXPECT_TRUE( word.ContainsBytes( Word( "βββ"      ) ) );
  EXPECT_TRUE( word.ContainsBytes( Word( ""         ) ) );
}


TEST( WordTest, DoesntMatchBytes ) {
  Word word( "Fo𐍈βＡr" );

  EXPECT_FALSE( word.ContainsBytes( Word( "Fo𐍈βＡrε" ) ) );
  EXPECT_FALSE( word.ContainsBytes( Word( "gggg"    ) ) );
  EXPECT_FALSE( word.ContainsBytes( Word( "χ"       ) ) );
  EXPECT_FALSE( word.ContainsBytes( Word( "nfooΒａr" ) ) );
  EXPECT_FALSE( word.ContainsBytes( Word( "Fβrmmm"  ) ) );
}

} // namespace YouCompleteMe
