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

#include <vector>
#include <boost/move/unique_ptr.hpp>
#include <boost/utility.hpp>
#include <boost/array.hpp>

#define NUM_LETTERS 128

namespace YouCompleteMe {

class LetterNode;

YCM_DLL_EXPORT bool IsUppercase( char letter );
bool IsInAsciiRange( int index );
YCM_DLL_EXPORT int IndexForLetter( char letter );

struct NearestLetterNodeIndices {
  NearestLetterNodeIndices()
    : eitherIndex( -1 ), upperIndex( -1 )
  {}

  short eitherIndex;
  short upperIndex;
};

class LetterNodeListMap : boost::noncopyable {
public:
  LetterNodeListMap();
  YCM_DLL_EXPORT ~LetterNodeListMap();

  NearestLetterNodeIndices &operator[] ( char letter );

  YCM_DLL_EXPORT NearestLetterNodeIndices *ListPointerAt( char letter );

private:
  typedef boost::array<NearestLetterNodeIndices , NUM_LETTERS> NearestLetterNodeArray;

  boost::movelib::unique_ptr< NearestLetterNodeArray > letters_;
};

} // namespace YouCompleteMe

#endif /* end of include guard: LETTERNODELISTMAP_H_BRK2UMC1 */

