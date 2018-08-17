// Copyright (C) 2018 ycmd contributors
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

#ifndef FIXIT_H_LHWQA2O9
#define FIXIT_H_LHWQA2O9

#include "Location.h"
#include "Range.h"

#include <string>
#include <vector>

namespace YouCompleteMe {

/// Information about a replacement that can be made to the source to "fix" a
/// diagnostic.
struct FixItChunk {
  /// The replacement string. This string should replace the source range
  /// represented by 'range'.
  std::string replacement_text;

  /// The range within the file to replace with replacement_text.
  Range range;

};


/// Collection of FixItChunks which, when applied together, fix a particular
/// diagnostic. This structure forms the reply to the "FixIt" subcommand, and
/// represents a lightweight view of a diagnostic. The location is included to
/// aid clients in applying the most appropriate FixIt based on context.
struct FixIt {
  std::vector< FixItChunk > chunks;

  Location location;

  /// This is the text of the diagnostic. This is useful when there are
  /// multiple diagnostics offering different fixit options. The text is
  /// displayed to the user, allowing them choose which diagnostic to apply.
  std::string text;
};

} // namespace YouCompleteMe

#endif /* end of include guard: FIXIT_H_LHWQA2O9 */
