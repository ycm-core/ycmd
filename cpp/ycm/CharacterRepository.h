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

#ifndef CHARACTER_REPOSITORY_H_36TXTS6C
#define CHARACTER_REPOSITORY_H_36TXTS6C

#include "Character.h"

#include <memory>
#include <mutex>
#include <string>
#include <unordered_map>
#include <vector>

namespace YouCompleteMe {

using CharacterHolder = std::unordered_map< std::string,
                                            std::unique_ptr< Character > >;


// This singleton stores already built Character objects for character strings
// that were already seen. If Characters are requested for previously unseen
// strings, new Character objects are built.
//
// This class is thread-safe.
class CharacterRepository {
public:
  YCM_EXPORT static CharacterRepository &Instance();
  // Make class noncopyable
  CharacterRepository( const CharacterRepository& ) = delete;
  CharacterRepository& operator=( const CharacterRepository& ) = delete;

  YCM_EXPORT size_t NumStoredCharacters();

  YCM_EXPORT CharacterSequence GetCharacters(
    const std::vector< std::string > &characters );

  // This should only be used to isolate tests and benchmarks.
  YCM_EXPORT void ClearCharacters();

private:
  CharacterRepository() = default;
  ~CharacterRepository() = default;

  // This data structure owns all the Character pointers
  CharacterHolder character_holder_;
  std::mutex character_holder_mutex_;
};

} // namespace YouCompleteMe

#endif /* end of include guard: CHARACTER_REPOSITORY_H_36TXTS6C */
