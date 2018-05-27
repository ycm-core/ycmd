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
#include "CodePoint.h"

#include <algorithm>

namespace YouCompleteMe {

namespace {

bool CodePointCompare( const CodePoint *left, const CodePoint *right ) {
  return *left < *right;
}


// Sort the code points according to the Canonical Ordering Algorithm.
// See https://www.unicode.org/versions/Unicode10.0.0/ch03.pdf#G49591
CodePointSequence CanonicalSort( CodePointSequence code_points ) {
  auto code_point_start = code_points.begin();

  while ( code_point_start != code_points.end() ) {
    if ( ( *code_point_start )->CombiningClass() == 0 ) {
      ++code_point_start;
      continue;
    }

    auto code_point_end = code_point_start + 1;
    while ( code_point_end != code_points.end() &&
            ( *code_point_end )->CombiningClass() != 0 ) {
      ++code_point_end;
    }

    std::sort( code_point_start, code_point_end, CodePointCompare );

    if ( code_point_end == code_points.end() ) {
      break;
    }

    code_point_start = code_point_end + 1;
  }

  return code_points;
}


// Decompose a UTF-8 encoded string into a sequence of code points according to
// Canonical Decomposition. See
// https://www.unicode.org/versions/Unicode10.0.0/ch03.pdf#G733
CodePointSequence CanonicalDecompose( const std::string &text ) {
  CodePointSequence code_points = BreakIntoCodePoints( text );
  std::string normal;

  for ( const auto &code_point : code_points ) {
    normal.append( code_point->Normal() );
  }

  return CanonicalSort( BreakIntoCodePoints( normal ) );
}

} // unnamed namespace

Character::Character( const std::string &character )
  : is_base_( true ),
    is_letter_( false ),
    is_punctuation_( false ),
    is_uppercase_( false ) {
  // Normalize the character through NFD (Normalization Form D). See
  // https://www.unicode.org/versions/Unicode10.0.0/ch03.pdf#G49621
  CodePointSequence code_points = CanonicalDecompose( character );

  for ( const auto &code_point : code_points ) {
    normal_.append( code_point->Normal() );
    folded_case_.append( code_point->FoldedCase() );
    swapped_case_.append( code_point->SwappedCase() );
    is_letter_ |= code_point->IsLetter();
    is_punctuation_ |= code_point->IsPunctuation();
    is_uppercase_ |= code_point->IsUppercase();

    switch ( code_point->GetBreakProperty() ) {
      case BreakProperty::PREPEND:
      case BreakProperty::EXTEND:
      case BreakProperty::SPACINGMARK:
        is_base_ = false;
        break;
      default:
        base_.append( code_point->FoldedCase() );
    }
  }
}

} // namespace YouCompleteMe
