// Copyright (C) 2015-2017 ycmd contributors
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

#include "Detail.h"

namespace YouCompleteMe {

namespace detail {

bool isprint( char c ) {
  return std::isprint( c, loc );
}

bool islower( char c ) {
  return std::islower( c, loc );
}

bool isupper( char c ) {
  return std::isupper( c, loc );
}

}

}
