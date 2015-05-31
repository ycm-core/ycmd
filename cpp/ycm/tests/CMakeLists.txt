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
cmake_minimum_required( VERSION 2.8 )

# The gtest library triggers these warnings, so we turn them off; it's not up to
# us to fix gtest warnings, it's up to upstream.
if ( COMPILER_IS_CLANG )
  set( CMAKE_CXX_FLAGS
    "${CMAKE_CXX_FLAGS} -Wno-long-long -Wno-variadic-macros -Wno-missing-field-initializers -Wno-unused-private-field -Wno-c++98-compat" )
endif()


option( USE_SYSTEM_GMOCK "Set to ON to use the system gmock/gtest libraries" OFF )

if ( USE_SYSTEM_GMOCK )
  set( CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake;${CMAKE_MODULE_PATH}" )
  find_package( GTest REQUIRED )
  find_package( GMock REQUIRED )
else()
  if ( WIN32 )
    # Override BUILD_SHARED_LIBS option in gmock and gtest CMakeLists
    set( BUILD_SHARED_LIBS ON CACHE BOOL "Build shared libraries (DLLs)." )
  endif()

  add_subdirectory( gmock )
  set( GTEST_INCLUDE_DIRS ${gtest_SOURCE_DIR} ${gtest_SOURCE_DIR}/include )
  set( GMOCK_INCLUDE_DIRS ${gmock_SOURCE_DIR} ${gmock_SOURCE_DIR}/include )
  set( GTEST_LIBRARIES "" )
  set( GMOCK_LIBRARIES gmock )
endif()

include_directories(
  ${ycm_support_libs_SOURCE_DIR}
  )

include_directories(
  SYSTEM
  ${GMOCK_INCLUDE_DIRS}
  ${GTEST_INCLUDE_DIRS}
  )

link_directories(
  ${Boost_LIBRARY_DIRS}
  ${PYTHON_LIBRARIES}
  )

file( GLOB_RECURSE SOURCES *.h *.cpp )

# We don't want gmock sources in this target
file( GLOB_RECURSE to_remove gmock/*.h gmock/*.cpp CMakeFiles/*.cpp
  testdata/*.cpp testdata/*.h )

if( to_remove )
  list( REMOVE_ITEM SOURCES ${to_remove} )
endif()

if ( NOT USE_CLANG_COMPLETER )
  file( GLOB_RECURSE to_remove_clang ClangCompleter/*.h ClangCompleter/*.cpp )

  if( to_remove_clang )
    list( REMOVE_ITEM SOURCES ${to_remove_clang} )
  endif()
endif()

add_executable( ${PROJECT_NAME}
                ${SOURCES}
              )

if ( MSVC )
  # This is needed to compile tests with the gtest shared library
  set_target_properties( ${PROJECT_NAME}
                         PROPERTIES
                         COMPILE_DEFINITIONS
                         "GTEST_LINKED_AS_SHARED_LIBRARY=1" )

  # Fix gtest build on MSVC 11.  See: http://stackoverflow.com/a/8274747
  if ( MSVC_VERSION EQUAL 1700 )
    add_definitions( /D _VARIADIC_MAX=10 )
  endif()

  # Build gmock and ycm_core_tests targets in cmake ycm/tests folder
  foreach( OUTPUTCONFIG ${CMAKE_CONFIGURATION_TYPES} )
    string( TOUPPER ${OUTPUTCONFIG} OUTPUTCONFIG )
    set_target_properties( ${GMOCK_LIBRARIES} PROPERTIES
      RUNTIME_OUTPUT_DIRECTORY_${OUTPUTCONFIG} ${PROJECT_BINARY_DIR} )
    set_target_properties( ${PROJECT_NAME} PROPERTIES
      RUNTIME_OUTPUT_DIRECTORY_${OUTPUTCONFIG} ${PROJECT_BINARY_DIR} )
  endforeach()
endif()

target_link_libraries( ${PROJECT_NAME}
                       ${Boost_LIBRARIES}
                       ${SERVER_LIB}
                       ${CLIENT_LIB}
                       ${GTEST_LIBRARIES}
                       ${GMOCK_LIBRARIES} )

if ( NOT CMAKE_GENERATOR_IS_XCODE )
  # The test executable expects a "testdata" dir in its working directory. Why?
  # Because there's NO reliable, cross-platform way of getting the directory in
  # which the executable is located.
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
