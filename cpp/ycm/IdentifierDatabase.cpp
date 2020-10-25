// Copyright (C) 2013-2018 ycmd contributors
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

#include "IdentifierDatabase.h"

#include "Candidate.h"
#include "CandidateRepository.h"
#include "IdentifierUtils.h"
#include "Result.h"
#include "Utils.h"

#include <memory>
#include <unordered_set>

namespace YouCompleteMe {

IdentifierDatabase::IdentifierDatabase()
  : candidate_repository_( CandidateRepository::Instance() ) {
}


void IdentifierDatabase::AddIdentifiers(
  FiletypeIdentifierMap&& filetype_identifier_map ) {
  std::lock_guard locker( filetype_candidate_map_mutex_ );

  for ( auto&& filetype_and_map : filetype_identifier_map ) {
    for ( auto&& filepath_and_identifiers : filetype_and_map.second ) {
      auto filetype = filetype_and_map.first;
      auto filepath = filepath_and_identifiers.first;
      AddIdentifiersNoLock( std::move( filepath_and_identifiers.second ),
                            std::move( filetype ),
                            std::move( filepath ) );
    }
  }
}


void IdentifierDatabase::AddIdentifiers(
  std::vector< std::string >&& new_candidates,
  std::string&& filetype,
  std::string&& filepath ) {
  std::lock_guard locker( filetype_candidate_map_mutex_ );
  AddIdentifiersNoLock( std::move( new_candidates ), std::move( filetype ), std::move( filepath ) );
}


void IdentifierDatabase::ClearCandidatesStoredForFile(
  std::string&& filetype,
  std::string&& filepath ) {
  std::lock_guard locker( filetype_candidate_map_mutex_ );
  GetCandidateSet( std::move( filetype ), std::move( filepath ) ).clear();
}


std::vector< Result > IdentifierDatabase::ResultsForQueryAndType(
  std::string&& query,
  const std::string &filetype,
  const size_t max_results ) const {
  FiletypeCandidateMap::const_iterator it;
  {
    std::shared_lock locker( filetype_candidate_map_mutex_ );
    it = filetype_candidate_map_.find( filetype );

    if ( it == filetype_candidate_map_.end() ) {
      return {};
    }
  }
  Word query_object( std::move( query ) );

  std::unordered_set< const Candidate * > seen_candidates;
  seen_candidates.reserve( candidate_repository_.NumStoredCandidates() );
  std::vector< Result > results;

  {
    std::lock_guard locker( filetype_candidate_map_mutex_ );
    for ( const auto& path_and_candidates : *it->second ) {
      for ( const Candidate * candidate : *path_and_candidates.second ) {
        if ( ContainsKey( seen_candidates, candidate ) ) {
          continue;
        }
        seen_candidates.insert( candidate );

        if ( candidate->IsEmpty() ||
             !candidate->ContainsBytes( query_object ) ) {
          continue;
        }

        Result result = candidate->QueryMatchResult( query_object );

        if ( result.IsSubsequence() ) {
          results.push_back( result );
        }
      }
    }
  }

  PartialSort( results, max_results );
  return results;
}


// WARNING: You need to hold the filetype_candidate_map_mutex_ before calling
// this function and while using the returned set.
std::set< const Candidate * > &IdentifierDatabase::GetCandidateSet(
  std::string&& filetype,
  std::string&& filepath ) {
  std::unique_ptr< FilepathToCandidates > &path_to_candidates =
    filetype_candidate_map_[ std::move( filetype ) ];

  if ( !path_to_candidates ) {
    path_to_candidates = std::make_unique< FilepathToCandidates >();
  }

  std::unique_ptr< std::set< const Candidate * > > &candidates =
    ( *path_to_candidates )[ std::move( filepath ) ];

  if ( !candidates ) {
    candidates = std::make_unique< std::set< const Candidate * > >();
  }

  return *candidates;
}


// WARNING: You need to hold the filetype_candidate_map_mutex_ before calling
// this function and while using the returned set.
void IdentifierDatabase::AddIdentifiersNoLock(
  std::vector< std::string >&& new_candidates,
  std::string&& filetype,
  std::string&& filepath ) {
  std::set< const Candidate *> &candidates =
    GetCandidateSet( std::move( filetype ), std::move( filepath ) );

  std::vector< const Candidate * > repository_candidates =
    candidate_repository_.GetCandidatesForStrings(
      std::move( new_candidates ) );

  candidates.insert( repository_candidates.begin(),
                     repository_candidates.end() );
}


} // namespace YouCompleteMe
