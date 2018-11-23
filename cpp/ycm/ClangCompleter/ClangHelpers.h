// Copyright (C) 2013-2018 ycmd contributors
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

#ifndef CLANGHELPERS_H_T3ME71LG
#define CLANGHELPERS_H_T3ME71LG

#include "CompletionData.h"
#include "Diagnostic.h"
#include "UnsavedFile.h"

#include <clang-c/Index.h>
#include <memory>
#include <vector>

namespace YouCompleteMe {

using DiagnosticWrap =
  std::shared_ptr< std::remove_pointer< CXDiagnostic >::type >;

std::vector< CompletionData > ToCompletionDataVector(
  CXCodeCompleteResults *results );

// NOTE: CXUnsavedFiles store pointers to data in UnsavedFiles, so UnsavedFiles
// need to outlive CXUnsavedFiles!
std::vector< CXUnsavedFile > ToCXUnsavedFiles(
  const std::vector< UnsavedFile > &unsaved_files );

Diagnostic BuildDiagnostic( const DiagnosticWrap &diagnostic_wrap,
                            CXTranslationUnit translation_unit );

} // namespace YouCompleteMe

#endif /* end of include guard: CLANGHELPERS_H_T3ME71LG */

