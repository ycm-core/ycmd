# Copyright (C) 2017 ycmd contributors
#
# This file is part of ycmd.
#
# ycmd is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ycmd is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ycmd.  If not, see <http://www.gnu.org/licenses/>.

project( ycm_core_benchmarks )
cmake_minimum_required( VERSION 3.14 )

# We don't want to test the benchmark library.
set( BENCHMARK_ENABLE_TESTING
     OFF CACHE BOOL "Enable testing of the benchmark library" )
set( BUILD_SHARED_LIBS OFF )

if ( USE_SYSTEM_BENCHMARK )
  find_package( benchmark REQUIRED )
else()
  include( FetchContent )
  FetchContent_Declare(
    benchmark
    GIT_REPOSITORY https://github.com/google/benchmark
    GIT_TAG 3b19d7222db7babfdc9b3949408b2294c3bbb540
    SOURCE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/benchmark
  )
  FetchContent_MakeAvailable( benchmark )
endif()

file( GLOB SOURCES *.h *.cpp )

add_executable( ${PROJECT_NAME} ${SOURCES} )

if( MSVC )
  # Build benchmark and ycm_core_benchmarks targets in cmake ycm/benchmarks
  # folder.
  foreach( OUTPUTCONFIG ${CMAKE_CONFIGURATION_TYPES} )
    # Can't use benchmark::benchmark ALIAS target here
    foreach( TARGET_LIBRARY benchmark ${PROJECT_NAME} )
      string( TOUPPER ${OUTPUTCONFIG} OUTPUTCONFIG )
      set_target_properties( ${TARGET_LIBRARY} PROPERTIES
        RUNTIME_OUTPUT_DIRECTORY_${OUTPUTCONFIG} ${PROJECT_BINARY_DIR} )
    endforeach()
  endforeach()
endif()

target_link_libraries( ${PROJECT_NAME}
                       PRIVATE ycm_core
                       PRIVATE benchmark::benchmark )
