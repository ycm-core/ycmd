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

#include <cmath>
#include <limits>
#include <string>
#include <vector>
#include <boost/filesystem.hpp>

namespace fs = boost::filesystem;

namespace YouCompleteMe {

inline bool AlmostEqual( double a, double b ) {
  return std::abs( a - b ) <=
         ( std::numeric_limits< double >::epsilon() *
           std::max( std::abs( a ), std::abs( b ) ) );
}


YCM_DLL_EXPORT inline bool IsLowercase( char letter ) {
  return 'a' <= letter && letter <= 'z';
}


YCM_DLL_EXPORT inline bool IsUppercase( char letter ) {
  return 'A' <= letter && letter <= 'Z';
}


// A character is ASCII if it's in the range 0-127 i.e. its most significant bit
// is 0.
YCM_DLL_EXPORT inline bool IsAscii( char letter ) {
  return !( letter & 0x80 );
}


YCM_DLL_EXPORT inline bool IsAlpha( char letter ) {
  return IsLowercase( letter ) || IsUppercase( letter );
}


YCM_DLL_EXPORT inline bool IsPrintable( char letter ) {
  return ' ' <= letter && letter <= '~';
}


YCM_DLL_EXPORT inline bool IsPrintable( const std::string &text ) {
  for ( char letter : text ) {
    if ( !IsPrintable( letter ) )
      return false;
  }
  return true;
}


YCM_DLL_EXPORT inline bool IsPunctuation( char letter ) {
  return ( '!' <= letter && letter <= '/' ) ||
         ( ':' <= letter && letter <= '@' ) ||
         ( '[' <= letter && letter <= '`' ) ||
         ( '{' <= letter && letter <= '~' );
}


// A string is assumed to be in lowercase if none of its characters are
// uppercase.
YCM_DLL_EXPORT inline bool IsLowercase( const std::string &text ) {
  for ( char letter : text ) {
    if ( IsUppercase( letter ) )
      return false;
  }
  return true;
}


// An uppercase character can be converted to lowercase and vice versa by
// flipping its third most significant bit.
YCM_DLL_EXPORT inline char Lowercase( char letter ) {
  if ( IsUppercase( letter ) )
    return letter ^ 0x20;
  return letter;
}


YCM_DLL_EXPORT inline std::string Lowercase( const std::string &text ) {
  std::string result;
  for ( char letter : text )
    result.push_back( Lowercase( letter ) );
  return result;
}


YCM_DLL_EXPORT inline char Uppercase( char letter ) {
  if ( IsLowercase( letter ) )
    return letter ^ 0x20;
  return letter;
}


YCM_DLL_EXPORT inline bool HasUppercase( const std::string &text ) {
  for ( char letter : text ) {
    if ( IsUppercase( letter ) )
      return true;
  }
  return false;
}


YCM_DLL_EXPORT inline char SwapCase( char letter ) {
  if ( IsAlpha( letter ) )
    return letter ^ 0x20;
  return letter;
}


YCM_DLL_EXPORT inline std::string SwapCase( const std::string &text ) {
  std::string result;
  for ( char letter : text )
    result.push_back( SwapCase( letter ) );
  return result;
}

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


// Shrink a vector to its sorted |num_sorted_elements| smallest elements. If
// |num_sorted_elements| is 0 or larger than the vector size, sort the whole
// vector.
template <typename Element>
void PartialSort( std::vector< Element > &elements,
                  const size_t num_sorted_elements ) {

  size_t nb_elements = elements.size();
  size_t max_elements = num_sorted_elements > 0 &&
                        nb_elements >= num_sorted_elements ?
                        num_sorted_elements : nb_elements;

  // When the number of elements to sort is more than 1024 and one sixty-fourth
  // of the total number of elements, switch to std::nth_element followed by
  // std::sort. This heuristic is based on the observation that
  // std::partial_sort (heapsort) is the most efficient algorithm when the
  // number of elements to sort is small and that std::nth_element (introselect)
  // combined with std::sort (introsort) always perform better than std::sort
  // alone in other cases.
  if ( max_elements <= std::max( static_cast< size_t >( 1024 ),
                                 nb_elements / 64 ) ) {
    std::partial_sort( elements.begin(),
                       elements.begin() + max_elements,
                       elements.end() );
  } else {
    std::nth_element( elements.begin(),
                      elements.begin() + max_elements,
                      elements.end() );
    std::sort( elements.begin(), elements.begin() + max_elements );
  }

  // Remove the unsorted elements. Use erase instead of resize as it doesn't
  // require a default constructor on Element.
  elements.erase( elements.begin() + max_elements, elements.end() );
}

} // namespace YouCompleteMe

#endif /* end of include guard: UTILS_H_KEPMRPBH */
