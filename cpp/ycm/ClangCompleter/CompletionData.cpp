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

#include "CompletionData.h"
#include "ClangUtils.h"

#include <algorithm>
#include <numeric>
#include <utility>

namespace YouCompleteMe {

namespace {

CompletionKind CursorKindToCompletionKind( CXCursorKind kind ) {
  switch ( kind ) {
    case CXCursor_StructDecl:
      return CompletionKind::STRUCT;

    case CXCursor_ClassDecl:
    case CXCursor_ClassTemplate:
    case CXCursor_ObjCInterfaceDecl:
    case CXCursor_ObjCImplementationDecl:
      return CompletionKind::CLASS;

    case CXCursor_EnumDecl:
      return CompletionKind::ENUM;

    case CXCursor_UnexposedDecl:
    case CXCursor_UnionDecl:
    case CXCursor_TypedefDecl:
      return CompletionKind::TYPE;

    case CXCursor_FieldDecl:
    case CXCursor_ObjCIvarDecl:
    case CXCursor_ObjCPropertyDecl:
    case CXCursor_EnumConstantDecl:
      return CompletionKind::MEMBER;

    case CXCursor_FunctionDecl:
    case CXCursor_CXXMethod:
    case CXCursor_FunctionTemplate:
    case CXCursor_ConversionFunction:
    case CXCursor_Constructor:
    case CXCursor_Destructor:
    case CXCursor_ObjCClassMethodDecl:
    case CXCursor_ObjCInstanceMethodDecl:
      return CompletionKind::FUNCTION;

    case CXCursor_VarDecl:
      return CompletionKind::VARIABLE;

    case CXCursor_MacroDefinition:
      return CompletionKind::MACRO;

    case CXCursor_ParmDecl:
      return CompletionKind::PARAMETER;

    case CXCursor_Namespace:
    case CXCursor_NamespaceAlias:
      return CompletionKind::NAMESPACE;

    default:
      return CompletionKind::UNKNOWN;
  }
}


bool IsMainCompletionTextInfo( CXCompletionChunkKind kind ) {
  return
    kind == CXCompletionChunk_Optional     ||
    kind == CXCompletionChunk_TypedText    ||
    kind == CXCompletionChunk_Placeholder  ||
    kind == CXCompletionChunk_LeftParen    ||
    kind == CXCompletionChunk_RightParen   ||
    kind == CXCompletionChunk_RightBracket ||
    kind == CXCompletionChunk_LeftBracket  ||
    kind == CXCompletionChunk_LeftBrace    ||
    kind == CXCompletionChunk_RightBrace   ||
    kind == CXCompletionChunk_RightAngle   ||
    kind == CXCompletionChunk_LeftAngle    ||
    kind == CXCompletionChunk_Comma        ||
    kind == CXCompletionChunk_Colon        ||
    kind == CXCompletionChunk_SemiColon    ||
    kind == CXCompletionChunk_Equal        ||
    kind == CXCompletionChunk_Informative  ||
    kind == CXCompletionChunk_HorizontalSpace ||
    kind == CXCompletionChunk_Text;

}


std::string ChunkToString( CXCompletionString completion_string,
                           size_t chunk_num ) {
  if ( !completion_string ) {
    return std::string();
  }

  return CXStringToString(
           clang_getCompletionChunkText( completion_string, chunk_num ) );
}


std::string OptionalChunkToString( CXCompletionString completion_string,
                                   size_t chunk_num ) {
  std::string final_string;

  if ( !completion_string ) {
    return final_string;
  }

  CXCompletionString optional_completion_string =
    clang_getCompletionChunkCompletionString( completion_string, chunk_num );

  if ( !optional_completion_string ) {
    return final_string;
  }

  size_t optional_num_chunks = clang_getNumCompletionChunks(
                               optional_completion_string );

  for ( size_t j = 0; j < optional_num_chunks; ++j ) {
    CXCompletionChunkKind kind = clang_getCompletionChunkKind(
                                   optional_completion_string, j );

    if ( kind == CXCompletionChunk_Optional ) {
      final_string.append( OptionalChunkToString( optional_completion_string,
                                                  j ) );
    } else {
      final_string.append( ChunkToString( optional_completion_string, j ) );
    }
  }

  return final_string;
}


bool IdentifierEndsWith( const std::string &identifier,
                         const std::string &end ) {
  if ( identifier.size() >= end.size() ) {
    return 0 == identifier.compare( identifier.length() - end.length(),
                                    end.length(),
                                    end );
  }

  return false;
}


// foo( -> foo
// foo() -> foo
std::string RemoveTrailingParens( std::string text ) {
  if ( IdentifierEndsWith( text, "(" ) ) {
    text.erase( text.length() - 1, 1 );
  } else if ( IdentifierEndsWith( text, "()" ) ) {
    text.erase( text.length() - 2, 2 );
  }

  return text;
}

} // unnamed namespace


CompletionData::CompletionData( CXCompletionString completion_string,
                                CXCursorKind kind,
                                std::shared_ptr< CXCodeCompleteResults > results,
                                size_t index )
        : completion_string_( completion_string ),
          index_( index ),
          results_( std::move( results ) ) {
  size_t num_chunks = clang_getNumCompletionChunks( completion_string );
  bool saw_placeholder = false;

  completion_chunk_kinds_.reserve( num_chunks );
  for ( size_t j = 0; j < num_chunks; ++j ) {
    CXCompletionChunkKind completion_chunk_kind = clang_getCompletionChunkKind(
                                   completion_string, j );

    completion_chunk_kinds_.push_back( completion_chunk_kind );
    if ( completion_chunk_kind == CXCompletionChunk_Placeholder ) {
          saw_placeholder = true;
    }
    if ( ( completion_chunk_kind == CXCompletionChunk_TypedText ||
           completion_chunk_kind == CXCompletionChunk_Text ||
           // need to add paren to insert string
           // when implementing inherited methods or declared methods in objc.
           completion_chunk_kind == CXCompletionChunk_LeftParen ||
           completion_chunk_kind == CXCompletionChunk_RightParen ||
           completion_chunk_kind == CXCompletionChunk_HorizontalSpace ) &&
           !saw_placeholder ) {
      original_string_ += ChunkToString( completion_string, j );
    }
  }

  original_string_ = RemoveTrailingParens( std::move( original_string_ ) );
  kind_ = CursorKindToCompletionKind( kind );

  detailed_info_.append( "YCM_REPLACE\n" );
}


FixIt CompletionData::BuildCompletionFixIt() {
  if ( fixit_.chunks.empty() ) {
    CXCodeCompleteResults *results = results_.get();
    size_t num_chunks = clang_getCompletionNumFixIts( results, index_ );
    if ( !num_chunks ) {
      return fixit_;
    }

    fixit_.chunks.reserve( num_chunks );

    for ( size_t chunk_index = 0; chunk_index < num_chunks; ++chunk_index ) {
      FixItChunk chunk;
      CXSourceRange range;
      chunk.replacement_text = CXStringToString(
                                 clang_getCompletionFixIt( results,
                                                           index_,
                                                           chunk_index,
                                                           &range ) );

      chunk.range = Range( range );
      fixit_.chunks.push_back( chunk );
    }
  }
  return fixit_;
}


std::string CompletionData::DocString() {
  if ( doc_string_.empty() ) {
    doc_string_ = CXStringToString(
      clang_getCompletionBriefComment( completion_string_ ) );
  }
  return doc_string_;
}


std::string CompletionData::ExtraMenuInfo() {
  if ( return_type_.empty() ) {
    auto ret = std::find( completion_chunk_kinds_.begin(),
                          completion_chunk_kinds_.end(),
                          CXCompletionChunk_ResultType );
    size_t index = std::distance( completion_chunk_kinds_.begin(), ret );
    return_type_ = ChunkToString( completion_string_, index );
  }
  return return_type_;
}


std::string CompletionData::MainCompletionText() {
  if ( everything_except_return_type_.empty() ) {
    bool saw_left_paren = false;
    bool saw_function_params = false;
    everything_except_return_type_ = std::accumulate(
      completion_chunk_kinds_.begin(),
      completion_chunk_kinds_.end(),
      std::string{},
      [ & ]( std::string& current,
             const CXCompletionChunkKind& kind ) {
        std::string piece;
        if ( IsMainCompletionTextInfo( kind ) ) {
          if ( kind == CXCompletionChunk_LeftParen ) {
            saw_left_paren = true;
          } else if ( saw_left_paren &&
                      !saw_function_params &&
                      kind != CXCompletionChunk_RightParen &&
                      kind != CXCompletionChunk_Informative ) {
            saw_function_params = true;
            piece.append( " " );
          } else if ( saw_function_params &&
                      kind == CXCompletionChunk_RightParen ) {
            piece.append( " " );
          }
          size_t index = &kind - &*completion_chunk_kinds_.begin();
          if ( kind == CXCompletionChunk_Optional ) {
            piece.append( OptionalChunkToString( completion_string_, index ) );
          } else {
            piece.append( ChunkToString( completion_string_, index ) );
          }
        }
        return std::move( current ) + piece;
      } );
  }
  return everything_except_return_type_;
}


std::string CompletionData::DetailedInfoForPreviewWindow() {
  if ( detailed_info_.compare( 0, 11, "YCM_REPLACE" ) == 0 ) {
    detailed_info_.replace( 0,
                            11,
                            ExtraMenuInfo() + " " + MainCompletionText() );
  }
  return detailed_info_;
}

} // namespace YouCompleteMe
