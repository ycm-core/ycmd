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

#include "CompilationDatabase.h"
#include "ClangUtils.h"
#include "PythonSupport.h"

#include <memory>

using std::lock_guard;
using std::unique_lock;
using std::try_to_lock_t;
using std::remove_pointer;
using std::shared_ptr;
using std::mutex;

namespace YouCompleteMe {

using CompileCommandsWrap =
  shared_ptr< remove_pointer< CXCompileCommands >::type >;


CompilationDatabase::CompilationDatabase(
  const pybind11::object &path_to_directory )
  : is_loaded_( false ),
    path_to_directory_( GetUtf8String( path_to_directory ) ) {
  CXCompilationDatabase_Error status;
  compilation_database_ = clang_CompilationDatabase_fromDirectory(
                            path_to_directory_.c_str(),
                            &status );
  is_loaded_ = status == CXCompilationDatabase_NoError;
}


CompilationDatabase::~CompilationDatabase() {
  clang_CompilationDatabase_dispose( compilation_database_ );
}


bool CompilationDatabase::DatabaseSuccessfullyLoaded() {
  return is_loaded_;
}


bool CompilationDatabase::AlreadyGettingFlags() {
  unique_lock< mutex > lock( compilation_database_mutex_, try_to_lock_t() );
  return !lock.owns_lock();
}


CompilationInfoForFile CompilationDatabase::GetCompilationInfoForFile(
  const pybind11::object &path_to_file ) {
  CompilationInfoForFile info;

  if ( !is_loaded_ ) {
    return info;
  }

  std::string path_to_file_string = GetUtf8String( path_to_file );
  pybind11::gil_scoped_release unlock;

  lock_guard< mutex > lock( compilation_database_mutex_ );

  CompileCommandsWrap commands(
    clang_CompilationDatabase_getCompileCommands(
      compilation_database_,
      path_to_file_string.c_str() ), clang_CompileCommands_dispose );

  size_t num_commands = clang_CompileCommands_getSize( commands.get() );

  if ( num_commands < 1 ) {
    return info;
  }

  // We always pick the first command offered
  CXCompileCommand command = clang_CompileCommands_getCommand(
                               commands.get(),
                               0 );

  info.compiler_working_dir_ = CXStringToString(
                                 clang_CompileCommand_getDirectory( command ) );

  size_t num_flags = clang_CompileCommand_getNumArgs( command );
  info.compiler_flags_.reserve( num_flags );

  for ( size_t i = 0; i < num_flags; ++i ) {
    info.compiler_flags_.push_back(
      CXStringToString( clang_CompileCommand_getArg( command, i ) ) );
  }

  return info;
}

} // namespace YouCompleteMe

