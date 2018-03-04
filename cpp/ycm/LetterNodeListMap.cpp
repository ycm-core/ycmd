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

#include "LetterNodeListMap.h"

namespace YouCompleteMe {

int IndexForLetter( char letter ) {
  if ( IsUppercase( letter ) ) {
    return letter + ( 'a' - 'A' );
  }

  return letter;
}


const NearestLetterNodeIndices &LetterNodeListMap::ListPointerAt( char letter ) const {
  return letters_.at( IndexForLetter( letter ) );
}


void LetterNodeListMap::SetNodeIndexForLetterIfNearest( char letter, uint16_t index ) {
  NearestLetterNodeIndices& currentLetterNodeIndices = letters_.at( IndexForLetter( letter ) );
  if ( IsUppercase( letter ) ) {
    if ( currentLetterNodeIndices.indexOfFirstUppercaseOccurrence == 0 ) {
      currentLetterNodeIndices.indexOfFirstUppercaseOccurrence = index;
    }
  }

  if ( currentLetterNodeIndices.indexOfFirstOccurrence == 0 ) {
    currentLetterNodeIndices.indexOfFirstOccurrence = index;
  }
}

} // namespace YouCompleteMe
