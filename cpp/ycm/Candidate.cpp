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

#include "Candidate.h"
#include "Result.h"

namespace YouCompleteMe {

void Candidate::ComputeCaseSwappedText() {
  for ( const auto &character : Characters() ) {
    case_swapped_text_.append( character->SwappedCase() );
  }
}


void Candidate::ComputeWordBoundaryChars() {
  const CharacterSequence &characters = Characters();

  auto character_pos = characters.begin();
  if ( character_pos == characters.end() ) {
    return;
  }

  const auto &first_character = *character_pos;
  if ( !first_character->IsPunctuation() ) {
    word_boundary_chars_.push_back( first_character );
  }

  auto previous_character_pos = characters.begin();
  ++character_pos;
  for ( ; character_pos != characters.end(); ++previous_character_pos,
                                             ++character_pos ) {
    const auto &previous_character = *previous_character_pos;
    const auto &character = *character_pos;

    if ( ( !previous_character->IsUppercase() && character->IsUppercase() ) ||
         ( previous_character->IsPunctuation() && character->IsLetter() ) ) {
      word_boundary_chars_.push_back( character );
    }
  }
}


void Candidate::ComputeTextIsLowercase() {
  for ( const auto &character : Characters() ) {
    if ( character->IsUppercase() ) {
      text_is_lowercase_ = false;
      return;
    }
  }

  text_is_lowercase_ = true;
}


Candidate::Candidate( const std::string &text )
  : Word( text ) {
  ComputeCaseSwappedText();
  ComputeWordBoundaryChars();
  ComputeTextIsLowercase();
}


Result Candidate::QueryMatchResult( const Word &query ) const {
  // Check if the query is a subsequence of the candidate and return a result
  // accordingly. This is done by simultaneously going through the characters of
  // the query and the candidate. If both characters match, we move to the next
  // character in the query and the candidate. Otherwise, we only move to the
  // next character in the candidate. The matching is a combination of smart
  // base matching and smart case matching. If there is no character left in the
  // query, the query is not a subsequence and we return an empty result. If
  // there is no character left in the candidate, the query is a subsequence and
  // we return a result with the query, the candidate, the sum of indexes of the
  // candidate where characters matched, and a boolean that is true if the query
  // is a prefix of the candidate.

  if ( query.IsEmpty() ) {
    return Result( this, &query, 0, false );
  }

  if ( Length() < query.Length() ) {
    return Result();
  }

  size_t query_index = 0;
  size_t candidate_index = 0;
  size_t index_sum = 0;

  const CharacterSequence &query_characters = query.Characters();
  const CharacterSequence &candidate_characters = Characters();

  auto query_character_pos = query_characters.begin();
  auto candidate_character_pos = candidate_characters.begin();

  for ( ; candidate_character_pos != candidate_characters.end();
          ++candidate_character_pos, ++candidate_index ) {

    const auto &candidate_character = *candidate_character_pos;
    const auto &query_character = *query_character_pos;

    if ( query_character->MatchesSmart( *candidate_character ) ) {
      index_sum += candidate_index;

      ++query_character_pos;
      if ( query_character_pos == query_characters.end() ) {
        return Result( this,
                       &query,
                       index_sum,
                       candidate_index == query_index );
      }

      ++query_index;
    }
  }

  return Result();
}

} // namespace YouCompleteMe
