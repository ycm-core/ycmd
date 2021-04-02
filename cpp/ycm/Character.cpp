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
#include <cassert>

namespace YouCompleteMe {

namespace {

bool CodePointCompare( const CodePoint *left, const CodePoint *right ) {
  return *left < *right;
}


// Sort the code points according to the Canonical Ordering Algorithm.
// See https://www.unicode.org/versions/Unicode13.0.0/ch03.pdf#G49591
CodePointSequence CanonicalSort( CodePointSequence code_points ) {
  auto code_point_start = code_points.begin();
  auto code_point_end = code_points.end();

  while ( code_point_start != code_points.end() ) {
    // Find the first sortable code point
    code_point_start = std::find_if(
      code_point_start,
      code_points.end(),
      [](const CodePoint* cp ) {
        return cp->CombiningClass() != 0;
      } );

    // Find the last consecutive sortable code point
    code_point_end = std::find_if(
      code_point_start,
      code_points.end(),
      []( const CodePoint* cp ) {
        return cp->CombiningClass() == 0;
      } );

    std::sort( code_point_start, code_point_end, CodePointCompare );

    code_point_start = code_point_end;
  }

  return code_points;
}


// Decompose a UTF-8 encoded string into a sequence of code points according to
// Canonical Decomposition. See
// https://www.unicode.org/versions/Unicode13.0.0/ch03.pdf#G733
CodePointSequence CanonicalDecompose( std::string_view text ) {
  assert( NormalizeInput( text ) == text );
  return CanonicalSort( BreakIntoCodePoints( text ) );
}

} // unnamed namespace

Character::Character( std::string_view character )
  : is_base_( true ),
    is_letter_( false ),
    is_punctuation_( false ),
    is_uppercase_( false ) {
  // Normalize the character through NFD (Normalization Form D). See
  // https://www.unicode.org/versions/Unicode13.0.0/ch03.pdf#G49621
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


std::string NormalizeInput( std::string_view text ) {
    CodePointSequence code_points = BreakIntoCodePoints( text );
    std::string normal;

    for ( const auto &code_point : code_points ) {
      normal.append( code_point->Normal() );
    }
    return normal;
}

} // namespace YouCompleteMe
