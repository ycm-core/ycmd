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

#include <unordered_map>
#include <regex>

namespace YouCompleteMe {

namespace fs = boost::filesystem;

namespace {

// For details on the tag format supported, see here for details:
// http://ctags.sourceforge.net/FORMAT
// TL;DR: The only supported format is the one Exuberant Ctags emits.
const char *const TAG_REGEX =
  "^([^\\t]+)"  // The first field is the identifier
  "\\t"  // A TAB char is the field separator
  // The second field is the path to the file that has the identifier; either
  // absolute or relative to the tags file.
  "([^\\t]+)"
  "\\t.*"
  "language:([^\\t]+)"  // We want to capture the language of the file
  ".*$";

// Only used as the equality comparer for the below unordered_map which stores
// const char* pointers and not std::string but needs to hash based on string
// values and not pointer values.
// When passed a const char* this will create a temporary std::string for
// comparison, but it's fast enough for our use case.
struct StringEqualityComparer :
    std::binary_function< std::string, std::string, bool > {
  bool operator()( const std::string &a, const std::string &b ) const {
    return a == b;
  }
};

// List of languages Exuberant Ctags supports:
//   ctags --list-languages
// To map a language name to a filetype, see this file:
//   :e $VIMRUNTIME/filetype.vim
// This is a map of const char* and not std::string to prevent issues with
// static initialization.
const std::unordered_map < const char *,
      const char *,
      std::hash< std::string >,
      StringEqualityComparer > LANG_TO_FILETYPE = {
        { "Ant"        , "ant"        },
        { "Asm"        , "asm"        },
        { "Awk"        , "awk"        },
        { "Basic"      , "basic"      },
        { "C++"        , "cpp"        },
        { "C#"         , "cs"         },
        { "C"          , "c"          },
        { "COBOL"      , "cobol"      },
        { "DosBatch"   , "dosbatch"   },
        { "Eiffel"     , "eiffel"     },
        { "Elixir"     , "elixir"     },
        { "Erlang"     , "erlang"     },
        { "Fortran"    , "fortran"    },
        { "Go"         , "go"         },
        { "Haskell"    , "haskell"    },
        { "HTML"       , "html"       },
        { "Java"       , "java"       },
        { "JavaScript" , "javascript" },
        { "Lisp"       , "lisp"       },
        { "Lua"        , "lua"        },
        { "Make"       , "make"       },
        { "MatLab"     , "matlab"     },
        { "OCaml"      , "ocaml"      },
        { "Pascal"     , "pascal"     },
        { "Perl"       , "perl"       },
        { "PHP"        , "php"        },
        { "Python"     , "python"     },
        { "REXX"       , "rexx"       },
        { "Ruby"       , "ruby"       },
        { "Scheme"     , "scheme"     },
        { "Sh"         , "sh"         },
        { "SLang"      , "slang"      },
        { "SML"        , "sml"        },
        { "SQL"        , "sql"        },
        { "Tcl"        , "tcl"        },
        { "Tex"        , "tex"        },
        { "Vera"       , "vera"       },
        { "Verilog"    , "verilog"    },
        { "VHDL"       , "vhdl"       },
        { "Vim"        , "vim"        },
        { "YACC"       , "yacc"       }
      };

const char *const NOT_FOUND = "YCMFOOBAR_NOT_FOUND";

}  // unnamed namespace


FiletypeIdentifierMap ExtractIdentifiersFromTagsFile(
  const fs::path &path_to_tag_file ) {
  std::vector< std::string > tags_file_contents;

  try {
    tags_file_contents = ReadUtf8File( path_to_tag_file );
  } catch ( ... ) {
    return {};
  }

  FiletypeIdentifierMap filetype_identifier_map;
  std::smatch matches;
  const std::regex expression( TAG_REGEX, std::regex::optimize );

  for ( const auto& line : tags_file_contents ) {
    if ( std::regex_search( line, matches, expression ) ) {
      const std::string language( matches[ 3 ] );
      const std::string filetype = FindWithDefault( LANG_TO_FILETYPE,
                                                    language.c_str(),
                                                    NOT_FOUND );
      if ( filetype == NOT_FOUND )
        continue;

      const std::string identifier( matches[ 1 ] );
      fs::path path( matches[ 2 ].str() );
      path = fs::absolute( path, path_to_tag_file.parent_path() )
              .make_preferred();

      filetype_identifier_map[ filetype ][ path.string() ]
              .emplace_back( std::move( identifier ) );
    }
  }

  return filetype_identifier_map;
}

} // namespace YouCompleteMe
