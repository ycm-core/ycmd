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

#include "Candidate.h"
#include "Result.h"

#include <algorithm>
#include <locale>

using std::all_of;

namespace YouCompleteMe {

static bool IsPrint( char c ) {
  return std::isprint( c, std::locale::classic() );
}


static bool IsLower( char c ) {
  return std::islower( c, std::locale::classic() );
}


bool IsPrintable( const std::string &text ) {
  return all_of( text.cbegin(), text.cend(), IsPrint );
}


std::string GetWordBoundaryChars( const std::string &text ) {
  std::string result;

  for ( size_t i = 0; i < text.size(); ++i ) {
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

  for ( char letter : text ) {
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
  text_is_lowercase_( all_of( text.cbegin(), text.cend(), IsLower ) ),
  letters_present_( LetterBitsetFromString( text ) ),
  root_node_( new LetterNode( text ) ) {
}


Result Candidate::QueryMatchResult( const std::string &query,
                                    bool case_sensitive ) const {
  LetterNode *node = root_node_.get();
  int index_sum = 0;

  for ( char letter : query ) {
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
