// Copyright (C) 2013-2018 ycmd contributors
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

#ifndef RANGE_H_4MFTIGQK
#define RANGE_H_4MFTIGQK

#include "Location.h"

namespace YouCompleteMe {

// Half-open, [start, end>
struct Range {
  Range() = default;

  Range( const Location &start_location, const Location &end_location )
    : start_( start_location ),
      end_( end_location ) {
  }

  explicit Range( const CXSourceRange &range );

  Location start_;
  Location end_;
};

} // namespace YouCompleteMe

#endif /* end of include guard: RANGE_H_4MFTIGQK */
