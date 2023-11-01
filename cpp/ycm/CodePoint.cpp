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

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstring>

namespace YouCompleteMe {

namespace {

int GetCodePointLength( uint8_t leading_byte ) {
  // 0xxxxxxx
  if ( ( leading_byte & 0x80 ) == 0x00 ) {
    return 1;
  }
  // 110xxxxx
  if ( ( leading_byte & 0xe0 ) == 0xc0 ) {
    return 2;
  }
  // 1110xxxx
  if ( ( leading_byte & 0xf0 ) == 0xe0 ) {
    return 3;
  }
  // 11110xxx
  if ( ( leading_byte & 0xf8 ) == 0xf0 ) {
    return 4;
  }
  throw UnicodeDecodeError( "Invalid leading byte in code point." );
}


RawCodePoint FindCodePoint( std::string_view text ) {
#include "UnicodeTable.inc"

  // Do a binary search on the array of code points to find the raw code point
  // corresponding to the text. If no code point is found, return the default
  // raw code point for that text.
  const auto& original = code_points.original;

  auto it = std::lower_bound( original.begin(), original.end(), text );
  if ( it != original.end() && text == *it ) {
    auto index = static_cast< size_t >( std::distance( original.begin(), it ) );
    return { *it,
             code_points.normal[ index ],
             code_points.folded_case[ index ],
             code_points.swapped_case[ index ],
             code_points.is_letter[ index ],
             code_points.is_punctuation[ index ],
             code_points.is_uppercase[ index ],
             code_points.break_property[ index ],
             code_points.combining_class[ index ],
             code_points.indic_conjunct_break[ index ] };
  }

  return { text, text, text, text, false, false, false, 0, 0, 0 };
}

} // unnamed namespace

CodePoint::CodePoint( std::string_view code_point )
  : CodePoint( FindCodePoint( code_point ) ) {
}


CodePoint::CodePoint( RawCodePoint&& code_point )
  : normal_( code_point.normal ),
    folded_case_( code_point.folded_case ),
    swapped_case_( code_point.swapped_case ),
    is_letter_( code_point.is_letter ),
    is_punctuation_( code_point.is_punctuation ),
    is_uppercase_( code_point.is_uppercase ),
    break_property_(
      static_cast< BreakProperty >( code_point.break_property ) ),
    combining_class_( code_point.combining_class ),
    indic_property_(
      static_cast< IndicBreakProperty >( code_point.indic_break_property ) ) {
}


CodePointSequence BreakIntoCodePoints( std::string_view text ) {
  // NOTE: for efficiency, we don't check if the number of continuation bytes
  // and the bytes themselves are valid (they must start with bits '10').
  std::vector< std::string > code_points;
  for ( auto iter = text.begin(); iter != text.end(); ) {
    int length = GetCodePointLength( static_cast< uint8_t >( *iter ) );
    if ( text.end() - iter < length ) {
      throw UnicodeDecodeError( "Invalid code point length." );
    }
    code_points.emplace_back( iter, iter + length );
    iter += length;
  }

  return Repository< CodePoint >::Instance().GetElements( std::move( code_points ) );
}


const char* UnicodeDecodeError::what() const noexcept {
  return std::runtime_error::what();
}

} // namespace YouCompleteMe
