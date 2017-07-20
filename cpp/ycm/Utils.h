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

#ifndef UTILS_H_KEPMRPBH
#define UTILS_H_KEPMRPBH

#include "DLLDefines.h"

#include <string>
#include <vector>
#include <boost/filesystem.hpp>

namespace fs = boost::filesystem;

namespace YouCompleteMe {

bool AlmostEqual( double a, double b );

// Reads the entire contents of the specified file. If the file does not exist,
// an exception is thrown.
std::string ReadUtf8File( const fs::path &filepath );

// Writes the entire contents of the specified file. If the file does not exist,
// an exception is thrown.
YCM_DLL_EXPORT void WriteUtf8File( const fs::path &filepath,
                                   const std::string &contents );

template <class Container, class Key>
typename Container::mapped_type &
GetValueElseInsert( Container &container,
                    const Key &key,
                    const typename Container::mapped_type &value ) {
  return container.insert( typename Container::value_type( key, value ) )
         .first->second;
}


template <class Container, class Key>
bool ContainsKey( Container &container, const Key &key ) {
  return container.find( key ) != container.end();
}


template <class Container, class Key>
typename Container::mapped_type
FindWithDefault( Container &container,
                 const Key &key,
                 const typename Container::mapped_type &value ) {
  typename Container::const_iterator it = container.find( key );
  return it != container.end() ? it->second : value;
}


template <class Container, class Key>
bool Erase( Container &container, const Key &key ) {
  typename Container::iterator it = container.find( key );

  if ( it != container.end() ) {
    container.erase( it );
    return true;
  }

  return false;
}


YCM_DLL_EXPORT bool IsAscii( char letter );
YCM_DLL_EXPORT bool IsAlpha( char letter );
YCM_DLL_EXPORT bool IsPrintable( char letter );
YCM_DLL_EXPORT bool IsPrintable( const std::string &text );
YCM_DLL_EXPORT bool IsPunctuation( char letter );
YCM_DLL_EXPORT bool IsLowercase( char letter );
YCM_DLL_EXPORT bool IsLowercase( const std::string &text );
YCM_DLL_EXPORT bool IsUppercase( char letter );
YCM_DLL_EXPORT char Lowercase( char letter );
YCM_DLL_EXPORT char Uppercase( char letter );
YCM_DLL_EXPORT bool HasUppercase( const std::string &text );
YCM_DLL_EXPORT char SwapCase( char letter );
YCM_DLL_EXPORT std::string SwapCase( const std::string &text );

} // namespace YouCompleteMe

#endif /* end of include guard: UTILS_H_KEPMRPBH */
