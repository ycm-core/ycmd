// Copyright (C) 2017 ycmd contributors
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

#include "benchmark/benchmark_api.h"
#include "BenchUtils.h"
#include "CandidateRepository.h"
// iostream is included because of a bug with Python earlier than 2.7.12
// and 3.5.3 on OSX and FreeBSD.
#include <iostream>
#include "PythonSupport.h"

namespace YouCompleteMe {

class PythonSupportFixture : public benchmark::Fixture {
public:
  void SetUp( const benchmark::State& state ) {
    CandidateRepository::Instance().ClearCandidates();
  }
};


BENCHMARK_DEFINE_F( PythonSupportFixture,
                    FilterAndSortUnstoredCandidatesWithCommonPrefix )(
    benchmark::State& state ) {

  std::vector< std::string > raw_candidates;
  raw_candidates = GenerateCandidatesWithCommonPrefix( "a_A_a_",
                                                       state.range( 0 ) );

  boost::python::list candidates;
  for ( auto insertion_text : raw_candidates ) {
    boost::python::dict candidate;
    candidate[ "insertion_text" ] = insertion_text;
    candidates.append( candidate );
  }

  while ( state.KeepRunning() ) {
    state.PauseTiming();
    CandidateRepository::Instance().ClearCandidates();
    state.ResumeTiming();
    FilterAndSortCandidates( candidates, "insertion_text", "aA",
                             state.range( 1 ) );
  }

  state.SetComplexityN( state.range( 0 ) );
}


BENCHMARK_DEFINE_F( PythonSupportFixture,
                    FilterAndSortStoredCandidatesWithCommonPrefix )(
    benchmark::State& state ) {

  std::vector< std::string > raw_candidates;
  raw_candidates = GenerateCandidatesWithCommonPrefix( "a_A_a_",
                                                       state.range( 0 ) );

  boost::python::list candidates;
  for ( auto insertion_text : raw_candidates ) {
    boost::python::dict candidate;
    candidate[ "insertion_text" ] = insertion_text;
    candidates.append( candidate );
  }

  // Store the candidates in the repository.
  FilterAndSortCandidates( candidates, "insertion_text", "aA",
                           state.range( 1 ) );

  while ( state.KeepRunning() )
    FilterAndSortCandidates( candidates, "insertion_text", "aA",
                             state.range( 1 ) );

  state.SetComplexityN( state.range( 0 ) );
}


BENCHMARK_REGISTER_F( PythonSupportFixture,
                      FilterAndSortUnstoredCandidatesWithCommonPrefix )
    ->RangeMultiplier( 1 << 4 )
    ->Ranges( { { 1, 1 << 16 }, { 0, 0 } } )
    ->Complexity();

BENCHMARK_REGISTER_F( PythonSupportFixture,
                      FilterAndSortUnstoredCandidatesWithCommonPrefix )
    ->RangeMultiplier( 1 << 4 )
    ->Ranges( { { 1, 1 << 16 }, { 50, 50 } } )
    ->Complexity();


BENCHMARK_REGISTER_F( PythonSupportFixture,
                      FilterAndSortStoredCandidatesWithCommonPrefix )
    ->RangeMultiplier( 1 << 4 )
    ->Ranges( { { 1, 1 << 16 }, { 0, 0 } } )
    ->Complexity();

BENCHMARK_REGISTER_F( PythonSupportFixture,
                      FilterAndSortStoredCandidatesWithCommonPrefix )
    ->RangeMultiplier( 1 << 4 )
    ->Ranges( { { 1, 1 << 16 }, { 50, 50 } } )
    ->Complexity();

} // namespace YouCompleteMe
