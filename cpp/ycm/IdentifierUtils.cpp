// Copyright (C) 2011, 2012 Google Inc.
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

#include "IdentifierUtils.h"
#include "Utils.h"

#include <array>
#include <filesystem>
#include <functional>
#include <string_view>
#include <utility>

namespace YouCompleteMe {

namespace fs = std::filesystem;

namespace {

// List of languages Universal Ctags supports:
//   ctags --list-languages
// To map a language name to a filetype, see this file:
//   :e $VIMRUNTIME/filetype.vim
using namespace std::literals;
constexpr std::array LANG_TO_FILETYPE = {
  std::pair{ "C#"sv               , "cs"sv          },
  std::pair{ "C++"sv              , "cpp"sv         },
  std::pair{ "gdbinit"sv          , "gdb"sv         },
  std::pair{ "JavaProperties"sv   , "jproperties"sv },
  std::pair{ "ObjectiveC"sv       , "objc"sv        },
  std::pair{ "PuppetManifest"sv   , "puppet"sv      },
  std::pair{ "RelaxNG"sv          , "rng"sv         },
  std::pair{ "reStructuredText"sv , "rst"sv         },
  std::pair{ "RpmSpec"sv          , "spec"sv        },
  std::pair{ "SystemdUnit"sv      , "systemd"sv     },
};

}  // unnamed namespace


// For details on the tag format supported, see here for details:
// http://ctags.sourceforge.net/FORMAT
// TL;DR: The only supported format is the one Exuberant Ctags emits.
FiletypeIdentifierMap ExtractIdentifiersFromTagsFile(
  const fs::path &path_to_tag_file ) {
  FiletypeIdentifierMap filetype_identifier_map;
  const auto lines = [ &path_to_tag_file ]{
    try {
      return ReadUtf8File( path_to_tag_file );
    } catch ( ... ) {
      return std::vector< std::string >{};
    }
  }();

  for ( auto&& line : lines ) {
    // Identifier name is from the start of the line to the first \t.
    const auto id_end = std::find( line.cbegin(), line.cend(), '\t' );
    if ( id_end == line.cend() ) {
      continue;
    }
    // File path the identifier is in is the second field.
    const auto path_begin = std::find_if( id_end + 1, line.cend(), [](char c) {
      return c != '\t';
    } );
    if ( path_begin == line.cend() ) {
      continue;
    }
    const auto path_end = std::find( path_begin + 1, line.cend(), '\t' );
    if ( path_end == line.cend() ) {
      continue;
    }
    // IdentifierCompleter depends on the "language:Foo" field.
    const std::string_view lang_str = "language:";
    auto searcher = std::default_searcher( lang_str.cbegin(), lang_str.cend() );
    const auto lang_begin = searcher( path_end + 1, line.cend() ).second;
    if ( lang_begin == line.cend() ) {
      continue;
    }
    const auto lang_end = [ &line, lang_begin ] {
      auto end = std::find( lang_begin + 1, line.cend(), '\t' );
      if (end == line.cend() ) {
        end = line.back() == '\r' ? line.cend() - 1 : line.cend();
      }
      return end;
    }();
    std::string_view identifier( line.data(), id_end - line.cbegin() );
    fs::path path( path_begin, path_end );
    path = fs::weakly_canonical( path_to_tag_file.parent_path() / path );
    std::string_view language( &*lang_begin, lang_end - lang_begin );
    std::string filetype( FindWithDefault( LANG_TO_FILETYPE,
                                           language,
                                           Lowercase( language ) ) );
    filetype_identifier_map[ std::move( filetype ) ]
                           [ std::move( path ).string() ]
      .emplace_back( identifier );
  }
  return filetype_identifier_map;
}

} // namespace YouCompleteMe
