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

#ifndef DIAGNOSTIC_H_BZH3BWIZ
#define DIAGNOSTIC_H_BZH3BWIZ

#include "FixIt.h"

#include <pymetabind/utils.hpp>

namespace YouCompleteMe {

enum class [[=pymetabind::utils::make_binding()]] DiagnosticKind {
  INFORMATION = 0,
  ERROR,
  WARNING
};


struct [[=pymetabind::utils::make_binding(), =pymetabind::utils::make_vector()]] Diagnostic {

  [[=pymetabind::utils::readonly()]] Location location_;

  [[=pymetabind::utils::readonly()]] Range location_extent_;

  [[=pymetabind::utils::readonly()]] std::vector< Range > ranges_;

  [[=pymetabind::utils::readonly()]] DiagnosticKind kind_;

  [[=pymetabind::utils::readonly()]] std::string text_;

  [[=pymetabind::utils::readonly()]] std::string long_formatted_text_;

  /// The (cached) changes required to fix this diagnostic.
  /// Note: when there are child diagnostics, there may be multiple possible
  /// FixIts for the main reported diagnostic. These are typically notes,
  /// offering alternative ways to fix the error.
  [[=pymetabind::utils::readonly()]] std::vector< FixIt > fixits_;
};

} // namespace YouCompleteMe

#endif /* end of include guard: DIAGNOSTIC_H_BZH3BWIZ */
