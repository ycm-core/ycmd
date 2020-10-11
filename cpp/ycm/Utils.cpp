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

#include "Utils.h"

#include <cmath>
#include <filesystem>
#include <fstream>
#include <limits>
#include <string>
#include <vector>

namespace fs = std::filesystem;

namespace YouCompleteMe {

std::vector< std::string > ReadUtf8File( const fs::path &filepath ) {
  std::vector< std::string > contents;
  if ( !fs::is_empty( filepath ) && fs::is_regular_file( filepath ) ) {
    std::string line;
    for( std::ifstream file( filepath.string(),
                             std::ios::in | std::ios::binary );
         std::getline( file, line ); ) {
      contents.push_back( std::move( line ) );
    }
  }
  return contents;
}

} // namespace YouCompleteMe
