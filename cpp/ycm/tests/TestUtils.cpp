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

#include "TestUtils.h"

#include <whereami.c>

namespace boost {

namespace filesystem {

void PrintTo( const fs::path &path, std::ostream *os ) {
  *os << path;
}

} // namespace filesystem

} // namespace boost

namespace YouCompleteMe {

std::ostream& operator<<( std::ostream& os, const CodePointTuple &code_point ) {
  os << "{ " << PrintToString( code_point.normal_ ) << ", "
             << PrintToString( code_point.folded_case_ ) << ", "
             << PrintToString( code_point.swapped_case_ ) << ", "
             << PrintToString( code_point.is_letter_ ) << ", "
             << PrintToString( code_point.is_punctuation_ ) << ", "
             << PrintToString( code_point.is_uppercase_ ) << ", "
             << PrintToString( code_point.break_property_ ) << " }";
  return os;
}

std::ostream& operator<<( std::ostream& os, const CodePoint &code_point ) {
  os << CodePointTuple( code_point );
  return os;
}


std::ostream& operator<<( std::ostream& os, const CodePoint *code_point ) {
  os << "*" << *code_point;
  return os;
}


std::ostream& operator<<( std::ostream& os, const CharacterTuple &character ) {
  os << "{ " << PrintToString( character.normal_ ) << ", "
             << PrintToString( character.base_ ) << ", "
             << PrintToString( character.folded_case_ ) << ", "
             << PrintToString( character.swapped_case_ ) << ", "
             << PrintToString( character.is_base_ ) << ", "
             << PrintToString( character.is_letter_ ) << ", "
             << PrintToString( character.is_punctuation_ ) << ", "
             << PrintToString( character.is_uppercase_ ) << " }";
  return os;
}


std::ostream& operator<<( std::ostream& os, const Character &character ) {
  os << PrintToString( CharacterTuple( character ) );
  return os;
}


std::ostream& operator<<( std::ostream& os, const Character *character ) {
  os << "*" << *character;
  return os;
}


std::ostream& operator<<( std::ostream& os, const WordTuple &word ) {
  os << "{ " << PrintToString( word.text_ ) << ", { ";
  const std::vector< const char* > &characters( word.characters_ );
  auto character_pos = characters.begin();
  if ( character_pos != characters.end() ) {
    os << PrintToString( *character_pos );
    ++character_pos;
    for ( ; character_pos != characters.end() ; ++character_pos ) {
      os << ", " << PrintToString( *character_pos );
    }
    os << " }";
  }
  return os;
}


std::ostream& operator<<( std::ostream& os, const fs::path *path ) {
  os << *path;
  return os;
}


fs::path PathToTestFile( const std::string &filepath ) {
  int dirname_length;
  int exec_length = wai_getExecutablePath( NULL, 0, NULL );
  std::unique_ptr< char[] > executable( new char [ exec_length ] );
  wai_getExecutablePath( executable.get(), exec_length, &dirname_length );
  executable[ dirname_length ] = '\0';
  fs::path path_to_testdata = fs::path( executable.get() ) / "testdata";
  return path_to_testdata / fs::path( filepath );
}

} // namespace YouCompleteMe
