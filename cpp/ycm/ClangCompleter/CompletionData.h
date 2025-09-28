// Copyright (C) 2011-2018 ycmd contributors
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

#include "FixIt.h"

#include <pymetabind/utils.hpp>

namespace YouCompleteMe {

enum class [[=pymetabind::utils::make_binding()]] CompletionKind {
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
struct [[=pymetabind::utils::make_binding(), =pymetabind::utils::make_vector()]] CompletionData {
  CompletionData() = default;
  [[=pymetabind::utils::skip_member()]] CompletionData( CXCompletionString completion_string,
                  CXCursorKind kind,
                  CXCodeCompleteResults *results,
                  size_t index );

  // What should actually be inserted into the buffer. For a function like
  // "int foo(int x)", this is just "foo". Same for a data member like "foo_":
  // we insert just "foo_".
  std::string TextToInsertInBuffer() const {
    return original_string_;
  }

  // Currently, here we show the full function signature (without the return
  // type) if the current completion is a function or just the raw TypedText if
  // the completion is, say, a data member. So for a function like "int foo(int
  // x)", this would be "foo(int x)". For a data member like "count_", it would
  // be just "count_".
  std::string MainCompletionText() const {
    return everything_except_return_type_;
  }

  // This is extra info shown in the pop-up completion menu, after the
  // completion text and the kind. Currently we put the return type of the
  // function here, if any.
  std::string ExtraMenuInfo() const {
    return return_type_;
  }

  // This is used to show extra information in vim's preview window. This is the
  // window that vim usually shows at the top of the buffer. This should be used
  // for extra information about the completion.
  std::string DetailedInfoForPreviewWindow() const {
    return detailed_info_;
  }

  std::string DocString() const {
    return doc_string_;
  }

  [[=pymetabind::utils::skip_member()]] std::string detailed_info_;

  [[=pymetabind::utils::skip_member()]] std::string return_type_;

  [[=pymetabind::utils::readonly()]] CompletionKind kind_;

  // The original, raw completion string. For a function like "int foo(int x)",
  // the original string is "foo". For a member data variable like "foo_", this
  // is just "foo_". This corresponds to clang's TypedText chunk of the
  // completion string.
  [[=pymetabind::utils::skip_member()]] std::string original_string_;

  [[=pymetabind::utils::skip_member()]] std::string everything_except_return_type_;

  [[=pymetabind::utils::skip_member()]] std::string doc_string_;

  [[=pymetabind::utils::readonly()]] FixIt fixit_;

private:

  void ExtractDataFromChunk( CXCompletionString completion_string,
                             size_t chunk_num,
                             bool &saw_left_paren,
                             bool &saw_function_params,
                             bool &saw_placeholder );

  void BuildCompletionFixIt( CXCodeCompleteResults *results, size_t index );
};

} // namespace YouCompleteMe


#endif /* end of include guard: COMPLETIONDATA_H_2JCTF1NU */
