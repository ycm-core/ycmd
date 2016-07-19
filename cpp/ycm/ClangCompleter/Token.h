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

#ifndef SYNTAX_H_IC9ZDM5T
#define SYNTAX_H_IC9ZDM5T

#include "Range.h"

#include <string>

#include <clang-c/Index.h>

namespace YouCompleteMe {

/// Represents single semantic token as a (Kind, Type) enum pair corresponding
/// to the clang's CXTokenKind and CXCursorKind enums.
struct Token {

  enum Kind {
    PUNCTUATION = 0,
    KEYWORD,
    IDENTIFIER,
    LITERAL,
    COMMENT
  };

  // Divided into groups of possible values for each Kind enum value.
  enum Type {
    // Punctutation and Comment
    NONE = 0,

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
    MEMBER_VARIABLE,
    TYPEDEF,
    TEMPLATE_TYPE,
    ENUM,
    ENUM_CONSTANT,
    PREPROCESSING_DIRECTIVE,
    MACRO,
    FUNCTION,
    FUNCTION_PARAM,

    // Identifier without mapping to the Type enum.
    UNSUPPORTED
  };

  Token();

  Token( const CXTokenKind kind, const CXSourceRange& tokenRange,
         const CXCursor& cursor );

  bool operator==( const Token& other ) const;

  Kind kind;

  Type type;

  Range range;

private:

  void MapKindAndType( const CXTokenKind kind, const CXCursor& cursor );

};

} // YouCompleteMe

#endif /* end of include guard: SYNTAX_H_IC9ZDM5T */
