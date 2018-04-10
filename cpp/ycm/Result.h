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

#ifndef RESULT_H_CZYD2SGN
#define RESULT_H_CZYD2SGN

#include "Candidate.h"

#include <string>

namespace YouCompleteMe {

class Result {
public:
  Result();
  ~Result() = default;

  Result( const Candidate *candidate,
          const Word *query,
          size_t char_match_index_sum,
          bool query_is_candidate_prefix );

  bool operator< ( const Result &other ) const;

  inline const std::string &Text() const {
    return candidate_->Text();
  }

  inline size_t NumWordBoundaryChars() const {
    return candidate_->WordBoundaryChars().size();
  }

  inline bool IsSubsequence() const {
    return is_subsequence_;
  }

private:
  void SetResultFeaturesFromQuery();

  // true when the characters of the query are a subsequence of the characters
  // in the candidate text, e.g. the characters "abc" are a subsequence for
  // "xxaygbefc" but not for "axxcb" since they occur in the correct order ('a'
  // then 'b' then 'c') in the first string but not in the second.
  bool is_subsequence_;

  // true when the first character of the query and the candidate match
  bool first_char_same_in_query_and_text_;

  // true when the query is a prefix of the candidate string, e.g. "foo" query
  // for "foobar" candidate.
  bool query_is_candidate_prefix_;

  // The sum of the indexes of all the letters the query "hit" in the candidate
  // text. For instance, the result for the query "abc" in the candidate
  // "012a45bc8" has char_match_index_sum of 3 + 6 + 7 = 16 because those are
  // the char indexes of those letters in the candidate string.
  size_t char_match_index_sum_;

  // The number of characters in the query that match word boundary characters
  // in the candidate. Characters must match in the same order of appearance
  // (i.e. these characters must be a subsequence of the word boundary
  // characters). Case is ignored. A character is a word boundary character if
  // one of these is true:
  //  - this is the first character and not a punctuation;
  //  - the character is uppercase but not the previous one;
  //  - the character is a letter and the previous one is a punctuation.
  size_t num_wb_matches_;

  // NOTE: we don't use references for the query and the candidate because we
  // are sorting results through std::sort or std::partial_sort and these
  // functions require move assignments which is not possible with reference
  // members.

  // Points to the candidate.
  const Candidate *candidate_;

  // Points to the query.
  const Word *query_;
};

template< class T >
struct ResultAnd {
  ResultAnd( const Result &result, T extra_object )
    : extra_object_( extra_object ),
      result_( result ) {
  }

  bool operator< ( const ResultAnd &other ) const {
    return result_ < other.result_;
  }

  T extra_object_;
  Result result_;
};

template< class T >
struct ResultAnd<T * > {
  ResultAnd( const Result &result, const T *extra_object )
    : extra_object_( extra_object ),
      result_( result ) {
  }

  bool operator< ( const ResultAnd &other ) const {
    return result_ < other.result_;
  }

  const T *extra_object_;
  Result result_;
};

} // namespace YouCompleteMe

#endif /* end of include guard: RESULT_H_CZYD2SGN */

