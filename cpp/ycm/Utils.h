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

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <limits>
#include <string>
#include <string_view>
#include <type_traits>
#include <vector>

namespace fs = std::filesystem;

namespace YouCompleteMe {

YCM_EXPORT inline bool IsUppercase( uint8_t ascii_character ) {
  return 'A' <= ascii_character && ascii_character <= 'Z';
}


// An uppercase ASCII character can be converted to lowercase and vice versa by
// flipping its third most significant bit.
YCM_EXPORT inline char Lowercase( uint8_t ascii_character ) {
  if ( IsUppercase( ascii_character ) ) {
    return static_cast< char >( ascii_character ^ 0x20 );
  }
  return static_cast< char >( ascii_character );
}


YCM_EXPORT inline std::string Lowercase( std::string_view text ) {
  std::string result( text.size(), '\0' );
  std::transform( text.begin(),
                  text.end(),
                  result.begin(),
                  []( char c ) {
                    return Lowercase( static_cast< uint8_t >( c ) );
                  } );
  return result;
}


// Reads the entire contents of the specified file. If the file does not exist,
// an exception is thrown.
std::vector< std::string > ReadUtf8File( const fs::path &filepath );


template <class Container, class Key, typename Value>
typename Container::mapped_type &
GetValueElseInsert( Container &container,
                    Key&& key,
                    Value&& value ) {
  return container.try_emplace(
    std::forward< Key >( key ), std::forward< Value >( value ) ).first->second;
}


template<typename C, typename = void>
struct is_associative : std::false_type {};

template<typename C>
struct is_associative<C, std::void_t<typename C::mapped_type>> : std::true_type {};

template <class Container, class Key, class Ret>
Ret
FindWithDefault( Container &container,
                 const Key &key,
                 Ret&& value ) {
  typename Container::const_iterator it = [ &key ]( auto&& c ) {
    if constexpr ( is_associative<Container>::value ) {
      return c.find( key );
    } else {
      return std::find_if( c.begin(), c.end(), [ &key ]( auto&& p ) {
          return p.first == key; } );
    }
  }( container );
  if ( it != container.end() ) {
    return Ret{ it->second };
  }
  return std::move( value );
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

  using diff = typename std::vector< Element >::iterator::difference_type;
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
                       elements.begin() + static_cast< diff >( max_elements ),
                       elements.end() );
  } else {
    std::nth_element( elements.begin(),
                      elements.begin() + static_cast< diff >( max_elements ),
                      elements.end() );
    std::sort( elements.begin(), elements.begin() + static_cast< diff >( max_elements ) );
  }

  // Remove the unsorted elements. Use erase instead of resize as it doesn't
  // require a default constructor on Element.
  elements.erase( elements.begin() + static_cast< diff >( max_elements ),
                  elements.end() );
}

} // namespace YouCompleteMe

#endif /* end of include guard: UTILS_H_KEPMRPBH */
