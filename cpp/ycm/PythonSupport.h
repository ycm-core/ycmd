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
/// original objects that survived the filtering.
boost::python::list FilterAndSortCandidates(
  const boost::python::list &candidates,
  const std::string &candidate_property,
  const std::string &query );

/// Given a Python object that's supposed to be "string-like", returns a UTF-8
/// encoded std::string. If the object can't be converted to a string, returns an
/// empty one.
std::string GetUtf8String( const boost::python::object &string_or_unicode );

} // namespace YouCompleteMe

#endif /* end of include guard: PYTHONSUPPORT_H_KWGFEX0V */

