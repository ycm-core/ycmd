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

#ifndef TESTUTILS_H_G4RKMGUD
#define TESTUTILS_H_G4RKMGUD

#include "Character.h"
#include "CodePoint.h"
#include "Word.h"

#include <boost/filesystem.hpp>
#include <gmock/gmock.h>
#include <string>
#include <vector>

using ::testing::PrintToString;

namespace fs = boost::filesystem;

// A segmentation fault occurs when gtest tries to print a
// boost::filesystem::path. Teach gtest how to print it.
namespace boost {

namespace filesystem {

void PrintTo( const fs::path &path, std::ostream *os );

}

}

namespace YouCompleteMe {

// Tuple-like structures to help writing tests for CodePoint, Character, and
// Word objects. We can't use std::tuple because its constructor is explicit in
// old versions of the GNU C++ library which prevent us to do things like:
//   std::vector< std::tuple< ... > > tuples{ { ... } }
struct CodePointTuple {
  CodePointTuple()
    : CodePointTuple( "", "", "", false, false, false, BreakProperty::OTHER ) {
  }

  CodePointTuple( const CodePoint &code_point )
    : CodePointTuple( code_point.Normal().c_str(),
                      code_point.FoldedCase().c_str(),
                      code_point.SwappedCase().c_str(),
                      code_point.IsLetter(),
                      code_point.IsPunctuation(),
                      code_point.IsUppercase(),
                      code_point.GetBreakProperty() ) {
  }

  CodePointTuple( const std::string &normal,
                  const std::string &folded_case,
                  const std::string &swapped_case,
                  bool is_letter,
                  bool is_punctuation,
                  bool is_uppercase,
                  BreakProperty break_property )
    : normal_( normal ),
      folded_case_( folded_case ),
      swapped_case_( swapped_case ),
      is_letter_( is_letter ),
      is_punctuation_( is_punctuation ),
      is_uppercase_( is_uppercase ),
      break_property_( break_property ) {
  }

  bool operator== ( const CodePointTuple &other ) const {
    return normal_ == other.normal_ &&
           folded_case_ == other.folded_case_ &&
           swapped_case_ == other.swapped_case_ &&
           is_letter_ == other.is_letter_ &&
           is_punctuation_ == other.is_punctuation_ &&
           is_uppercase_ == other.is_uppercase_ &&
           break_property_ == other.break_property_;
  };

  std::string normal_;
  std::string folded_case_;
  std::string swapped_case_;
  bool is_letter_;
  bool is_punctuation_;
  bool is_uppercase_;
  BreakProperty break_property_;
};


struct CharacterTuple {
  CharacterTuple()
    : CharacterTuple( "", "", "", "", false, false, false, false ) {
  }

  CharacterTuple( const Character &character )
    : CharacterTuple( character.Normal(),
                      character.Base(),
                      character.FoldedCase(),
                      character.SwappedCase(),
                      character.IsBase(),
                      character.IsLetter(),
                      character.IsPunctuation(),
                      character.IsUppercase() ) {
  }

  CharacterTuple( const std::string &normal,
                  const std::string &base,
                  const std::string &folded_case,
                  const std::string &swapped_case,
                  bool is_base,
                  bool is_letter,
                  bool is_punctuation,
                  bool is_uppercase )
    : normal_( normal ),
      base_( base ),
      folded_case_( folded_case ),
      swapped_case_( swapped_case ),
      is_base_( is_base ),
      is_letter_( is_letter ),
      is_punctuation_( is_punctuation ),
      is_uppercase_( is_uppercase ) {
  }

  bool operator== ( const CharacterTuple &other ) const {
    return normal_ == other.normal_ &&
           base_ == other.base_ &&
           folded_case_ == other.folded_case_ &&
           swapped_case_ == other.swapped_case_ &&
           is_base_ == other.is_base_ &&
           is_letter_ == other.is_letter_ &&
           is_punctuation_ == other.is_punctuation_ &&
           is_uppercase_ == other.is_uppercase_;
  };

  std::string normal_;
  std::string base_;
  std::string folded_case_;
  std::string swapped_case_;
  bool is_base_;
  bool is_letter_;
  bool is_punctuation_;
  bool is_uppercase_;
};


struct WordTuple {
  WordTuple()
    : WordTuple( "", {} ) {
  }

  WordTuple( const char* text,
             const std::vector< const char* > &characters )
    : text_( text ),
      characters_( characters ) {
  }

  bool operator== ( const WordTuple &other ) const {
    return text_ == other.text_ &&
           characters_ == other.characters_;
  };

  const char* text_;
  std::vector< const char* > characters_;
};


// Pretty print the CodePoint, Character, and Word objects in the tests.
std::ostream& operator<<( std::ostream& os, const CodePointTuple &code_point );
std::ostream& operator<<( std::ostream& os, const CodePoint &code_point );
std::ostream& operator<<( std::ostream& os, const CodePoint *code_point );
std::ostream& operator<<( std::ostream& os, const CharacterTuple &character );
std::ostream& operator<<( std::ostream& os, const Character &character );
std::ostream& operator<<( std::ostream& os, const Character *character );
std::ostream& operator<<( std::ostream& os, const WordTuple &word );


// These matchers are used to remove the "is equal to" output from gtest.
MATCHER_P( IsCodePointWithProperties,
           properties,
           PrintToString( properties ) ) {
  return CodePointTuple( arg ) == properties;
}


MATCHER_P( IsCharacterWithProperties,
           properties,
           PrintToString( properties ) ) {
  return CharacterTuple( arg ) == properties;
}


MATCHER_P( Equals, expected, PrintToString( expected ) ) {
  return arg == expected;
}


MATCHER_P( ContainsPointees, expected, PrintToString( expected ) ) {
  if ( arg.size() != expected.size() ) {
    return false;
  }

  auto actual_pos = arg.begin();
  auto expected_pos = expected.begin();
  for ( ; actual_pos != arg.end() && expected_pos != expected.end();
          ++actual_pos, ++expected_pos ) {
    if ( !( **actual_pos == **expected_pos ) ) {
      return false;
    }
  }
  return true;
}


fs::path PathToTestFile( const std::string &filepath );

} // namespace YouCompleteMe

#endif /* end of include guard: TESTUTILS_H_G4RKMGUD */
