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

#ifndef COMPLETIONDATA_H_2JCTF1NU
#define COMPLETIONDATA_H_2JCTF1NU

#include "standard.h"
#include <string>
#include <vector>
#include <clang-c/Index.h>

namespace YouCompleteMe {

enum CompletionKind {
  STRUCT = 0,
  CLASS,
  ENUM,
  TYPE,
  MEMBER,
  FUNCTION,
  VARIABLE,
  MACRO,
  PARAMETER,
  NAMESPACE,
  UNKNOWN
};

struct CompletionPart {
  CompletionPart() {}
  CompletionPart( const std::string &part, bool literal = true ): part_( part ), literal_( literal ) {}

  std::string Part() const {
    return part_;
  }

  bool operator== ( const CompletionPart &other ) const {
    return
      part_ == other.part_ &&
      literal_ == other.literal_;
  }

  std::string part_;

  bool literal_;

};

// This class holds pieces of information about a single completion coming from
// clang. These pieces are shown in clients' UI in different ways.
struct CompletionData {
  CompletionData() {}
  CompletionData( const CXCompletionResult &completion_result );

  std::string TypedString() const {
    return typed_string_;
  }

  // Currently, here we show the full function signature (without the return
  // type) if the current completion is a function or just the raw TypedText if
  // the completion is, say, a data member. So for a function like "int foo(int
  // x)", this would be "foo(int x)". For a data member like "count_", it would
  // be just "count_".
  std::string DisplayString() const {
    return display_string_;
  }

  // What should actually be inserted into the buffer. For a function like
  // "int foo(int x)", the CompletionPart for "for(" and ")" are literal and
  // that for "int x" is not literal. Clients should insert literal parts as
  // normal strings and non-literal parts as placeholders.
  std::vector<CompletionPart> CompletionParts() const {
    return completion_parts_;
  }

  // This is the type the completion expression would have.
  std::string ResultType() const {
    return result_type_;
  }

  std::string DocString() const {
    return doc_string_;
  }

  bool operator== ( const CompletionData &other ) const {
    return
      kind_ == other.kind_ &&
      typed_string_ == other.typed_string_ &&
      result_type_ == other.result_type_ &&
      display_string_ == other.display_string_;
  }

  CompletionKind kind_;

  std::string typed_string_;

  std::string display_string_;

  std::vector<CompletionPart> completion_parts_;

  std::string result_type_;

  std::string doc_string_;

private:

  void ExtractDataFromString( CXCompletionString completion_string );

};

} // namespace YouCompleteMe


#endif /* end of include guard: COMPLETIONDATA_H_2JCTF1NU */
