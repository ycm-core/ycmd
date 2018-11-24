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

#include "ClangHelpers.h"
#include "ClangUtils.h"
#include "Location.h"
#include "PythonSupport.h"
#include "Range.h"
#include "UnsavedFile.h"
#include "Utils.h"

#include <unordered_map>
#include <utility>

using std::unordered_map;

namespace YouCompleteMe {
namespace {

DiagnosticKind DiagnosticSeverityToType( CXDiagnosticSeverity severity ) {
  switch ( severity ) {
    case CXDiagnostic_Ignored:
    case CXDiagnostic_Note:
      return DiagnosticKind::INFORMATION;

    case CXDiagnostic_Warning:
      return DiagnosticKind::WARNING;

    case CXDiagnostic_Error:
    case CXDiagnostic_Fatal:
    default:
      return DiagnosticKind::ERROR;
  }
}

FixIt BuildDiagnosticFixIt( const std::string& text, CXDiagnostic diagnostic ) {
  FixIt fixit;

  size_t num_chunks = clang_getDiagnosticNumFixIts( diagnostic );
  if ( !num_chunks ) {
    return fixit;
  }

  fixit.chunks.reserve( num_chunks );
  fixit.location = Location( clang_getDiagnosticLocation( diagnostic ) );
  fixit.text = text;

  for ( size_t idx = 0; idx < num_chunks; ++idx ) {
    FixItChunk chunk;
    CXSourceRange range;
    chunk.replacement_text = CXStringToString(
                               clang_getDiagnosticFixIt( diagnostic,
                                                         idx,
                                                         &range ) );

    chunk.range = Range( range );
    fixit.chunks.push_back( chunk );
  }

  return fixit;
}

/// This method generates a FixIt object for the supplied diagnostic, and any
/// child diagnostics (recursively), should a FixIt be available and appends
/// them to fixits.
/// Similarly it populates full_diagnostic_text with a concatenation of the
/// diagnostic text for the supplied diagnostic and each child diagnostic
/// (recursively).
/// Warning: This method is re-entrant (recursive).
void BuildFullDiagnosticDataFromChildren(
  std::string& full_diagnostic_text,
  std::vector< FixIt >& fixits,
  CXDiagnostic diagnostic ) {

  std::string diag_text = CXStringToString( clang_formatDiagnostic(
                              diagnostic,
                              clang_defaultDiagnosticDisplayOptions() ) );

  full_diagnostic_text.append( diag_text );

  // Populate any fixit attached to this diagnostic.
  FixIt fixit = BuildDiagnosticFixIt( diag_text, diagnostic );
  if ( !fixit.chunks.empty() ) {
    fixits.push_back( fixit );
  }

  // Note: clang docs say that a CXDiagnosticSet retrieved with
  // clang_getChildDiagnostics do NOT need to be released with
  // clang_diposeDiagnosticSet
  CXDiagnosticSet diag_set = clang_getChildDiagnostics( diagnostic );

  if ( !diag_set ) {
    return;
  }

  size_t num_child_diagnostics = clang_getNumDiagnosticsInSet( diag_set );

  if ( !num_child_diagnostics ) {
    return;
  }

  for ( size_t i = 0; i < num_child_diagnostics; ++i ) {
    CXDiagnostic child_diag = clang_getDiagnosticInSet( diag_set, i );

    if( !child_diag ) {
      continue;
    }

    full_diagnostic_text.append( "\n" );

    // recurse
    BuildFullDiagnosticDataFromChildren( full_diagnostic_text,
                                         fixits,
                                         child_diag );
  }
}

// Returns true when the provided completion string is available to the user;
// unavailable completion strings refer to entities that are private/protected,
// deprecated etc.
bool CompletionStringAvailable( CXCompletionString completion_string ) {
  return clang_getCompletionAvailability( completion_string ) ==
         CXAvailability_Available;
}


std::vector< Range > GetRanges( const DiagnosticWrap &diagnostic_wrap ) {
  std::vector< Range > ranges;
  size_t num_ranges = clang_getDiagnosticNumRanges( diagnostic_wrap.get() );
  ranges.reserve( num_ranges );

  for ( size_t i = 0; i < num_ranges; ++i ) {
    ranges.emplace_back( clang_getDiagnosticRange( diagnostic_wrap.get(), i ) );
  }

  return ranges;
}


Range GetLocationExtent( CXSourceLocation source_location,
                         CXTranslationUnit translation_unit ) {
  // If you think the below code is an idiotic way of getting the source range
  // for an identifier at a specific source location, you are not the only one.
  // I cannot believe that this is the only way to achieve this with the
  // libclang API in a robust way.
  // I've tried many simpler ways of doing this and they all fail in various
  // situations.

  CXSourceRange range = clang_getRange( source_location, source_location );
  CXToken *tokens;
  unsigned int num_tokens;
  clang_tokenize( translation_unit, range, &tokens, &num_tokens );

  Location location( source_location );
  Range final_range( range );

  for ( size_t i = 0; i < num_tokens; ++i ) {
    CXToken token = tokens[ i ];
    if ( clang_getTokenKind( token ) == CXToken_Comment ) {
      continue;
    }

    Location token_location( clang_getTokenLocation( translation_unit,
                                                     token ) );

    if ( token_location == location ) {
      final_range = Range( clang_getTokenExtent( translation_unit, token ) );
      break;
    }
  }

  clang_disposeTokens( translation_unit, tokens, num_tokens );
  return final_range;
}


} // unnamed namespace

std::vector< CXUnsavedFile > ToCXUnsavedFiles(
  const std::vector< UnsavedFile > &unsaved_files ) {
  std::vector< CXUnsavedFile > clang_unsaved_files( unsaved_files.size() );

  for ( size_t i = 0; i < unsaved_files.size(); ++i ) {
    clang_unsaved_files[ i ].Filename = unsaved_files[ i ].filename_.c_str();
    clang_unsaved_files[ i ].Contents = unsaved_files[ i ].contents_.c_str();
    clang_unsaved_files[ i ].Length   = unsaved_files[ i ].length_;
  }

  return clang_unsaved_files;
}


std::vector< CompletionData > ToCompletionDataVector(
  CXCodeCompleteResults *results ) {
  std::vector< CompletionData > completions;

  if ( !results || !results->Results ) {
    return completions;
  }

  completions.reserve( results->NumResults );
  unordered_map< std::string, size_t > seen_data;

  for ( size_t i = 0; i < results->NumResults; ++i ) {
    CXCompletionResult result = results->Results[ i ];
    CXCompletionString completion_string = result.CompletionString;

    if ( !completion_string ||
         !CompletionStringAvailable( completion_string ) ) {
      continue;
    }

    CompletionData data( completion_string, result.CursorKind, results, i );
    size_t index = GetValueElseInsert( seen_data,
                                       data.original_string_,
                                       completions.size() );

    if ( index == completions.size() ) {
      completions.push_back( std::move( data ) );
    } else {
      // If we have already seen this completion, then this is an overload of a
      // function we have seen. We add the signature of the overload to the
      // detailed information.
      completions[ index ].detailed_info_
      .append( data.return_type_ )
      .append( " " )
      .append( data.everything_except_return_type_ )
      .append( "\n" );
    }
  }

  return completions;
}


Diagnostic BuildDiagnostic( const DiagnosticWrap &diagnostic_wrap,
                            CXTranslationUnit translation_unit ) {
  Diagnostic diagnostic;

  if ( !diagnostic_wrap ) {
    return diagnostic;
  }

  diagnostic.kind_ = DiagnosticSeverityToType(
                       clang_getDiagnosticSeverity( diagnostic_wrap.get() ) );

  // If this is an "ignored" diagnostic, there's no point in continuing since we
  // won't display those to the user
  if ( diagnostic.kind_ == DiagnosticKind::INFORMATION ) {
    return diagnostic;
  }

  CXSourceLocation source_location =
    clang_getDiagnosticLocation( diagnostic_wrap.get() );
  diagnostic.location_ = Location( source_location );
  diagnostic.location_extent_ = GetLocationExtent( source_location,
                                                   translation_unit );
  diagnostic.ranges_ = GetRanges( diagnostic_wrap );
  diagnostic.text_ = CXStringToString(
                       clang_getDiagnosticSpelling( diagnostic_wrap.get() ) );

  BuildFullDiagnosticDataFromChildren( diagnostic.long_formatted_text_,
                                       diagnostic.fixits_,
                                       diagnostic_wrap.get() );

  return diagnostic;
}

} // namespace YouCompleteMe
