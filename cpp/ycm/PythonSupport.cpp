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

#include <iterator>
#include <thread>
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
  result_and_objects.reserve( repository_candidates.size() );
  {
    pybind11::gil_scoped_release unlock;
    Word query_object( std::move( query ) );

    if ( num_candidates >= 256 ) {
      const auto n_threads = std::thread::hardware_concurrency();
      std::vector< std::future< std::vector< ResultAnd< size_t > > > > futures( n_threads );
      auto begin = repository_candidates.begin();
      auto end = repository_candidates.begin() + num_candidates / n_threads + 1;
      const auto chunk_size = end - begin;
      for ( size_t thread_index = 0; thread_index < n_threads; ++thread_index ) {
        futures[ thread_index ] = tasks.push(
          [ &, thread_index ] ( auto begin, auto end ) {
	    std::vector< ResultAnd< size_t > > partial;
	    partial.reserve( end - begin );
            auto i = thread_index * chunk_size;
            std::for_each(
              begin,
              end,
              [ &, i ] ( const Candidate* candidate ) mutable {
                if ( !candidate->IsEmpty() &&
                     candidate->ContainsBytes( query_object ) ) {
                  Result result = candidate->QueryMatchResult( query_object );
                  if ( result.IsSubsequence() ) {
                    partial.emplace_back( result, i );
                  }
                }
                ++i;
            } );
	    return partial;
        }, begin, end );
        begin = end;
        if ( repository_candidates.end() - begin < chunk_size ) {
          end = repository_candidates.end();
        } else {
          end = begin + chunk_size;
        }
      }
      for ( auto&& f : futures ) {
	auto partial = f.get();
        result_and_objects.insert( result_and_objects.end(),
                                   std::make_move_iterator( partial.begin() ),
                                   std::make_move_iterator( partial.end() ) );
      }
    } else {
      std::for_each(
        repository_candidates.begin(),
        repository_candidates.end(),
        [ &, i = 0 ] ( const Candidate* candidate ) mutable {
          if ( !candidate->IsEmpty() &&
               candidate->ContainsBytes( query_object ) ) {
            Result result = candidate->QueryMatchResult( query_object );
            if ( result.IsSubsequence() ) {
              result_and_objects.emplace_back( result, i );
            }
          }
          ++i;
      } );
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
    ssize_t size = 0;
    const char* buffer = nullptr;
    buffer = PyUnicode_AsUTF8AndSize( value.ptr(), &size );
    return { buffer, static_cast< size_t >( size ) };
  }
  if ( PyBytes_CheckExact( value.ptr() ) ) {
    ssize_t size = 0;
    char* buffer = nullptr;
    PyBytes_AsStringAndSize( value.ptr(), &buffer, &size );
    return { buffer, static_cast< size_t >( size ) };
  }

  // Otherwise go through Python's built-in `str`.
  pybind11::str keep_alive( value );
  ssize_t size = 0;
  const char* buffer =
      PyUnicode_AsUTF8AndSize( keep_alive.ptr(), &size );
  return { buffer, static_cast< size_t >( size ) };
}

} // namespace YouCompleteMe
