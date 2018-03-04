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


namespace YouCompleteMe {

LetterNode::LetterNode( const std::string &text ) 
 : letternodemap_per_text_index_( text.size() ) {

  for ( size_t i = 0; i < text.size(); ++i ) {
    for ( size_t j = i; j < text.size(); ++j ) {
      letternodemap_per_text_index_[ i ].SetNodeIndexForLetterIfNearest( text[ j ],
                                                                      j + 1 );
    }
  }
}

} // namespace YouCompleteMe
