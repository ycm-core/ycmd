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

#ifndef LETTERNODELISTMAP_H_BRK2UMC1
#define LETTERNODELISTMAP_H_BRK2UMC1

#include "DLLDefines.h"
#include "Utils.h"

#include <vector>
#include <memory>
#include <array>

#define NUM_LETTERS 128

namespace YouCompleteMe {

class LetterNode;

YCM_DLL_EXPORT int IndexForLetter( char letter );

/*
 * This struct is used as part of the LetterNodeListMap structure.
 * Every LetterNode represents 1 position in a string, and contains
 * one LetterNodeListMap. The LetterNodeListMap records the first
 * occurrence of all ascii characters after the current LetterNode
 * in the original string. For each character, the
 * LetterNodeListMap contains one instance of NearestLetterNodeIndices
 *
 * The struct records the position in the original string of the character
 * after the current LetterNode, both the first occurrence overall and the
 * first uppercase occurrence. If the letter (or uppercase version)
 * doesn't occur, it records -1, indicating it isn't present.
 *
 * The indices can be used to retrieve the corresponding LetterNode from
 * the root LetterNode, as it contains a vector of LetterNodes, one per
 * position in the original string.
 */
struct NearestLetterNodeIndices {
  NearestLetterNodeIndices()
    : indexOfFirstOccurrence( -1 ),
      indexOfFirstUppercaseOccurrence( -1 )
  {}

  short indexOfFirstOccurrence;
  short indexOfFirstUppercaseOccurrence;
};

class LetterNodeListMap {
public:
  LetterNodeListMap();
  LetterNodeListMap( const LetterNodeListMap &other );

  NearestLetterNodeIndices &operator[] ( char letter );

  YCM_DLL_EXPORT NearestLetterNodeIndices *ListPointerAt( char letter );

private:
  typedef std::array<NearestLetterNodeIndices , NUM_LETTERS>
    NearestLetterNodeArray;

  std::unique_ptr< NearestLetterNodeArray > letters_;
};

} // namespace YouCompleteMe

#endif /* end of include guard: LETTERNODELISTMAP_H_BRK2UMC1 */

