// Copyright (C) 2018 ycmd contributors
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

#include "Character.h"
#include "CharacterRepository.h"
#include "CodePoint.h"
#include "TestUtils.h"

#include <array>
#include <gtest/gtest.h>
#include <gmock/gmock.h>

using ::testing::TestWithParam;
using ::testing::ValuesIn;

namespace YouCompleteMe {

struct NormalizationTuple {
  const char* source;
  const char* nfc;
  const char* nfd;
  const char* nfkc;
  const char* nfkd;
};


std::ostream& operator<<( std::ostream& os,
                          const NormalizationTuple &tuple ) {
  os << "{ " << PrintToString( tuple.source ) << ", "
             << PrintToString( tuple.nfc    ) << ", "
             << PrintToString( tuple.nfd    ) << ", "
             << PrintToString( tuple.nfkc   ) << ", "
             << PrintToString( tuple.nfkd   ) << " }";
  return os;
}


class NormalizationTest : public TestWithParam< NormalizationTuple > {
protected:
  NormalizationTest()
    : repo_( CharacterRepository::Instance() ) {
  }

  virtual void SetUp() {
    repo_.ClearCharacters();
    tuple_ = GetParam();
  }

  CharacterRepository &repo_;
  NormalizationTuple tuple_;
};


TEST_P( NormalizationTest, NormalizationFormDecompositionIsConform ) {
  EXPECT_THAT( Character( tuple_.source ).Normal(), Equals( tuple_.nfd  ) );
  EXPECT_THAT( Character( tuple_.nfc    ).Normal(), Equals( tuple_.nfd  ) );
  EXPECT_THAT( Character( tuple_.nfd    ).Normal(), Equals( tuple_.nfd  ) );
  EXPECT_THAT( Character( tuple_.nfkc   ).Normal(), Equals( tuple_.nfkd ) );
  EXPECT_THAT( Character( tuple_.nfkd   ).Normal(), Equals( tuple_.nfkd ) );
}


// Tests generated from
// https://unicode.org/Public/UCD/latest/ucd/NormalizationTest.txt
const NormalizationTuple tests[] = {
#include "NormalizationCases.inc"
};


INSTANTIATE_TEST_SUITE_P( UnicodeTest, NormalizationTest, ValuesIn( tests ) );

} // namespace YouCompleteMe
