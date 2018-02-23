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

cmake_minimum_required( VERSION 2.8.7 )

project( ycm_core )

option( USE_DEV_FLAGS "Use compilation flags meant for YCM developers" OFF )
option( USE_CLANG_COMPLETER "Use Clang semantic completer for C/C++/ObjC" OFF )
option( USE_SYSTEM_LIBCLANG "Set to ON to use the system libclang library" OFF )
set( PATH_TO_LLVM_ROOT "" CACHE PATH "Path to the root of a LLVM+Clang binary distribution" )
set( EXTERNAL_LIBCLANG_PATH "" CACHE PATH "Path to the libclang library to use" )

if ( USE_CLANG_COMPLETER AND
     NOT USE_SYSTEM_LIBCLANG AND
     NOT PATH_TO_LLVM_ROOT AND
     NOT EXTERNAL_LIBCLANG_PATH )

  set( CLANG_VERSION 5.0.1 )

  if ( APPLE )
    set( LIBCLANG_DIRNAME "libclang-${CLANG_VERSION}-x86_64-apple-darwin" )
    set( LIBCLANG_SHA256
         "93c45885fc9b56767c166a2b2693a85df66bae5cc2c88afb1bffa1e5571e9c1e" )
  elseif ( WIN32 )
    if( 64_BIT_PLATFORM )
      set( LIBCLANG_DIRNAME "libclang-${CLANG_VERSION}-win64" )
      set( LIBCLANG_SHA256
           "31bbc56ef62147c9fb0b1d791eccb9d0d48e44f9560d560087ea1f838c81c28b" )
    else()
      set( LIBCLANG_DIRNAME "libclang-${CLANG_VERSION}-win32" )
      set( LIBCLANG_SHA256
           "63ab3842da6965a02035c77e5cb04b01545ffa9429e40132c016218d6e0c2ef2" )
    endif()
  elseif ( SYSTEM_IS_FREEBSD )
    if ( 64_BIT_PLATFORM )
      set( LIBCLANG_DIRNAME
           "libclang-${CLANG_VERSION}-amd64-unknown-freebsd10" )
      set( LIBCLANG_SHA256
           "7a6727624be8d96304dc6f30d4b4918e75e44c8ffada0a6964d2741f043f8bde" )
    else()
      set( LIBCLANG_DIRNAME "libclang-${CLANG_VERSION}-i386-unknown-freebsd10" )
      set( LIBCLANG_SHA256
           "0b9359521ad77e896fdc0ce87dd0ada95444b629f319ebe1d8f1e2d0ba1b3ced" )
    endif()
  elseif ( CMAKE_SYSTEM_PROCESSOR MATCHES "^(aarch64.*|AARCH64.*)" )
    set( LIBCLANG_DIRNAME "libclang-${CLANG_VERSION}-aarch64-linux-gnu" )
    set( LIBCLANG_SHA256
         "a26702938baa2b3d433ce832b603fa51c85b922ec0068e6de4c369a9d9305ab6" )
  elseif ( CMAKE_SYSTEM_PROCESSOR MATCHES "^(arm.*|ARM.*)" )
    set( LIBCLANG_DIRNAME "libclang-${CLANG_VERSION}-armv7a-linux-gnueabihf" )
    set( LIBCLANG_SHA256
         "9744e55629309ae6780fef2ec0007b5da5b496134d50531adfd818348384f8ae" )
  else()
    if ( 64_BIT_PLATFORM )
      set( LIBCLANG_DIRNAME
           "libclang-${CLANG_VERSION}-x86_64-linux-gnu-ubuntu-14.04" )
      set( LIBCLANG_SHA256
           "70c1709a12deddb5599cd30fbd19436fb231772fbbb2bf53a7b2e89f9af0ec9e" )
    else()
      message( FATAL_ERROR
        "No prebuilt Clang ${CLANG_VERSION} binaries for 32-bit Linux. "
        "You'll have to compile Clang ${CLANG_VERSION} from source. "
        "See the YCM docs for details on how to use a user-compiled libclang." )
    endif()
  endif()

  set( LIBCLANG_FILENAME "${LIBCLANG_DIRNAME}.tar.bz2" )

  set( LIBCLANG_DOWNLOAD ON )
  set( LIBCLANG_URL
       "https://dl.bintray.com/micbou/libclang/${LIBCLANG_FILENAME}" )

  # Check if the Clang archive is already downloaded and its checksum is
  # correct.  If this is not the case, remove it if needed and download it.
  set( LIBCLANG_LOCAL_FILE
       "${CMAKE_SOURCE_DIR}/../clang_archives/${LIBCLANG_FILENAME}" )

  if( EXISTS "${LIBCLANG_LOCAL_FILE}" )
    file( SHA256 "${LIBCLANG_LOCAL_FILE}" LIBCLANG_LOCAL_SHA256 )

    if( "${LIBCLANG_LOCAL_SHA256}" STREQUAL "${LIBCLANG_SHA256}" )
      set( LIBCLANG_DOWNLOAD OFF )
    else()
      file( REMOVE "${LIBCLANG_LOCAL_FILE}" )
    endif()
  endif()

  if( LIBCLANG_DOWNLOAD )
    message( STATUS
             "Downloading libclang ${CLANG_VERSION} from ${LIBCLANG_URL}" )

    file(
      DOWNLOAD "${LIBCLANG_URL}" "${LIBCLANG_LOCAL_FILE}"
      SHOW_PROGRESS EXPECTED_HASH SHA256=${LIBCLANG_SHA256}
    )
  else()
    message( STATUS "Using libclang archive: ${LIBCLANG_LOCAL_FILE}" )
  endif()

  # Copy and extract the Clang archive in the building directory.
  file( COPY "${LIBCLANG_LOCAL_FILE}" DESTINATION "${CMAKE_CURRENT_BINARY_DIR}/../" )
  execute_process( COMMAND ${CMAKE_COMMAND} -E tar -xjf ${LIBCLANG_FILENAME} )

  # We determine PATH_TO_LLVM_ROOT by searching the libclang library path in
  # CMake build folder.
  file( GLOB_RECURSE PATH_TO_LIBCLANG ${CMAKE_BINARY_DIR}/libclang.* )
  if ( NOT PATH_TO_LIBCLANG )
    message( FATAL_ERROR "Cannot find path to libclang in prebuilt binaries" )
  endif()
  # file( GLOB_RECURSE ... ) returns a list of files. Take the first one.
  list( GET PATH_TO_LIBCLANG 0 PATH_TO_LIBCLANG )
  # We know that LLVM root is parent to the directory containing libclang so we
  # need to go up two directories:
  #
  #   /path/to/llvm/root/lib/libclang.so/../.. = /path/to/llvm/root/
  #
  get_filename_component( PATH_TO_LLVM_ROOT "${PATH_TO_LIBCLANG}/../.."
                          ABSOLUTE )
endif()

if ( PATH_TO_LLVM_ROOT OR USE_SYSTEM_LIBCLANG OR EXTERNAL_LIBCLANG_PATH )
  set( USE_CLANG_COMPLETER TRUE )
endif()

if ( USE_CLANG_COMPLETER AND
     NOT PATH_TO_LLVM_ROOT AND
     NOT USE_SYSTEM_LIBCLANG AND
     NOT EXTERNAL_LIBCLANG_PATH )
  message( FATAL_ERROR
    "You have not specified which libclang to use. You have several options:\n"
    " 1. Set PATH_TO_LLVM_ROOT to a path to the root of a LLVM+Clang binary "
    "distribution. You can download such a binary distro from llvm.org. This "
    "is the recommended approach.\n"
    " 2. Set USE_SYSTEM_LIBCLANG to ON; this makes YCM search for the system "
    "version of libclang.\n"
    " 3. Set EXTERNAL_LIBCLANG_PATH to a path to whatever "
    "libclang.[so|dylib|dll] you wish to use.\n"
    "You HAVE to pick one option. See the docs for more information.")
endif()

if ( USE_CLANG_COMPLETER )
  message( STATUS "Using libclang to provide semantic completion for C/C++/ObjC" )
else()
  message( STATUS "NOT using libclang, no semantic completion for "
                  "C/C++/ObjC will be available" )
endif()

if ( NOT LIBCLANG_FILENAME AND PATH_TO_LLVM_ROOT )
  set( CLANG_INCLUDES_DIR "${PATH_TO_LLVM_ROOT}/include" )
else()
  set( CLANG_INCLUDES_DIR "${CMAKE_SOURCE_DIR}/llvm/include" )
endif()

if ( NOT IS_ABSOLUTE "${CLANG_INCLUDES_DIR}" )
  get_filename_component(CLANG_INCLUDES_DIR
    "${CMAKE_BINARY_DIR}/${CLANG_INCLUDES_DIR}" ABSOLUTE)
endif()

if ( NOT EXTERNAL_LIBCLANG_PATH AND PATH_TO_LLVM_ROOT )
  if ( MINGW )
    set( LIBCLANG_SEARCH_PATH "${PATH_TO_LLVM_ROOT}/bin" )
  else()
    set( LIBCLANG_SEARCH_PATH "${PATH_TO_LLVM_ROOT}/lib" )
  endif()

  # Need TEMP because find_library does not work with an option variable
  find_library( TEMP NAMES clang libclang
                PATHS ${LIBCLANG_SEARCH_PATH}
                NO_DEFAULT_PATH )
  set( EXTERNAL_LIBCLANG_PATH ${TEMP} )
endif()

# This is a workaround for a CMake bug with include_directories(SYSTEM ...)
# on Mac OS X. Bug report: http://public.kitware.com/Bug/view.php?id=10837
if ( APPLE )
  set( CMAKE_INCLUDE_SYSTEM_FLAG_CXX "-isystem " )
endif()

if ( USE_SYSTEM_BOOST )
  set( Boost_COMPONENTS filesystem regex system )
  # Gentoo allows a very convenient system-wide python version switching
  # that handles symlinks of everything needed, including Boost.Python.
  # Thus, on Gentoo, we want to always link against boost_python.
  if( USE_PYTHON2 OR DISTRIBUTION STREQUAL "Gentoo" )
    list( APPEND Boost_COMPONENTS python )
  else()
    list( APPEND Boost_COMPONENTS python3 )
  endif()
  find_package( Boost REQUIRED COMPONENTS ${Boost_COMPONENTS} )
else()
  set( Boost_INCLUDE_DIR ${BoostParts_SOURCE_DIR} )
  set( Boost_LIBRARIES BoostParts )
endif()

file( GLOB_RECURSE SERVER_SOURCES *.h *.cpp )

# The test and benchmark sources are a part of a different target, so we remove
# them. The CMakeFiles cpp file is picked up when the user creates an in-source
# build, and we don't want that. We also remove client-specific code.
file( GLOB_RECURSE to_remove tests/*.h tests/*.cpp benchmarks/*.h
                             benchmarks/*.cpp CMakeFiles/*.cpp *client* )

if( to_remove )
  list( REMOVE_ITEM SERVER_SOURCES ${to_remove} )
endif()

if ( USE_CLANG_COMPLETER )
  include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}
    "${CMAKE_CURRENT_SOURCE_DIR}/ClangCompleter" )
  add_definitions( -DUSE_CLANG_COMPLETER )
else()
  file( GLOB_RECURSE to_remove_clang ClangCompleter/*.h ClangCompleter/*.cpp )

  if( to_remove_clang )
    list( REMOVE_ITEM SERVER_SOURCES ${to_remove_clang} )
  endif()
endif()

# The SYSTEM flag makes sure that -isystem[header path] is passed to the
# compiler instead of the standard -I[header path]. Headers included with
# -isystem do not generate warnings (and they shouldn't; e.g. boost warnings are
# just noise for us since we won't be changing them).
# Since there is no -isystem flag equivalent on Windows, headers from external
# projects may conflict with our headers and override them. We prevent that by
# including these directories after ours.
include_directories(
  SYSTEM
  ${Boost_INCLUDE_DIR}
  ${PYTHON_INCLUDE_DIRS}
  ${CLANG_INCLUDES_DIR}
  )

#############################################################################

# One can use the system libclang.[so|dylib] like so:
#   cmake -DUSE_SYSTEM_LIBCLANG=1 [...]
# One can also explicitly pick the external libclang.[so|dylib] for use like so:
#   cmake -DEXTERNAL_LIBCLANG_PATH=/path/to/libclang.so [...]
# The final .so we build will then first look in the same dir in which it is
# located for libclang.so. This is provided by the rpath = $ORIGIN feature.

if ( EXTERNAL_LIBCLANG_PATH OR USE_SYSTEM_LIBCLANG )
  if ( USE_SYSTEM_LIBCLANG )
    if ( APPLE )
      set( ENV_LIB_PATHS ENV DYLD_LIBRARY_PATH )
    elseif ( UNIX )
      set( ENV_LIB_PATHS ENV LD_LIBRARY_PATH )
    elseif ( WIN32 )
      set( ENV_LIB_PATHS ENV PATH )
    else ()
      set( ENV_LIB_PATHS "" )
    endif()
    find_program( LLVM_CONFIG_EXECUTABLE NAMES llvm-config )
    if ( LLVM_CONFIG_EXECUTABLE )
      execute_process( COMMAND ${LLVM_CONFIG_EXECUTABLE} --libdir
                       OUTPUT_VARIABLE LLVM_CONFIG_PATH
                       OUTPUT_STRIP_TRAILING_WHITESPACE )
    endif()
    # On Debian-based systems, llvm installs into /usr/lib/llvm-x.y.
    file( GLOB SYS_LLVM_PATHS "/usr/lib/llvm*/lib" )
    # On FreeBSD , llvm install into /usr/local/llvm-xy
    file ( GLOB FREEBSD_LLVM_PATHS "/usr/local/llvm*/lib")
    # Need TEMP because find_library does not work with an option variable
    # On Debian-based systems only a symlink to libclang.so.1 is created
    find_library( TEMP
                  NAMES
                  clang
                  libclang.so.1
                  PATHS
                  ${ENV_LIB_PATHS}
                  ${LLVM_CONFIG_PATH}
                  /usr/lib
                  /usr/lib/llvm
                  ${SYS_LLVM_PATHS}
                  ${FREEBSD_LLVM_PATHS}
                  /Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/lib
                  /Library/Developer/CommandLineTools/usr/lib )
    set( EXTERNAL_LIBCLANG_PATH ${TEMP} )
  else()
    # For Macs, we do things differently; look further in this file.
    if ( NOT APPLE AND NOT MSVC )
      # Setting this to true makes sure that libraries we build will have our
      # rpath set even without having to do "make install"
      set( CMAKE_BUILD_WITH_INSTALL_RPATH TRUE )
      set( CMAKE_INSTALL_RPATH "\$ORIGIN" )
      # Add directories from all libraries outside the build tree to the rpath.
      # This makes the dynamic linker able to find non system libraries that
      # our libraries require, in particular the Python one (from pyenv for
      # instance).
      set( CMAKE_INSTALL_RPATH_USE_LINK_PATH TRUE )
    endif()
  endif()

  # On Linux, the library target is a symlink of the soversion one.  Since it
  # will be copied in the project folder, we need the symlinked library.
  get_filename_component( LIBCLANG_TARGET "${EXTERNAL_LIBCLANG_PATH}" REALPATH )
  message( STATUS "Using external libclang: ${LIBCLANG_TARGET}" )
else()
  set( LIBCLANG_TARGET )
endif()

if ( EXTRA_RPATH )
  set( CMAKE_INSTALL_RPATH "${EXTRA_RPATH}:${CMAKE_INSTALL_RPATH}" )
endif()

# Needed on Linux machines, but not on Macs and OpenBSD
if ( UNIX AND NOT ( APPLE OR SYSTEM_IS_OPENBSD OR HAIKU ) )
  set( EXTRA_LIBS rt )
endif()

#############################################################################

add_library( ${PROJECT_NAME} SHARED
             ${SERVER_SOURCES}
           )

if ( USE_CLANG_COMPLETER AND NOT LIBCLANG_TARGET )
     message( FATAL_ERROR "Using Clang completer, but no libclang found. "
                          "Try setting EXTERNAL_LIBCLANG_PATH or revise "
                          "your configuration" )
endif()

target_link_libraries( ${PROJECT_NAME}
                       ${Boost_LIBRARIES}
                       ${PYTHON_LIBRARIES}
                       ${LIBCLANG_TARGET}
                       ${EXTRA_LIBS}
                     )

if( LIBCLANG_TARGET )
  # When building with MSVC, we need to copy libclang.dll instead of libclang.lib
  if( MSVC )
    add_custom_command(
      TARGET ${PROJECT_NAME}
      POST_BUILD
      COMMAND ${CMAKE_COMMAND} -E copy "${PATH_TO_LLVM_ROOT}/bin/libclang.dll" "$<TARGET_FILE_DIR:${PROJECT_NAME}>"
    )
  else()
    add_custom_command(
      TARGET ${PROJECT_NAME}
      POST_BUILD
      COMMAND ${CMAKE_COMMAND} -E copy "${LIBCLANG_TARGET}" "$<TARGET_FILE_DIR:${PROJECT_NAME}>"
    )

    if( NOT APPLE AND NOT WIN32 )
      # When loading our library, the dynamic linker may look for
      # libclang.so.x instead of libclang.so.x.y. Create the corresponding
      # symlink.
      get_filename_component( LIBCLANG_NAME ${LIBCLANG_TARGET} NAME )
      string( REGEX REPLACE "([^.]+).([0-9]+).([0-9]+)$" "\\1.\\2"
              LIBCLANG_SONAME ${LIBCLANG_NAME} )
      add_custom_command(
        TARGET ${PROJECT_NAME}
        POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E create_symlink
        "${LIBCLANG_NAME}"
        "$<TARGET_FILE_DIR:${PROJECT_NAME}>/${LIBCLANG_SONAME}"
      )
    endif()
  endif()
endif()


#############################################################################

# Things are a bit different on Macs when using an external libclang.dylib; here
# we want to make sure we use @loader_path/libclang.dylib instead of
# @rpath/libclang.dylib in the final ycm_core.so. If we use the
# @rpath version, then it may load the system libclang which the user
# explicitely does not want (otherwise the user would specify
# USE_SYSTEM_LIBCLANG). If we hardcode with `@loader_path/libclang.dylib`,
# it guarantees to search `@loader_path` for libclang.dylib first and use it
# only. So with `@loader_path`, we make sure that only the libclang.dylib
# present in the same directory as our ycm_core.so is used.
# And the extra `rpath` is helpful to find libclang.dylib's dependencies
# if it is built with `--enable-shared` flag.
if ( EXTERNAL_LIBCLANG_PATH AND APPLE AND NOT USE_SYSTEM_LIBCLANG)
  get_filename_component(EXTRA_LIB_PATH ${EXTERNAL_LIBCLANG_PATH} DIRECTORY)

  set_target_properties(${PROJECT_NAME}
    PROPERTIES LINK_FLAGS "-Wl,-rpath,${EXTRA_LIB_PATH}")

  add_custom_command( TARGET ${PROJECT_NAME}
                      POST_BUILD
                      COMMAND install_name_tool
                      "-change"
                      "@rpath/libclang.dylib"
                      "@loader_path/libclang.dylib"
                      "$<TARGET_FILE:${PROJECT_NAME}>"
                    )
endif()


#############################################################################

# We don't want the "lib" prefix, it can screw up python when it tries to search
# for our module
set_target_properties( ${PROJECT_NAME} PROPERTIES PREFIX "")

if ( WIN32 OR CYGWIN OR MSYS )
  # DLL platforms put dlls in the RUNTIME_OUTPUT_DIRECTORY
  # First for the generic no-config case (e.g. with mingw)
  set_target_properties( ${PROJECT_NAME} PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY ${PROJECT_SOURCE_DIR}/../.. )
  # Second, for multi-config builds (e.g. msvc)
  foreach( OUTPUTCONFIG ${CMAKE_CONFIGURATION_TYPES} )
    string( TOUPPER ${OUTPUTCONFIG} OUTPUTCONFIG )
    set_target_properties( ${PROJECT_NAME} PROPERTIES
      RUNTIME_OUTPUT_DIRECTORY_${OUTPUTCONFIG} ${PROJECT_SOURCE_DIR}/../.. )
  endforeach()

  if ( WIN32 )
    # This is the extension for compiled Python modules on Windows
    set_target_properties( ${PROJECT_NAME} PROPERTIES SUFFIX ".pyd")
  elseif ( CYGWIN OR MSYS )
    # This is the extension for compiled Python modules in Cygwin and msys
    set_target_properties( ${PROJECT_NAME} PROPERTIES SUFFIX ".dll")
  endif()
else()
  # Even on macs, we want a .so extension instead of a .dylib which is what
  # cmake would give us by default. Python won't recognize a .dylib as a module,
  # but it will recognize a .so
  set_target_properties( ${PROJECT_NAME} PROPERTIES SUFFIX ".so")
endif()

set_target_properties( ${PROJECT_NAME} PROPERTIES
  LIBRARY_OUTPUT_DIRECTORY ${PROJECT_SOURCE_DIR}/../.. )

#############################################################################


# For some reason, Xcode is too dumb to understand the -isystem flag and thus
# borks on warnings in Boost.
if ( USE_DEV_FLAGS AND ( CMAKE_COMPILER_IS_GNUCXX OR COMPILER_IS_CLANG ) AND
     NOT CMAKE_GENERATOR_IS_XCODE )
  # We want all warnings, and warnings should be treated as errors
  set( CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -Werror" )
endif()

#############################################################################

if( SYSTEM_IS_SUNOS )
  # SunOS needs this setting for thread support
  set( CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -pthreads" )
endif()

if( SYSTEM_IS_OPENBSD OR SYSTEM_IS_FREEBSD )
  set( CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -pthread" )
endif()

if ( DEFINED ENV{YCM_TESTRUN} )
  add_subdirectory( tests )
endif()
if ( DEFINED ENV{YCM_BENCHMARK} )
  add_subdirectory( benchmarks )
endif()
