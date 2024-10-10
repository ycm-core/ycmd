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

#ifndef CODE_POINT_H_3W0LNCLY
#define CODE_POINT_H_3W0LNCLY

#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>

namespace YouCompleteMe {

// See
// http://www.unicode.org/reports/tr29#Grapheme_Cluster_Break_Property_Values
// NOTE: The properties must take the same value as the ones defined in the
// update_unicode.py script.
enum class GraphemeBreakProperty : uint8_t {
  OTHER              =  0,
  CR                 =  1,
  LF                 =  2,
  CONTROL            =  3,
  EXTEND             =  4,
  ZWJ                =  5,
  REGIONAL_INDICATOR =  6,
  PREPEND            =  7,
  SPACINGMARK        =  8,
  L                  =  9,
  V                  = 10,
  T                  = 11,
  LV                 = 12,
  LVT                = 13,
  EXTPICT            = 18
};
// See https://www.unicode.org/reports/tr44/#Indic_Conjunct_Break
// NOTE: The properties must take the same value as the ones defined in the
// update_unicode.py script.
enum class IndicConjunctBreakProperty : uint8_t {
  None      =  0,
  LINKER    =  1,
  CONSONANT =  2,
  EXTEND    =  3,
};


// This is the structure used to store the data in the Unicode table. See the
// CodePoint class for a description of the members.
struct RawCodePoint {
  std::string_view original;
  std::string_view normal;
  std::string_view folded_case;
  std::string_view swapped_case;
  bool is_letter;
  bool is_punctuation;
  bool is_uppercase;
  uint8_t grapheme_break_property;
  uint8_t combining_class;
  uint8_t indic_conjunct_break_property;
};


// This class represents a UTF-8 code point. It takes a UTF-8 encoded string
// corresponding to a UTF-8 code point and compute the following properties
// from a Unicode table:
//  - the UTF-8 code point itself;
//  - its normalized version: two code points (or sequence of code points)
//    represent the same character if they have identical normalized version;
//  - its case-folded version: identical to the normalized version if the code
//    point is caseless;
//  - its case-swapped version: lowercase if the code point is uppercase,
//    uppercase if the code point is lowercase, identical to the normalized
//    version if the code point is caseless;
//  - if the code point is a letter;
//  - if the code point is a punctuation;
//  - if the code point is in uppercase: false if the code point has no
//    uppercase version;
//  - its breaking property: used to split a word into characters.
//  - its combining class: used to sort a sequence of code points according to
//    the Canonical Ordering algorithm (see
//    https://www.unicode.org/versions/latest/core-spec/chapter-3/#G49591).
class CodePoint {
public:
  YCM_EXPORT explicit CodePoint( std::string_view code_point );
  // Make class noncopyable
  CodePoint( const CodePoint& ) = delete;
  CodePoint& operator=( const CodePoint& ) = delete;
  CodePoint( CodePoint&& ) = default;
  CodePoint& operator=( CodePoint&& ) = default;

  inline const std::string &Normal() const {
    return normal_;
  }

  inline const std::string &FoldedCase() const {
    return folded_case_;
  }

  inline const std::string &SwappedCase() const {
    return swapped_case_;
  }

  inline bool IsLetter() const {
    return is_letter_;
  }

  inline bool IsPunctuation() const {
    return is_punctuation_;
  }

  inline bool IsUppercase() const {
    return is_uppercase_;
  }

  inline GraphemeBreakProperty GetGraphemeBreakProperty() const {
    return grapheme_break_property_;
  }

  inline uint8_t CombiningClass() const {
    return combining_class_;
  }

  inline IndicConjunctBreakProperty GetIndicConjunctBreakProperty() const {
    return indic_conjunct_break_property_;
  }

  inline bool operator< ( const CodePoint &other ) const {
    return combining_class_ < other.combining_class_;
  }

private:
  explicit CodePoint( RawCodePoint&& code_point );

  std::string normal_;
  std::string folded_case_;
  std::string swapped_case_;
  bool is_letter_;
  bool is_punctuation_;
  bool is_uppercase_;
  GraphemeBreakProperty grapheme_break_property_;
  uint8_t combining_class_;
  IndicConjunctBreakProperty indic_conjunct_break_property_;
};


using CodePointSequence = std::vector< const CodePoint * >;


// Split a UTF-8 encoded string into UTF-8 code points.
YCM_EXPORT CodePointSequence BreakIntoCodePoints( std::string_view text );


// Thrown when an error occurs while decoding a UTF-8 string.
struct YCM_EXPORT UnicodeDecodeError : std::runtime_error {
  using std::runtime_error::runtime_error;
  const char* what() const noexcept override;
};

} // namespace YouCompleteMe

#endif /* end of include guard: CODE_POINT_H_3W0LNCLY */
