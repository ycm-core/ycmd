// Copyright (C) 2011-2018 ycmd contributors
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

#ifndef LOCATION_H_6TLFQH4I
#define LOCATION_H_6TLFQH4I

#include "ClangUtils.h"

#include <clang-c/Index.h>
#include <string>

#include <pymetabind/utils.hpp>

namespace YouCompleteMe {

struct [[=pymetabind::utils::make_binding()]] Location {
  // Creates an invalid location
  Location() = default;

  [[=pymetabind::utils::skip_member()]] Location( const std::string &filename,
            unsigned int line,
            unsigned int column )
    : line_number_( line ),
      column_number_( column ),
      filename_( filename ) {
  }

  [[=pymetabind::utils::skip_member()]] explicit Location( const CXSourceLocation &location ) {
    CXFile file;
    unsigned int unused_offset;
    clang_getExpansionLocation( location,
                                &file,
                                &line_number_,
                                &column_number_,
                                &unused_offset );
    filename_ = CXFileToFilepath( file );
  }

  bool operator== ( const Location &other ) const {
    return line_number_ == other.line_number_ &&
           column_number_ == other.column_number_ &&
           filename_ == other.filename_;
  }

  bool IsValid() const {
    return !filename_.empty();
  }

  [[=pymetabind::utils::readonly()]] unsigned int line_number_{ 0 };
  [[=pymetabind::utils::readonly()]] unsigned int column_number_{ 0 };

  // The full, absolute path
  [[=pymetabind::utils::readonly()]] std::string filename_;
};

} // namespace YouCompleteMe

#endif /* end of include guard: LOCATION_H_6TLFQH4I */
