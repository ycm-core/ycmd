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

#include <vector>

namespace YouCompleteMe {

LetterNode::LetterNode( char letter, int index )
  : is_uppercase_( IsUppercase( letter ) ),
    index_( index ) {
}


LetterNode::LetterNode( const std::string &text )
  : is_uppercase_( false ),
    index_( -1 ) {
  std::vector< LetterNode * > letternode_per_text_index( text.size() );

  for ( uint i = 0; i < text.size(); ++i ) {
    char letter = text[ i ];
    LetterNode *node = new LetterNode( letter, i );
    letters_[ letter ].push_back( node );
    letternode_per_text_index[ i ] = node;
  }

  for ( int i = static_cast< int >( letternode_per_text_index.size() ) - 1;
        i >= 0; --i ) {
    LetterNode *node_to_add = letternode_per_text_index[ i ];

    for ( int j = i - 1; j >= 0; --j ) {
      letternode_per_text_index[ j ]->PrependNodeForLetter( text[ i ],
                                                            node_to_add );
    }
  }
}

} // namespace YouCompleteMe
