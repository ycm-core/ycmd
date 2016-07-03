// Copyright (C) 2011, 2012 Google Inc.
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
#include "standard.h"
#include <algorithm>

namespace YouCompleteMe {

bool IsUppercase( char letter ) {
  return 'A' <= letter && letter <= 'Z';
}


bool IsInAsciiRange( int index ) {
  return 0 <= index && index < NUM_LETTERS;
}


int IndexForLetter( char letter ) {
  if ( IsUppercase( letter ) )
    return letter + ( 'a' - 'A' );

  return letter;
}


LetterNodeListMap::LetterNodeListMap() {
}


LetterNodeListMap::LetterNodeListMap( const LetterNodeListMap &other ) {
  if ( other.letters_ )
    letters_.reset( new NearestLetterNodeArray( *other.letters_ ) );
}


NearestLetterNodeIndices &LetterNodeListMap::operator[] ( char letter ) {
  if ( !letters_ )
    letters_.reset( new NearestLetterNodeArray() );

  int letter_index = IndexForLetter( letter );

  return letters_->at( letter_index );
}


NearestLetterNodeIndices *LetterNodeListMap::ListPointerAt( char letter ) {
  if ( !letters_ )
    return NULL;

  return &letters_->at( IndexForLetter( letter ) );
}

} // namespace YouCompleteMe
