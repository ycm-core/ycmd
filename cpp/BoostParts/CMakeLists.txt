# Copyright (C) 2011, 2012  Google Inc.
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

# The interesting parts of Boost have been extracted using
# the BCP tool:
#   http://www.boost.org/doc/libs/1_54_0/tools/bcp/doc/html/index.html
#
# See the top-level update_boost.sh script for details on how bcp is called to
# generate BoostParts.

cmake_minimum_required( VERSION 2.8 )

project( BoostParts )

file( GLOB_RECURSE SOURCES *.cpp )

#############################################################################

include_directories(
  SYSTEM
  ${CMAKE_CURRENT_SOURCE_DIR}
  ${PYTHON_INCLUDE_DIRS}
  )

add_library( BoostParts STATIC ${SOURCES} )

#############################################################################

# No warnings. We just use Boost as is so warnings coming from it are just
# noise.
if( CMAKE_COMPILER_IS_GNUCXX OR COMPILER_IS_CLANG )
  set( CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -w" )
elseif( MSVC )
  add_definitions( /W0 -D_SCL_SECURE_NO_WARNINGS )
endif()

#############################################################################

if( NOT WIN32 )
  # Linking fails without this on some platforms, notably anything x64.
  set_target_properties( BoostParts PROPERTIES COMPILE_FLAGS "-fPIC")
endif()

#############################################################################

# Special compiler and linker flags for MSVC
if( MSVC )
  set( CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} /Oi /GL" )
  set_target_properties( ${PROJECT_NAME} PROPERTIES STATIC_LIBRARY_FLAGS "/LTCG" )
endif()

if( SYSTEM_IS_SUNOS )
  # SunOS needs this setting for thread support
  set( CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -pthreads" )
endif()
