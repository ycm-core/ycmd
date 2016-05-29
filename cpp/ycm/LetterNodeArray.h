// Copyright (C) 2016 ycmd contributors
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

#ifndef LETTERNODEARRAY_H_EIZ6JVWC
#define LETTERNODEARRAY_H_EIZ6JVWC

#include <string>
#include "DLLDefines.h"

namespace YouCompleteMe {

class LetterNode;

class LetterNodeArray {
public:
  LetterNodeArray() : elements_( NULL ), size_( 0 ) {}
  LetterNodeArray( const std::string &text );
  YCM_DLL_EXPORT ~LetterNodeArray();

  YCM_DLL_EXPORT LetterNode &operator[]( size_t index );

private:
  LetterNode *elements_;
  unsigned size_;
};

}

#endif /* end of include guard: LETTERNODEARRAY_H_EIZ6JVWC */

