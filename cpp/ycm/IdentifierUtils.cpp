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

#include <boost/algorithm/string/regex.hpp>
#include <boost/regex.hpp>
#include <unordered_map>

namespace YouCompleteMe {

namespace fs = boost::filesystem;

namespace {

// For details on the tag format supported, see here for details:
// http://ctags.sourceforge.net/FORMAT
// TL;DR: The only supported format is the one Exuberant Ctags emits.
const char *const TAG_REGEX =
  "^([^\\t\\n\\r]+)"  // The first field is the identifier
  "\\t"  // A TAB char is the field separator
  // The second field is the path to the file that has the identifier; either
  // absolute or relative to the tags file.
  "([^\\t\\n\\r]+)"
  "\\t.*?"  // Non-greedy everything
  "language:([^\\t\\n\\r]+)"  // We want to capture the language of the file
  ".*?$";

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


FiletypeIdentifierMap ExtractIdentifiersFromTagsFile(
  const fs::path &path_to_tag_file ) {
  FiletypeIdentifierMap filetype_identifier_map;
  std::string tags_file_contents;

  try {
    tags_file_contents = ReadUtf8File( path_to_tag_file );
  } catch ( ... ) {
    return filetype_identifier_map;
  }

  std::string::const_iterator start = tags_file_contents.begin();
  std::string::const_iterator end   = tags_file_contents.end();

  boost::smatch matches;
  const boost::regex expression( TAG_REGEX );
  const boost::match_flag_type options = boost::match_not_dot_newline;

  while ( boost::regex_search( start, end, matches, expression, options ) ) {
    start = matches[ 0 ].second;

    std::string language( matches[ 3 ] );
    std::string filetype = FindWithDefault( LANG_TO_FILETYPE,
                                            language.c_str(),
                                            Lowercase( language ).c_str() );

    std::string identifier( matches[ 1 ] );
    fs::path path( matches[ 2 ].str() );
    path = NormalizePath( path, path_to_tag_file.parent_path() );

    filetype_identifier_map[ filetype ][ path.string() ].push_back( identifier );
  }

  return filetype_identifier_map;
}

} // namespace YouCompleteMe
