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

#ifndef UNSAVEDFILE_H_0GIYZQL4
#define UNSAVEDFILE_H_0GIYZQL4

#include <string>

struct UnsavedFile {
  UnsavedFile() : filename_( "" ), contents_( "" ), length_( 0 ) {}

  std::string filename_;
  std::string contents_;
  unsigned long length_;
};


#endif /* end of include guard: UNSAVEDFILE_H_0GIYZQL4 */

