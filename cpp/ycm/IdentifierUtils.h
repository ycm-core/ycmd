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

#ifndef IDENTIFIERUTILS_CPP_WFFUZNET
#define IDENTIFIERUTILS_CPP_WFFUZNET

#include "DLLDefines.h"
#include "IdentifierDatabase.h"

#include <vector>
#include <string>

#include <boost/filesystem.hpp>

namespace YouCompleteMe {

YCM_DLL_EXPORT FiletypeIdentifierMap ExtractIdentifiersFromTagsFile(
  const boost::filesystem::path &path_to_tag_file );

} // namespace YouCompleteMe

#endif /* end of include guard: IDENTIFIERUTILS_CPP_WFFUZNET */
