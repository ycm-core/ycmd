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

#ifndef UTILS_H_KEPMRPBH
#define UTILS_H_KEPMRPBH

#include <boost/filesystem.hpp>
#include <cmath>
#include <limits>
#include <string>
#include <vector>

namespace fs = boost::filesystem;

namespace YouCompleteMe {

YCM_EXPORT inline bool IsUppercase( uint8_t ascii_character ) {
  return 'A' <= ascii_character && ascii_character <= 'Z';
}


// An uppercase ASCII character can be converted to lowercase and vice versa by
// flipping its third most significant bit.
YCM_EXPORT inline uint8_t Lowercase( uint8_t ascii_character ) {
  if ( IsUppercase( ascii_character ) ) {
    return ascii_character ^ 0x20;
  }
  return ascii_character;
}


YCM_EXPORT inline std::string Lowercase( const std::string &text ) {
  std::string result;
  for ( uint8_t ascii_character : text ) {
    result.push_back( Lowercase( ascii_character ) );
  }
  return result;
}


// Reads the entire contents of the specified file. If the file does not exist,
// an exception is thrown.
std::string ReadUtf8File( const fs::path &filepath );


// Normalizes a path by making it absolute relative to |base|, resolving
// symbolic links, removing '.' and '..' in the path, and converting slashes
// into backslashes on Windows. Contrarily to boost::filesystem::canonical, this
// works even if the file doesn't exist.
YCM_EXPORT fs::path NormalizePath( const fs::path &filepath,
                                   const fs::path &base = fs::current_path() );


template <class Container, class Key>
typename Container::mapped_type &
GetValueElseInsert( Container &container,
                    const Key &key,
                    typename Container::mapped_type &&value ) {
  return container.insert(
    typename Container::value_type( key, std::move( value ) ) ).first->second;
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
