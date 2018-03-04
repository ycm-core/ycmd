// Copyright (C) 2016 ycmd contributors
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
#include <gmock/gmock.h>
#include "LetterNode.h"

namespace YouCompleteMe {

using ::testing::AllOf;
using ::testing::ElementsAre;
using ::testing::IsNull;
using ::testing::Property;
using ::testing::StrEq;

TEST( LetterNodeTest, AsciiText ) {
  LetterNode root_node( "ascIi_texT" );

  const NearestLetterNodeIndices *nearest_nodes =
    root_node.NearestLetterNodesForLetter( 0, 'i' );

  EXPECT_EQ( nearest_nodes->indexOfFirstOccurrence, 4 );
  EXPECT_EQ( nearest_nodes->indexOfFirstUppercaseOccurrence, 4 );

  nearest_nodes = root_node.NearestLetterNodesForLetter(nearest_nodes->indexOfFirstOccurrence, 'i');

  EXPECT_EQ( nearest_nodes->indexOfFirstOccurrence, 5 );
  EXPECT_EQ( nearest_nodes->indexOfFirstUppercaseOccurrence, 0 );

  nearest_nodes = root_node.NearestLetterNodesForLetter(5, 't');
  
  EXPECT_EQ( nearest_nodes->indexOfFirstOccurrence, 7 );
  EXPECT_EQ( nearest_nodes->indexOfFirstUppercaseOccurrence, 10 );

  nearest_nodes = root_node.NearestLetterNodesForLetter(5, 'c');
  EXPECT_EQ( nearest_nodes->indexOfFirstOccurrence, 0 );
  EXPECT_EQ( nearest_nodes->indexOfFirstUppercaseOccurrence, 0 );
}


TEST( LetterNodeTest, ThrowOnNonAsciiCharacters ) {
  // UTF-8 characters representation:
  //   ¢: \xc2\xa2
  //   €: \xe2\x82\xac
  //   𐍈: \xf0\x90\x8d\x88
  ASSERT_THROW( LetterNode root_node( "uni¢𐍈d€" ), std::out_of_range );
}

} // namespace YouCompleteMe
