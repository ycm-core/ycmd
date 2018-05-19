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

#include "PythonSupport.h"
#include "Candidate.h"
#include "CandidateRepository.h"
#include "Result.h"
#include "Utils.h"

#include <utility>
#include <vector>

using pybind11::len;
using pybind11::str;
using pybind11::bytes;
using pybind11::object;
using pybind11::isinstance;
using pylist = pybind11::list;

namespace YouCompleteMe {

namespace {

std::vector< const Candidate * > CandidatesFromObjectList(
  const pylist &candidates,
  const std::string &candidate_property ) {
  size_t num_candidates = len( candidates );
  std::vector< std::string > candidate_strings;
  candidate_strings.reserve( num_candidates );
  // Store the property in a native Python string so that the below doesn't need
  // to reconvert over and over:
  str py_prop( candidate_property );

  for ( size_t i = 0; i < num_candidates; ++i ) {
    if ( candidate_property.empty() ) {
      candidate_strings.emplace_back( GetUtf8String( candidates[ i ] ) );
    } else {
      candidate_strings.emplace_back( GetUtf8String(
                                        candidates[ i ][ py_prop ] ) );
    }
  }

  return CandidateRepository::Instance().GetCandidatesForStrings(
           candidate_strings );
}

} // unnamed namespace


pylist FilterAndSortCandidates(
  const pylist &candidates,
  const std::string &candidate_property,
  const std::string &query,
  const size_t max_candidates ) {
  pylist filtered_candidates;

  size_t num_candidates = len( candidates );
  std::vector< const Candidate * > repository_candidates =
    CandidatesFromObjectList( candidates, candidate_property );

  std::vector< ResultAnd< size_t > > result_and_objects;
  {
    pybind11::gil_scoped_release unlock;
    Word query_object( query );

    for ( size_t i = 0; i < num_candidates; ++i ) {
      const Candidate *candidate = repository_candidates[ i ];

      if ( candidate->IsEmpty() || !candidate->ContainsBytes( query_object ) ) {
        continue;
      }

      Result result = candidate->QueryMatchResult( query_object );

      if ( result.IsSubsequence() ) {
        result_and_objects.emplace_back( result, i );
      }
    }

    PartialSort( result_and_objects, max_candidates );
  }

  for ( const ResultAnd< size_t > &result_and_object : result_and_objects ) {
    filtered_candidates.append( candidates[ result_and_object.extra_object_ ] );
  }

  return filtered_candidates;
}


std::string GetUtf8String( const object &value ) {
  // If already a unicode or string (or something derived from it)
  // pybind will already convert to utf8 when converting to std::string.
  // For `bytes` the contents are left untouched:
  if ( isinstance< str >( value ) || isinstance< bytes >( value ) ) {
    return value.cast< std::string >();
  }

  // Otherwise go through `pybind11::str()`,
  // which goes through Python's built-in `str`.
  return str( value );
}

} // namespace YouCompleteMe
