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
#include "IdentifierUtils.h"
#include "Repository.h"
#include "Result.h"
#include "Utils.h"

#ifdef YCM_ABSEIL_SUPPORTED
#include <absl/container/flat_hash_set.h>
namespace YouCompleteMe {
template< typename T, typename H, typename Eq >
using HashSet = absl::flat_hash_set< T, H, Eq >;
template< typename T > using Hash = absl::Hash< T >;
} // namespace YouCompleteMe
#else
#include <unordered_set>
namespace YouCompleteMe {
template< typename T, typename H, typename Eq >
using HashSet = std::unordered_set< T, H, Eq >;
template< typename T >
using Hash = std::hash< T >;
} // namespace YouCompleteMe
#endif
#include <memory>

namespace YouCompleteMe {

namespace {
struct CandidateHasher {
  size_t operator() ( const Candidate* c ) const noexcept {
    static Hash< std::string > h;
    return h(c->Text());
  }
};
struct CandidateCompareEq {
  bool operator() ( const Candidate* a, const Candidate* b ) const noexcept {
    return a->Text() == b->Text();
  }
};
} // namespace



IdentifierDatabase::IdentifierDatabase()
  : candidate_repository_( Repository< Candidate >::Instance() ) {
}


void IdentifierDatabase::RecreateIdentifiers(
  FiletypeIdentifierMap&& filetype_identifier_map ) {
  std::lock_guard locker( filetype_candidate_map_mutex_ );

  for ( auto&& [ filetype, paths_to_candidates ] : filetype_identifier_map ) {
    for ( auto&& [ filepath, identifiers ] : paths_to_candidates ) {
      RecreateIdentifiersNoLock( std::move( identifiers ),
                                 std::string( filetype ),
                                 std::string( filepath ) );
    }
  }
}


void IdentifierDatabase::AddSingleIdentifier(
  std::string&& new_candidate,
  std::string&& filetype,
  std::string&& filepath ) {
  std::lock_guard locker( filetype_candidate_map_mutex_ );
  std::vector< std::string > candidate_vector( 1 );
  auto candidate_pointer = candidate_repository_.GetElements(
         { new_candidate } )[ 0 ];
  auto& current_identifier_set = GetCandidateSet( std::move( filetype ),
                                                  std::move( filepath ) );
  auto it = std::find_if( current_identifier_set.begin(),
                          current_identifier_set.end(),
                          [ candidate_pointer ]( const Candidate& c ) {
                                return c.Text() == candidate_pointer->Text();
                          } );
  if ( it == current_identifier_set.end() ) {
    current_identifier_set.push_back( candidate_pointer->clone() );
  }
}


void IdentifierDatabase::RecreateIdentifiers(
  std::vector< std::string >&& new_candidates,
  std::string&& filetype,
  std::string&& filepath ) {
  std::lock_guard locker( filetype_candidate_map_mutex_ );
  RecreateIdentifiersNoLock( std::move( new_candidates ),
                             std::move( filetype ),
                             std::move( filepath ) );
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

  HashSet< const Candidate *,
           CandidateHasher,
           CandidateCompareEq > seen_candidates;
  seen_candidates.reserve( candidate_repository_.NumStoredElements() );
  std::vector< Result > results;

  {
    std::lock_guard locker( filetype_candidate_map_mutex_ );
    auto& paths_to_candidates = it->second;
    for ( const auto& [ _, candidates ] : paths_to_candidates ) {
      for ( const Candidate& candidate : candidates ) {
        if ( !seen_candidates.insert( &candidate ).second ) {
          continue;
        }

        if ( candidate.IsEmpty() ||
             !candidate.ContainsBytes( query_object ) ) {
          continue;
        }

        Result result = candidate.QueryMatchResult( query_object );

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
std::vector< Candidate > &IdentifierDatabase::GetCandidateSet(
  std::string&& filetype,
  std::string&& filepath ) {
  return filetype_candidate_map_[ std::move( filetype ) ]
                                [ std::move( filepath ) ];
}


// WARNING: You need to hold the filetype_candidate_map_mutex_ before calling
// this function and while using the returned set.
void IdentifierDatabase::RecreateIdentifiersNoLock(
  std::vector< std::string >&& new_candidates,
  std::string&& filetype,
  std::string&& filepath ) {

  auto& current_identifier_set = GetCandidateSet( std::move( filetype ),
                                                  std::move( filepath ) );
  auto candidate_pointers = candidate_repository_.GetElements(
                  std::move( new_candidates ) );
  current_identifier_set.clear();
  current_identifier_set.reserve( candidate_pointers.size() );
  std::transform( candidate_pointers.begin(),
                  candidate_pointers.end(),
                  std::back_inserter( current_identifier_set ),
                  []( const Candidate* candidate_ptr ) {
                    return candidate_ptr->clone();
                  } );
}

} // namespace YouCompleteMe
