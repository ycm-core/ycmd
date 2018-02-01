// Copyright (C) 2011, 2012, 2013 Google Inc.
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

#ifndef PYTHONSUPPORT_H_KWGFEX0V
#define PYTHONSUPPORT_H_KWGFEX0V

#include <boost/python.hpp>

namespace YouCompleteMe {

/// Given a list of python objects (that represent completion candidates) in a
/// python list |candidates|, a |candidate_property| on which to filter and sort
/// the candidates and a user query, returns a new sorted python list with the
/// original objects that survived the filtering. This list contains at most
/// |max_candidates|. If |max_candidates| is omitted or 0, all candidates are
/// sorted.
YCM_EXPORT boost::python::list FilterAndSortCandidates(
  const boost::python::list &candidates,
  const std::string &candidate_property,
  const std::string &query,
  const size_t max_candidates = 0 );

/// Given a Python object that's supposed to be "string-like", returns a UTF-8
/// encoded std::string. Raises an exception if the object can't be converted to
/// a string. Supports newstr and newbytes from python-future on Python 2.
std::string GetUtf8String( const boost::python::object &value );

/// Expose the C++ exception |CppException| as a Python exception inheriting
/// from the base exception |base_exception| (default being Exception) with the
/// fully qualified name <module>.|name| where <module> is the current
/// Boost.Python module. |CppException| must define a what() method (easiest way
/// is to derive it from std::runtime_error). This templated class should be
/// instantiated inside the BOOST_PYTHON_MODULE macro.
template< typename CppException >
class PythonException {
public:

  PythonException( const char* name,
                   PyObject* base_exception = PyExc_Exception ) {
    std::string module_name = boost::python::extract< std::string >(
        boost::python::scope().attr( "__name__" ) );
    std::string fully_qualified_name = module_name + "." + name;
    // PyErr_NewException does not modify the exception name so it's safe to
    // cast away constness.
    char *raw_name = const_cast< char * >( fully_qualified_name.c_str() );
    python_exception_ = PyErr_NewException( raw_name, base_exception, NULL );

    // Add the Python exception to the current Boost.Python module.
    boost::python::scope().attr( name ) = boost::python::handle<>(
      python_exception_ );

    boost::python::register_exception_translator< CppException >( *this );
  };

  void operator() ( const CppException &cpp_exception ) const {
    PyErr_SetString( python_exception_, cpp_exception.what() );
  }

private:
  PyObject* python_exception_;

};

} // namespace YouCompleteMe

#endif /* end of include guard: PYTHONSUPPORT_H_KWGFEX0V */

