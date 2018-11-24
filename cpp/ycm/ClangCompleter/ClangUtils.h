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

#ifndef CLANGUTILS_H_9MVHQLJS
#define CLANGUTILS_H_9MVHQLJS

#include <clang-c/Index.h>
#include <stdexcept>
#include <string>

namespace YouCompleteMe {

/**
 * Return a std::string from the supplied CXString.
 *
 * Takes ownership of, and destroys, the supplied CXString which must not be used
 * subsequently.
 */
std::string CXStringToString( CXString text );

bool CursorIsValid( CXCursor cursor );

std::string CXFileToFilepath( CXFile file );

std::string ClangVersion();

const char *CXErrorCodeToString( CXErrorCode code );

/**
 * Thrown when libclang fails to parse (or reparse) the translation unit.
 */
struct YCM_EXPORT ClangParseError : std::runtime_error {
  explicit ClangParseError( const char *what_arg );
  explicit ClangParseError( CXErrorCode code );
};

} // namespace YouCompleteMe

#endif /* end of include guard: CLANGUTILS_H_9MVHQLJS */

