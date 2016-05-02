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

#include "LetterNodeArray.h"
#include "LetterNode.h"
#include "standard.h"


namespace YouCompleteMe {

// LetterNodeArray
LetterNodeArray::LetterNodeArray( const std::string &text )
  : size_( text.size() ) {
  // properly aligned type to hold elements
  typedef boost::aligned_storage<sizeof( LetterNode ), boost::alignment_of<LetterNode>::value>::type storage_type;

  // allocate uninitialized memory
  elements_ = reinterpret_cast<LetterNode *>( new storage_type[size_] );

  // initialize elements
  for ( size_t i = 0; i < size_; ++i ) {
    new ( elements_ + i ) LetterNode( text[i], i );
  }
}

LetterNode &LetterNodeArray::operator[]( size_t index ) {
  assert( index < size_ );
  return elements_[index];
}

LetterNodeArray::~LetterNodeArray() {
  // properly aligned type to hold elements
  typedef boost::aligned_storage<sizeof( LetterNode ), boost::alignment_of<LetterNode>::value>::type storage_type;

  for ( size_t i = 0; i < size_; ++i ) {
    elements_[i].~LetterNode();
  }

  delete[] reinterpret_cast<storage_type *>( elements_ );
}

} // namespace YouCompleteMe
