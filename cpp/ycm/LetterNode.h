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

#include "DLLDefines.h"
#include "LetterNodeListMap.h"

#include <vector>
#include <list>
#include <string>


namespace YouCompleteMe {

class LetterNode {
public:
  LetterNode( char letter, int index );

  YCM_DLL_EXPORT explicit LetterNode( const std::string &text );

  inline bool LetterIsUppercase() const {
    return is_uppercase_;
  }

  inline const NearestLetterNodeIndices *NearestLetterNodesForLetter(
    char letter ) {

    return letters_.ListPointerAt( letter );
  }

  void SetNodeIndexForLetterIfNearest( char letter, short index );

  inline int Index() const {
    return index_;
  }

  inline LetterNode *operator[]( int index ) {
    return &letternode_per_text_index_[ index ];
  }

private:
  LetterNodeListMap letters_;
  std::vector<LetterNode> letternode_per_text_index_;
  int index_;
  bool is_uppercase_;
};

} // namespace YouCompleteMe

#endif /* end of include guard: LETTERNODE_H_EIZ6JVWC */

