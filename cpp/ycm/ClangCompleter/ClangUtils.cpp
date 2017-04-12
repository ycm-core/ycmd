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

#include "ClangUtils.h"

namespace YouCompleteMe {

std::string CXStringToString( CXString text ) {
  std::string final_string;

  if ( !text.data )
    return final_string;

  final_string = std::string( clang_getCString( text ) );
  clang_disposeString( text );
  return final_string;
}

bool CursorIsValid( CXCursor cursor ) {
  return !clang_Cursor_isNull( cursor ) &&
         !clang_isInvalid( clang_getCursorKind( cursor ) );
}

std::string CXFileToFilepath( CXFile file ) {
  return CXStringToString( clang_getFileName( file ) );
}

std::string ClangVersion() {
  return CXStringToString( clang_getClangVersion() );
}

} // namespace YouCompleteMe
