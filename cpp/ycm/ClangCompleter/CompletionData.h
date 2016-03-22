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

#ifndef COMPLETIONDATA_H_2JCTF1NU
#define COMPLETIONDATA_H_2JCTF1NU

#include "standard.h"
#include <string>
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

// This class holds pieces of information about a single completion coming from
// clang. These pieces are shown in Vim's UI in different ways.
//
// Normally, the completion menu looks like this (without square brackets):
//
//   [main completion text]  [kind]  [extra menu info]
//   [main completion text]  [kind]  [extra menu info]
//   [main completion text]  [kind]  [extra menu info]
//    ... (etc.) ...
//
// The user can also enable a "preview" window that will show extra information
// about a completion at the top of the buffer.
struct CompletionData {
  CompletionData() {}
  CompletionData( const CXCompletionResult &completion_result );

  // Text that users would be expected to type to get this completion result.
  // It is used for filtering, sorting and grouping.
  std::string TypedString() const {
    return typed_string_;
  }

  // What should actually be inserted into the buffer. For a function like
  // "int foo(int x)", this is just "foo". Same for a data member like "foo_":
  // we insert just "foo_".
  std::string TextToInsertInBuffer() const {
    return original_string_;
  }

  // Text that is displayed for users.
  // Currently, here we show the full function signature (without the return
  // type) if the current completion is a function or just the raw TypedText if
  // the completion is, say, a data member. So for a function like "int foo(int
  // x)", this would be "foo(int x)". For a data member like "count_", it would
  // be just "count_".
  std::string DisplayString() const {
    return display_string_;
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
      typed_string_ == other.typed_string_ &&
      kind_ == other.kind_ &&
      display_string_ == other.display_string_ &&
      result_type_ == other.result_type_ &&
      original_string_ == other.original_string_;
      // doc_string_ doesn't matter
  }

  std::string typed_string_;

  std::string result_type_;

  CompletionKind kind_;

  // The original, raw completion string. For a function like "int foo(int x)",
  // the original string is "foo". For a member data variable like "foo_", this
  // is just "foo_". This corresponds to clang's TypedText chunk of the
  // completion string.
  std::string original_string_;

  std::string display_string_;

  std::string doc_string_;

private:

  void ExtractDataFromChunk( CXCompletionString completion_string,
                             uint chunk_num,
                             bool &saw_left_paren,
                             bool &saw_function_params,
                             bool &saw_placeholder );
};

} // namespace YouCompleteMe


#endif /* end of include guard: COMPLETIONDATA_H_2JCTF1NU */
