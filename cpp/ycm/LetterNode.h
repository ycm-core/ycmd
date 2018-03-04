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

#ifndef LETTERNODE_H_EIZ6JVWC
#define LETTERNODE_H_EIZ6JVWC

#include "LetterNodeListMap.h"

#include <vector>
#include <list>
#include <string>


namespace YouCompleteMe {

// LetterNodes are indexed by number [0..N], 0 being the root node that doesn't
// represent a character in the input, N representing the last character
class LetterNode {
public:
  YCM_EXPORT explicit LetterNode( const std::string &text );

  inline const NearestLetterNodeIndices *NearestLetterNodesForLetter( size_t node_index, char letter ) const {
    if (node_index >= letternodemap_per_text_index_.size()) {
      return nullptr;
    }

    return &letternodemap_per_text_index_[ node_index ].ListPointerAt( letter );
  }

private:
  // [0..N) maps, since from the last character you can't find
  // any other characters anyway
  std::vector<LetterNodeListMap> letternodemap_per_text_index_;
};

} // namespace YouCompleteMe

#endif /* end of include guard: LETTERNODE_H_EIZ6JVWC */

