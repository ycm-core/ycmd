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
#include "CodePointRepository.h"

#include <array>
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


const RawCodePoint FindCodePoint( const char *text ) {
#include "UnicodeTable.inc"

  // Do a binary search on the array of code points to find the raw code point
  // corresponding to the text. If no code point is found, return the default
  // raw code point for that text.
  const auto& original = code_points.original;
  auto first = original.begin();
  const auto start = first;
  size_t count = original.size();

  while ( count > 0 ) {
    size_t step = count / 2;
    auto it = first + step;
    int cmp = std::strcmp( *it, text );
    if ( cmp == 0 ) {
      size_t index = std::distance( start, it );
      return { *it,
               code_points.normal[ index ],
               code_points.folded_case[ index ],
               code_points.swapped_case[ index ],
               code_points.is_letter[ index ],
               code_points.is_punctuation[ index ],
               code_points.is_uppercase[ index ],
               code_points.break_property[ index ],
               code_points.combining_class[ index ] };
    }
    if ( cmp < 0 ) {
      first = ++it;
      count -= step + 1;
    } else {
      count = step;
    }
  }

  return { text, text, text, text, false, false, false, 0, 0 };
}

} // unnamed namespace

CodePoint::CodePoint( const std::string &code_point )
  : CodePoint( FindCodePoint( code_point.c_str() ) ) {
}


CodePoint::CodePoint( const RawCodePoint &code_point )
  : normal_( code_point.normal ),
    folded_case_( code_point.folded_case ),
    swapped_case_( code_point.swapped_case ),
    is_letter_( code_point.is_letter ),
    is_punctuation_( code_point.is_punctuation ),
    is_uppercase_( code_point.is_uppercase ),
    break_property_(
      static_cast< BreakProperty >( code_point.break_property ) ),
    combining_class_( code_point.combining_class ) {
}


CodePointSequence BreakIntoCodePoints( const std::string &text ) {
  // NOTE: for efficiency, we don't check if the number of continuation bytes
  // and the bytes themselves are valid (they must start with bits '10').
  std::vector< std::string > code_points;
  for ( auto iter = text.begin(); iter != text.end(); ) {
    int length = GetCodePointLength( *iter );
    if ( text.end() - iter < length ) {
      throw UnicodeDecodeError( "Invalid code point length." );
    }
    code_points.emplace_back( iter, iter + length );
    iter += length;
  }

  return CodePointRepository::Instance().GetCodePoints( code_points );
}

} // namespace YouCompleteMe
