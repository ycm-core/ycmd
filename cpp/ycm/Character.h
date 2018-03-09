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

#ifndef CHARACTER_H_YTIET2HZ
#define CHARACTER_H_YTIET2HZ

#include <string>
#include <vector>

namespace YouCompleteMe {

// This class represents a UTF-8 character. It takes a UTF-8 encoded string
// corresponding to a grapheme cluster (see
// https://www.unicode.org/glossary/#grapheme_cluster), normalize it through NFD
// (see https://www.unicode.org/versions/Unicode10.0.0/ch03.pdf#G49621), and
// compute the folded and swapped case versions of the normalized character. It
// also holds some properties like if the character is a letter or a
// punctuation, and if it is uppercase.
class Character {
public:
  YCM_EXPORT explicit Character( const std::string &character );
  // Make class noncopyable
  Character( const Character& ) = delete;
  Character& operator=( const Character& ) = delete;

  inline std::string Normal() const {
    return normal_;
  }

  inline std::string Base() const {
    return base_;
  }

  inline std::string FoldedCase() const {
    return folded_case_;
  }

  inline std::string SwappedCase() const {
    return swapped_case_;
  }

  inline bool IsBase() const {
    return is_base_;
  }

  inline bool IsLetter() const {
    return is_letter_;
  }

  inline bool IsPunctuation() const {
    return is_punctuation_;
  }

  inline bool IsUppercase() const {
    return is_uppercase_;
  }

  inline bool operator== ( const Character &other ) const {
    return normal_ == other.normal_;
  };

  inline bool EqualsBase( const Character &other ) const {
    return base_ == other.base_;
  }

  inline bool EqualsIgnoreCase( const Character &other ) const {
    return folded_case_ == other.folded_case_;
  };

  // Smart base matching on top of smart case matching, e.g.:
  //  - e matches e, é, E, É;
  //  - E matches E, É but not e, é;
  //  - é matches é, É but not e, E;
  //  - É matches É but not e, é, E.
  inline bool MatchesSmart( const Character &other ) const {
    return ( is_base_ && EqualsBase( other ) &&
             ( !is_uppercase_ || other.is_uppercase_ ) ) ||
           ( !is_uppercase_ && EqualsIgnoreCase( other ) ) ||
           normal_ == other.normal_;
  };

private:
  std::string normal_;
  std::string base_;
  std::string folded_case_;
  std::string swapped_case_;
  bool is_base_;
  bool is_letter_;
  bool is_punctuation_;
  bool is_uppercase_;
};


using CharacterSequence = std::vector< const Character * >;

} // namespace YouCompleteMe

#endif /* end of include guard: CHARACTER_H_YTIET2HZ */
