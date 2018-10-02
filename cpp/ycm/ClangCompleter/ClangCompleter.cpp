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

#include "ClangCompleter.h"
#include "Candidate.h"
#include "CandidateRepository.h"
#include "ClangUtils.h"
#include "CompletionData.h"
#include "Result.h"
#include "TranslationUnit.h"
#include "Utils.h"

#include <clang-c/Index.h>
#include <memory>


using std::shared_ptr;

namespace YouCompleteMe {

ClangCompleter::ClangCompleter()
  : clang_index_( clang_createIndex( 0, 0 ) ),
    translation_unit_store_( clang_index_ ) {
  // The libclang docs don't say what is the default value for crash recovery.
  // I'm pretty sure it's turned on by default, but I'm not going to take any
  // chances.
  clang_toggleCrashRecovery( true );
}


ClangCompleter::~ClangCompleter() {
  // We need to destroy all TUs before calling clang_disposeIndex because
  // the translation units need to be destroyed before the index is destroyed.
  // Technically, a thread could still be holding onto a shared_ptr<TU> object
  // when we destroy the clang index, but since we're shutting down, we don't
  // really care.
  // In practice, this situation shouldn't happen because the server threads are
  // Python deamon threads and will all be killed before the main thread exits.
  translation_unit_store_.RemoveAll();
  clang_disposeIndex( clang_index_ );
}


bool ClangCompleter::UpdatingTranslationUnit( const std::string &filename ) {
  shared_ptr< TranslationUnit > unit = translation_unit_store_.Get( filename );

  if ( !unit ) {
    return false;
  }

  // Thankfully, an invalid, sentinel TU always returns true for
  // IsCurrentlyUpdating, so no caller will try to rely on the TU object, even
  // if unit is currently pointing to a sentinel.
  return unit->IsCurrentlyUpdating();
}


std::vector< Diagnostic > ClangCompleter::UpdateTranslationUnit(
  const std::string &translation_unit,
  const std::vector< UnsavedFile > &unsaved_files,
  const std::vector< std::string > &flags ) {
  bool translation_unit_created;
  shared_ptr< TranslationUnit > unit = translation_unit_store_.GetOrCreate(
                                         translation_unit,
                                         unsaved_files,
                                         flags,
                                         translation_unit_created );

  try {
    return unit->Reparse( unsaved_files );
  } catch ( const ClangParseError & ) {
    // If unit->Reparse fails, then the underlying TranslationUnit object is not
    // valid anymore and needs to be destroyed and removed from the filename ->
    // TU map.
    translation_unit_store_.Remove( translation_unit );
    throw;
  }
}


std::vector< CompletionData >
ClangCompleter::CandidatesForLocationInFile(
  const std::string &translation_unit,
  const std::string &filename,
  int line,
  int column,
  const std::vector< UnsavedFile > &unsaved_files,
  const std::vector< std::string > &flags ) {
  shared_ptr< TranslationUnit > unit =
    translation_unit_store_.GetOrCreate( translation_unit,
                                         unsaved_files,
                                         flags );

  return unit->CandidatesForLocation( filename,
                                      line,
                                      column,
                                      unsaved_files );
}


Location ClangCompleter::GetDeclarationLocation(
  const std::string &translation_unit,
  const std::string &filename,
  int line,
  int column,
  const std::vector< UnsavedFile > &unsaved_files,
  const std::vector< std::string > &flags,
  bool reparse ) {
  shared_ptr< TranslationUnit > unit =
    translation_unit_store_.GetOrCreate( translation_unit,
                                         unsaved_files,
                                         flags );

  return unit->GetDeclarationLocation( filename,
                                       line,
                                       column,
                                       unsaved_files,
                                       reparse );
}


Location ClangCompleter::GetDefinitionLocation(
  const std::string &translation_unit,
  const std::string &filename,
  int line,
  int column,
  const std::vector< UnsavedFile > &unsaved_files,
  const std::vector< std::string > &flags,
  bool reparse ) {
  shared_ptr< TranslationUnit > unit =
    translation_unit_store_.GetOrCreate( translation_unit,
                                         unsaved_files,
                                         flags );

  return unit->GetDefinitionLocation( filename,
                                      line,
                                      column,
                                      unsaved_files,
                                      reparse );
}

Location ClangCompleter::GetDefinitionOrDeclarationLocation(
  const std::string &translation_unit,
  const std::string &filename,
  int line,
  int column,
  const std::vector< UnsavedFile > &unsaved_files,
  const std::vector< std::string > &flags,
  bool reparse ) {
  shared_ptr< TranslationUnit > unit =
    translation_unit_store_.GetOrCreate( translation_unit,
                                         unsaved_files,
                                         flags );

  return unit->GetDefinitionOrDeclarationLocation( filename,
                                                   line,
                                                   column,
                                                   unsaved_files,
                                                   reparse );
}

std::string ClangCompleter::GetTypeAtLocation(
  const std::string &translation_unit,
  const std::string &filename,
  int line,
  int column,
  const std::vector< UnsavedFile > &unsaved_files,
  const std::vector< std::string > &flags,
  bool reparse ) {

  shared_ptr< TranslationUnit > unit =
    translation_unit_store_.GetOrCreate( translation_unit,
                                         unsaved_files,
                                         flags );

  return unit->GetTypeAtLocation( filename,
                                  line,
                                  column,
                                  unsaved_files,
                                  reparse );
}

std::string ClangCompleter::GetEnclosingFunctionAtLocation(
  const std::string &translation_unit,
  const std::string &filename,
  int line,
  int column,
  const std::vector< UnsavedFile > &unsaved_files,
  const std::vector< std::string > &flags,
  bool reparse ) {

  shared_ptr< TranslationUnit > unit =
    translation_unit_store_.GetOrCreate( translation_unit,
                                         unsaved_files,
                                         flags );

  return unit->GetEnclosingFunctionAtLocation( filename,
                                               line,
                                               column,
                                               unsaved_files,
                                               reparse );
}

std::vector< FixIt >
ClangCompleter::GetFixItsForLocationInFile(
  const std::string &translation_unit,
  const std::string &filename,
  int line,
  int column,
  const std::vector< UnsavedFile > &unsaved_files,
  const std::vector< std::string > &flags,
  bool reparse ) {


  shared_ptr< TranslationUnit > unit =
    translation_unit_store_.GetOrCreate( translation_unit,
                                         unsaved_files,
                                         flags );

  return unit->GetFixItsForLocationInFile( filename,
                                           line,
                                           column,
                                           unsaved_files,
                                           reparse );

}

DocumentationData ClangCompleter::GetDocsForLocationInFile(
  const std::string &translation_unit,
  const std::string &filename,
  int line,
  int column,
  const std::vector< UnsavedFile > &unsaved_files,
  const std::vector< std::string > &flags,
  bool reparse ) {


  shared_ptr< TranslationUnit > unit =
    translation_unit_store_.GetOrCreate( translation_unit,
                                         unsaved_files,
                                         flags );

  Location location( unit->GetDeclarationLocation( filename,
                                                   line,
                                                   column,
                                                   unsaved_files,
                                                   reparse ) );
  // By default, libclang ignores comments from system headers and, in
  // particular, headers included with the -isystem flag. If the declaration is
  // found in such header, get the documentation directly from the corresponding
  // translation unit. Comments in the main file of a translation unit are not
  // ignored.
  if ( unit->LocationIsInSystemHeader( location ) ) {
    unit = translation_unit_store_.GetOrCreate( location.filename_,
                                                unsaved_files,
                                                flags );
    return unit->GetDocsForLocation( location, unsaved_files, reparse );
  }

  // This translation unit has already been parsed when getting the
  // declaration's location.
  return unit->GetDocsForLocation( location, unsaved_files, false );
}

void ClangCompleter::DeleteCachesForFile( const std::string &filename ) {
  translation_unit_store_.Remove( filename );
}


} // namespace YouCompleteMe
