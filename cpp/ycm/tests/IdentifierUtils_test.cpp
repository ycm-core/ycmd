// Copyright (C) 2011, 2012  Google Inc.
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

#include "IdentifierUtils.h"
#include "TestUtils.h"
#include "IdentifierDatabase.h"

#include <gtest/gtest.h>
#include <gmock/gmock.h>
#include <boost/filesystem.hpp>

namespace YouCompleteMe {

namespace fs = boost::filesystem;
using ::testing::ElementsAre;
using ::testing::ContainerEq;
using ::testing::WhenSorted;


TEST( IdentifierUtilsTest, ExtractIdentifiersFromTagsFileWorks ) {
  fs::path root = fs::current_path().root_path();
  fs::path testfile = PathToTestFile( "basic.tags" );
  fs::path testfile_parent = testfile.parent_path();

  FiletypeIdentifierMap expected;
  expected[ "cpp" ][ ( testfile_parent / "foo" ).string() ]
  .push_back( "i1" );
  expected[ "cpp" ][ ( testfile_parent / "bar" ).string() ]
  .push_back( "i1" );
  expected[ "cpp" ][ ( testfile_parent / "foo" ).string() ]
  .push_back( "foosy" );
  expected[ "cpp" ][ ( testfile_parent / "bar" ).string() ]
  .push_back( "fooaaa" );

  expected[ "c" ][ ( root / "foo" / "zoo" ).string() ].push_back( "Floo::goo" );
  expected[ "c" ][ ( root / "foo" / "goo maa" ).string() ].push_back( "!goo" );

  expected[ "cs" ][ ( root / "m_oo" ).string() ].push_back( "#bleh" );

  EXPECT_THAT( ExtractIdentifiersFromTagsFile( testfile ),
               ContainerEq( expected ) );
}

} // namespace YouCompleteMe

