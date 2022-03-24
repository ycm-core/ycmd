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
#include "Repository.h"
#include "Result.h"
#include "Utils.h"

#include <utility>
#include <vector>

namespace YouCompleteMe {

namespace {

std::vector< const Candidate * > CandidatesFromObjectList(
  const pybind11::list& candidates,
  pybind11::str candidate_property,
  size_t num_candidates ) {
  std::vector< std::string > candidate_strings( num_candidates );
  auto it = candidate_strings.begin();

  if ( !PyUnicode_GET_LENGTH( candidate_property.ptr() ) ) {
    for ( size_t i = 0; i < num_candidates; ++i ) {
      *it++ = GetUtf8String( PyList_GET_ITEM( candidates.ptr(), i ) );
    }
  } else {
    for ( size_t i = 0; i < num_candidates; ++i ) {
        auto element = PyDict_GetItem( PyList_GET_ITEM( candidates.ptr(), i ),
                                       candidate_property.ptr() );
        *it++ = GetUtf8String( element );
    }
  }

  return Repository< Candidate >::Instance().GetElements(
           std::move( candidate_strings ) );
}

} // unnamed namespace


pybind11::list FilterAndSortCandidates(
  const pybind11::list& candidates,
  pybind11::str candidate_property,
  std::string& query,
  const size_t max_candidates ) {

  auto num_candidates = size_t( PyList_GET_SIZE( candidates.ptr() ) );
  std::vector< const Candidate * > repository_candidates =
    CandidatesFromObjectList( candidates,
                              std::move( candidate_property ),
                              num_candidates );

  std::vector< ResultAnd< size_t > > result_and_objects;
  {
    pybind11::gil_scoped_release unlock;
    Word query_object( std::move( query ) );

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

  pybind11::list filtered_candidates( result_and_objects.size() );
  for ( size_t i = 0; i < result_and_objects.size(); ++i ) {
    auto new_candidate = PyList_GET_ITEM(
        candidates.ptr(),
        result_and_objects[ i ].extra_object_ );
    Py_INCREF( new_candidate );
    PyList_SET_ITEM( filtered_candidates.ptr(), i, new_candidate );
  }

  return filtered_candidates;
}


std::string GetUtf8String( pybind11::handle value ) {
  // If already a unicode or string (or something derived from it)
  // pybind will already convert to utf8 when converting to std::string.
  // For `bytes` the contents are left untouched:
  if ( PyUnicode_CheckExact( value.ptr() ) ) {
    ptrdiff_t size = 0;
    const char* buffer = nullptr;
    buffer = PyUnicode_AsUTF8AndSize( value.ptr(), &size );
    return { buffer, static_cast< size_t >( size ) };
  }
  if ( PyBytes_CheckExact( value.ptr() ) ) {
    ptrdiff_t size = 0;
    char* buffer = nullptr;
    PyBytes_AsStringAndSize( value.ptr(), &buffer, &size );
    return { buffer, static_cast< size_t >( size ) };
  }

  // Otherwise go through Python's built-in `str`.
  pybind11::str keep_alive( value );
  ptrdiff_t size = 0;
  const char* buffer =
      PyUnicode_AsUTF8AndSize( keep_alive.ptr(), &size );
  return { buffer, static_cast< size_t >( size ) };
}

} // namespace YouCompleteMe
