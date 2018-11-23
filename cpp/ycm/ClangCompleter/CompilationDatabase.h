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

#ifndef COMPILATIONDATABASE_H_ZT7MQXPG
#define COMPILATIONDATABASE_H_ZT7MQXPG

#include <clang-c/CXCompilationDatabase.h>
#include <mutex>
#include <pybind11/pybind11.h>
#include <string>
#include <vector>

namespace YouCompleteMe {

struct CompilationInfoForFile {
  std::vector< std::string > compiler_flags_;
  std::string compiler_working_dir_;
};


// Access to Clang's internal CompilationDatabase. This class is thread-safe.
class CompilationDatabase {
public:
  // |path_to_directory| should be a string-like object.
  explicit CompilationDatabase( const pybind11::object &path_to_directory );
  CompilationDatabase( const CompilationDatabase& ) = delete;
  CompilationDatabase& operator=( const CompilationDatabase& ) = delete;
  ~CompilationDatabase();

  bool DatabaseSuccessfullyLoaded();

  // Returns true when a separate thread is already getting flags; this is
  // useful so that the caller doesn't need to block.
  bool AlreadyGettingFlags();

  // NOTE: Multiple calls to this function from separate threads will be
  // serialized since Clang internals are not thread-safe.
  // |path_to_file| should be a string-like object.
  CompilationInfoForFile GetCompilationInfoForFile(
    const pybind11::object &path_to_file );

  std::string GetDatabaseDirectory() {
    return path_to_directory_;
  }

private:

  bool is_loaded_;
  std::string path_to_directory_;
  CXCompilationDatabase compilation_database_;
  std::mutex compilation_database_mutex_;
};

} // namespace YouCompleteMe

#endif /* end of include guard: COMPILATIONDATABASE_H_ZT7MQXPG */
