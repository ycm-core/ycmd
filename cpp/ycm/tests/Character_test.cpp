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
#include "Repository.h"
#include "CodePoint.h"
#include "TestUtils.h"

#include <array>
#include <gtest/gtest.h>
#include <gmock/gmock.h>

using ::testing::TestWithParam;
using ::testing::ValuesIn;

namespace YouCompleteMe {

// Check that characters equalities and inequalities are symmetric (a == b if
// and only if b == a).
MATCHER( CharactersAreEqual, "" ) {
  for ( size_t i = 0; i < arg.size() - 1; ++i ) {
    for ( size_t j = i + 1; j < arg.size(); ++j ) {
      if ( !( *arg[ i ] == *arg[ j ] ) || !( *arg[ j ] == *arg[ i ] ) ) {
        return false;
      }
    }
  }
  return true;
}


MATCHER( CharactersAreNotEqual, "" ) {
  for ( size_t i = 0; i < arg.size() - 1; ++i ) {
    for ( size_t j = i + 1; j < arg.size(); ++j ) {
      if ( *arg[ i ] == *arg[ j ] || *arg[ j ] == *arg[ i ] ) {
        return false;
      }
    }
  }
  return true;
}


MATCHER( CharactersAreEqualWhenCaseIsIgnored, "" ) {
  for ( size_t i = 0; i < arg.size() - 1; ++i ) {
    for ( size_t j = i + 1; j < arg.size(); ++j ) {
      if ( !( arg[ i ]->EqualsIgnoreCase( *arg[ j ] ) ) ||
           !( arg[ j ]->EqualsIgnoreCase( *arg[ i ] ) ) ) {
        return false;
      }
    }
  }
  return true;
}


MATCHER( CharactersAreNotEqualWhenCaseIsIgnored, "" ) {
  for ( size_t i = 0; i < arg.size() - 1; ++i ) {
    for ( size_t j = i + 1; j < arg.size(); ++j ) {
      if ( arg[ i ]->EqualsIgnoreCase( *arg[ j ] ) ||
           arg[ j ]->EqualsIgnoreCase( *arg[ i ] ) ) {
        return false;
      }
    }
  }
  return true;
}


MATCHER( BaseCharactersAreEqual, "" ) {
  for ( size_t i = 0; i < arg.size() - 1; ++i ) {
    for ( size_t j = i + 1; j < arg.size(); ++j ) {
      if ( !( arg[ i ]->EqualsBase( *arg[ j ] ) ) ||
           !( arg[ j ]->EqualsBase( *arg[ i ] ) ) ) {
        return false;
      }
    }
  }
  return true;
}


MATCHER( BaseCharactersAreNotEqual, "" ) {
  for ( size_t i = 0; i < arg.size() - 1; ++i ) {
    for ( size_t j = i + 1; j < arg.size(); ++j ) {
      if ( arg[ i ]->EqualsBase( *arg[ j ] ) ||
           arg[ j ]->EqualsBase( *arg[ i ] ) ) {
        return false;
      }
    }
  }
  return true;
}


struct TextCharacterPair {
  const char* text;
  CharacterTuple character_tuple;
};


std::ostream& operator<<( std::ostream& os,
                          const TextCharacterPair &pair ) {
  os << "{ " << PrintToString( pair.text ) << ", "
             << PrintToString( pair.character_tuple ) << " }";
  return os;
}


class CharacterTest : public TestWithParam< TextCharacterPair > {
protected:
  CharacterTest()
    : repo_( Repository< Character >::Instance() ) {
  }

  virtual void SetUp() {
    repo_.ClearElements();
    pair_ = GetParam();
  }

  Repository< Character > &repo_;
  const char* text_;
  TextCharacterPair pair_;
};


TEST( CharacterTest, ExceptionThrownWhenLeadingByteInCodePointIsInvalid ) {
  try {
    // Leading byte cannot start with bits '10'.
    Character( NormalizeInput( "\xaf" ) );
    FAIL() << "Expected UnicodeDecodeError exception.";
  } catch ( const UnicodeDecodeError &error ) {
    EXPECT_STREQ( error.what(), "Invalid leading byte in code point." );
  } catch ( ... ) {
    FAIL() << "Expected UnicodeDecodeError exception.";
  }
}


TEST( CharacterTest, ExceptionThrownWhenCodePointIsOutOfBound ) {
  try {
    // Leading byte indicates a sequence of three bytes but only two are given.
    Character( NormalizeInput( "\xe4\xbf" ) );
    FAIL() << "Expected UnicodeDecodeError exception.";
  } catch ( const UnicodeDecodeError &error ) {
    EXPECT_STREQ( error.what(), "Invalid code point length." );
  } catch ( ... ) {
    FAIL() << "Expected UnicodeDecodeError exception.";
  }
}


TEST_P( CharacterTest, PropertiesAreCorrect ) {
  EXPECT_THAT( Character( NormalizeInput( pair_.text ) ),
               IsCharacterWithProperties( pair_.character_tuple ) );
}


const std::array< TextCharacterPair, 13 > tests = { {
  // Musical symbol eighth note (three code points)
  { "𝅘𝅥𝅮", { "𝅘𝅥𝅮", "𝅘", "𝅘𝅥𝅮", "𝅘𝅥𝅮", false, false, false, false } },

  // Punctuations
  // Fullwidth low line
  { "＿", { "＿", "＿", "＿", "＿", true, false, true, false } },
  // Wavy dash
  { "〰", { "〰", "〰", "〰", "〰", true, false, true, false } },
  // Left floor
  { "⌊", { "⌊", "⌊", "⌊", "⌊", true, false, true, false } },
  // Fullwidth right square bracket
  { "］", { "］", "］", "］", "］", true, false, true, false } },
  { "«", { "«", "«", "«", "«", true, false, true, false } },
  // Right substitution bracket
  { "⸃", { "⸃", "⸃", "⸃", "⸃", true, false, true, false } },
  // Large one dot over two dots punctuation
  { "𐬽", { "𐬽", "𐬽", "𐬽", "𐬽", true, false, true, false } },

  // Letters
  // Latin capital letter S with dot below and dot above (three code points)
  { "Ṩ", { "Ṩ", "s", "ṩ", "ṩ", false, true, false, true } },
  // Greek small letter alpha with psili and varia and ypogegrammeni (four code
  // points)
  { "ᾂ", { "ᾂ", "α", "ἂι", "ἊΙ", false, true, false, false } },
  // Greek capital letter eta with dasia and perispomeni and prosgegrammeni
  // (four code points)
  { "ᾟ", { "ᾟ", "η", "ἧι", "ἧΙ", false, true, false, true } },
  // Hiragana voiced iteration mark (two code points)
  { "ゞ", { "ゞ", "ゝ", "ゞ", "ゞ", false, true, false, false } },
  // Hebrew letter shin with Dagesh and Shin dot (three code points)
  { "שּׁ", { "שּׁ", "ש", "שּׁ", "שּׁ", false, true, false, false } }
} };


INSTANTIATE_TEST_SUITE_P( UnicodeTest, CharacterTest, ValuesIn( tests ) );


TEST( CharacterTest, Equality ) {
  Repository< Character >& repo( Repository< Character >::Instance() );

  // The lowercase of the Latin capital letter e with acute "É" (which can be
  // represented as the Latin capital letter "E" plus the combining acute
  // character) is the Latin small letter e with acute "é".
  EXPECT_THAT( repo.GetElements( { NormalizeInput( "e" ),
                                   NormalizeInput( "é" ),
                                   NormalizeInput( "E" ),
                                   NormalizeInput( "É" ) } ),
               CharactersAreNotEqual() );
  EXPECT_THAT( repo.GetElements( { NormalizeInput( "é" ),
                                   NormalizeInput( "é" ) } ),
	       CharactersAreEqual() );
  EXPECT_THAT( repo.GetElements( { NormalizeInput( "É" ),
                                   NormalizeInput( "É" ) } ),
	       CharactersAreEqual() );
  EXPECT_THAT( repo.GetElements( { NormalizeInput( "e" ),
                                   NormalizeInput( "E" ) } ),
               CharactersAreEqualWhenCaseIsIgnored() );
  EXPECT_THAT( repo.GetElements( { NormalizeInput( "é" ),
                                   NormalizeInput( "É" ),
                                   NormalizeInput( "É" ) } ),
               CharactersAreEqualWhenCaseIsIgnored() );
  EXPECT_THAT( repo.GetElements( { NormalizeInput( "e" ),
                                   NormalizeInput( "é" ),
                                   NormalizeInput( "é" ),
                                   NormalizeInput( "E" ),
                                   NormalizeInput( "É" ),
                                   NormalizeInput( "É" ) } ),
               BaseCharactersAreEqual() );

  // The Greek capital letter omega "Ω" is the same character as the ohm sign
  // "Ω". The lowercase of both characters is the Greek small letter omega "ω".
  EXPECT_THAT( repo.GetElements( { NormalizeInput( "Ω" ),
                                   NormalizeInput( "Ω" ) } ),
	       CharactersAreEqual() );
  EXPECT_THAT( repo.GetElements( { NormalizeInput( "ω" ),
                                   NormalizeInput( "Ω" ),
                                   NormalizeInput( "Ω" ) } ),
               CharactersAreEqualWhenCaseIsIgnored() );
  EXPECT_THAT( repo.GetElements( { NormalizeInput( "ω" ),
                                   NormalizeInput( "Ω" ),
                                   NormalizeInput( "Ω" ) } ),
               BaseCharactersAreEqual() );

  // The Latin capital letter a with ring above "Å" (which can be represented as
  // the Latin capital letter "A" plus the combining ring above character) is
  // the same character as the angstrom sign "Å". The lowercase of these
  // characters is the Latin small letter a with ring above "å" (which can also
  // be represented as the Latin small letter "a" plus the combining ring above
  // character).
  EXPECT_THAT( repo.GetElements( { NormalizeInput( "a" ),
                                   NormalizeInput( "å" ),
                                   NormalizeInput( "A" ),
                                   NormalizeInput( "Å" ) } ),
               CharactersAreNotEqual() );
  EXPECT_THAT( repo.GetElements( { NormalizeInput( "å" ),
                                   NormalizeInput( "å" ) } ),
	       CharactersAreEqual() );
  EXPECT_THAT( repo.GetElements( { NormalizeInput( "Å" ),
                                   NormalizeInput( "Å" ),
                                   NormalizeInput( "Å" ) } ),
	       CharactersAreEqual() );
  EXPECT_THAT( repo.GetElements( { NormalizeInput( "å" ),
                                   NormalizeInput( "å" ),
                                   NormalizeInput( "Å" ),
                                   NormalizeInput( "Å" ),
                                   NormalizeInput( "Å" ) } ),
               CharactersAreEqualWhenCaseIsIgnored() );
  EXPECT_THAT( repo.GetElements( { NormalizeInput( "a" ),
                                   NormalizeInput( "å" ),
                                   NormalizeInput( "å" ),
                                   NormalizeInput( "A" ),
                                   NormalizeInput( "Å" ),
                                   NormalizeInput( "Å" ),
                                   NormalizeInput( "Å" ) } ),
               BaseCharactersAreEqual() );

  // The uppercase of the Greek small letter sigma "σ" and Greek small letter
  // final sigma "ς" is the Greek capital letter sigma "Σ".
  EXPECT_THAT( repo.GetElements( { NormalizeInput( "σ" ),
                                   NormalizeInput( "ς" ),
                                   NormalizeInput( "Σ" ) } ),
               CharactersAreNotEqual() );
  EXPECT_THAT( repo.GetElements( { NormalizeInput( "σ" ),
                                   NormalizeInput( "ς" ),
                                   NormalizeInput( "Σ" ) } ),
               CharactersAreEqualWhenCaseIsIgnored() );
  EXPECT_THAT( repo.GetElements( { NormalizeInput( "σ" ),
                                   NormalizeInput( "ς" ),
                                   NormalizeInput( "Σ" ) } ),
               BaseCharactersAreEqual() );

  // The lowercase of the Greek capital theta symbol "ϴ" and capital letter
  // theta "Θ" is the Greek small letter theta "θ". There is also the Greek
  // theta symbol "ϑ" whose uppercase is "Θ".
  EXPECT_THAT( repo.GetElements( { NormalizeInput( "θ" ),
                                   NormalizeInput( "ϑ" ),
                                   NormalizeInput( "ϴ" ),
                                   NormalizeInput( "Θ" ) } ),
               CharactersAreNotEqual() );
  EXPECT_THAT( repo.GetElements( { NormalizeInput( "θ" ),
                                   NormalizeInput( "ϑ" ),
                                   NormalizeInput( "ϴ" ),
                                   NormalizeInput( "Θ" ) } ),
               CharactersAreEqualWhenCaseIsIgnored() );
  EXPECT_THAT( repo.GetElements( { NormalizeInput( "θ" ),
                                   NormalizeInput( "ϑ" ),
                                   NormalizeInput( "ϴ" ),
                                   NormalizeInput( "Θ" ) } ),
               BaseCharactersAreEqual() );

  // In the Latin alphabet, the uppercase of "i" (with a dot) is "I" (without a
  // dot). However, in the Turkish alphabet (a variant of the Latin alphabet),
  // there are two distinct versions of the letter "i":
  //  - "ı" (without a dot) whose uppercase is "I" (without a dot);
  //  - "i" (with a dot) whose uppercase is "İ" (with a dot), which can also be
  //    represented as the letter "I" plus the combining dot above character.
  // Since our matching is language-independent, the Turkish form is ignored and
  // the letter "ı" (without a dot) does not match "I" (without a dot) when the
  // case is ignored. Similarly, "ı" plus the combining dot above character does
  // not match "İ" (with a dot) or "I" plus the combining dot above character
  // but "i" (with a dot) plus the combining dot above does.
  EXPECT_THAT( repo.GetElements( { NormalizeInput( "i" ),
                                   NormalizeInput( "I" ),
                                   NormalizeInput( "ı" ),
                                   NormalizeInput( "ı̇" ),
                                   NormalizeInput( "i̇" ),
                                   NormalizeInput( "İ" ) } ),
               CharactersAreNotEqual() );
  EXPECT_THAT( repo.GetElements( { NormalizeInput( "İ" ),
                                   NormalizeInput( "İ" ) } ),
	       CharactersAreEqual() );
  EXPECT_THAT( repo.GetElements( { NormalizeInput( "i" ),
                                   NormalizeInput( "I" ) } ),
               CharactersAreEqualWhenCaseIsIgnored() );
  EXPECT_THAT( repo.GetElements( { NormalizeInput( "i̇" ),
                                   NormalizeInput( "İ" ),
                                   NormalizeInput( "İ" ) } ),
               CharactersAreEqualWhenCaseIsIgnored() );
  EXPECT_THAT( repo.GetElements( { NormalizeInput( "ı" ),
                                   NormalizeInput( "ı̇" ),
                                   NormalizeInput( "I" ),
                                   NormalizeInput( "İ" ) } ),
               CharactersAreNotEqualWhenCaseIsIgnored() );
  EXPECT_THAT( repo.GetElements( { NormalizeInput( "i" ),
                                   NormalizeInput( "ı" ) } ),
               BaseCharactersAreNotEqual() );
  EXPECT_THAT( repo.GetElements( { NormalizeInput( "i" ),
                                   NormalizeInput( "i̇" ),
                                   NormalizeInput( "I" ),
                                   NormalizeInput( "İ" ),
                                   NormalizeInput( "İ" ) } ),
               BaseCharactersAreEqual() );
  EXPECT_THAT( repo.GetElements( { NormalizeInput( "ı" ),
                                   NormalizeInput( "ı̇" ) } ),
               BaseCharactersAreEqual() );
}


TEST( CharacterTest, SmartMatching ) {
  // The letter "é" and "É" appear twice in the tests as they can be represented
  // on one code point or two ("e"/"E" plus the combining acute character).
  EXPECT_TRUE ( Character( NormalizeInput( "e" ) )
                .MatchesSmart( Character( NormalizeInput( "e" ) ) ) );
  EXPECT_TRUE ( Character( NormalizeInput( "e" ) )
                .MatchesSmart( Character( NormalizeInput( "é" ) ) ) );
  EXPECT_TRUE ( Character( NormalizeInput( "e" ) )
                .MatchesSmart( Character( NormalizeInput( "é" ) ) ) );
  EXPECT_TRUE ( Character( NormalizeInput( "e" ) )
                .MatchesSmart( Character( NormalizeInput( "E" ) ) ) );
  EXPECT_TRUE ( Character( NormalizeInput( "e" ) )
                .MatchesSmart( Character( NormalizeInput( "É" ) ) ) );
  EXPECT_TRUE ( Character( NormalizeInput( "e" ) )
                .MatchesSmart( Character( NormalizeInput( "É" ) ) ) );

  EXPECT_FALSE( Character( NormalizeInput( "é" ) )
                .MatchesSmart( Character( NormalizeInput( "e" ) ) ) );
  EXPECT_TRUE ( Character( NormalizeInput( "é" ) )
                .MatchesSmart( Character( NormalizeInput( "é" ) ) ) );
  EXPECT_TRUE ( Character( NormalizeInput( "é" ) )
                .MatchesSmart( Character( NormalizeInput( "é" ) ) ) );
  EXPECT_FALSE( Character( NormalizeInput( "é" ) )
                .MatchesSmart( Character( NormalizeInput( "E" ) ) ) );
  EXPECT_TRUE ( Character( NormalizeInput( "é" ) )
                .MatchesSmart( Character( NormalizeInput( "É" ) ) ) );
  EXPECT_TRUE ( Character( NormalizeInput( "é" ) )
                .MatchesSmart( Character( NormalizeInput( "É" ) ) ) );

  EXPECT_FALSE( Character( NormalizeInput( "é" ) )
                .MatchesSmart( Character( NormalizeInput( "e" ) ) ) );
  EXPECT_TRUE ( Character( NormalizeInput( "é" ) )
                .MatchesSmart( Character( NormalizeInput( "é" ) ) ) );
  EXPECT_TRUE ( Character( NormalizeInput( "é" ) )
                .MatchesSmart( Character( NormalizeInput( "é" ) ) ) );
  EXPECT_FALSE( Character( NormalizeInput( "é" ) )
                .MatchesSmart( Character( NormalizeInput( "E" ) ) ) );
  EXPECT_TRUE ( Character( NormalizeInput( "é" ) )
                .MatchesSmart( Character( NormalizeInput( "É" ) ) ) );
  EXPECT_TRUE ( Character( NormalizeInput( "é" ) )
                .MatchesSmart( Character( NormalizeInput( "É" ) ) ) );

  EXPECT_FALSE( Character( NormalizeInput( "E" ) )
                .MatchesSmart( Character( NormalizeInput( "e" ) ) ) );
  EXPECT_FALSE( Character( NormalizeInput( "E" ) )
                .MatchesSmart( Character( NormalizeInput( "é" ) ) ) );
  EXPECT_FALSE( Character( NormalizeInput( "E" ) )
                .MatchesSmart( Character( NormalizeInput( "é" ) ) ) );
  EXPECT_TRUE ( Character( NormalizeInput( "E" ) )
                .MatchesSmart( Character( NormalizeInput( "E" ) ) ) );
  EXPECT_TRUE ( Character( NormalizeInput( "E" ) )
                .MatchesSmart( Character( NormalizeInput( "É" ) ) ) );
  EXPECT_TRUE ( Character( NormalizeInput( "E" ) )
                .MatchesSmart( Character( NormalizeInput( "É" ) ) ) );

  EXPECT_FALSE( Character( NormalizeInput( "É" ) )
                .MatchesSmart( Character( NormalizeInput( "e" ) ) ) );
  EXPECT_FALSE( Character( NormalizeInput( "É" ) )
                .MatchesSmart( Character( NormalizeInput( "é" ) ) ) );
  EXPECT_FALSE( Character( NormalizeInput( "É" ) )
                .MatchesSmart( Character( NormalizeInput( "é" ) ) ) );
  EXPECT_FALSE( Character( NormalizeInput( "É" ) )
                .MatchesSmart( Character( NormalizeInput( "E" ) ) ) );
  EXPECT_TRUE ( Character( NormalizeInput( "É" ) )
                .MatchesSmart( Character( NormalizeInput( "É" ) ) ) );
  EXPECT_TRUE ( Character( NormalizeInput( "É" ) )
                .MatchesSmart( Character( NormalizeInput( "É" ) ) ) );

  EXPECT_FALSE( Character( NormalizeInput( "É" ) )
                .MatchesSmart( Character( NormalizeInput( "e" ) ) ) );
  EXPECT_FALSE( Character( NormalizeInput( "É" ) )
                .MatchesSmart( Character( NormalizeInput( "é" ) ) ) );
  EXPECT_FALSE( Character( NormalizeInput( "É" ) )
                .MatchesSmart( Character( NormalizeInput( "é" ) ) ) );
  EXPECT_FALSE( Character( NormalizeInput( "É" ) )
                .MatchesSmart( Character( NormalizeInput( "E" ) ) ) );
  EXPECT_TRUE ( Character( NormalizeInput( "É" ) )
                .MatchesSmart( Character( NormalizeInput( "É" ) ) ) );
  EXPECT_TRUE ( Character( NormalizeInput( "É" ) )
                .MatchesSmart( Character( NormalizeInput( "É" ) ) ) );

  EXPECT_FALSE( Character( NormalizeInput( "è" ) )
                .MatchesSmart( Character( NormalizeInput( "e" ) ) ) );
  EXPECT_FALSE( Character( NormalizeInput( "è" ) )
                .MatchesSmart( Character( NormalizeInput( "é" ) ) ) );
  EXPECT_FALSE( Character( NormalizeInput( "è" ) )
                .MatchesSmart( Character( NormalizeInput( "é" ) ) ) );
  EXPECT_FALSE( Character( NormalizeInput( "è" ) )
                .MatchesSmart( Character( NormalizeInput( "E" ) ) ) );
  EXPECT_FALSE( Character( NormalizeInput( "è" ) )
                .MatchesSmart( Character( NormalizeInput( "É" ) ) ) );
  EXPECT_FALSE( Character( NormalizeInput( "è" ) )
                .MatchesSmart( Character( NormalizeInput( "É" ) ) ) );
}

} // namespace YouCompleteMe
