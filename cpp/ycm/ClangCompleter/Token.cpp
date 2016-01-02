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

#include "Token.h"

#include "Range.h"

namespace YouCompleteMe {

namespace {

Token::Kind CXCursorToTokenKind( const CXCursor& cursor ) {
  CXCursorKind kind = clang_getCursorKind( cursor );
  switch (kind) {
    case CXCursor_Namespace:
    case CXCursor_NamespaceAlias:
    case CXCursor_NamespaceRef:
      return Token::NAMESPACE;

    case CXCursor_ClassDecl:
    case CXCursor_ClassTemplate:
      return Token::CLASS;

    case CXCursor_StructDecl:
      return Token::STRUCT;

    case CXCursor_UnionDecl:
      return Token::UNION;

    case CXCursor_FieldDecl:
      return Token::MEMBER_VARIABLE;

    case CXCursor_TypedefDecl: // typedef
    case CXCursor_TypeAliasDecl: // using
      return Token::TYPEDEF;

    case CXCursor_TemplateTypeParameter:
      return Token::TEMPLATE_TYPE;

    case CXCursor_EnumDecl:
      return Token::ENUM;

    case CXCursor_EnumConstantDecl:
      return Token::ENUM_CONSTANT;

    //case CXCursor_MacroDefinition: // Can be recognized by regexp.
    //case CXCursor_MacroExpansion: // Same as CXCursor_MacroInstantiation
    case CXCursor_MacroInstantiation:
      return Token::MACRO;

    case CXCursor_FunctionDecl:
    case CXCursor_CXXMethod:
      return Token::FUNCTION;

    case CXCursor_ParmDecl:
      return Token::FUNCTION_PARAM;

    // When we have a type reference we need to do one more step
    // to find out what it is referencing.
    case CXCursor_TypeRef:
    case CXCursor_TemplateRef:
    case CXCursor_DeclRefExpr:
    case CXCursor_MemberRefExpr:
    case CXCursor_MemberRef:
    case CXCursor_VariableRef:
    {
      CXCursor ref = clang_getCursorReferenced( cursor );
      if ( clang_Cursor_isNull( ref ) ) {
        return Token::UNSUPPORTED;
      } else {
        return CXCursorToTokenKind( ref );
      }
    }

    default:
      return Token::UNSUPPORTED;
  }
}

} // unnamed namespace

Token::Token()
  : kind_( UNSUPPORTED ) {
}

Token::Token( const CXSourceRange& tokenRange, const CXCursor& cursor ) {

  kind_ = CXCursorToTokenKind( cursor );
  if ( kind_ == UNSUPPORTED ) {
    return;
  }

  CXFile unused_file;
  uint unused_offset;
  clang_getExpansionLocation( clang_getRangeStart( tokenRange ),
                              &unused_file,
                              &line_number_,
                              &column_number_,
                              &unused_offset );

  uint end_line;
  uint end_column;
  clang_getExpansionLocation( clang_getRangeEnd( tokenRange ),
                              &unused_file,
                              &end_line,
                              &end_column,
                              &unused_offset );

  // There shouldn't exist any multiline Token, except for multiline strings,
  // which is a job for syntax highlighter, but better be safe then sorry.
  if ( line_number_ != end_line ) {
    kind_ = UNSUPPORTED;
    return;
  }
  offset_ = end_column - column_number_;
}

bool Token::operator== ( const Token& other ) const {
  return kind_ == other.kind_ &&
         line_number_ == other.line_number_ &&
         column_number_ == other.column_number_ &&
         offset_ == other.offset_;
}

} // YouCompleteMe
