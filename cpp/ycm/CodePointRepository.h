// Copyright (C) 2018 ycmd contributors
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

#ifndef CODE_POINT_REPOSITORY_H_ENE9FWXL
#define CODE_POINT_REPOSITORY_H_ENE9FWXL

#include "CodePoint.h"

#include <memory>
#include <mutex>
#include <string>
#include <unordered_map>
#include <vector>

namespace YouCompleteMe {

using CodePointHolder = std::unordered_map< std::string,
                                            std::unique_ptr< CodePoint > >;


// This singleton stores already built CodePoint objects for code points that
// were already seen. If CodePoints are requested for previously unseen code
// points, new CodePoint objects are built.
//
// This class is thread-safe.
class CodePointRepository {
public:
  YCM_EXPORT static CodePointRepository &Instance();
  // Make class noncopyable
  CodePointRepository( const CodePointRepository& ) = delete;
  CodePointRepository& operator=( const CodePointRepository& ) = delete;

  YCM_EXPORT size_t NumStoredCodePoints();

  YCM_EXPORT CodePointSequence GetCodePoints(
    const std::vector< std::string > &code_points );

  // This should only be used to isolate tests and benchmarks.
  YCM_EXPORT void ClearCodePoints();

private:
  CodePointRepository() = default;
  ~CodePointRepository() = default;

  // This data structure owns all the CodePoint pointers
  CodePointHolder code_point_holder_;
  std::mutex code_point_holder_mutex_;
};

} // namespace YouCompleteMe

#endif /* end of include guard: CODE_POINT_REPOSITORY_H_ENE9FWXL */
