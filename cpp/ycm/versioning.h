// Copyright (C) 2013 Google Inc.
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

#ifndef VERSIONING_H_EEJUU0AH
#define VERSIONING_H_EEJUU0AH

// The true value of this preprocessor definition is set in a compiler
// command-line flag. This is done in the main CMakeLists.txt file.
#if !defined( YCMD_CORE_VERSION )
#define YCMD_CORE_VERSION 0
#endif

#include <pymetabind/utils.hpp>

namespace YouCompleteMe {

[[=pymetabind::utils::make_binding()]] int YcmCoreVersion();

}  // namespace YouCompleteMe

#endif /* end of include guard: VERSIONING_H_EEJUU0AH */
