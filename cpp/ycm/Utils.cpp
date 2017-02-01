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
#include <limits>
#include <boost/filesystem.hpp>

namespace fs = boost::filesystem;

namespace YouCompleteMe {

bool AlmostEqual( double a, double b ) {
  return std::abs( a - b ) <=
         ( std::numeric_limits< double >::epsilon() *
           std::max( std::abs( a ), std::abs( b ) ) );
}


std::vector< std::string > ReadUtf8File( const fs::path &filepath ) {
  std::ifstream file;
  file.open(filepath.string());
  std::vector<std::string> lines;
  std::string temp_line;
  while (std::getline(file,temp_line))
    lines.push_back(temp_line);
  file.close();
  return lines;
}


void WriteUtf8File( const fs::path &filepath, const std::string &contents ) {
  fs::ofstream file;
  file.open( filepath );
  file << contents;
  file.close();
}

} // namespace YouCompleteMe
