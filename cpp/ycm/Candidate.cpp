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

namespace YouCompleteMe {

std::string GetWordBoundaryChars( const std::string &text ) {
  std::string result;

  for ( size_t i = 0; i < text.size(); ++i ) {
    bool is_first_char_but_not_punctuation = i == 0 &&
                                             !IsPunctuation( text[ i ] );
    bool is_good_uppercase = i > 0 &&
                             IsUppercase( text[ i ] ) &&
                             !IsUppercase( text[ i - 1 ] );
    bool is_alpha_after_punctuation = i > 0 &&
                                      IsPunctuation( text[ i - 1 ] ) &&
                                      IsAlpha( text[ i ] );

    if ( is_first_char_but_not_punctuation ||
         is_good_uppercase ||
         is_alpha_after_punctuation ) {
      result.push_back( Lowercase( text[ i ] ) );
    }
  }

  return result;
}


Bitset LetterBitsetFromString( const std::string &text ) {
  Bitset letter_bitset;

  for ( char letter : text ) {
    int letter_index = IndexForLetter( letter );

    if ( IsAscii( letter_index ) )
      letter_bitset.set( letter_index );
  }

  return letter_bitset;
}


Candidate::Candidate( const std::string &text )
  :
  text_( text ),
  case_swapped_text_( SwapCase( text ) ),
  word_boundary_chars_( GetWordBoundaryChars( text ) ),
  text_is_lowercase_( IsLowercase( text ) ),
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
      return Result();

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
      return Result();

    index_sum += node->Index();
  }

  return Result( true, &text_, &case_swapped_text_, text_is_lowercase_,
                 index_sum, word_boundary_chars_, query );
}

} // namespace YouCompleteMe
