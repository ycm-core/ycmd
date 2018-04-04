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
#include "TestUtils.h"

#include <gtest/gtest.h>
#include <gmock/gmock.h>

using ::testing::Pointee;
using ::testing::UnorderedElementsAre;

namespace YouCompleteMe {

class CharacterRepositoryTest : public ::testing::Test {
protected:
  CharacterRepositoryTest()
    : repo_( CharacterRepository::Instance() ) {
  }

  virtual void SetUp() {
    repo_.ClearCharacters();
  }

  CharacterRepository &repo_;
};


TEST_F( CharacterRepositoryTest, GetCharacters ) {
  CharacterSequence character_objects = repo_.GetCharacters( { "α", "ω" } );

  EXPECT_THAT( repo_.NumStoredCharacters(), 2 );
  EXPECT_THAT( character_objects, UnorderedElementsAre(
    Pointee( IsCharacterWithProperties< CharacterTuple >(
      { "α", "α", "α", "Α", true, true, false, false } ) ),
    Pointee( IsCharacterWithProperties< CharacterTuple >(
      { "ω", "ω", "ω", "Ω", true, true, false, false } ) )
  ) );
}

} // namespace YouCompleteMe
