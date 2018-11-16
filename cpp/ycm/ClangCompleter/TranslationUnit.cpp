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

#include "ClangUtils.h"
#include "ClangHelpers.h"
#include "CompletionData.h"
#include "TranslationUnit.h"
#include "Utils.h"

#include <algorithm>
#include <boost/filesystem.hpp>
#include <cstdlib>
#include <memory>

using std::unique_lock;
using std::mutex;
using std::try_to_lock_t;
using std::shared_ptr;
using std::remove_pointer;

namespace YouCompleteMe {

namespace {

unsigned EditingOptions() {
  // See cpp/llvm/include/clang-c/Index.h file for detail on these options.
  return CXTranslationUnit_DetailedPreprocessingRecord |
         CXTranslationUnit_Incomplete |
         CXTranslationUnit_IncludeBriefCommentsInCodeCompletion |
         CXTranslationUnit_CreatePreambleOnFirstParse |
         CXTranslationUnit_KeepGoing |
         clang_defaultEditingTranslationUnitOptions();
}

unsigned ReparseOptions( CXTranslationUnit translationUnit ) {
  return clang_defaultReparseOptions( translationUnit );
}


unsigned CompletionOptions() {
  return clang_defaultCodeCompleteOptions() |
         CXCodeComplete_IncludeBriefComments |
         CXCodeComplete_IncludeCompletionsWithFixIts;
}

void EnsureCompilerNamePresent( std::vector< const char * > &flags ) {
  bool no_compiler_name_set = !flags.empty() && flags.front()[ 0 ] == '-';

  if ( flags.empty() || no_compiler_name_set ) {
    flags.insert( flags.begin(), "clang" );
  }
}

}  // unnamed namespace

using CodeCompleteResultsWrap =
  shared_ptr< remove_pointer< CXCodeCompleteResults >::type >;

TranslationUnit::TranslationUnit()
  : clang_translation_unit_( nullptr ) {
}

TranslationUnit::TranslationUnit(
  const std::string &filename,
  const std::vector< UnsavedFile > &unsaved_files,
  const std::vector< std::string > &flags,
  CXIndex clang_index )
  : clang_translation_unit_( nullptr ) {
  std::vector< const char * > pointer_flags;
  pointer_flags.reserve( flags.size() );

  for ( const std::string & flag : flags ) {
    pointer_flags.push_back( flag.c_str() );
  }

  EnsureCompilerNamePresent( pointer_flags );

  std::vector< CXUnsavedFile > cxunsaved_files =
    ToCXUnsavedFiles( unsaved_files );
  const CXUnsavedFile *unsaved = cxunsaved_files.empty()
                                 ? nullptr : &cxunsaved_files[ 0 ];

  // Actually parse the translation unit.
  CXErrorCode failure = clang_parseTranslationUnit2FullArgv(
                          clang_index,
                          filename.c_str(),
                          &pointer_flags[ 0 ],
                          pointer_flags.size(),
                          const_cast<CXUnsavedFile *>( unsaved ),
                          cxunsaved_files.size(),
                          EditingOptions(),
                          &clang_translation_unit_ );
  if ( failure != CXError_Success ) {
    throw ClangParseError( failure );
  }
}


TranslationUnit::~TranslationUnit() {
  Destroy();
}

void TranslationUnit::Destroy() {
  unique_lock< mutex > lock( clang_access_mutex_ );

  if ( clang_translation_unit_ ) {
    clang_disposeTranslationUnit( clang_translation_unit_ );
    clang_translation_unit_ = nullptr;
  }
}


bool TranslationUnit::IsCurrentlyUpdating() const {
  // We return true when the TU is invalid; an invalid TU also acts a sentinel,
  // preventing other threads from trying to use it.
  if ( !clang_translation_unit_ ) {
    return true;
  }

  unique_lock< mutex > lock( clang_access_mutex_, try_to_lock_t() );
  return !lock.owns_lock();
}


std::vector< Diagnostic > TranslationUnit::Reparse(
  const std::vector< UnsavedFile > &unsaved_files ) {
  std::vector< CXUnsavedFile > cxunsaved_files =
    ToCXUnsavedFiles( unsaved_files );

  Reparse( cxunsaved_files );

  unique_lock< mutex > lock( diagnostics_mutex_ );
  return latest_diagnostics_;
}


std::vector< CompletionData > TranslationUnit::CandidatesForLocation(
  const std::string &filename,
  int line,
  int column,
  const std::vector< UnsavedFile > &unsaved_files ) {
  unique_lock< mutex > lock( clang_access_mutex_ );

  if ( !clang_translation_unit_ ) {
    return std::vector< CompletionData >();
  }

  std::vector< CXUnsavedFile > cxunsaved_files =
    ToCXUnsavedFiles( unsaved_files );
  const CXUnsavedFile *unsaved = cxunsaved_files.empty()
                                 ? nullptr : &cxunsaved_files[ 0 ];

  // codeCompleteAt reparses the TU if the underlying source file has changed on
  // disk since the last time the TU was updated and there are no unsaved files.
  // If there are unsaved files, then codeCompleteAt will parse the in-memory
  // file contents we are giving it. In short, it is NEVER a good idea to call
  // clang_reparseTranslationUnit right before a call to clang_codeCompleteAt.
  // This only makes clang reparse the whole file TWICE, which has a huge impact
  // on latency. At the time of writing, it seems that most users of libclang
  // in the open-source world don't realize this (I checked). Some don't even
  // call reparse*, but parse* which is even less efficient.

  CodeCompleteResultsWrap results(
    clang_codeCompleteAt( clang_translation_unit_,
                          filename.c_str(),
                          line,
                          column,
                          const_cast<CXUnsavedFile *>( unsaved ),
                          cxunsaved_files.size(),
                          CompletionOptions() ),
    clang_disposeCodeCompleteResults );

  std::vector< CompletionData > candidates = ToCompletionDataVector(
                                               results.get() );
  return candidates;
}

Location TranslationUnit::GetDeclarationLocationForCursor( CXCursor cursor ) {
  CXCursor referenced_cursor = clang_getCursorReferenced( cursor );

  if ( !CursorIsValid( referenced_cursor ) ) {
    return Location();
  }

  CXCursor canonical_cursor = clang_getCanonicalCursor( referenced_cursor );

  if ( !CursorIsValid( canonical_cursor ) ) {
    return Location( clang_getCursorLocation( referenced_cursor ) );
  }

  return Location( clang_getCursorLocation( canonical_cursor ) );
}

Location TranslationUnit::GetDeclarationLocation(
  const std::string &filename,
  int line,
  int column,
  const std::vector< UnsavedFile > &unsaved_files,
  bool reparse ) {
  if ( reparse ) {
    Reparse( unsaved_files );
  }

  unique_lock< mutex > lock( clang_access_mutex_ );

  if ( !clang_translation_unit_ ) {
    return Location();
  }

  CXCursor cursor = GetCursor( filename, line, column );

  if ( !CursorIsValid( cursor ) ) {
    return Location();
  }

  return GetDeclarationLocationForCursor( cursor );
}

Location TranslationUnit::GetDefinitionLocationForCursor( CXCursor cursor ) {
  CXCursor definition_cursor = clang_getCursorDefinition( cursor );

  if ( !CursorIsValid( definition_cursor ) ) {
    return Location();
  }

  return Location( clang_getCursorLocation( definition_cursor ) );
}

Location TranslationUnit::GetDefinitionLocation(
  const std::string &filename,
  int line,
  int column,
  const std::vector< UnsavedFile > &unsaved_files,
  bool reparse ) {
  if ( reparse ) {
    Reparse( unsaved_files );
  }

  unique_lock< mutex > lock( clang_access_mutex_ );

  if ( !clang_translation_unit_ ) {
    return Location();
  }

  CXCursor cursor = GetCursor( filename, line, column );

  if ( !CursorIsValid( cursor ) ) {
    return Location();
  }

  return GetDefinitionLocationForCursor( cursor );
}

Location TranslationUnit::GetDefinitionOrDeclarationLocation(
  const std::string &filename,
  int line,
  int column,
  const std::vector< UnsavedFile > &unsaved_files,
  bool reparse ) {
  if ( reparse ) {
    Reparse( unsaved_files );
  }

  unique_lock< mutex > lock( clang_access_mutex_ );

  if ( !clang_translation_unit_ ) {
    return Location();
  }

  CXCursor cursor = GetCursor( filename, line, column );

  if ( !CursorIsValid( cursor ) ) {
    return Location();
  }

  // Return the definition or the declaration of a symbol under the cursor
  // according to the following logic:
  //  - if the cursor is already on the definition, return the location of the
  //    declaration;
  //  - otherwise, search for the definition and return its location;
  //  - if no definition is found, return the location of the declaration.
  if ( clang_isCursorDefinition( cursor ) ) {
    return GetDeclarationLocationForCursor( cursor );
  }

  Location location = GetDefinitionLocationForCursor( cursor );

  if ( location.IsValid() ) {
    return location;
  }

  return GetDeclarationLocationForCursor( cursor );
}

std::string TranslationUnit::GetTypeAtLocation(
  const std::string &filename,
  int line,
  int column,
  const std::vector< UnsavedFile > &unsaved_files,
  bool reparse ) {

  if ( reparse ) {
    Reparse( unsaved_files );
  }

  unique_lock< mutex > lock( clang_access_mutex_ );

  if ( !clang_translation_unit_ ) {
    return "Internal error: no translation unit";
  }

  CXCursor cursor = GetCursor( filename, line, column );

  if ( !CursorIsValid( cursor ) ) {
    return "Internal error: cursor not valid";
  }

  // Cursors on member functions return a rather unhelpful type text of
  // "bound member function type".  To get a meaningful type, we must examine
  // the referenced cursor.  We must be careful though, as both member variables
  // and member functions are of kind MemberRefExpr, and getting the referenced
  // cursor of a cv-qualified type discards the cv-qualification.
  if ( clang_getCursorKind( cursor ) == CXCursor_MemberRefExpr ) {
    CXCursor ref = clang_getCursorReferenced( cursor );
    if ( clang_getCursorKind( ref ) == CXCursor_CXXMethod ) {
      cursor = ref;
    }
  }

  CXType type = clang_getCursorType( cursor );

  std::string type_description =
    CXStringToString( clang_getTypeSpelling( type ) );

  if ( type_description.empty() ) {
    return "Unknown type";
  }

  // We have a choice here; libClang provides clang_getCanonicalType which will
  // return the "underlying" type for the type returned by clang_getCursorType
  // e.g. for a typedef
  //     type = clang_getCanonicalType( type );
  //
  // Without the above, something like the following would return "MyType"
  // rather than int:
  //     typedef int MyType;
  //     MyType i = 100; <-- type = MyType, canonical type = int
  //
  // There is probably more semantic value in calling it MyType. Indeed, if we
  // opt for the more specific type, we can get very long or
  // confusing STL types even for simple usage. e.g. the following:
  //     std::string test = "test"; <-- type = std::string;
  //                                    canonical type = std::basic_string<char>
  //
  // So as a compromise, we return both if and only if the types differ, like
  //     std::string => std::basic_string<char>

  CXType canonical_type = clang_getCanonicalType( type );

  if ( !clang_equalTypes( type, canonical_type ) ) {
    std::string canonical_type_description = CXStringToString(
      clang_getTypeSpelling( canonical_type ) );

    // Clang may return that the canonical type of a symbol is distinct from its
    // type even though they result in the same string. Only append the
    // canonical type if the strings are different.
    if ( type_description != canonical_type_description ) {
      type_description += " => " + canonical_type_description;
    }
  }

  return type_description;
}

std::string TranslationUnit::GetEnclosingFunctionAtLocation(
  const std::string &filename,
  int line,
  int column,
  const std::vector< UnsavedFile > &unsaved_files,
  bool reparse ) {

  if ( reparse ) {
    Reparse( unsaved_files );
  }

  unique_lock< mutex > lock( clang_access_mutex_ );

  if ( !clang_translation_unit_ ) {
    return "Internal error: no translation unit";
  }

  CXCursor cursor = GetCursor( filename, line, column );

  if ( !CursorIsValid( cursor ) ) {
    return "Internal error: cursor not valid";
  }

  CXCursor parent = clang_getCursorSemanticParent( cursor );

  std::string parent_str =
    CXStringToString( clang_getCursorDisplayName( parent ) );

  if ( parent_str.empty() ) {
    return "Unknown semantic parent";
  }

  return parent_str;
}

// Argument taken as non-const ref because we need to be able to pass a
// non-const pointer to clang. This function (and clang too) will not modify the
// param though.
void TranslationUnit::Reparse(
  std::vector< CXUnsavedFile > &unsaved_files ) {
  unsigned options = ( clang_translation_unit_
                       ? ReparseOptions( clang_translation_unit_ )
                       : static_cast<unsigned>( CXReparse_None ) );

  Reparse( unsaved_files, options );
}


// Argument taken as non-const ref because we need to be able to pass a
// non-const pointer to clang. This function (and clang too) will not modify the
// param though.
void TranslationUnit::Reparse( std::vector< CXUnsavedFile > &unsaved_files,
                               size_t parse_options ) {
  CXErrorCode failure;
  {
    unique_lock< mutex > lock( clang_access_mutex_ );

    if ( !clang_translation_unit_ ) {
      return;
    }

    CXUnsavedFile *unsaved = unsaved_files.empty()
                             ? nullptr : &unsaved_files[ 0 ];

    // This function should technically return a CXErrorCode enum but return an
    // int instead.
    failure = static_cast< CXErrorCode >(
      clang_reparseTranslationUnit( clang_translation_unit_,
                                    unsaved_files.size(),
                                    unsaved,
                                    parse_options ) );
  }

  if ( failure != CXError_Success ) {
    Destroy();
    throw ClangParseError( failure );
  }

  UpdateLatestDiagnostics();
}

void TranslationUnit::UpdateLatestDiagnostics() {
  unique_lock< mutex > lock1( clang_access_mutex_ );
  unique_lock< mutex > lock2( diagnostics_mutex_ );

  latest_diagnostics_.clear();
  size_t num_diagnostics = clang_getNumDiagnostics( clang_translation_unit_ );
  latest_diagnostics_.reserve( num_diagnostics );

  for ( size_t i = 0; i < num_diagnostics; ++i ) {
    Diagnostic diagnostic =
      BuildDiagnostic(
        DiagnosticWrap( clang_getDiagnostic( clang_translation_unit_, i ),
                        clang_disposeDiagnostic ),
        clang_translation_unit_ );

    if ( diagnostic.kind_ != DiagnosticKind::INFORMATION ) {
      latest_diagnostics_.push_back( diagnostic );
    }
  }
}

namespace {

/// Sort a FixIt container by its location's distance from a given column
/// (such as the cursor location).
///
/// PreCondition: All FixIts in the container are on the same line.
struct sort_by_location {
  explicit sort_by_location( int column ) : column_( column ) { }

  bool operator()( const FixIt &a, const FixIt &b ) {
    int a_distance = a.location.column_number_ - column_;
    int b_distance = b.location.column_number_ - column_;

    return std::abs( a_distance ) < std::abs( b_distance );
  }

private:
  int column_;
};

} // unnamed namespace

std::vector< FixIt > TranslationUnit::GetFixItsForLocationInFile(
  const std::string &filename,
  int line,
  int column,
  const std::vector< UnsavedFile > &unsaved_files,
  bool reparse ) {

  if ( reparse ) {
    Reparse( unsaved_files );
  }

  std::vector< FixIt > fixits;

  auto normal_filename = NormalizePath( filename );

  {
    unique_lock< mutex > lock( diagnostics_mutex_ );

    for ( const Diagnostic& diagnostic : latest_diagnostics_ ) {
      auto this_filename = NormalizePath( diagnostic.location_.filename_ );

      if ( normal_filename != this_filename ) {
        continue;
      }

      // Find all diagnostics for the supplied line which have FixIts attached
      if ( diagnostic.location_.line_number_ !=
             static_cast< size_t >( line ) ) {
        continue;
      }

      fixits.insert( fixits.end(),
                     diagnostic.fixits_.begin(),
                     diagnostic.fixits_.end() );
    }
  }

  // Sort them by the distance to the supplied column
  std::sort( fixits.begin(),
             fixits.end(),
             sort_by_location( column ) );

  return fixits;
}

DocumentationData TranslationUnit::GetDocsForLocation(
  const Location &location,
  const std::vector< UnsavedFile > &unsaved_files,
  bool reparse ) {

  if ( reparse ) {
    Reparse( unsaved_files );
  }

  unique_lock< mutex > lock( clang_access_mutex_ );

  if ( !clang_translation_unit_ ) {
    return DocumentationData();
  }

  CXCursor cursor = GetCursor( location.filename_,
                               location.line_number_,
                               location.column_number_ );

  if ( !CursorIsValid( cursor ) ) {
    return DocumentationData();
  }

  return DocumentationData( cursor );
}

bool TranslationUnit::LocationIsInSystemHeader( const Location &location ) {
  unique_lock< mutex > lock( clang_access_mutex_ );

  if ( !clang_translation_unit_ || !location.IsValid() ) {
    return false;
  }

  return clang_Location_isInSystemHeader(
    GetSourceLocation( location.filename_,
                       location.line_number_,
                       location.column_number_ ) );
}

CXSourceLocation TranslationUnit::GetSourceLocation(
  const std::string &filename,
  int line,
  int column ) {

  // ASSUMES A LOCK IS ALREADY HELD ON clang_access_mutex_ AND THE TU IS VALID!
  CXFile file = clang_getFile( clang_translation_unit_, filename.c_str() );
  return clang_getLocation( clang_translation_unit_, file, line, column );
}

CXCursor TranslationUnit::GetCursor( const std::string &filename,
                                     int line,
                                     int column ) {
  // ASSUMES A LOCK IS ALREADY HELD ON clang_access_mutex_ AND THE TU IS VALID!
  return clang_getCursor( clang_translation_unit_,
                          GetSourceLocation( filename, line, column ) );
}

} // namespace YouCompleteMe
