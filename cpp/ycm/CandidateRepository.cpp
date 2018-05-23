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

#include "CandidateRepository.h"
#include "Candidate.h"
#include "Utils.h"

#include <mutex>

#ifdef USE_CLANG_COMPLETER
#  include "ClangCompleter/CompletionData.h"
#endif // USE_CLANG_COMPLETER

namespace YouCompleteMe {

namespace {

// We set a reasonable max limit to prevent issues with huge candidate strings
// entering the database. Such large candidates are almost never desirable.
const size_t MAX_CANDIDATE_SIZE = 80;

}  // unnamed namespace


CandidateRepository &CandidateRepository::Instance() {
  static CandidateRepository repo;
  return repo;
}


size_t CandidateRepository::NumStoredCandidates() {
  std::lock_guard< std::mutex > locker( candidate_holder_mutex_ );
  return candidate_holder_.size();
}


std::vector< const Candidate * > CandidateRepository::GetCandidatesForStrings(
  const std::vector< std::string > &strings ) {
  std::vector< const Candidate * > candidates;
  candidates.reserve( strings.size() );

  {
    std::lock_guard< std::mutex > locker( candidate_holder_mutex_ );

    for ( const std::string & candidate_text : strings ) {
      const std::string &validated_candidate_text =
        ValidatedCandidateText( candidate_text );

      std::unique_ptr< Candidate > &candidate = GetValueElseInsert(
                                                  candidate_holder_,
                                                  validated_candidate_text,
                                                  nullptr );

      if ( !candidate ) {
        candidate.reset( new Candidate( validated_candidate_text ) );
      }

      candidates.push_back( candidate.get() );
    }
  }

  return candidates;
}


void CandidateRepository::ClearCandidates() {
  candidate_holder_.clear();
}


// Returns a ref to empty_ if candidate not valid.
const std::string &CandidateRepository::ValidatedCandidateText(
  const std::string &candidate_text ) {
  if ( candidate_text.size() <= MAX_CANDIDATE_SIZE ) {
    return candidate_text;
  }

  return empty_;
}

} // namespace YouCompleteMe
