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

#include "LetterNode.h"
#include "standard.h"


namespace YouCompleteMe {

LetterNode::LetterNode( char letter, int index )
  : index_( index ),
    is_uppercase_( IsUppercase( letter ) ) {
}


LetterNode::LetterNode( const std::string &text )
  : index_( -1 ),
    is_uppercase_( false ) {

  letternode_per_text_index_.reserve( text.size() );

  for ( uint i = 0; i < text.size(); ++i ) {
    letternode_per_text_index_.push_back( LetterNode( text[ i ], i ) );
    SetNodeIndexForLetterIfNearest( text[ i ], i );
  }

  for ( size_t i = 0; i < text.size(); ++i ) {
    for ( size_t j = i + 1; j < text.size(); ++j ) {
      letternode_per_text_index_[ i ].SetNodeIndexForLetterIfNearest( text[ j ],
                                                                      j );
    }
  }
}

void LetterNode::SetNodeIndexForLetterIfNearest( char letter, short index ) {
  NearestLetterNodeIndices& currentLetterNodeIndices = letters_[ letter ];
  if ( IsUppercase( letter ) ) {
    if ( currentLetterNodeIndices.indexOfFirstUppercaseOccurrence == -1 )
      currentLetterNodeIndices.indexOfFirstUppercaseOccurrence = index;
  }

  if ( currentLetterNodeIndices.indexOfFirstOccurrence == -1 )
    currentLetterNodeIndices.indexOfFirstOccurrence = index;
}

} // namespace YouCompleteMe
