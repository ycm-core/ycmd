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

#ifndef SYNTAX_H_IC9ZDM5T
#define SYNTAX_H_IC9ZDM5T

#include "standard.h"

#include <string>

#include <clang-c/Index.h>

namespace YouCompleteMe {

struct Token {

  enum Kind {
    NAMESPACE = 0,
    CLASS,
    STRUCT,
    UNION,
    MEMBER_VARIABLE,
    TYPEDEF,
    TEMPLATE_TYPE,
    ENUM,
    ENUM_CONSTANT,
    MACRO,
    FUNCTION,
    FUNCTION_PARAM,
    UNSUPPORTED
  };

  Token();

  Token( const CXSourceRange& tokenRange, const CXCursor& cursor );

  bool operator== ( const Token& other ) const;

  Kind kind_;

  uint line_number_;

  uint column_number_;

  uint offset_;

};

} // YouCompleteMe

#endif /* end of include guard: SYNTAX_H_IC9ZDM5T */
