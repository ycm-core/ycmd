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

#include "Candidate.h"
#include "CodePoint.h"
#include "IdentifierCompleter.h"
#include "PythonSupport.h"
#include "versioning.h"

#ifdef USE_CLANG_COMPLETER
#  include "ClangCompleter.h"
#  include "ClangUtils.h"
#  include "CompilationDatabase.h"
#  include "CompletionData.h"
#  include "Diagnostic.h"
#  include "Documentation.h"
#  include "Location.h"
#  include "Range.h"
#  include "UnsavedFile.h"
#endif // USE_CLANG_COMPLETER

#include <pymetabind/bind.hpp>

namespace py = pybind11;
using namespace YouCompleteMe;

[[=pymetabind::utils::make_binding()]] static bool HasClangSupport() {
#ifdef USE_CLANG_COMPLETER
  return true;
#else
  return false;
#endif // USE_CLANG_COMPLETER
}

PYBIND11_MAKE_OPAQUE( std::vector< std::string > )
#ifdef USE_CLANG_COMPLETER
PYBIND11_MAKE_OPAQUE( std::vector< UnsavedFile > )
PYBIND11_MAKE_OPAQUE( std::vector< Range > )
PYBIND11_MAKE_OPAQUE( std::vector< CompletionData > )
PYBIND11_MAKE_OPAQUE( std::vector< Diagnostic > )
PYBIND11_MAKE_OPAQUE( std::vector< FixIt > )
PYBIND11_MAKE_OPAQUE( std::vector< FixItChunk > )
#endif // USE_CLANG_COMPLETER

PYBIND11_MODULE( ycm_core, mod )
{
  py::bind_vector< std::vector< std::string > >( mod, "StringVector" );

#ifdef USE_CLANG_COMPLETER
  pymetabind::bind::bind_enum<^^CXCursorKind>(mod);
#endif

  pymetabind::bind::bind_namespace<^^YouCompleteMe>(mod);

  // This is exposed so that we can test it.
  mod.def( "GetUtf8String", []( py::object o ) -> py::bytes {
                                  return GetUtf8String( o ); } );


#ifdef USE_CLANG_COMPLETER
  // Alternative for the FixIt faffing:
  //
  // 1. Do not anotate `struct FixIt` with `make_class()`.
  // 2. Rewrite the bindings
  //
  // ```c++
  // bind_class<^^FixIt>(mod)
  //     .def("kind", [](const py::handle) {
  //         return py::none();
  //     });
  // ```
  // Note that order of bindings matters when pybind11 generates docstrings.
  using pu_fixit_type = pymetabind::utils::py_class_type<FixIt>;
  auto py_fixit_generic = mod.attr("FixIt");
  auto pu_fixit = py::cast<pu_fixit_type>(py_fixit_generic);
  py_fixit.def_property_readonly( "kind", [](const py::handle) {
      return py::none();
    });

#endif // USE_CLANG_COMPLETER
}
