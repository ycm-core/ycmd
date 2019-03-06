# Copyright (C) 2011-2019 ycmd contributors
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

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa

import ycm_core
import os
import inspect
from future.utils import PY2, native
from ycmd import extra_conf_store
from ycmd.utils import ( OnMac,
                         OnWindows,
                         PathsToAllParentFolders,
                         re,
                         ToCppStringCompatible,
                         ToBytes,
                         ToUnicode,
                         CLANG_RESOURCE_DIR )
from ycmd.responses import NoExtraConfDetected

# -include-pch and --sysroot= must be listed before -include and --sysroot
# respectively because the latter is a prefix of the former (and the algorithm
# checks prefixes).
INCLUDE_FLAGS = [ '-isystem', '-I', '-iquote', '-isysroot', '--sysroot',
                  '-gcc-toolchain', '-include-pch', '-include', '-iframework',
                  '-F', '-imacros', '-idirafter', '-B' ]
INCLUDE_FLAGS_WIN_STYLE = [ '/I' ]
PATH_FLAGS =  [ '--sysroot=' ] + INCLUDE_FLAGS

# We need to remove --fcolor-diagnostics because it will cause shell escape
# sequences to show up in editors, which is bad. See Valloric/YouCompleteMe#1421
STATE_FLAGS_TO_SKIP = { '-c',
                        '-MP',
                        '-MD',
                        '-MMD',
                        '--fcolor-diagnostics' }

STATE_FLAGS_TO_SKIP_WIN_STYLE = { '/c' }

# The -M* flags spec:
#   https://gcc.gnu.org/onlinedocs/gcc-4.9.0/gcc/Preprocessor-Options.html
FILE_FLAGS_TO_SKIP = { '-MF',
                       '-MT',
                       '-MQ',
                       '-o',
                       '--serialize-diagnostics' }

# Use a regex to correctly detect c++/c language for both versioned and
# non-versioned compiler executable names suffixes
# (e.g., c++, g++, clang++, g++-4.9, clang++-3.7, c++-10.2 etc).
# See Valloric/ycmd#266
CPP_COMPILER_REGEX = re.compile( r'\+\+(-\d+(\.\d+){0,2})?$' )

# Use a regex to match all the possible forms of clang-cl or cl compiler
CL_COMPILER_REGEX = re.compile( r'(?:cl|clang-cl)(.exe)?$', re.IGNORECASE )

# List of file extensions to be considered "header" files and thus not present
# in the compilation database. The logic will try and find an associated
# "source" file (see SOURCE_EXTENSIONS below) and use the flags for that.
HEADER_EXTENSIONS = [ '.h', '.hxx', '.hpp', '.hh', '.cuh' ]

# List of file extensions which are considered "source" files for the purposes
# of heuristically locating the flags for a header file.
SOURCE_EXTENSIONS = [ '.cpp', '.cxx', '.cc', '.c', '.cu', '.m', '.mm' ]

EMPTY_FLAGS = {
  'flags': [],
}

MAC_XCODE_TOOLCHAIN_DIR = (
  '/Applications/Xcode.app/Contents/Developer/Toolchains'
  '/XcodeDefault.xctoolchain' )
MAC_COMMAND_LINE_TOOLCHAIN_DIR = '/Library/Developer/CommandLineTools'
MAC_XCODE_SYSROOT = (
  '/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform'
  '/Developer/SDKs/MacOSX.sdk' )
MAC_COMMAND_LINE_SYSROOT = (
  '/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk' )
MAC_FOUNDATION_HEADERS_RELATIVE_DIR = (
  'System/Library/Frameworks/Foundation.framework/Headers' )


class Flags( object ):
  """Keeps track of the flags necessary to compile a file.
  The flags are loaded from user-created python files (hereafter referred to as
  'modules') that contain a method Settings( **kwargs )."""

  def __init__( self ):
    # We cache the flags by a tuple of filename and client data.
    self.flags_for_file = {}
    self.no_extra_conf_file_warning_posted = False

    # We cache the compilation database for any given source directory
    # Keys are directory names and values are ycm_core.CompilationDatabase
    # instances or None. Value is None when it is known there is no compilation
    # database to be found for the directory.
    self.compilation_database_dir_map = {}

    # Sometimes we don't actually know what the flags to use are. Rather than
    # returning no flags, if we've previously found flags for a file in a
    # particular directory, return them. These will probably work in a high
    # percentage of cases and allow new files (which are not yet in the
    # compilation database) to receive at least some flags.
    # Keys are directory names and values are ycm_core.CompilationInfo
    # instances. Values may not be None.
    self.file_directory_heuristic_map = {}


  def FlagsForFile( self,
                    filename,
                    add_extra_clang_flags = True,
                    client_data = None ):
    """Returns a tuple describing the compiler invocation required to parse the
    file |filename|. The tuple contains 2 entries:
      1. A list of the compiler flags to use,
      2. The name of the translation unit to parse.
    Note that the second argument might not be the same as the |filename|
    argument to this method in the event that the extra conf file overrides the
    translation unit, e.g. in the case of a "unity" build."""

    # The try-catch here is to avoid a synchronisation primitive. This method
    # may be called from multiple threads, and python gives us
    # 1-python-statement synchronisation for "free" (via the GIL)
    try:
      return self.flags_for_file[ filename, client_data ]
    except KeyError:
      pass

    results = self._GetFlagsFromExtraConfOrDatabase( filename, client_data )
    if not results.get( 'flags_ready', True ):
      return [], filename

    return self._ParseFlagsFromExtraConfOrDatabase( filename,
                                                    results,
                                                    add_extra_clang_flags,
                                                    client_data )


  def _ParseFlagsFromExtraConfOrDatabase( self,
                                          filename,
                                          results,
                                          add_extra_clang_flags,
                                          client_data ):
    if 'override_filename' in results:
      filename = results[ 'override_filename' ] or filename

    flags = _ExtractFlagsList( results )
    if not flags:
      return [], filename

    sanitized_flags = PrepareFlagsForClang( flags,
                                            filename,
                                            add_extra_clang_flags,
                                            _ShouldAllowWinStyleFlags( flags ) )

    if results.get( 'do_cache', True ):
      self.flags_for_file[ filename, client_data ] = sanitized_flags, filename

    return sanitized_flags, filename


  def _GetFlagsFromExtraConfOrDatabase( self, filename, client_data ):
    # Load the flags from the extra conf file if one is found and is not global.
    module = extra_conf_store.ModuleForSourceFile( filename )
    if module and not extra_conf_store.IsGlobalExtraConfModule( module ):
      return _CallExtraConfFlagsForFile( module, filename, client_data )

    # Load the flags from the compilation database if any.
    database = self.FindCompilationDatabase( filename )
    if database:
      return self._GetFlagsFromCompilationDatabase( database, filename )

    # Load the flags from the global extra conf if set.
    if module:
      return _CallExtraConfFlagsForFile( module, filename, client_data )

    # No compilation database and no extra conf found. Warn the user if not
    # already warned.
    if not self.no_extra_conf_file_warning_posted:
      self.no_extra_conf_file_warning_posted = True
      raise NoExtraConfDetected

    return EMPTY_FLAGS


  def Clear( self ):
    self.flags_for_file.clear()
    self.compilation_database_dir_map.clear()
    self.file_directory_heuristic_map.clear()


  def _GetFlagsFromCompilationDatabase( self, database, file_name ):
    file_dir = os.path.dirname( file_name )
    _, file_extension = os.path.splitext( file_name )

    compilation_info = _GetCompilationInfoForFile( database,
                                                   file_name,
                                                   file_extension )

    if not compilation_info:
      # Note: Try-catch here synchronises access to the cache (as this can be
      # called from multiple threads).
      try:
        # We previously saw a file in this directory. As a guess, just
        # return the flags for that file. Hopefully this will at least give some
        # meaningful compilation.
        compilation_info = self.file_directory_heuristic_map[ file_dir ]
      except KeyError:
        # No cache for this directory and there are no flags for this file in
        # the database.
        return EMPTY_FLAGS

    # If this is the first file we've seen in path file_dir, cache the
    # compilation_info for it in case we see a file in the same dir with no
    # flags available.
    # The following updates file_directory_heuristic_map if and only if file_dir
    # isn't already there. This works around a race condition where 2 threads
    # could be executing this method in parallel.
    self.file_directory_heuristic_map.setdefault( file_dir, compilation_info )

    return {
      'flags': _MakeRelativePathsInFlagsAbsolute(
        compilation_info.compiler_flags_,
        compilation_info.compiler_working_dir_ ),
    }


  # Return a compilation database object for the supplied path or None if no
  # compilation database is found.
  def FindCompilationDatabase( self, file_dir ):
    # We search up the directory hierarchy, to first see if we have a
    # compilation database already for that path, or if a compile_commands.json
    # file exists in that directory.
    for folder in PathsToAllParentFolders( file_dir ):
      # Try/catch to syncronise access to cache
      try:
        return self.compilation_database_dir_map[ folder ]
      except KeyError:
        pass

      compile_commands = os.path.join( folder, 'compile_commands.json' )
      if os.path.exists( compile_commands ):
        database = ycm_core.CompilationDatabase( folder )

        if database.DatabaseSuccessfullyLoaded():
          self.compilation_database_dir_map[ folder ] = database
          return database

    # Nothing was found. No compilation flags are available.
    # Note: we cache the fact that none was found for this folder to speed up
    # subsequent searches.
    self.compilation_database_dir_map[ file_dir ] = None
    return None


def _ExtractFlagsList( flags_for_file_output ):
  return [ ToUnicode( x ) for x in flags_for_file_output[ 'flags' ] ]


def _ShouldAllowWinStyleFlags( flags ):
  if OnWindows():
    # Iterate in reverse because we only care
    # about the last occurrence of --driver-mode flag.
    for flag in reversed( flags ):
      if flag.startswith( '--driver-mode' ):
        return flag == '--driver-mode=cl'
    # If there was no --driver-mode flag,
    # check if we are using a compiler like clang-cl.
    return bool( CL_COMPILER_REGEX.search( flags[ 0 ] ) )

  return False


def _CallExtraConfFlagsForFile( module, filename, client_data ):
  # We want to ensure we pass a native py2 `str` on py2 and a native py3 `str`
  # (unicode) object on py3. That's the API we provide.
  # In a vacuum, always passing a unicode object (`unicode` on py2 and `str` on
  # py3) would be better, but we can't do that because that would break all the
  # ycm_extra_conf files already out there that expect a py2 `str` object on
  # py2, and WE DO NOT BREAK BACKWARDS COMPATIBILITY.
  # Hindsight is 20/20.
  if PY2:
    filename = native( ToBytes( filename ) )
  else:
    filename = native( ToUnicode( filename ) )

  if hasattr( module, 'Settings' ):
    results = module.Settings( language = 'cfamily',
                               filename = filename,
                               client_data = client_data )
  # For the sake of backwards compatibility, we need to first check whether the
  # FlagsForFile function in the extra conf module even allows keyword args.
  elif inspect.getargspec( module.FlagsForFile ).keywords:
    results = module.FlagsForFile( filename, client_data = client_data )
  else:
    results = module.FlagsForFile( filename )

  if not isinstance( results, dict ) or 'flags' not in results:
    return EMPTY_FLAGS

  results[ 'flags' ] = _MakeRelativePathsInFlagsAbsolute(
      results[ 'flags' ],
      results.get( 'include_paths_relative_to_dir' ) )

  return results


def PrepareFlagsForClang( flags,
                          filename,
                          add_extra_clang_flags = True,
                          enable_windows_style_flags = False ):
  flags = _AddLanguageFlagWhenAppropriate( flags, enable_windows_style_flags )
  flags = _RemoveXclangFlags( flags )
  flags = _RemoveUnusedFlags( flags, filename, enable_windows_style_flags )
  if add_extra_clang_flags:
    # This flag tells libclang where to find the builtin includes.
    flags.append( '-resource-dir=' + CLANG_RESOURCE_DIR )
    # On Windows, parsing of templates is delayed until instantiation time.
    # This makes GetType and GetParent commands fail to return the expected
    # result when the cursor is in a template.
    # Using the -fno-delayed-template-parsing flag disables this behavior. See
    # http://clang.llvm.org/extra/PassByValueTransform.html#note-about-delayed-template-parsing # noqa
    # for an explanation of the flag and
    # https://code.google.com/p/include-what-you-use/source/detail?r=566
    # for a similar issue.
    if OnWindows():
      flags.append( '-fno-delayed-template-parsing' )
    if OnMac():
      flags = _AddMacIncludePaths( flags )
    flags = _EnableTypoCorrection( flags )

  vector = ycm_core.StringVector()
  for flag in flags:
    vector.append( ToCppStringCompatible( flag ) )
  return vector


def _RemoveXclangFlags( flags ):
  """Drops -Xclang flags.  These are typically used to pass in options to
  clang cc1 which are not used in the front-end, so they are not needed for
  code completion."""

  sanitized_flags = []
  saw_xclang = False
  for flag in flags:
    if flag == '-Xclang':
      saw_xclang = True
      continue
    elif saw_xclang:
      saw_xclang = False
      continue

    sanitized_flags.append( flag )

  return sanitized_flags


def _RemoveFlagsPrecedingCompiler( flags, enable_windows_style_flags ):
  """Assuming that the flag just before the first flag (looks like a flag,
  not like a file path) is the compiler path, removes all flags preceding it."""

  for index, flag in enumerate( flags ):
    if ( flag.startswith( '-' ) or
         ( enable_windows_style_flags and
           flag.startswith( '/' ) and
           not os.path.exists( flag ) ) ):
      return ( flags[ index - 1: ] if index > 1 else
               flags )
  return flags[ :-1 ]


def _AddLanguageFlagWhenAppropriate( flags, enable_windows_style_flags ):
  """When flags come from the compile_commands.json file, the flag preceding the
  first flag starting with a dash is usually the path to the compiler that
  should be invoked. Since LibClang does not deduce the language from the
  compiler name, we explicitely set the language to C++ if the compiler is a C++
  one (g++, clang++, etc.). We also set the language to CUDA if any of the
  source files has a .cu or .cuh extension. Otherwise, we let LibClang guess the
  language from the file extension. This handles the case where the .h extension
  is used for C++ headers."""

  flags = _RemoveFlagsPrecedingCompiler( flags, enable_windows_style_flags )

  # First flag is now the compiler path, a flag starting with a dash or
  # a flag starting with a forward slash if enable_windows_style_flags is True.
  first_flag = flags[ 0 ]

  # Because of _RemoveFlagsPrecedingCompiler called above, irrelevant of
  # enable_windows_style_flags. the first flag is either the compiler
  # (path or executable), a Windows style flag or starts with a dash.
  if first_flag.startswith( '-' ):
    return flags

  # Explicitly set the language to CUDA to avoid setting it to C++ when
  # compiling CUDA source files with a C++ compiler
  if any( fl.endswith( '.cu' ) or fl.endswith( '.cuh' )
          for fl in reversed( flags ) ):
    return [ first_flag, '-x', 'cuda' ] + flags[ 1: ]

  # NOTE: This is intentionally NOT checking for enable_windows_style_flags.
  #
  # The first flag is now either an absolute path, a Windows style flag or a
  # C++ compiler executable from $PATH.
  #   If it starts with a forward slash the flag can either be an absolute
  #   flag or a Windows style flag.
  #     If it matches the regex, it is safe to assume the flag is a compiler
  #     path.
  #     If it does not match the regex, it could still be a Windows style
  #     path or an absolute path. - This is determined in _RemoveUnusedFlags()
  #     and cleaned properly.
  #   If the flag starts with anything else (i.e. not a '-' or a '/'), the flag
  #   is a stray file path and shall be gotten rid of in _RemoveUnusedFlags().
  if CPP_COMPILER_REGEX.search( first_flag ):
    return [ first_flag, '-x', 'c++' ] + flags[ 1: ]

  return flags


def _RemoveUnusedFlags( flags, filename, enable_windows_style_flags ):
  """Given an iterable object that produces strings (flags for Clang), removes
  the '-c' and '-o' options that Clang does not like to see when it's producing
  completions for a file. Same for '-MD' etc.

  We also try to remove any stray filenames in the flags that aren't include
  dirs."""

  new_flags = []

  # When flags come from the compile_commands.json file, the first flag is
  # usually the path to the compiler that should be invoked. Directly move it to
  # the new_flags list so it doesn't get stripped of in the loop below.
  if not flags[ 0 ].startswith( '-' ):
    new_flags = flags[ :1 ]
    flags = flags[ 1: ]

  skip_next = False
  current_flag = flags[ 0 ]

  filename = os.path.realpath( filename )
  for flag in flags:
    previous_flag = current_flag
    current_flag = flag

    if skip_next:
      skip_next = False
      continue

    if ( flag in STATE_FLAGS_TO_SKIP or
         ( enable_windows_style_flags and
           flag in STATE_FLAGS_TO_SKIP_WIN_STYLE ) ):
      continue

    if flag in FILE_FLAGS_TO_SKIP:
      skip_next = True
      continue

    if os.path.realpath( flag ) == filename:
      continue

    # We want to make sure that we don't have any stray filenames in our flags;
    # filenames that are part of include flags are ok, but others are not. This
    # solves the case where we ask the compilation database for flags for
    # "foo.cpp" when we are compiling "foo.h" because the comp db doesn't have
    # flags for headers. The returned flags include "foo.cpp" and we need to
    # remove that.
    if _SkipStrayFilenameFlag( current_flag,
                               previous_flag,
                               enable_windows_style_flags ):
      continue

    new_flags.append( flag )

  return new_flags


def _SkipStrayFilenameFlag( current_flag,
                            previous_flag,
                            enable_windows_style_flags ):
  current_flag_starts_with_slash = current_flag.startswith( '/' )
  previous_flag_starts_with_slash = previous_flag.startswith( '/' )

  current_flag_starts_with_dash = current_flag.startswith( '-' )
  previous_flag_starts_with_dash = previous_flag.startswith( '-' )

  previous_flag_is_include = ( previous_flag in INCLUDE_FLAGS or
                               ( enable_windows_style_flags and
                                 previous_flag in INCLUDE_FLAGS_WIN_STYLE ) )

  current_flag_may_be_path = ( '/' in current_flag or
                               ( enable_windows_style_flags and
                                 '\\' in current_flag ) )

  return ( not ( current_flag_starts_with_dash or
                 ( enable_windows_style_flags and
                   current_flag_starts_with_slash ) ) and
           ( not ( previous_flag_starts_with_dash or
                   ( enable_windows_style_flags and
                     previous_flag_starts_with_slash ) ) or
             ( not previous_flag_is_include and current_flag_may_be_path ) ) )


def _GetMacSysRoot():
  # Since macOS 10.14, the root framework directories do not contain the
  # headers. Instead of relying on the macOS version, check if the Headers
  # directory of a common framework (Foundation) exists. If it does, return the
  # base directory as the default sysroot.
  for sysroot in [ '/', MAC_XCODE_SYSROOT, MAC_COMMAND_LINE_SYSROOT ]:
    if os.path.exists( os.path.join( sysroot,
                                     MAC_FOUNDATION_HEADERS_RELATIVE_DIR ) ):
      return sysroot
  # No headers found. Use the root directory anyway.
  return '/'


def _ExtractInfoForMacIncludePaths( flags ):
  language = 'c++'
  use_libcpp = True
  sysroot = _GetMacSysRoot()
  isysroot = None

  previous_flag = None
  for current_flag in flags:
    if previous_flag == '-x':
      language = current_flag
    if current_flag.startswith( '-x' ):
      language = current_flag[ 2: ]
    if current_flag.startswith( '-stdlib=' ):
      use_libcpp = current_flag[ 8: ] == 'libc++'
    if previous_flag == '--sysroot':
      sysroot = current_flag
    if current_flag.startswith( '--sysroot=' ):
      sysroot = current_flag[ 10: ]
    if previous_flag == '-isysroot':
      isysroot = current_flag
    if current_flag.startswith( '-isysroot' ):
      isysroot = current_flag[ 9: ]
    previous_flag = current_flag

  # -isysroot takes precedence over --sysroot.
  if isysroot:
    sysroot = isysroot

  language_is_cpp = language in { 'c++', 'objective-c++' }

  return language_is_cpp, use_libcpp, sysroot


def _FindMacToolchain():
  for toolchain in [ MAC_XCODE_TOOLCHAIN_DIR, MAC_COMMAND_LINE_TOOLCHAIN_DIR ]:
    if os.path.exists( toolchain ):
      return toolchain
  return None


# We can't rely on upstream libclang to find the system headers on macOS 10.14
# as it's unable to locate the framework headers without setting the sysroot if
# Command Line Tools is not installed. So, we try to reproduce the logic used by
# Apple Clang to find the system headers by looking at the output of the command
#
#   clang++ -x c++ -E -v -
#
# which prints the list of system header directories and by reading the source
# code of upstream Clang:
# https://github.com/llvm-mirror/clang/blob/2709c8b804eb38dbdc8ae05b8fcf4f95c01b4102/lib/Frontend/InitHeaderSearch.cpp#L453-L510
# This has also the benefit of allowing completion of system header paths and
# navigation to these headers when the cursor is on an include statement.
def _AddMacIncludePaths( flags ):
  use_standard_cpp_includes = '-nostdinc++' not in flags
  use_standard_system_includes = '-nostdinc' not in flags
  use_builtin_includes = '-nobuiltininc' not in flags

  language_is_cpp, use_libcpp, sysroot = _ExtractInfoForMacIncludePaths( flags )

  toolchain = _FindMacToolchain()

  if ( language_is_cpp and
       use_standard_cpp_includes and
       use_standard_system_includes and
       use_libcpp ):
    if toolchain:
      flags.extend( [
        '-isystem', os.path.join( toolchain, 'usr/include/c++/v1' ) ] )
    flags.extend( [
      '-isystem', os.path.join( sysroot, 'usr/include/c++/v1' ) ] )

  if use_standard_system_includes:
    flags.extend( [
      '-isystem', os.path.join( sysroot, 'usr/local/include' ) ] )
    # Apple Clang always adds /usr/local/include to the list of system header
    # directories even if sysroot is not the root directory.
    if sysroot != '/':
      flags.extend( [ '-isystem', '/usr/local/include' ] )

  if use_builtin_includes:
    flags.extend( [
      '-isystem', os.path.join( CLANG_RESOURCE_DIR, 'include' ) ] )

  if use_standard_system_includes:
    if toolchain:
      flags.extend( [
        '-isystem', os.path.join( toolchain, 'usr/include' ) ] )
    flags.extend( [
      '-isystem',    os.path.join( sysroot, 'usr/include' ),
      '-iframework', os.path.join( sysroot, 'System/Library/Frameworks' ),
      '-iframework', os.path.join( sysroot, 'Library/Frameworks' ) ] )

  return flags


def _EnableTypoCorrection( flags ):
  """Adds the -fspell-checking flag if the -fno-spell-checking flag is not
  present"""

  # "Typo correction" (aka spell checking) in clang allows it to produce
  # hints (in the form of fix-its) in the case of certain diagnostics. A common
  # example is "no type named 'strng' in namespace 'std'; Did you mean
  # 'string'? (FixIt)". This is enabled by default in the clang driver (i.e. the
  # 'clang' binary), but is not when using libclang (as we do). It's a useful
  # enough feature that we just always turn it on unless the user explicitly
  # turned it off in their flags (with -fno-spell-checking).
  if '-fno-spell-checking' in flags:
    return flags

  flags.append( '-fspell-checking' )
  return flags


def _MakeRelativePathsInFlagsAbsolute( flags, working_directory ):
  if not working_directory:
    return list( flags )
  new_flags = []
  make_next_absolute = False
  path_flags = ( PATH_FLAGS + INCLUDE_FLAGS_WIN_STYLE
                 if _ShouldAllowWinStyleFlags( flags )
                 else PATH_FLAGS )
  for flag in flags:
    new_flag = flag

    if make_next_absolute:
      make_next_absolute = False
      if not os.path.isabs( new_flag ):
        new_flag = os.path.join( working_directory, flag )
      new_flag = os.path.normpath( new_flag )
    else:
      for path_flag in path_flags:
        # Single dash argument alone, e.g. -isysroot <path>
        if flag == path_flag:
          make_next_absolute = True
          break

        # Single dash argument with inbuilt path, e.g. -isysroot<path>
        # or double-dash argument, e.g. --isysroot=<path>
        if flag.startswith( path_flag ):
          path = flag[ len( path_flag ): ]
          if not os.path.isabs( path ):
            path = os.path.join( working_directory, path )
          path = os.path.normpath( path )

          new_flag = '{0}{1}'.format( path_flag, path )
          break

    if new_flag:
      new_flags.append( new_flag )
  return new_flags


# Find the compilation info structure from the supplied database for the
# supplied file. If the source file is a header, try and find an appropriate
# source file and return the compilation_info for that.
def _GetCompilationInfoForFile( database, file_name, file_extension ):
  # Ask the database for the flags.
  compilation_info = database.GetCompilationInfoForFile( file_name )
  if compilation_info.compiler_flags_:
    return compilation_info

  # The compilation_commands.json file generated by CMake does not have entries
  # for header files. So we do our best by asking the db for flags for a
  # corresponding source file, if any. If one exists, the flags for that file
  # should be good enough.
  if file_extension in HEADER_EXTENSIONS:
    for extension in SOURCE_EXTENSIONS:
      replacement_file = os.path.splitext( file_name )[ 0 ] + extension
      compilation_info = database.GetCompilationInfoForFile(
        replacement_file )
      if compilation_info and compilation_info.compiler_flags_:
        return compilation_info

  # No corresponding source file was found, so we can't generate any flags for
  # this source file.
  return None


def UserIncludePaths( user_flags, filename ):
  """
  Returns a tuple ( quoted_include_paths, include_paths )

  quoted_include_paths is a list of include paths that are only suitable for
  quoted include statement.
  include_paths is a list of include paths that can be used for angle bracketed
  and quoted include statement.
  """
  quoted_include_paths = [ ToUnicode( os.path.dirname( filename ) ) ]
  include_paths = []
  framework_paths = []

  if user_flags:
    include_flags = { '-iquote':     quoted_include_paths,
                      '-I':          include_paths,
                      '-isystem':    include_paths,
                      '-F':          framework_paths,
                      '-iframework': framework_paths }
    if _ShouldAllowWinStyleFlags( user_flags ):
      include_flags[ '/I' ] = include_paths

    try:
      it = iter( user_flags )
      for user_flag in it:
        user_flag_len = len( user_flag )
        for flag in include_flags:
          if user_flag.startswith( flag ):
            flag_len = len( flag )
            include_path = ( next( it ) if user_flag_len == flag_len else
                             user_flag[ flag_len: ] )
            if include_path:
              container = include_flags[ flag ]
              container.append( ToUnicode( include_path ) )
            break
    except StopIteration:
      pass

  return quoted_include_paths, include_paths, framework_paths
