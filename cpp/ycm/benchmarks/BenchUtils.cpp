// Copyright (C) 2017 ycmd contributors
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

#include "BenchUtils.h"

namespace YouCompleteMe {

std::vector< std::string > GenerateCandidatesWithCommonPrefix(
  const std::string prefix, int number ) {

  std::vector< std::string > candidates;

  for ( int i = 0; i < number; ++i ) {
    std::string candidate = "";
    int letter = i;
    for ( int pos = 0; pos < 5; letter /= 26, ++pos ) {
      candidate = std::string( 1, letter % 26 + 'a' ) + candidate;
    }
    candidate = prefix + candidate;
    candidates.push_back( candidate );
  }

  return candidates;
}

} // namespace YouCompleteMe
