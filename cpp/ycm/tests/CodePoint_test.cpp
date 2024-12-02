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

#include "CodePoint.h"
#include "Repository.h"
#include "TestUtils.h"

#include <array>
#include <gtest/gtest.h>
#include <gmock/gmock.h>

using ::testing::TestWithParam;
using ::testing::ValuesIn;

namespace YouCompleteMe {

struct TextCodePointPair {
  const char* text;
  CodePointTuple code_point_tuple;
};


std::ostream& operator<<( std::ostream& os,
                          const TextCodePointPair &pair ) {
  os << "{ " << PrintToString( pair.text ) << ", "
             << PrintToString( pair.code_point_tuple ) << " }";
  return os;
}


class CodePointTest : public TestWithParam< TextCodePointPair > {
protected:
  CodePointTest()
    : repo_( Repository< CodePoint >::Instance() ) {
  }

  virtual void SetUp() {
    repo_.ClearElements();
    pair_ = GetParam();
  }

  Repository< CodePoint > &repo_;
  TextCodePointPair pair_;
};


TEST_P( CodePointTest, PropertiesAreCorrect ) {
  EXPECT_THAT( CodePoint( pair_.text ),
               IsCodePointWithProperties( pair_.code_point_tuple ) );
}


// Tests mostly based on the table
// http://www.unicode.org/reports/tr29#Grapheme_Cluster_Break_Property_Values
const TextCodePointPair tests[] = {
  { "\r", { "\r", "\r", "\r", false, false, false, GraphemeBreakProperty::CR } },

  { "\n", { "\n", "\n", "\n", false, false, false, GraphemeBreakProperty::LF } },

  { "\t", { "\t", "\t", "\t", false, false, false, GraphemeBreakProperty::CONTROL } },
  // Line separator
  { "\xe2\x80\xa8", { "\xe2\x80\xa8", "\xe2\x80\xa8", "\xe2\x80\xa8",
                      false, false, false, GraphemeBreakProperty::CONTROL } },
  // Paragraph separator
  { "\xe2\x80\xa9", { "\xe2\x80\xa9", "\xe2\x80\xa9", "\xe2\x80\xa9",
                      false, false, false, GraphemeBreakProperty::CONTROL } },
  // Zero-width space
  { "​", { "​", "​", "​", false, false, false,
                GraphemeBreakProperty::CONTROL } },

  // Combining grave accent
  { "̀", { "̀", "̀", "̀", false, false, false,
                GraphemeBreakProperty::EXTEND,
                IndicConjunctBreakProperty::EXTEND } },
  // Bengali vowel sign Aa
  { "া", { "া", "া", "া", false, false, false,
                 GraphemeBreakProperty::EXTEND,
                 IndicConjunctBreakProperty::EXTEND } },
  // Zero-width non-joiner
  { "‌", { "‌", "‌", "‌", false, false, false,
                GraphemeBreakProperty::EXTEND } },
  // Combining cyrillic millions sign
  { "҈", { "҈", "҈", "҈", false, false, false,
                GraphemeBreakProperty::EXTEND,
                IndicConjunctBreakProperty::EXTEND } },

  // Zero-width joiner
  { "‍", { "‍", "‍", "‍", false, false, false,
                GraphemeBreakProperty::ZWJ,
		IndicConjunctBreakProperty::EXTEND } },

  // Regional indicator symbol letter b
  { "🇧", { "🇧", "🇧", "🇧", false, false, false,
            GraphemeBreakProperty::REGIONAL_INDICATOR } },

  // Arabic number sign
  { "؀", { "؀", "؀", "؀", false, false, false, GraphemeBreakProperty::PREPEND } },

  // Thai character Sara Am
  { "ำ", { "ำ", "ำ", "ำ", true, false, false, GraphemeBreakProperty::SPACINGMARK } },
  // Lao vowel sign Am
  { "ຳ", { "ຳ", "ຳ", "ຳ", true, false, false, GraphemeBreakProperty::SPACINGMARK } },

  // Hangul Choseong Kiyeok
  { "ᄀ", { "ᄀ", "ᄀ", "ᄀ", true, false, false, GraphemeBreakProperty::L } },
  // Hangul Choseong Filler
  { "ᅟ", { "ᅟ", "ᅟ", "ᅟ", true, false, false, GraphemeBreakProperty::L } },
  // Hangul Choseong Tikeut-mieum
  { "ꥠ", { "ꥠ", "ꥠ", "ꥠ", true, false, false, GraphemeBreakProperty::L } },
  // Hangul Choseong Ssangyeorinhieuh
  { "ꥼ", { "ꥼ", "ꥼ", "ꥼ", true, false, false, GraphemeBreakProperty::L } },

  // Hangul Jungseong Filler
  { "ᅠ", { "ᅠ", "ᅠ", "ᅠ", true, false, false, GraphemeBreakProperty::V } },
  // Hangul Jungseong Ssangaraea
  { "ᆢ", { "ᆢ", "ᆢ", "ᆢ", true, false, false, GraphemeBreakProperty::V } },
  // Hangul Jungseong O-yeo
  { "ힰ", { "ힰ", "ힰ", "ힰ", true, false, false, GraphemeBreakProperty::V } },
  // Hangul Jungseong Araea-e
  { "ퟆ", { "ퟆ", "ퟆ", "ퟆ", true, false, false, GraphemeBreakProperty::V } },

  // Hangul Jongseong Kiyeok
  { "ᆨ", { "ᆨ", "ᆨ", "ᆨ", true, false, false, GraphemeBreakProperty::T } },
  // Hangul Jongseong Yeorinhieuh
  { "ᇹ", { "ᇹ", "ᇹ", "ᇹ", true, false, false, GraphemeBreakProperty::T } },
  // Hangul Jongseong Nieun-rieul
  { "ퟋ", { "ퟋ", "ퟋ", "ퟋ", true, false, false, GraphemeBreakProperty::T } },
  // Hangul Jongseong Phieuph-thieuth
  { "ퟻ", { "ퟻ", "ퟻ", "ퟻ", true, false, false, GraphemeBreakProperty::T } },

  // Hangul syllable Ga
  { "가", { "가", "가", "가", true, false, false, GraphemeBreakProperty::LV } },
  // Hangul syllable Gae
  { "개", { "개", "개", "개", true, false, false, GraphemeBreakProperty::LV } },
  // Hangul syllable Gya
  { "갸", { "갸", "갸", "갸", true, false, false, GraphemeBreakProperty::LV } },

  // Hangul syllable Gag
  { "각", { "각", "각", "각", true, false, false, GraphemeBreakProperty::LVT } },
  // Hangul syllable Gagg
  { "갂", { "갂", "갂", "갂", true, false, false, GraphemeBreakProperty::LVT } },
  // Hangul syllable Gags
  { "갃", { "갃", "갃", "갃", true, false, false, GraphemeBreakProperty::LVT } },
  // Hangul syllable Gan
  { "간", { "간", "간", "간", true, false, false, GraphemeBreakProperty::LVT } },

  // Copyright sign
  { "©", { "©", "©", "©", false, false, false, GraphemeBreakProperty::EXTPICT } },

  // Characters with none of the above break properties.

  // One byte characters
  // NOTE: there are no Unicode letters coded with one byte (i.e. ASCII letters)
  // without a lowercase or uppercase version.
  { "r", { "r", "r", "R", true,  false, false, GraphemeBreakProperty::OTHER } },
  { "R", { "R", "r", "r", true,  false, true,  GraphemeBreakProperty::OTHER } },
  { "'", { "'", "'", "'", false, true,  false, GraphemeBreakProperty::OTHER } },
  { "=", { "=", "=", "=", false, false, false, GraphemeBreakProperty::OTHER } },
  // Two bytes characters
  { "é", { "é", "é", "É", true,  false, false, GraphemeBreakProperty::OTHER } },
  { "É", { "É", "é", "é", true,  false, true,  GraphemeBreakProperty::OTHER } },
  { "ĸ", { "ĸ", "ĸ", "ĸ", true,  false, false, GraphemeBreakProperty::OTHER } },
  { "»", { "»", "»", "»", false, true,  false, GraphemeBreakProperty::OTHER } },
  { "¥", { "¥", "¥", "¥", false, false, false, GraphemeBreakProperty::OTHER } },
  // Three bytes characters
  { "ⱥ", { "ⱥ", "ⱥ", "Ⱥ", true,  false, false, GraphemeBreakProperty::OTHER } },
  { "Ɐ", { "Ɐ", "ɐ", "ɐ", true,  false, true,  GraphemeBreakProperty::OTHER } },
  { "の", { "の", "の", "の", true, false, false, GraphemeBreakProperty::OTHER } },
  { "•", { "•", "•", "•", false, true,  false, GraphemeBreakProperty::OTHER } },
  { "∅", { "∅", "∅", "∅", false, false, false, GraphemeBreakProperty::OTHER } },
  // Four bytes characters
  { "𐐫", { "𐐫", "𐐫", "𐐃", true,  false, false, GraphemeBreakProperty::OTHER } },
  { "𐐃", { "𐐃", "𐐫", "𐐫", true,  false, true,  GraphemeBreakProperty::OTHER } },
  { "𐰬", { "𐰬", "𐰬", "𐰬", true,  false, false, GraphemeBreakProperty::OTHER } },
  { "𐬿", { "𐬿", "𐬿", "𐬿", false, true,  false, GraphemeBreakProperty::OTHER } },
  { "𝛁", { "𝛁", "𝛁", "𝛁", false, false, false, GraphemeBreakProperty::OTHER } },

  // Indic conjunct properties
  // Devanagari sign virama
  { "्", { "्", "्", "्", false, false, false,
                GraphemeBreakProperty::EXTEND,
                IndicConjunctBreakProperty::LINKER } },
  // Oriya letter wa
  { "ୱ", { "ୱ", "ୱ", "ୱ", true, false, false,
                GraphemeBreakProperty::OTHER,
                IndicConjunctBreakProperty::CONSONANT } },
  // Tibetan mark tsa -phru
  { "༹", { "༹", "༹", "༹", false, false, false,
                GraphemeBreakProperty::EXTEND,
                IndicConjunctBreakProperty::EXTEND } },
};


INSTANTIATE_TEST_SUITE_P( UnicodeTest, CodePointTest, ValuesIn( tests ) );

} // namespace YouCompleteMe
