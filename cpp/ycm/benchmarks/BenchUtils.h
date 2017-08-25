// Copyright (C) 2017 ycmd contributores
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

#ifndef BENCHUTILS_H_7UY2GEP1
#define BENCHUTILS_H_7UY2GEP1

#include <string>
#include <vector>

namespace YouCompleteMe {

// Generate a list of |number| candidates of the form |prefix|[a-z]{5}.
std::vector< std::string > GenerateCandidatesWithCommonPrefix(
  const std::string prefix, int number );

} // namespace YouCompleteMe

#endif /* end of include guard: BENCHUTILS_H_7UY2GEP1 */
