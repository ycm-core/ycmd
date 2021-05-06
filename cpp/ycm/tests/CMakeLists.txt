# Copyright (C) 2011 Google Inc.
#
# This file is part of YouCompleteMe.
#
# YouCompleteMe is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# YouCompleteMe is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with YouCompleteMe.  If not, see <http://www.gnu.org/licenses/>.

project( ycm_core_tests )
cmake_minimum_required( VERSION 3.14 )

# The gtest library triggers warnings, so we turn them off; it's not up to us to
# fix gtest warnings, it's up to upstream.
if ( COMPILER_IS_CLANG )
  set( CMAKE_CXX_FLAGS
    "${CMAKE_CXX_FLAGS} -Wno-long-long -Wno-variadic-macros -Wno-missing-field-initializers -Wno-unused-private-field" )
elseif( MSVC )
  add_definitions( /W0 )
endif()


option( USE_SYSTEM_GMOCK "Set to ON to use the system gmock/gtest libraries" OFF )

if ( USE_SYSTEM_GMOCK )
  find_package( GTest REQUIRED )
else()
  if ( WIN32 )
    # Override BUILD_SHARED_LIBS option in gmock and gtest CMakeLists
    set( BUILD_SHARED_LIBS ON CACHE BOOL "Build shared libraries (DLLs)." )
  endif()

  include( FetchContent )
  FetchContent_Declare(
    gmock
    GIT_REPOSITORY https://github.com/google/googletest
    GIT_TAG f5e592d8ee5ffb1d9af5be7f715ce3576b8bf9c4
    SOURCE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/gmock
  )
  FetchContent_GetProperties( gmock )
  if ( NOT benchmark_POPULATED )
    FetchContent_Populate( gmock )
  endif()
  add_subdirectory( gmock )
endif()

file( GLOB SOURCES *.h *.cpp )

if ( USE_CLANG_COMPLETER )
  file( GLOB_RECURSE add_clang ClangCompleter/*.h ClangCompleter/*.cpp )

  if( add_clang )
    list( APPEND SOURCES ${add_clang} )
  endif()
endif()

add_executable( ${PROJECT_NAME} ${SOURCES} )

target_include_directories(
  ${PROJECT_NAME}
  SYSTEM
  PRIVATE ${ycm_core_SOURCE_DIR}/../whereami
  )

if ( MSVC )
  # Build ycm_core_tests and dependencies targets in cmake ycm/tests folder
  foreach( OUTPUTCONFIG ${CMAKE_CONFIGURATION_TYPES} )
    foreach( TARGET_LIBRARY gtest gmock ${PROJECT_NAME} )
      string( TOUPPER ${OUTPUTCONFIG} OUTPUTCONFIG )
      set_target_properties( ${TARGET_LIBRARY} PROPERTIES
        RUNTIME_OUTPUT_DIRECTORY_${OUTPUTCONFIG} ${PROJECT_BINARY_DIR} )
    endforeach()
  endforeach()
endif()

target_link_libraries( ${PROJECT_NAME}
                       PRIVATE ycm_core
                       PRIVATE gtest
                       PRIVATE gmock )

if ( NOT CMAKE_GENERATOR_IS_XCODE )
  # There is no portable way of discovering the absolute path of the executable,
  # but whereami library supports all OS's on which we run tests regularly plus
  # some *BSD flavours on top of that.
  add_custom_target( copy_testdata
                     COMMAND cmake -E copy_directory
                     ${CMAKE_CURRENT_SOURCE_DIR}/testdata
                     ${CMAKE_CURRENT_BINARY_DIR}/testdata )
else()
  add_custom_target( copy_testdata
                     COMMAND cmake -E copy_directory
                     ${CMAKE_CURRENT_SOURCE_DIR}/testdata
                     ${CMAKE_CURRENT_BINARY_DIR}/Debug/testdata
                     COMMAND cmake -E copy_directory
                     ${CMAKE_CURRENT_SOURCE_DIR}/testdata
                     ${CMAKE_CURRENT_BINARY_DIR}/Release/testdata )

endif()

add_dependencies( ${PROJECT_NAME} copy_testdata )
