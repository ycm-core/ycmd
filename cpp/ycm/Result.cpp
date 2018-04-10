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

#include "Result.h"
#include "Utils.h"

namespace YouCompleteMe {

namespace {

size_t LongestCommonSubsequenceLength( const CharacterSequence &first,
                                       const CharacterSequence &second ) {
  const auto &longer  = first.size() > second.size() ? first  : second;
  const auto &shorter = first.size() > second.size() ? second : first;

  size_t longer_len  = longer.size();
  size_t shorter_len = shorter.size();

  std::vector< size_t > previous( shorter_len + 1, 0 );
  std::vector< size_t > current(  shorter_len + 1, 0 );

  for ( size_t i = 0; i < longer_len; ++i ) {
    for ( size_t j = 0; j < shorter_len; ++j ) {
      if ( longer[ i ]->EqualsBase( *shorter[ j ] ) ) {
        current[ j + 1 ] = previous[ j ] + 1;
      } else {
        current[ j + 1 ] = std::max( current[ j ], previous[ j + 1 ] );
      }
    }

    for ( size_t j = 0; j < shorter_len; ++j ) {
      previous[ j + 1 ] = current[ j + 1 ];
    }
  }

  return current[ shorter_len ];
}


} // unnamed namespace

Result::Result()
  : is_subsequence_( false ),
    first_char_same_in_query_and_text_( false ),
    query_is_candidate_prefix_( false ),
    char_match_index_sum_( 0 ),
    num_wb_matches_( 0 ),
    candidate_( nullptr ),
    query_( nullptr ) {
}


Result::Result( const Candidate *candidate,
                const Word *query,
                size_t char_match_index_sum,
                bool query_is_candidate_prefix )
  : is_subsequence_( true ),
    first_char_same_in_query_and_text_( false ),
    query_is_candidate_prefix_( query_is_candidate_prefix ),
    char_match_index_sum_( char_match_index_sum ),
    num_wb_matches_( 0 ),
    candidate_( candidate ),
    query_( query ) {
  SetResultFeaturesFromQuery();
}


bool Result::operator< ( const Result &other ) const {
  // Yes, this is ugly but it also needs to be fast.  Since this is called a
  // bazillion times, we have to make sure only the required comparisons are
  // made, and no more.

  if ( !query_->IsEmpty() ) {
    // This is the core of the ranking system. A result has more weight than
    // another if one of these conditions is satisfied, in that order:
    //  - it starts with the same character as the query while the other does
    //    not;
    //  - one of the results has all its word boundary characters matched and
    //    it has more word boundary characters matched than the other;
    //  - both results have all their word boundary characters matched and it
    //    has less word boundary characters than the other;
    //  - the query is a prefix of the result but not a prefix of the other;
    //  - it has more word boundary characters matched than the other;
    //  - it has less word boundary characters than the other;
    //  - its sum of indexes of its matched characters is less than the sum of
    //    indexes of the other result;
    //  - it has less characters than the other result;
    //  - all its characters are in lowercase while the other has at least one
    //    uppercase character;
    //  - it appears before the other result in lexicographic order.

    if ( first_char_same_in_query_and_text_ !=
         other.first_char_same_in_query_and_text_ ) {
      return first_char_same_in_query_and_text_;
    }

    if ( num_wb_matches_ == query_->Length() ||
         other.num_wb_matches_ == query_->Length() ) {
      if ( num_wb_matches_ != other.num_wb_matches_ ) {
        return num_wb_matches_ > other.num_wb_matches_;
      }

      if ( NumWordBoundaryChars() != other.NumWordBoundaryChars() ) {
        return NumWordBoundaryChars() < other.NumWordBoundaryChars();
      }
    }

    if ( query_is_candidate_prefix_ != other.query_is_candidate_prefix_ ) {
      return query_is_candidate_prefix_;
    }

    if ( num_wb_matches_ != other.num_wb_matches_ ) {
      return num_wb_matches_ > other.num_wb_matches_;
    }

    if ( NumWordBoundaryChars() != other.NumWordBoundaryChars() ) {
      return NumWordBoundaryChars() < other.NumWordBoundaryChars();
    }

    if ( char_match_index_sum_ != other.char_match_index_sum_ ) {
      return char_match_index_sum_ < other.char_match_index_sum_;
    }

    if ( candidate_->Length() != other.candidate_->Length() ) {
      return candidate_->Length() < other.candidate_->Length();
    }

    if ( candidate_->TextIsLowercase() !=
         other.candidate_->TextIsLowercase() ) {
      return candidate_->TextIsLowercase();
    }
  }

  // Lexicographic comparison, but we prioritize lowercase letters over
  // uppercase ones. So "foo" < "Foo".
  return candidate_->CaseSwappedText() < other.candidate_->CaseSwappedText();
}


void Result::SetResultFeaturesFromQuery() {
  if ( query_->IsEmpty() || candidate_->IsEmpty() ) {
    return;
  }

  first_char_same_in_query_and_text_ =
    candidate_->Characters()[ 0 ]->EqualsBase( *query_->Characters()[ 0 ] );

  num_wb_matches_ = LongestCommonSubsequenceLength(
    query_->Characters(), candidate_->WordBoundaryChars() );
}

} // namespace YouCompleteMe
