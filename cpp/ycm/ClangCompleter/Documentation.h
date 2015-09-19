// Copyright (C) 2015 YouCompleteMe Contributors
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

#ifndef DOCUMENTATION_H_POYSHVX8
#define DOCUMENTATION_H_POYSHVX8

#include <clang-c/Index.h>
#include <string>


namespace YouCompleteMe {

/// This class holds information useful for generating a documentation response
/// for a given cursor
struct DocumentationData {
  /// Construct an empty object
  DocumentationData() {}

  /// Construct and extract information from the supplied cursor. The cursor
  /// should be pointing to a canonical declaration, such as returned by
  /// clang_getCanonicalCursor( clang_getCursorReferenced( cursor ) )
  DocumentationData( const CXCursor &cursor );

  /// XML data as parsed by libclang. This provides full semantic parsing of
  /// doxygen-syntax comments.
  std::string comment_xml;

  /// The raw text of the comment preceding the declaration
  std::string raw_comment;
  /// The brief comment (either first paragraph or \brief) as parsed by libclang
  std::string brief_comment;
  /// The canonical type of the referenced cursor
  std::string canonical_type;
  /// The display name of the referenced cursor
  std::string display_name;
};

} // namespace YouCompleteMe

#endif /* end of include guard: DOCUMENTATION_H_POYSHVX8 */
