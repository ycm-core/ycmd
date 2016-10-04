// Copyright (C) 2016 Davit Samvelyan
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

#ifndef TOKEN_H_IC9ZDM5T
#define TOKEN_H_IC9ZDM5T

#include "Range.h"

#include <string>

#include <clang-c/Index.h>

namespace YouCompleteMe {

/// Represents single semantic token as a (Kind, Type) enum pair corresponding
/// to the clang's CXTokenKind and CXCursorKind enums.
struct Token {

  enum Kind {
    PUNCTUATION = 0,
    COMMENT,
    KEYWORD,
    LITERAL,
    IDENTIFIER
  };

  // Divided into groups of possible values for each Kind enum value.
  // TODO change to enum class and remove _TYPE suffixes after switch to C++11
  enum Type {
    // Punctuation types
    PUNCTUATION_TYPE = 0,

    // Comment types
    COMMENT_TYPE,

    // Keyword types
    KEYWORD_TYPE,

    // Literal types
    // true/false are keywords
    INTEGER,
    FLOATING,
    IMAGINARY,
    STRING,
    CHARACTER,

    // Identifier types
    NAMESPACE,
    CLASS,
    STRUCT,
    UNION,
    TYPE_ALIAS,
    MEMBER_VARIABLE,
    VARIABLE,
    FUNCTION,
    FUNCTION_PARAMETER,
    ENUMERATION,
    ENUMERATOR,
    TEMPLATE_PARAMETER,
    TEMPLATE_NON_TYPE_PARAMETER,
    PREPROCESSING_DIRECTIVE,
    MACRO,

    // Identifier without mapping to the Type enum.
    UNSUPPORTED
  };

  Token();

  Token( const CXTokenKind kind, const CXSourceRange &tokenRange,
         const CXCursor &cursor );

  bool operator==( const Token &other ) const;

  Kind kind;

  Type type;

  Range range;

private:

  void MapKindAndType( const CXTokenKind kind, const CXCursor &cursor );

};

} // YouCompleteMe

#endif /* end of include guard: TOKEN_H_IC9ZDM5T */
