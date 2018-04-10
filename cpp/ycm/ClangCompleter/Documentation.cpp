// Copyright (C) 2015-2018 ycmd contributors
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

#include "Documentation.h"
#include "ClangHelpers.h"

#include <clang-c/Documentation.h>

namespace YouCompleteMe {

namespace {

bool CXCommentValid( const CXComment &comment ) {
  return clang_Comment_getKind( comment ) != CXComment_Null;
}

} // unnamed namespace

DocumentationData::DocumentationData( const CXCursor &cursor )
  : raw_comment( CXStringToString(
      clang_Cursor_getRawCommentText( cursor ) ) ),
    brief_comment( CXStringToString(
      clang_Cursor_getBriefCommentText( cursor ) ) ),
    canonical_type( CXStringToString(
      clang_getTypeSpelling( clang_getCursorType( cursor ) ) ) ),
    display_name( CXStringToString( clang_getCursorSpelling( cursor ) ) ) {

  CXComment parsed_comment = clang_Cursor_getParsedComment( cursor );

  if ( CXCommentValid( parsed_comment ) ) {
    comment_xml = CXStringToString(
                    clang_FullComment_getAsXML( parsed_comment ) );
  }
}

} // namespace YouCompleteMe
