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
#include <boost/filesystem/fstream.hpp>

namespace fs = boost::filesystem;

namespace YouCompleteMe {

bool AlmostEqual( double a, double b ) {
  return std::abs( a - b ) <=
         ( std::numeric_limits< double >::epsilon() *
           std::max( std::abs( a ), std::abs( b ) ) );
}


std::string ReadUtf8File( const fs::path &filepath ) {
  // fs::is_empty() can throw basic_filesystem_error< Path >
  // in case filepath doesn't exist, or
  // in case filepath's file_status is "other".
  // "other" in this case means everything that is not a regular file,
  // directory or a symlink.
  if ( !fs::is_empty( filepath ) && fs::is_regular_file( filepath ) ) {
    fs::ifstream file( filepath, std::ios::in | std::ios::binary );
    std::vector< char > contents( ( std::istreambuf_iterator< char >( file ) ),
                                  std::istreambuf_iterator< char >() );
    return std::string( contents.begin(), contents.end() );
  }
  return std::string();
}


void WriteUtf8File( const fs::path &filepath, const std::string &contents ) {
  fs::ofstream file;
  file.open( filepath );
  file << contents;
  file.close();
}


// A character is ASCII if it's in the range 0-127 i.e. its most significant bit
// is 0.
bool IsAscii( char letter ) {
  return !( letter & 0x80 );
}


bool IsAlpha( char letter ) {
  return IsLowercase( letter ) || IsUppercase( letter );
}


bool IsPrintable( char letter ) {
  return ' ' <= letter && letter <= '~';
}


bool IsPrintable( const std::string &text ) {
  for ( char letter : text ) {
    if ( !IsPrintable( letter ) )
      return false;
  }
  return true;
}


bool IsPunctuation( char letter ) {
  return ( '!' <= letter && letter <= '/' ) ||
         ( ':' <= letter && letter <= '@' ) ||
         ( '[' <= letter && letter <= '`' ) ||
         ( '{' <= letter && letter <= '~' );
}


bool IsLowercase( char letter ) {
  return 'a' <= letter && letter <= 'z';
}


// A string is assumed to be in lowercase if none of its characters are
// uppercase.
bool IsLowercase( const std::string &text ) {
  for ( char letter : text ) {
    if ( IsUppercase( letter ) )
      return false;
  }
  return true;
}


bool IsUppercase( char letter ) {
  return 'A' <= letter && letter <= 'Z';
}


// An uppercase character can be converted to lowercase and vice versa by
// flipping its third most significant bit.
char Lowercase( char letter ) {
  if ( IsUppercase( letter ) )
    return letter ^ 0x20;
  return letter;
}


char Uppercase( char letter ) {
  if ( IsLowercase( letter ) )
    return letter ^ 0x20;
  return letter;
}


bool HasUppercase( const std::string &text ) {
  for ( char letter : text ) {
    if ( IsUppercase( letter ) )
      return true;
  }
  return false;
}


char SwapCase( char letter ) {
  if ( IsAlpha( letter ) )
    return letter ^ 0x20;
  return letter;
}


std::string SwapCase( const std::string &text ) {
  std::string result;
  for ( char letter : text )
    result.push_back( SwapCase( letter ) );
  return result;
}

} // namespace YouCompleteMe
