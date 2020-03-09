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

namespace YouCompleteMe {

namespace fs = boost::filesystem;

namespace {

// Only used as the equality comparer for the below unordered_map which stores
// const char* pointers and not std::string but needs to hash based on string
// values and not pointer values.
// When passed a const char* this will create a temporary std::string for
// comparison, but it's fast enough for our use case.
struct StringEqualityComparer {
  bool operator()( const std::string &a, const std::string &b ) const {
    return a == b;
  }
};

// List of languages Universal Ctags supports:
//   ctags --list-languages
// To map a language name to a filetype, see this file:
//   :e $VIMRUNTIME/filetype.vim
// This is a map of const char* and not std::string to prevent issues with
// static initialization.
const std::unordered_map < const char *,
      const char *,
      std::hash< std::string >,
      StringEqualityComparer > LANG_TO_FILETYPE = {
        { "Ada"                 , "ada"                 },
        { "AnsiblePlaybook"     , "ansibleplaybook"     },
        { "Ant"                 , "ant"                 },
        { "Asm"                 , "asm"                 },
        { "Asp"                 , "asp"                 },
        { "Autoconf"            , "autoconf"            },
        { "Automake"            , "automake"            },
        { "Awk"                 , "awk"                 },
        { "Basic"               , "basic"               },
        { "BETA"                , "beta"                },
        { "C"                   , "c"                   },
        { "C#"                  , "cs"                  },
        { "C++"                 , "cpp"                 },
        { "Clojure"             , "clojure"             },
        { "Cobol"               , "cobol"               },
        { "CPreProcessor"       , "cpreprocessor"       },
        { "CSS"                 , "css"                 },
        { "ctags"               , "ctags"               },
        { "CUDA"                , "cuda"                },
        { "D"                   , "d"                   },
        { "DBusIntrospect"      , "dbusintrospect"      },
        { "Diff"                , "diff"                },
        { "DosBatch"            , "dosbatch"            },
        { "DTD"                 , "dtd"                 },
        { "DTS"                 , "dts"                 },
        { "Eiffel"              , "eiffel"              },
        { "elm"                 , "elm"                 },
        { "Erlang"              , "erlang"              },
        { "Falcon"              , "falcon"              },
        { "Flex"                , "flex"                },
        { "Fortran"             , "fortran"             },
        { "gdbinit"             , "gdb"                 },
        { "Glade"               , "glade"               },
        { "Go"                  , "go"                  },
        { "HTML"                , "html"                },
        { "Iniconf"             , "iniconf"             },
        { "ITcl"                , "itcl"                },
        { "Java"                , "java"                },
        { "JavaProperties"      , "jproperties"         },
        { "JavaScript"          , "javascript"          },
        { "JSON"                , "json"                },
        { "LdScript"            , "ldscript"            },
        { "Lisp"                , "lisp"                },
        { "Lua"                 , "lua"                 },
        { "M4"                  , "m4"                  },
        { "Make"                , "make"                },
        { "man"                 , "man"                 },
        { "MatLab"              , "matlab"              },
        { "Maven2"              , "maven2"              },
        { "Myrddin"             , "myrddin"             },
        { "ObjectiveC"          , "objc"                },
        { "OCaml"               , "ocaml"               },
        { "Pascal"              , "pascal"              },
        { "passwd"              , "passwd"              },
        { "Perl"                , "perl"                },
        { "Perl6"               , "perl6"               },
        { "PHP"                 , "php"                 },
        { "PlistXML"            , "plistxml"            },
        { "pod"                 , "pod"                 },
        { "Protobuf"            , "protobuf"            },
        { "PuppetManifest"      , "puppet"              },
        { "Python"              , "python"              },
        { "PythonLoggingConfig" , "pythonloggingconfig" },
        { "QemuHX"              , "qemuhx"              },
        { "R"                   , "r"                   },
        { "RelaxNG"             , "rng"                 },
        { "reStructuredText"    , "rst"                 },
        { "REXX"                , "rexx"                },
        { "Robot"               , "robot"               },
        { "RpmSpec"             , "spec"                },
        { "RSpec"               , "rspec"               },
        { "Ruby"                , "ruby"                },
        { "Rust"                , "rust"                },
        { "Scheme"              , "scheme"              },
        { "Sh"                  , "sh"                  },
        { "SLang"               , "slang"               },
        { "SML"                 , "sml"                 },
        { "SQL"                 , "sql"                 },
        { "SVG"                 , "svg"                 },
        { "SystemdUnit"         , "systemd"             },
        { "SystemVerilog"       , "systemverilog"       },
        { "Tcl"                 , "tcl"                 },
        { "TclOO"               , "tcloo"               },
        { "Tex"                 , "tex"                 },
        { "TTCN"                , "ttcn"                },
        { "Vera"                , "vera"                },
        { "Verilog"             , "verilog"             },
        { "VHDL"                , "vhdl"                },
        { "Vim"                 , "vim"                 },
        { "WindRes"             , "windres"             },
        { "XSLT"                , "xslt"                },
        { "YACC"                , "yacc"                },
        { "Yaml"                , "yaml"                },
        { "YumRepo"             , "yumrepo"             },
        { "Zephir"              , "zephir"              }
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

  for (auto&& line : lines) {
    // Identifier name is from the start of the line to the first \t.
    const size_t id_end = line.find( '\t' );
    if ( id_end == std::string::npos ) {
      continue;
    }
    // File path the identifier is in is the second field.
    const size_t path_begin = line.find_first_not_of( '\t', id_end + 1 );
    if ( path_begin == std::string::npos ) {
      continue;
    }
    const size_t path_end = line.find( '\t', path_begin + 1 );
    if ( path_end == std::string::npos ) {
      continue;
    }
    // IdentifierCompleter depends on the "language:Foo" field.
    // strlen( "language:" ) == 9
    const size_t lang_begin = line.find( "language:", path_end + 1 ) + 9;
    if ( lang_begin == std::string::npos + 9 ) {
      continue;
    }
    const size_t lang_end = [ &line, lang_begin ] {
      auto end = line.find( '\t', lang_begin + 1 );
      if (end == std::string::npos) {
        end = line.back() == '\r' ? line.size() - 1 : line.size();
      }
      return end;
    }();
    auto identifier = line.substr( 0, id_end );
    fs::path path( line.substr( path_begin, path_end - path_begin ) );
    path = NormalizePath( path, path_to_tag_file.parent_path() );
    const auto language = line.substr( lang_begin, lang_end - lang_begin );
    std::string filetype = FindWithDefault( LANG_TO_FILETYPE,
                                            language.c_str(),
                                            Lowercase( language ).c_str() );
    filetype_identifier_map[ std::move( filetype ) ][ path.string() ]
      .push_back( std::move( identifier ) );
  }
  return filetype_identifier_map;
}

} // namespace YouCompleteMe
