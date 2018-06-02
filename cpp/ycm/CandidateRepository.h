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

#ifndef CANDIDATEREPOSITORY_H_K9OVCMHG
#define CANDIDATEREPOSITORY_H_K9OVCMHG

#include "Candidate.h"
#include "Mutex.h"

#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

namespace YouCompleteMe {

using CandidateHolder = std::unordered_map< std::string,
                                            std::unique_ptr< Candidate > >;


// This singleton stores already built Candidate objects for candidate strings
// that were already seen. If Candidates are requested for previously unseen
// strings, new Candidate objects are built.
//
// This is shared by the identifier completer and the clang completer so that
// work is not repeated.
//
// This class is thread-safe.
class CandidateRepository {
public:
  YCM_EXPORT static CandidateRepository &Instance();
  // Make class noncopyable
  CandidateRepository( const CandidateRepository& ) = delete;
  CandidateRepository& operator=( const CandidateRepository& ) = delete;

  size_t NumStoredCandidates();

  YCM_EXPORT std::vector< const Candidate * > GetCandidatesForStrings(
    const std::vector< std::string > &strings );

  // This should only be used to isolate tests and benchmarks.
  YCM_EXPORT void ClearCandidates() NO_THREAD_SAFETY_ANALYSIS;

private:
  CandidateRepository() = default;
  ~CandidateRepository() = default;

  const std::string &ValidatedCandidateText(
      const std::string &candidate_text );

  static CandidateRepository *instance_ GUARDED_BY( instance_mutex_ );
  static Mutex instance_mutex_;

  // MSVC 12 complains that no appropriate default constructor is available if
  // this property is not initialized.
  const std::string empty_{};

  // This data structure owns all the Candidate pointers
  CandidateHolder candidate_holder_ GUARDED_BY( candidate_holder_mutex_ );
  Mutex candidate_holder_mutex_;
};

} // namespace YouCompleteMe

#endif /* end of include guard: CANDIDATEREPOSITORY_H_K9OVCMHG */
