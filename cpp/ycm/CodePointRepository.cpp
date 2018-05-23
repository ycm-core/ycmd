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

#include "CodePointRepository.h"
#include "CodePoint.h"
#include "Utils.h"

#include <mutex>

namespace YouCompleteMe {

CodePointRepository &CodePointRepository::Instance() {
  static CodePointRepository repo;
  return repo;
}


size_t CodePointRepository::NumStoredCodePoints() {
  std::lock_guard< std::mutex > locker( code_point_holder_mutex_ );
  return code_point_holder_.size();
}


CodePointSequence CodePointRepository::GetCodePoints(
  const std::vector< std::string > &code_points ) {
  CodePointSequence code_point_objects;
  code_point_objects.reserve( code_points.size() );

  {
    std::lock_guard< std::mutex > locker( code_point_holder_mutex_ );

    for ( const std::string & code_point : code_points ) {
      std::unique_ptr< CodePoint > &code_point_object = GetValueElseInsert(
                                                          code_point_holder_,
                                                          code_point,
                                                          nullptr );

      if ( !code_point_object ) {
        code_point_object.reset( new CodePoint( code_point ) );
      }

      code_point_objects.push_back( code_point_object.get() );
    }
  }

  return code_point_objects;
}


void CodePointRepository::ClearCodePoints() {
  code_point_holder_.clear();
}


} // namespace YouCompleteMe
