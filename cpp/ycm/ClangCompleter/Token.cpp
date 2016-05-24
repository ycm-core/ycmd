// Copyright (C) 2016 Davit Samvelyan
//
// This file is part of ycmd.
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
#include "standard.h"

namespace YouCompleteMe {

namespace {

// This is a recursive function.
// Recursive call is made for the reference cursor kind,
// with the referenced cursor as an argument,
// therefore recursion level should not exceed 2.
Token::Type CXCursorToTokenType( const CXCursor& cursor ) {
  CXCursorKind kind = clang_getCursorKind( cursor );
  switch (kind) {
    case CXCursor_IntegerLiteral:
      return Token::INTEGER;

    case CXCursor_FloatingLiteral:
      return Token::FLOATING;

    case CXCursor_ImaginaryLiteral:
      return Token::IMAGINARY;

    case CXCursor_StringLiteral:
      return Token::STRING;

    case CXCursor_CharacterLiteral:
      return Token::CHARACTER;

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

    case CXCursor_PreprocessingDirective:
      return Token::PREPROCESSING_DIRECTIVE;

    case CXCursor_MacroDefinition:
    //case CXCursor_MacroExpansion: // Same as CXCursor_MacroInstantiation
    case CXCursor_MacroInstantiation:
      return Token::MACRO;

    case CXCursor_FunctionDecl:
    case CXCursor_CXXMethod:
    case CXCursor_Constructor:
    case CXCursor_Destructor:
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
        return CXCursorToTokenType( ref );
      }
    }

    default:
      return Token::UNSUPPORTED;
  }
}

} // unnamed namespace

Token::Token()
  : kind( Token::IDENTIFIER )
  , type( Token::UNSUPPORTED )
  , range()
{
}

Token::Token( const CXTokenKind cx_kind, const CXSourceRange& cx_range,
              const CXCursor& cx_cursor )
  : range( cx_range )
{
  MapKindAndType( cx_kind, cx_cursor );
}

bool Token::operator==( const Token& other ) const {
  return kind == other.kind &&
         type == other.type &&
         range == other.range;
}

void Token::MapKindAndType( const CXTokenKind cx_kind, const CXCursor& cx_cursor ) {
  switch ( cx_kind ) {
    case CXToken_Punctuation:
      kind = Token::PUNCTUATION;
      type = Token::NONE;
      break;
    case CXToken_Keyword:
      kind = Token::KEYWORD;
      type = Token::NONE;
      break;
    case CXToken_Identifier:
      kind = Token::IDENTIFIER;
      type = CXCursorToTokenType( cx_cursor );
      break;
    case CXToken_Literal:
      kind = Token::LITERAL;
      type = CXCursorToTokenType( cx_cursor );
      break;
    case CXToken_Comment:
      kind = Token::COMMENT;
      type = Token::NONE;
      break;
  }
}

} // YouCompleteMe
