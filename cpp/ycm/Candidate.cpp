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

#include "standard.h"
#include "Candidate.h"
#include "Result.h"

#include <boost/algorithm/string.hpp>
#include <cctype>
#include <locale>

using boost::algorithm::all;
using boost::algorithm::is_lower;
using boost::algorithm::is_print;

namespace YouCompleteMe {

bool IsPrintable( const std::string &text ) {
  return all( text, is_print( std::locale::classic() ) );
}


std::string GetWordBoundaryChars( const std::string &text ) {
  std::string result;

  for ( uint i = 0; i < text.size(); ++i ) {
    bool is_first_char_but_not_punctuation = i == 0 && !ispunct( text[ i ] );
    bool is_good_uppercase = i > 0 &&
                             IsUppercase( text[ i ] ) &&
                             !IsUppercase( text[ i - 1 ] );
    bool is_alpha_after_punctuation = i > 0 &&
                                      ispunct( text[ i - 1 ] ) &&
                                      isalpha( text[ i ] );

    if ( is_first_char_but_not_punctuation ||
         is_good_uppercase ||
         is_alpha_after_punctuation ) {
      result.push_back( tolower( text[ i ] ) );
    }
  }

  return result;
}


Bitset LetterBitsetFromString( const std::string &text ) {
  Bitset letter_bitset;

  foreach ( char letter, text ) {
    int letter_index = IndexForLetter( letter );

    if ( IsInAsciiRange( letter_index ) )
      letter_bitset.set( letter_index );
  }

  return letter_bitset;
}


Candidate::Candidate( const std::string &text )
  :
  text_( text ),
  word_boundary_chars_( GetWordBoundaryChars( text ) ),
  text_is_lowercase_( all( text, is_lower() ) ),
  letters_present_( LetterBitsetFromString( text ) ),
  root_node_( new LetterNode( text ) ) {
}


Result Candidate::QueryMatchResult( const std::string &query,
                                    bool case_sensitive ) const {
  LetterNode *node = root_node_.get();
  int index_sum = 0;

  foreach ( char letter, query ) {
    const NearestLetterNodeIndices *nearest =
      node->NearestLetterNodesForLetter( letter );

    if ( !nearest )
      return Result( false );

    // When the query letter is uppercase, then we force an uppercase match
    // but when the query letter is lowercase, then it can match both an
    // uppercase and a lowercase letter. This is by design and it's much
    // better than forcing lowercase letter matches.
    node = NULL;
    if ( case_sensitive && IsUppercase( letter ) ) {
      if ( nearest->indexOfFirstUppercaseOccurrence >= 0 )
        node = ( *root_node_ )[ nearest->indexOfFirstUppercaseOccurrence ];
    } else {
      if ( nearest->indexOfFirstOccurrence >= 0 )
        node = ( *root_node_ )[ nearest->indexOfFirstOccurrence ];
    }

    if ( !node )
      return Result( false );

    index_sum += node->Index();
  }

  return Result( true, &text_, text_is_lowercase_, index_sum,
                 word_boundary_chars_, query );
}

} // namespace YouCompleteMe
