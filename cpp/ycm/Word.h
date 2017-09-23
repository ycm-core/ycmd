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

#ifndef WORD_H_UOHAUKVQ
#define WORD_H_UOHAUKVQ

#include "Character.h"

#include <bitset>
#include <string>
#include <vector>

#define NUM_BYTES 256

namespace YouCompleteMe {

using Bitset = std::bitset< NUM_BYTES >;


// This class represents a sequence of UTF-8 characters. It takes a UTF-8
// encoded string and splits that string into characters following the rules in
// https://www.unicode.org/reports/tr29/#Grapheme_Cluster_Boundary_Rules
class Word {
public:
  YCM_EXPORT explicit Word( const std::string &text );
  // Make class noncopyable
  Word( const Word& ) = delete;
  Word& operator=( const Word& ) = delete;
  ~Word() = default;

  inline const CharacterSequence &Characters() const {
    return characters_;
  }

  inline const std::string &Text() const {
    return text_;
  }

  inline size_t Length() const {
    return characters_.size();
  }

  // Returns true if the word contains the bytes from another word (it may also
  // contain other bytes).
  inline bool ContainsBytes( const Word &other ) const {
    return ( bytes_present_ & other.bytes_present_ ) == other.bytes_present_;
  }

  inline bool IsEmpty() const {
    return characters_.empty();
  }

private:
  void BreakIntoCharacters();
  void ComputeBytesPresent();

  std::string text_;
  CharacterSequence characters_;
  Bitset bytes_present_;
};

} // namespace YouCompleteMe

#endif /* end of include guard: WORD_H_UOHAUKVQ */
