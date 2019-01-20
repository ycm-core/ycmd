# Copyright (C) 2011-2018 ycmd contributors
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

if ( APPLE )
  # OSX requires CMake >= 2.8.12, see YCM issue #1439
  cmake_minimum_required( VERSION 2.8.12 )
else()
  # CMake 2.8.11 is the latest available version on RHEL/CentOS 7
  cmake_minimum_required( VERSION 2.8.11 )
endif()

project( YouCompleteMe )

# Get the core version
file( STRINGS "../CORE_VERSION" YCMD_CORE_VERSION )
add_definitions( -DYCMD_CORE_VERSION=${YCMD_CORE_VERSION} )

option( UNIVERSAL "Build universal mac binary" OFF )

if ( CMAKE_GENERATOR STREQUAL Xcode )
  set( CMAKE_GENERATOR_IS_XCODE true )
endif()

if ( ${CMAKE_SYSTEM_NAME} MATCHES "FreeBSD" )
  set( SYSTEM_IS_FREEBSD true )
endif()

if ( ${CMAKE_SYSTEM_NAME} MATCHES "OpenBSD" )
  set( SYSTEM_IS_OPENBSD true )
endif()

if ( ${CMAKE_SYSTEM_NAME} MATCHES "SunOS" )
  set( SYSTEM_IS_SUNOS true )
endif()

# Check if platform is 64 bit
if( CMAKE_SIZEOF_VOID_P EQUAL 4 )
  set( 64_BIT_PLATFORM 0 )
else()
  set( 64_BIT_PLATFORM 1 )
endif()

#############################################################################

# Linux distribution detection.

# Red Hat and CentOS detection.
if ( EXISTS /etc/redhat-release )
  file( READ /etc/redhat-release CONTENTS )
  if ( CONTENTS MATCHES "Red Hat" )
    set( DISTRIBUTION "Red Hat" )
  elseif ( CONTENTS MATCHES "CentOS" )
    set( DISTRIBUTION "CentOS" )
  endif()
# Gentoo detection. Needed because Gentoo is a special snowflake that puts
# llvm in weird places.
elseif ( EXISTS /etc/os-release )
  file( READ /etc/os-release CONTENTS )
  if ( CONTENTS MATCHES "Gentoo" )
    set( DISTRIBUTION "Gentoo" )
  endif()
endif()

#############################################################################

# Turning on this flag tells cmake to emit a compile_commands.json file.
# This file can be used to load compilation flags into YCM. See here for more
# details: http://clang.llvm.org/docs/JSONCompilationDatabase.html
set( CMAKE_EXPORT_COMPILE_COMMANDS 1 )

#############################################################################

# This is needed so that on macs, the library is built in both 32 bit and 64 bit
# versions. Without this python might refuse to load the module, depending on
# how python was built.
# On Mac, boost needs to be compiled universal as well, if used instead of the
# included BoostParts lib. For brew, that's
# "brew install boost --universal"
# If the user chose to use the system libclang.dylib (or the libclang.dylib
# binary downloaded from llvm.org) on a mac, then we don't specify universal
# binary building since the system libclang on macs is not  universal (and thus
# linking would fail with universal).
if ( UNIVERSAL AND NOT USE_SYSTEM_LIBCLANG )
  set( CMAKE_OSX_ARCHITECTURES "i386;x86_64" )
endif()

#############################################################################

# To shut up the warning about CMake policy CMP0042
set( CMAKE_MACOSX_RPATH ON )

#############################################################################

if ( CMAKE_CXX_COMPILER_ID STREQUAL "Clang" )
  set( COMPILER_IS_CLANG true )

  # Linux machines don't necessarily have libc++ installed alongside clang,
  # but HAS_LIBCXX11 doesn't always trigger for machines that DO have libc++. We
  # know that at least all the Mac OS versions we support that use Clang have
  # libc++, so we're safe there. On FreeBSD 9 libc++ is an optional build
  # toggle. On FreeBSD 10 it is the default.
  if ( HAS_LIBCXX11 OR APPLE OR SYSTEM_IS_FREEBSD )
    set( CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -stdlib=libc++" )
  endif()

  # Ninja will by default prevent Clang from outputting diagnostics in color, so
  # we force color output
  if ( CMAKE_GENERATOR STREQUAL "Ninja" )
    set( CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fcolor-diagnostics" )
  endif()
endif()

#############################################################################

# MSVC has symbols hidden by default. On GCC and Clang we need to explicitly
# set the visibility to hidden to achieve the same result and then manually
# expose what we need. This results in smaller ycm_core dynamic library and thus
# a shorter loading time and higher performance.
if( CMAKE_COMPILER_IS_GNUCXX OR COMPILER_IS_CLANG )
  set( CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fvisibility=hidden" )
endif()

if ( DEFINED ENV{YCM_BENCHMARK} OR DEFINED ENV{YCM_TESTRUN})
  if ( MSVC )
    add_definitions( -DYCM_EXPORT=__declspec\(\ dllexport\ \) )
  elseif( CMAKE_COMPILER_IS_GNUCXX OR COMPILER_IS_CLANG )
    add_definitions(
      -DYCM_EXPORT=__attribute__\(\(visibility\(\"default\"\)\)\) )
  else()
    add_definitions( -DYCM_EXPORT= )
  endif()
else()
  add_definitions( -DYCM_EXPORT= )
endif()

#############################################################################

# MSVC has snprintf since version 14 which is newer than what we support.
# *NOT* defining HAVE_SNPRINTF will break compiling the bundled boost libraries.
if ( MSVC )
  add_definitions( -DHAVE_SNPRINTF )
endif()

#############################################################################

# Force release build by default, speed is of the essence
if ( NOT CMAKE_BUILD_TYPE )
  set( CMAKE_BUILD_TYPE Release )
endif()

#############################################################################

# Determining the presence of C++11 support in the compiler
set( CPP11_AVAILABLE false )
if ( CMAKE_COMPILER_IS_GNUCXX )
  if ( NOT CMAKE_CXX_COMPILER_VERSION VERSION_LESS 4.8 )
    set( CPP11_AVAILABLE true )
  endif()
elseif( COMPILER_IS_CLANG )
  if ( NOT CMAKE_CXX_COMPILER_VERSION VERSION_LESS 3.3 )
    set( CPP11_AVAILABLE true )
    set( CMAKE_XCODE_ATTRIBUTE_CLANG_CXX_LANGUAGE_STANDARD "c++11" )
    set( CMAKE_XCODE_ATTRIBUTE_CLANG_CXX_LIBRARY "libc++" )
  endif()
elseif( MSVC )
  if ( NOT MSVC_VERSION LESS 1900 )
    set( CPP11_AVAILABLE true )
  endif()
endif()

#############################################################################

# For MSVC enable UNICODE and compilation on multiple processors. Increase the
# number of sections that an object file can hold. This is needed for storing
# the Unicode table. Also, force MSVC to treat source files as UTF-8 encoded.
if ( MSVC )
  add_definitions( /DUNICODE /D_UNICODE /Zc:wchar_t- )
  set( CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} /MP /bigobj /utf-8" )
endif()

if( MSVC OR CYGWIN OR MSYS)
  # BOOST_ALL_NO_LIB turns off MSVC library autolinking
  add_definitions( -DBOOST_ALL_NO_LIB )
endif()

# Enables Python compilation for 64-bit Windows. Already defined by Python
# headers when compiling with MSVC.
if( WIN32 OR CYGWIN OR MSYS AND NOT MSVC AND 64_BIT_PLATFORM )
  add_definitions( -DMS_WIN64 )
endif()

#############################################################################

if ( CPP11_AVAILABLE )
  # Cygwin needs its hand held a bit; see issue #473
  if ( CYGWIN AND CMAKE_COMPILER_IS_GNUCXX )
    set( CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=gnu++11" )
  elseif( NOT MSVC )
    set( CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11" )
  endif()
else()
  # Platform-specific advice goes here. In particular, we have plenty of users
  # in corporate environments on RHEL/CentOS, where the default system compiler
  # is too old.

  # on RHEL and CentOS, users require the devtoolset-3 or greater. However, we
  # recommended the devtoolset-6 because it is the newest at the time of
  # writing. And why not.
  if ( DISTRIBUTION STREQUAL "CentOS" OR DISTRIBUTION STREQUAL "Red Hat" )
    message( STATUS "NOTE: You appear to be on ${DISTRIBUTION}. "
    "In order to use this application, you require a more modern compiler "
    "than the default compiler on this platform. "
    "Please install the devtoolset-6 or greater. For example, see this link: "
    "https://www.softwarecollections.org/en/scls/rhscl/devtoolset-6/" )

    # Finally, just check if it is installed and they just need to activate it.
    if ( EXISTS /opt/rh/devtoolset-6 )
      message( STATUS "NOTE: It looks like you have the devtoolset-6 "
                      "installed in /opt/rh/devtoolset-6, so you probably "
                      "just need to activate it and re-run the installation. "
                      "For example: source /opt/rh/devtoolset-6/enable")
    endif()
  endif()

  message( FATAL_ERROR "Your C++ compiler does NOT fully support C++11." )
endif()

# Note: build.py always explicitly sets this option, so the default used here
# rarely matters.
option( USE_PYTHON2 "If on, link to Python 2 instead of 3" ON )

if ( USE_PYTHON2 )
  find_package( PythonLibs 2.7 REQUIRED )

  if ( NOT PYTHONLIBS_VERSION_STRING VERSION_LESS "3.0.0" )
    message( FATAL_ERROR
      "You set USE_PYTHON2 to make CMake find python2 libs only, but CMake "
      "found python3 libs instead. Either don't set USE_PYTHON2 or install the "
      "necessary python2 headers & libraries." )
  endif()
else()
  set( Python_ADDITIONAL_VERSIONS 3.7 3.6 3.5 3.4 )
  find_package( PythonLibs 3.4 REQUIRED )  # 3.4 is ONLY the mininum
endif()

#############################################################################

option( USE_SYSTEM_BOOST "Set to ON to use the system boost libraries" OFF )

if (NOT USE_SYSTEM_BOOST)
  add_subdirectory( BoostParts )
endif()

add_subdirectory( ycm )
