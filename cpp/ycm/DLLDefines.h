// Copyright (C) 2015 ycmd contributors
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

#ifndef DLLDEFINES_H_0IYA3AQ3
#define DLLDEFINES_H_0IYA3AQ3

// We need to export symbols for gmock tests on Windows.  The preprocessor
// symbol ycm_core_EXPORTS is defined by CMake when building a shared library.
#if defined( _WIN32 ) && defined( ycm_core_EXPORTS )
  #define YCM_DLL_EXPORT __declspec( dllexport )
#else
  #define YCM_DLL_EXPORT
#endif

#endif /* end of include guard: DLLDEFINES_H_0IYA3AQ3 */
