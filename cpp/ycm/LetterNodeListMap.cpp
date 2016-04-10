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
  std::fill( letters_.begin(),
             letters_.end(),
             static_cast< std::list< LetterNode * >* >( NULL ) );
}


LetterNodeListMap::~LetterNodeListMap() {
  for ( uint i = 0; i < letters_.size(); ++i ) {
    delete letters_[ i ];
  }
}


std::list< LetterNode * > &LetterNodeListMap::operator[] ( char letter ) {
  int letter_index = IndexForLetter( letter );

  std::list< LetterNode * > *list = letters_.at( letter_index );

  if ( list )
    return *list;

  letters_[ letter_index ] = new std::list< LetterNode * >();
  return *letters_[ letter_index ];
}


std::list< LetterNode * > *LetterNodeListMap::ListPointerAt( char letter ) {
  return letters_.at( IndexForLetter( letter ) );
}

} // namespace YouCompleteMe
