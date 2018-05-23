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

#include "CharacterRepository.h"
#include "Character.h"
#include "Utils.h"

#include <mutex>

namespace YouCompleteMe {

CharacterRepository &CharacterRepository::Instance() {
  static CharacterRepository repo;
  return repo;
}


size_t CharacterRepository::NumStoredCharacters() {
  std::lock_guard< std::mutex > locker( character_holder_mutex_ );
  return character_holder_.size();
}


CharacterSequence CharacterRepository::GetCharacters(
  const std::vector< std::string > &characters ) {
  CharacterSequence character_objects;
  character_objects.reserve( characters.size() );

  {
    std::lock_guard< std::mutex > locker( character_holder_mutex_ );

    for ( const std::string & character : characters ) {
      std::unique_ptr< Character > &character_object = GetValueElseInsert(
                                                         character_holder_,
                                                         character,
                                                         nullptr );

      if ( !character_object ) {
        character_object.reset( new Character( character ) );
      }

      character_objects.push_back( character_object.get() );
    }
  }

  return character_objects;
}


void CharacterRepository::ClearCharacters() {
  character_holder_.clear();
}


} // namespace YouCompleteMe
