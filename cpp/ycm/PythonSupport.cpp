// Copyright (C) 2011, 2012, 2013  Google Inc.
//
// This file is part of YouCompleteMe.
//
// YouCompleteMe is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// YouCompleteMe is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with YouCompleteMe.  If not, see <http://www.gnu.org/licenses/>.

#include "PythonSupport.h"
#include "standard.h"
#include "Result.h"
#include "Candidate.h"
#include "CandidateRepository.h"
#include "ReleaseGil.h"

#include <boost/algorithm/string.hpp>
#include <boost/algorithm/cxx11/any_of.hpp>
#include <vector>

using boost::algorithm::any_of;
using boost::algorithm::is_upper;
using boost::python::len;
using boost::python::str;
using boost::python::extract;
using boost::python::object;
typedef boost::python::list pylist;

namespace YouCompleteMe {

namespace {

std::string GetUtf8String( const boost::python::object &string_or_unicode ) {
  extract< std::string > to_string( string_or_unicode );

  if ( to_string.check() )
    return to_string();

  return extract< std::string >( str( string_or_unicode ).encode( "utf8" ) );
}

std::vector< const Candidate * > CandidatesFromObjectList(
  const pylist &candidates,
  const std::string &candidate_property ) {
  int num_candidates = len( candidates );
  std::vector< std::string > candidate_strings;
  candidate_strings.reserve( num_candidates );

  for ( int i = 0; i < num_candidates; ++i ) {
    if ( candidate_property.empty() ) {
      candidate_strings.push_back( GetUtf8String( candidates[ i ] ) );
    } else {
      object holder = extract< object >( candidates[ i ] );
      candidate_strings.push_back( GetUtf8String(
                                     holder[ candidate_property.c_str() ] ) );
    }
  }

  return CandidateRepository::Instance().GetCandidatesForStrings(
           candidate_strings );
}

} // unnamed namespace

boost::python::list FilterAndSortCandidates(
  const boost::python::list &candidates,
  const std::string &candidate_property,
  const std::string &query ) {
  pylist filtered_candidates;

  if ( query.empty() ) {
    return candidates;
  }

  int num_candidates = len( candidates );
  std::vector< const Candidate * > repository_candidates =
    CandidatesFromObjectList( candidates, candidate_property );

  std::vector< ResultAnd< int > > result_and_objects;
  {
    ReleaseGil unlock;
    Bitset query_bitset = LetterBitsetFromString( query );
    bool query_has_uppercase_letters = any_of( query, is_upper() );

    for ( int i = 0; i < num_candidates; ++i ) {
      const Candidate *candidate = repository_candidates[ i ];

      if ( !candidate->MatchesQueryBitset( query_bitset ) )
        continue;

      Result result = candidate->QueryMatchResult( query,
                                                   query_has_uppercase_letters );

      if ( result.IsSubsequence() ) {
        ResultAnd< int > result_and_object( result, i );
        result_and_objects.push_back( boost::move( result_and_object ) );
      }
    }

    std::sort( result_and_objects.begin(), result_and_objects.end() );
  }

  foreach ( const ResultAnd< int > &result_and_object,
            result_and_objects ) {
    filtered_candidates.append( candidates[ result_and_object.extra_object_ ] );
  }

  return filtered_candidates;
}

} // namespace YouCompleteMe
