// Copyright (C) 2011, 2012  Google Inc.
//
// This file is part of YouCompleteMe.
//
// YouCompleteMe is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// YouCompleteMe is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with YouCompleteMe.  If not, see <http://www.gnu.org/licenses/>.

#include "CompletionData.h"
#include "ClangUtils.h"

#include <boost/algorithm/string/erase.hpp>
#include <boost/algorithm/string/predicate.hpp>
#include <boost/move/move.hpp>

namespace YouCompleteMe {

namespace {

CompletionKind CursorKindToCompletionKind( CXCursorKind kind ) {
  switch ( kind ) {
    case CXCursor_StructDecl:
      return STRUCT;

    case CXCursor_ClassDecl:
    case CXCursor_ClassTemplate:
    case CXCursor_ObjCInterfaceDecl:
    case CXCursor_ObjCImplementationDecl:
      return CLASS;

    case CXCursor_EnumDecl:
      return ENUM;

    case CXCursor_UnexposedDecl:
    case CXCursor_UnionDecl:
    case CXCursor_TypedefDecl:
      return TYPE;

    case CXCursor_FieldDecl:
    case CXCursor_ObjCIvarDecl:
    case CXCursor_ObjCPropertyDecl:
    case CXCursor_EnumConstantDecl:
      return MEMBER;

    case CXCursor_FunctionDecl:
    case CXCursor_CXXMethod:
    case CXCursor_FunctionTemplate:
    case CXCursor_ConversionFunction:
    case CXCursor_Constructor:
    case CXCursor_Destructor:
    case CXCursor_ObjCClassMethodDecl:
    case CXCursor_ObjCInstanceMethodDecl:
      return FUNCTION;

    case CXCursor_VarDecl:
      return VARIABLE;

    case CXCursor_MacroDefinition:
      return MACRO;

    case CXCursor_ParmDecl:
      return PARAMETER;

    case CXCursor_Namespace:
    case CXCursor_NamespaceAlias:
      return NAMESPACE;

    default:
      return UNKNOWN;
  }
}

//TODO: maybe not needed
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
                           uint chunk_num ) {
  if ( !completion_string )
    return std::string();

  return YouCompleteMe::CXStringToString(
           clang_getCompletionChunkText( completion_string, chunk_num ) );
}

// NOTE: this function accepts the text param by value on purpose; it internally
// needs a copy before processing the text so the copy might as well be made on
// the parameter BUT if this code is compiled in C++11 mode a move constructor
// can be called on the passed-in value. This is not possible if we accept the
// param by const ref.
std::string RemoveTwoConsecutiveUnderscores( std::string text ) {
  boost::erase_all( text, "__" );
  return text;
}

} // unnamed namespace


CompletionData::CompletionData( const CXCompletionResult &completion_result ) {
  kind_ = CursorKindToCompletionKind( completion_result.CursorKind );

  CXCompletionString completion_string = completion_result.CompletionString;

  if ( completion_string ) {
    doc_string_ = YouCompleteMe::CXStringToString(
                    clang_getCompletionBriefComment( completion_string ) );
    ExtractDataFromString( completion_string );
  }
}

void CompletionData::ExtractDataFromString( CXCompletionString completion_string ) {
  uint num_chunks = clang_getNumCompletionChunks( completion_string );

  for ( uint chunk_number = 0; chunk_number < num_chunks; chunk_number++ ) {
    CXCompletionChunkKind kind = clang_getCompletionChunkKind( completion_string, chunk_number );
    std::string part;

    switch ( kind ) {
      case CXCompletionChunk_Optional: {
        CXCompletionString optional_string = clang_getCompletionChunkCompletionString( completion_string, chunk_number );
        ExtractDataFromString( optional_string );
        break;
      }

      case CXCompletionChunk_TypedText:
      case CXCompletionChunk_Text:
      case CXCompletionChunk_LeftParen:
      case CXCompletionChunk_RightParen:
      case CXCompletionChunk_LeftBracket:
      case CXCompletionChunk_RightBracket:
      case CXCompletionChunk_LeftBrace:
      case CXCompletionChunk_RightBrace:
      case CXCompletionChunk_LeftAngle:
      case CXCompletionChunk_RightAngle:
      case CXCompletionChunk_Comma:
      case CXCompletionChunk_Colon:
      case CXCompletionChunk_SemiColon:
      case CXCompletionChunk_Equal:
      case CXCompletionChunk_HorizontalSpace:
      case CXCompletionChunk_VerticalSpace:
        part = ChunkToString( completion_string, chunk_number );

        if ( kind == CXCompletionChunk_TypedText )
          typed_string_ += part;

        display_string_ += part;

        if ( completion_parts_.size() > 0 && completion_parts_.back().literal_ )
          completion_parts_.back().part_ += part;
        else
          completion_parts_.push_back( boost::move( CompletionPart( part ) ) );

        break;

      case CXCompletionChunk_Placeholder:
      case CXCompletionChunk_CurrentParameter:
        part = ChunkToString( completion_string, chunk_number );
        part = RemoveTwoConsecutiveUnderscores( boost::move( part ) );

        display_string_ += part;
        completion_parts_.push_back( boost::move( CompletionPart( part, false ) ) );

        break;

      case CXCompletionChunk_ResultType:
        result_type_ += ChunkToString( completion_string, chunk_number );
        break;

      case CXCompletionChunk_Informative:
        display_string_ += ChunkToString( completion_string, chunk_number );
        break;
    }
  }
}


} // namespace YouCompleteMe
