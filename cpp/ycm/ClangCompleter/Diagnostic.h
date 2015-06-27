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

#ifndef DIAGNOSTIC_H_BZH3BWIZ
#define DIAGNOSTIC_H_BZH3BWIZ

#include "standard.h"
#include "Range.h"
#include "Location.h"

#include <string>
#include <vector>

namespace YouCompleteMe {

enum DiagnosticKind {
  INFORMATION = 0,
  ERROR,
  WARNING
};

/// Information about a replacement that can be made to the source to "fix" a
/// diagnostic.
struct FixItChunk {
  /// The replacement string. This string should replace the source range
  /// represented by 'range'.
  std::string replacement_text;

  /// The range within the file to replace with replacement_text.
  Range range;

  bool operator == ( const FixItChunk &other ) const {
    return replacement_text == other.replacement_text &&
           range == other.range;
  }
};

/// Collection of FixItChunks which, when applied together, fix a particular
/// diagnostic. This structure forms the reply to the "FixIt" subcommand, and
/// represents a lightweight view of a diagnostic. The location is included to
/// aid clients in applying the most appropriate FixIt based on context.
struct FixIt {
  std::vector< FixItChunk > chunks;

  Location location;

  bool operator==( const FixIt &other ) const {
    return chunks == other.chunks &&
           location == other.location;
  }
};

struct Diagnostic {
  bool operator== ( const Diagnostic &other ) const {
    return
      location_ == other.location_ &&
      kind_ == other.kind_ &&
      text_ == other.text_;
  }

  Location location_;

  Range location_extent_;

  std::vector< Range > ranges_;

  DiagnosticKind kind_;

  std::string text_;

  std::string long_formatted_text_;

  /// The (cached) changes required to fix this diagnostic
  std::vector< FixItChunk > fixits_;
};

} // namespace YouCompleteMe

#endif /* end of include guard: DIAGNOSTIC_H_BZH3BWIZ */
