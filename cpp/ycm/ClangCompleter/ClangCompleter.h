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

#ifndef CLANGCOMPLETE_H_WLKDU0ZV
#define CLANGCOMPLETE_H_WLKDU0ZV

#include "Diagnostic.h"
#include "Documentation.h"
#include "TranslationUnitStore.h"
#include "UnsavedFile.h"

#include <string>

using CXTranslationUnit = CXTranslationUnitImpl*;

namespace YouCompleteMe {

class TranslationUnit;
struct CompletionData;
struct Location;

using CompletionDatas = std::vector< CompletionData >;


// All filename parameters must be absolute paths.
class ClangCompleter {
public:
  YCM_EXPORT ClangCompleter();
  YCM_EXPORT ~ClangCompleter();
  ClangCompleter( const ClangCompleter& ) = delete;
  ClangCompleter& operator=( const ClangCompleter& ) = delete;

  bool UpdatingTranslationUnit( const std::string &filename );

  YCM_EXPORT std::vector< Diagnostic > UpdateTranslationUnit(
    const std::string &translation_unit,
    const std::vector< UnsavedFile > &unsaved_files,
    const std::vector< std::string > &flags );

  YCM_EXPORT std::vector< CompletionData > CandidatesForLocationInFile(
    const std::string &translation_unit,
    const std::string &filename,
    int line,
    int column,
    const std::vector< UnsavedFile > &unsaved_files,
    const std::vector< std::string > &flags );

  YCM_EXPORT Location GetDeclarationLocation(
    const std::string &translation_unit,
    const std::string &filename,
    int line,
    int column,
    const std::vector< UnsavedFile > &unsaved_files,
    const std::vector< std::string > &flags,
    bool reparse = true );

  YCM_EXPORT Location GetDefinitionLocation(
    const std::string &translation_unit,
    const std::string &filename,
    int line,
    int column,
    const std::vector< UnsavedFile > &unsaved_files,
    const std::vector< std::string > &flags,
    bool reparse = true );

  YCM_EXPORT Location GetDefinitionOrDeclarationLocation(
    const std::string &translation_unit,
    const std::string &filename,
    int line,
    int column,
    const std::vector< UnsavedFile > &unsaved_files,
    const std::vector< std::string > &flags,
    bool reparse = true );

  YCM_EXPORT std::string GetTypeAtLocation(
    const std::string &translation_unit,
    const std::string &filename,
    int line,
    int column,
    const std::vector< UnsavedFile > &unsaved_files,
    const std::vector< std::string > &flags,
    bool reparse = true );

  YCM_EXPORT std::string GetEnclosingFunctionAtLocation(
    const std::string &translation_unit,
    const std::string &filename,
    int line,
    int column,
    const std::vector< UnsavedFile > &unsaved_files,
    const std::vector< std::string > &flags,
    bool reparse = true );

  YCM_EXPORT std::vector< FixIt > GetFixItsForLocationInFile(
    const std::string &translation_unit,
    const std::string &filename,
    int line,
    int column,
    const std::vector< UnsavedFile > &unsaved_files,
    const std::vector< std::string > &flags,
    bool reparse = true );

  YCM_EXPORT DocumentationData GetDocsForLocationInFile(
    const std::string &translation_unit,
    const std::string &filename,
    int line,
    int column,
    const std::vector< UnsavedFile > &unsaved_files,
    const std::vector< std::string > &flags,
    bool reparse = true );

  void DeleteCachesForFile( const std::string &filename );

private:

  /////////////////////////////
  // PRIVATE MEMBER VARIABLES
  /////////////////////////////

  CXIndex clang_index_;

  TranslationUnitStore translation_unit_store_;
};

} // namespace YouCompleteMe

#endif /* end of include guard: CLANGCOMPLETE_H_WLKDU0ZV */
