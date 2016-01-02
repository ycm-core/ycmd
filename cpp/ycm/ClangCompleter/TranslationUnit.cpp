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

#include "TranslationUnit.h"
#include "CompletionData.h"
#include "standard.h"
#include "exceptions.h"
#include "ClangUtils.h"
#include "ClangHelpers.h"

#include <algorithm>

#include <boost/shared_ptr.hpp>
#include <boost/scoped_array.hpp>
#include <boost/type_traits/remove_pointer.hpp>

using boost::unique_lock;
using boost::mutex;
using boost::try_to_lock_t;
using boost::shared_ptr;
using boost::remove_pointer;

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
         CXCodeComplete_IncludeBriefComments;
}

void EnsureCompilerNamePresent( std::vector< const char * > &flags ) {
  bool no_compiler_name_set = !flags.empty() && flags.front()[ 0 ] == '-';

  if ( flags.empty() || no_compiler_name_set )
    flags.insert( flags.begin(), "clang" );
}

}  // unnamed namespace

typedef shared_ptr <
remove_pointer< CXCodeCompleteResults >::type > CodeCompleteResultsWrap;

TranslationUnit::TranslationUnit()
  : filename_( "" ),
    clang_translation_unit_( NULL ) {
}

TranslationUnit::TranslationUnit(
  const std::string &filename,
  const std::vector< UnsavedFile > &unsaved_files,
  const std::vector< std::string > &flags,
  CXIndex clang_index )
  : filename_( filename ),
    clang_translation_unit_( NULL ) {
  std::vector< const char * > pointer_flags;
  pointer_flags.reserve( flags.size() );

  foreach ( const std::string & flag, flags ) {
    pointer_flags.push_back( flag.c_str() );
  }

  EnsureCompilerNamePresent( pointer_flags );

  std::vector< CXUnsavedFile > cxunsaved_files =
    ToCXUnsavedFiles( unsaved_files );
  const CXUnsavedFile *unsaved = cxunsaved_files.size() > 0
                                 ? &cxunsaved_files[ 0 ] : NULL;

  // Actually parse the translation unit.
  CXErrorCode result = clang_parseTranslationUnit2FullArgv(
                         clang_index,
                         filename.c_str(),
                         &pointer_flags[ 0 ],
                         pointer_flags.size(),
                         const_cast<CXUnsavedFile *>( unsaved ),
                         cxunsaved_files.size(),
                         EditingOptions(),
                         &clang_translation_unit_ );

  if ( result != CXError_Success )
    boost_throw( ClangParseError() );
}


TranslationUnit::~TranslationUnit() {
  Destroy();
}

void TranslationUnit::Destroy() {
  unique_lock< mutex > lock( clang_access_mutex_ );

  if ( clang_translation_unit_ ) {
    clang_disposeTranslationUnit( clang_translation_unit_ );
    clang_translation_unit_ = NULL;
  }
}


bool TranslationUnit::IsCurrentlyUpdating() const {
  // We return true when the TU is invalid; an invalid TU also acts a sentinel,
  // preventing other threads from trying to use it.
  if ( !clang_translation_unit_ )
    return true;

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
  int line,
  int column,
  const std::vector< UnsavedFile > &unsaved_files ) {
  unique_lock< mutex > lock( clang_access_mutex_ );

  if ( !clang_translation_unit_ )
    return std::vector< CompletionData >();

  std::vector< CXUnsavedFile > cxunsaved_files =
    ToCXUnsavedFiles( unsaved_files );
  const CXUnsavedFile *unsaved = cxunsaved_files.size() > 0
                                 ? &cxunsaved_files[ 0 ] : NULL;

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
                          filename_.c_str(),
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

Location TranslationUnit::GetDeclarationLocation(
  int line,
  int column,
  const std::vector< UnsavedFile > &unsaved_files,
  bool reparse ) {
  if ( reparse )
    Reparse( unsaved_files );

  unique_lock< mutex > lock( clang_access_mutex_ );

  if ( !clang_translation_unit_ )
    return Location();

  CXCursor cursor = GetCursor( line, column );

  if ( !CursorIsValid( cursor ) )
    return Location();

  CXCursor referenced_cursor = clang_getCursorReferenced( cursor );

  if ( !CursorIsValid( referenced_cursor ) )
    return Location();

  CXCursor canonical_cursor = clang_getCanonicalCursor( referenced_cursor );

  if ( !CursorIsValid( canonical_cursor ) )
    return Location( clang_getCursorLocation( referenced_cursor ) );

  return Location( clang_getCursorLocation( canonical_cursor ) );
}

Location TranslationUnit::GetDefinitionLocation(
  int line,
  int column,
  const std::vector< UnsavedFile > &unsaved_files,
  bool reparse ) {
  if ( reparse )
    Reparse( unsaved_files );

  unique_lock< mutex > lock( clang_access_mutex_ );

  if ( !clang_translation_unit_ )
    return Location();

  CXCursor cursor = GetCursor( line, column );

  if ( !CursorIsValid( cursor ) )
    return Location();

  CXCursor definition_cursor = clang_getCursorDefinition( cursor );

  if ( !CursorIsValid( definition_cursor ) )
    return Location();

  return Location( clang_getCursorLocation( definition_cursor ) );
}

std::string TranslationUnit::GetTypeAtLocation(
  int line,
  int column,
  const std::vector< UnsavedFile > &unsaved_files,
  bool reparse ) {

  if ( reparse )
    Reparse( unsaved_files );

  unique_lock< mutex > lock( clang_access_mutex_ );

  if ( !clang_translation_unit_ )
    return "Internal error: no translation unit";

  CXCursor cursor = GetCursor( line, column );

  if ( !CursorIsValid( cursor ) )
    return "Internal error: cursor not valid";

  CXType type = clang_getCursorType( cursor );

  std::string type_description =
    CXStringToString( clang_getTypeSpelling( type ) );

  if ( type_description.empty() )
    return "Unknown type";

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
    type_description += " => ";
    type_description += CXStringToString(
                          clang_getTypeSpelling( canonical_type ) );
  }

  return type_description;
}

std::string TranslationUnit::GetEnclosingFunctionAtLocation(
  int line,
  int column,
  const std::vector< UnsavedFile > &unsaved_files,
  bool reparse ) {

  if ( reparse )
    Reparse( unsaved_files );

  unique_lock< mutex > lock( clang_access_mutex_ );

  if ( !clang_translation_unit_ )
    return "Internal error: no translation unit";

  CXCursor cursor = GetCursor( line, column );

  if ( !CursorIsValid( cursor ) )
    return "Internal error: cursor not valid";

  CXCursor parent = clang_getCursorSemanticParent( cursor );

  std::string parent_str =
    CXStringToString( clang_getCursorDisplayName( parent ) );

  if ( parent_str.empty() )
    return "Unknown semantic parent";

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
                               uint parse_options ) {
  int failure = 0;
  {
    unique_lock< mutex > lock( clang_access_mutex_ );

    if ( !clang_translation_unit_ )
      return;

    CXUnsavedFile *unsaved = unsaved_files.size() > 0
                             ? &unsaved_files[ 0 ] : NULL;

    failure = clang_reparseTranslationUnit( clang_translation_unit_,
                                            unsaved_files.size(),
                                            unsaved,
                                            parse_options );
  }

  if ( failure ) {
    Destroy();
    boost_throw( ClangParseError() );
  }

  UpdateLatestDiagnostics();
}

void TranslationUnit::UpdateLatestDiagnostics() {
  unique_lock< mutex > lock1( clang_access_mutex_ );
  unique_lock< mutex > lock2( diagnostics_mutex_ );

  latest_diagnostics_.clear();
  uint num_diagnostics = clang_getNumDiagnostics( clang_translation_unit_ );
  latest_diagnostics_.reserve( num_diagnostics );

  for ( uint i = 0; i < num_diagnostics; ++i ) {
    Diagnostic diagnostic =
      BuildDiagnostic(
        DiagnosticWrap( clang_getDiagnostic( clang_translation_unit_, i ),
                        clang_disposeDiagnostic ),
        clang_translation_unit_ );

    if ( diagnostic.kind_ != INFORMATION )
      latest_diagnostics_.push_back( diagnostic );
  }
}

namespace {
/// Sort a FixIt container by its location's distance from a given column
/// (such as the cursor location).
///
/// PreCondition: All FixIts in the container are on the same line.
struct sort_by_location {
  sort_by_location( int column ) : column_( column ) { }

  bool operator()( const FixIt &a, const FixIt &b ) {
    int a_distance = a.location.column_number_ - column_;
    int b_distance = b.location.column_number_ - column_;

    return std::abs( a_distance ) < std::abs( b_distance );
  }

private:
  int column_;
};
}

std::vector< FixIt > TranslationUnit::GetFixItsForLocationInFile(
  int line,
  int column,
  const std::vector< UnsavedFile > &unsaved_files,
  bool reparse ) {

  if ( reparse )
    Reparse( unsaved_files );

  std::vector< FixIt > fixits;

  {
    unique_lock< mutex > lock( diagnostics_mutex_ );

    foreach( const Diagnostic& diagnostic, latest_diagnostics_ ) {
      // Find all diagnostics for the supplied line which have FixIts attached
      if ( diagnostic.location_.line_number_ == static_cast< uint >( line ) ) {
        fixits.insert( fixits.end(),
                       diagnostic.fixits_.begin(),
                       diagnostic.fixits_.end() );
      }
    }
  }

  // Sort them by the distance to the supplied column
  std::sort( fixits.begin(),
             fixits.end(),
             sort_by_location( column ) );

  return fixits;
}

DocumentationData TranslationUnit::GetDocsForLocationInFile(
  int line,
  int column,
  const std::vector< UnsavedFile > &unsaved_files,
  bool reparse ) {

  if ( reparse )
    Reparse( unsaved_files );

  unique_lock< mutex > lock( clang_access_mutex_ );

  if ( !clang_translation_unit_ )
    return DocumentationData();

  CXCursor cursor = GetCursor( line, column );

  if ( !CursorIsValid( cursor ) )
    return DocumentationData();

  // If the original cursor is a reference, then we return the documentation
  // for the type/method/etc. that is referenced
  CXCursor referenced_cursor = clang_getCursorReferenced( cursor );

  if ( CursorIsValid( referenced_cursor ) )
    cursor = referenced_cursor;

  // We always want the documentation associated with the canonical declaration
  CXCursor canonical_cursor = clang_getCanonicalCursor( cursor );

  if ( !CursorIsValid( canonical_cursor ) )
    return DocumentationData();

  return DocumentationData( canonical_cursor );
}


namespace {

void zeroToOne( uint& value ) {
  if ( value == 0 ) {
    value = 1;
  }
}

} // unnamed namespace

std::vector< Token > TranslationUnit::GetSemanticTokens(
  uint start_line,
  uint start_column,
  uint end_line,
  uint end_column ) {

  unique_lock< mutex > lock1( clang_access_mutex_ );
  if ( !clang_translation_unit_ ) {
    return std::vector< Token >();
  }

  zeroToOne( start_line );
  zeroToOne( start_column );
  zeroToOne( end_column );
  if ( end_line == 0 ) {
    // In this case we should tokenize till the end.
    // We are just setting maximum possible line number, clang supports this.
    end_line = static_cast< uint >( -1 );
  }

  CXFile file = GetFile();
  CXSourceLocation start = GetLocation( file, start_line, start_column );
  CXSourceLocation end = GetLocation( file, end_line, end_column );
  CXSourceRange range = clang_getRange( start, end );

  CXToken* tokens = 0;
  uint num_tokens = 0;
  clang_tokenize( clang_translation_unit_, range, &tokens, &num_tokens );

  boost::scoped_array< CXCursor > cursors( new CXCursor[ num_tokens ] );
  clang_annotateTokens( clang_translation_unit_, tokens, num_tokens,
                        cursors.get() );

  std::vector< Token > semantic_tokens;
  for ( uint i = 0; i < num_tokens; ++i ) {
    if ( clang_getTokenKind( tokens[ i ] ) != CXToken_Identifier ) {
      continue;
    }
    CXSourceRange tokenRange = clang_getTokenExtent( clang_translation_unit_,
                                                     tokens[ i ] );
    Token token( tokenRange, cursors[ i ] );
    if ( token.kind_ != Token::UNSUPPORTED ) {
      semantic_tokens.push_back( token );
    }
  }

  clang_disposeTokens( clang_translation_unit_, tokens, num_tokens );
  return semantic_tokens;
}


CXFile TranslationUnit::GetFile() {
  // ASSUMES A LOCK IS ALREADY HELD ON clang_access_mutex_!
  // and clang_translation_unit_ is valid!
  return clang_getFile( clang_translation_unit_, filename_.c_str() );
}

CXSourceLocation TranslationUnit::GetLocation(
  CXFile file, int line, int column ) {

  // ASSUMES A LOCK IS ALREADY HELD ON clang_access_mutex_!
  // and clang_translation_unit_ is valid!
  return clang_getLocation( clang_translation_unit_, file, line, column );
}

CXSourceLocation TranslationUnit::GetLocation( int line, int column ) {
  // ASSUMES A LOCK IS ALREADY HELD ON clang_access_mutex_!
  // and clang_translation_unit_ is valid!
  return clang_getLocation( clang_translation_unit_, GetFile(), line, column );
}

CXCursor TranslationUnit::GetCursor( int line, int column ) {
  // ASSUMES A LOCK IS ALREADY HELD ON clang_access_mutex_!
  if ( !clang_translation_unit_ )
    return clang_getNullCursor();

  CXSourceLocation source_location = GetLocation(line, column);

  return clang_getCursor( clang_translation_unit_, source_location );
}

} // namespace YouCompleteMe
