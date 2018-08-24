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

#include <clang-c/Index.h>
#include <iostream>

// This small program simulates the output of the clang executable when ran with
// the -E and -v flags. It takes a list of flags as arguments and creates the
// corresponding translation unit. When retrieving user flags, ycmd executes
// this program as follows
//
//   ycm_fake_clang -resource-dir=... [flag ...] -E -v filename
//
// and extract the list of system header paths from the output. These
// directories are then added to the list of flags to provide completion of
// system headers in include statements and allow jumping to these headers.
int main( int argc, char **argv ) {
  CXIndex index = clang_createIndex( 0, 0 );
  CXTranslationUnit tu;
  CXErrorCode result = clang_parseTranslationUnit2FullArgv(
    index, nullptr, argv, argc, nullptr, 0, CXTranslationUnit_None, &tu );
  if ( result != CXError_Success ) {
    return EXIT_FAILURE;
  }

  clang_disposeTranslationUnit( tu );
  return EXIT_SUCCESS;
}
