// Copyright (C) 2011, 2012 Google Inc.
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

#include <gtest/gtest.h>
#include "CandidateRepository.h"
#include "Candidate.h"
#include "Result.h"

namespace YouCompleteMe {

TEST( CandidateRepositoryTest, Basic ) {
  std::vector< std::string > inputs;
  inputs.push_back( "foobar" );

  CandidateRepository &repo = CandidateRepository::Instance();
  std::vector< const Candidate * > candidates =
    repo.GetCandidatesForStrings( inputs );

  EXPECT_EQ( "foobar", candidates[ 0 ]->Text() );
}


TEST( CandidateRepositoryTest, TooLongCandidateSkipped ) {
  std::vector< std::string > inputs;
  inputs.push_back( std::string( 81, 'a' ) );  // this one is too long
  inputs.push_back( std::string( 80, 'b' ) );  // this one is *just* right

  CandidateRepository &repo = CandidateRepository::Instance();
  std::vector< const Candidate * > candidates =
    repo.GetCandidatesForStrings( inputs );

  EXPECT_EQ( "", candidates[ 0 ]->Text() );
  EXPECT_EQ( 'b', candidates[ 1 ]->Text()[ 0 ] );
}


TEST( CandidateRepositoryTest, EmptyCandidatesForUnicode ) {
  std::vector< std::string > inputs;
  inputs.push_back( "fooδιακριτικός" );
  inputs.push_back( "fooδιακός" );

  CandidateRepository &repo = CandidateRepository::Instance();
  std::vector< const Candidate * > candidates =
    repo.GetCandidatesForStrings( inputs );

  EXPECT_EQ( "", candidates[ 0 ]->Text() );
  EXPECT_EQ( "", candidates[ 1 ]->Text() );
}


TEST( CandidateRepositoryTest, EmptyCandidatesForNonPrintable ) {
  std::vector< std::string > inputs;
  inputs.push_back( "\x01\x05\x0a\x15" );

  CandidateRepository &repo = CandidateRepository::Instance();
  std::vector< const Candidate * > candidates =
    repo.GetCandidatesForStrings( inputs );

  EXPECT_EQ( "", candidates[ 0 ]->Text() );
}


} // namespace YouCompleteMe

