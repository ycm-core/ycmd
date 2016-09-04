# Copyright (C) 2011, 2012 Google Inc.
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
from future import standard_library
standard_library.install_aliases()
from builtins import *  # noqa

import ycm_core
import os
import inspect
import re
from future.utils import PY2, native
from ycmd import extra_conf_store
from ycmd.utils import ( ToCppStringCompatible, OnMac, OnWindows, ToUnicode,
                         ToBytes )
from ycmd.responses import NoExtraConfDetected

INCLUDE_FLAGS = [ '-isystem', '-I', '-iquote', '-isysroot', '--sysroot',
                  '-gcc-toolchain', '-include', '-include-pch', '-iframework',
                  '-F', '-imacros' ]

# We need to remove --fcolor-diagnostics because it will cause shell escape
# sequences to show up in editors, which is bad. See Valloric/YouCompleteMe#1421
STATE_FLAGS_TO_SKIP = set( [ '-c',
                             '-MP',
                             '-MD',
                             '-MMD',
                             '--fcolor-diagnostics' ] )

# The -M* flags spec:
#   https://gcc.gnu.org/onlinedocs/gcc-4.9.0/gcc/Preprocessor-Options.html
FILE_FLAGS_TO_SKIP = set( [ '-MF',
                            '-MT',
                            '-MQ',
                            '-o',
                            '--serialize-diagnostics' ] )

# Use a regex to correctly detect c++/c language for both versioned and
# non-versioned compiler executable names suffixes
# (e.g., c++, g++, clang++, g++-4.9, clang++-3.7, c++-10.2 etc).
# See Valloric/ycmd#266
CPP_COMPILER_REGEX = re.compile( r'\+\+(-\d+(\.\d+){0,2})?$' )


class Flags( object ):
  """Keeps track of the flags necessary to compile a file.
  The flags are loaded from user-created python files (hereafter referred to as
  'modules') that contain a method FlagsForFile( filename )."""

  def __init__( self ):
    # It's caches all the way down...
    self.flags_for_file = {}
    self.extra_clang_flags = _ExtraClangFlags()
    self.no_extra_conf_file_warning_posted = False


  def FlagsForFile( self,
                    filename,
                    add_extra_clang_flags = True,
                    client_data = None ):
    try:
      return self.flags_for_file[ filename ]
    except KeyError:
      module = extra_conf_store.ModuleForSourceFile( filename )
      if not module:
        if not self.no_extra_conf_file_warning_posted:
          self.no_extra_conf_file_warning_posted = True
          raise NoExtraConfDetected
        return None

      results = _CallExtraConfFlagsForFile( module,
                                            filename,
                                            client_data )

      if not results or not results.get( 'flags_ready', True ):
        return None

      flags = _ExtractFlagsList( results )
      if not flags:
        return None

      if add_extra_clang_flags:
        flags += self.extra_clang_flags

      sanitized_flags = PrepareFlagsForClang( flags,
                                              filename,
                                              add_extra_clang_flags )

      if results.get( 'do_cache', True ):
        self.flags_for_file[ filename ] = sanitized_flags
      return sanitized_flags


  def UserIncludePaths( self, filename, client_data ):
    flags = [ ToUnicode( x ) for x in
              self.FlagsForFile( filename, client_data = client_data ) ]

    quoted_include_paths = [ os.path.dirname( filename ) ]
    include_paths = []

    if flags:
      quote_flag = '-iquote'
      path_flags = [ '-isystem', '-I' ]

      try:
        it = iter( flags )
        for flag in it:
          flag_len = len( flag )
          if flag.startswith( quote_flag ):
            quote_flag_len = len( quote_flag )
            # Add next flag to the include paths if current flag equals to
            # '-iquote', or add remaining string otherwise.
            quoted_include_paths.append( next( it )
                                         if flag_len == quote_flag_len
                                         else flag[ quote_flag_len: ] )
          else:
            for path_flag in path_flags:
              if flag.startswith( path_flag ):
                path_flag_len = len( path_flag )
                include_paths.append( next( it )
                                      if flag_len == path_flag_len
                                      else flag[ path_flag_len: ] )
                break
      except StopIteration:
        pass

    return ( [ x for x in quoted_include_paths if x ],
             [ x for x in include_paths if x ] )


  def Clear( self ):
    self.flags_for_file.clear()


def _ExtractFlagsList( flags_for_file_output ):
  return [ ToUnicode( x ) for x in flags_for_file_output[ 'flags' ] ]


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

  # For the sake of backwards compatibility, we need to first check whether the
  # FlagsForFile function in the extra conf module even allows keyword args.
  if inspect.getargspec( module.FlagsForFile ).keywords:
    return module.FlagsForFile( filename, client_data = client_data )
  else:
    return module.FlagsForFile( filename )


def PrepareFlagsForClang( flags, filename, add_extra_clang_flags = True ):
  flags = _CompilerToLanguageFlag( flags )
  flags = _RemoveXclangFlags( flags )
  flags = _RemoveUnusedFlags( flags, filename )
  if add_extra_clang_flags:
    flags = _EnableTypoCorrection( flags )
  flags = _SanitizeFlags( flags )
  return flags


def _RemoveXclangFlags( flags ):
  """Drops -Xclang flags.  These are typically used to pass in options to
  clang cc1 which are not used in the front-end, so they are not needed for
  code completion."""

  sanitized_flags = []
  saw_xclang = False
  for i, flag in enumerate( flags ):
    if flag == '-Xclang':
      saw_xclang = True
      continue
    elif saw_xclang:
      saw_xclang = False
      continue

    sanitized_flags.append( flag )

  return sanitized_flags


def _SanitizeFlags( flags ):
  """Drops unsafe flags. Currently these are only -arch flags; they tend to
  crash libclang."""

  sanitized_flags = []
  saw_arch = False
  for i, flag in enumerate( flags ):
    if flag == '-arch':
      saw_arch = True
      continue
    elif flag.startswith( '-arch' ):
      continue
    elif saw_arch:
      saw_arch = False
      continue

    sanitized_flags.append( flag )

  vector = ycm_core.StringVector()
  for flag in sanitized_flags:
    vector.append( ToCppStringCompatible( flag ) )
  return vector


def _RemoveFlagsPrecedingCompiler( flags ):
  """Assuming that the flag just before the first flag (which starts with a
  dash) is the compiler path, removes all flags preceding it."""

  for index, flag in enumerate( flags ):
    if flag.startswith( '-' ):
      return ( flags[ index - 1: ] if index > 1 else
               flags )
  return flags[ :-1 ]


def _CompilerToLanguageFlag( flags ):
  """When flags come from the compile_commands.json file, the flag preceding
  the first flag starting with a dash is usually the path to the compiler that
  should be invoked.  We want to replace it with a corresponding language flag.
  E.g., -x c for gcc and -x c++ for g++."""

  flags = _RemoveFlagsPrecedingCompiler( flags )

  # First flag is now the compiler path or a flag starting with a dash
  if flags[ 0 ].startswith( '-' ):
    return flags

  language = ( 'c++' if CPP_COMPILER_REGEX.search( flags[ 0 ] ) else
               'c' )

  return flags[ :1 ] + [ '-x', language ] + flags[ 1: ]


def _RemoveUnusedFlags( flags, filename ):
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
  previous_flag_is_include = False
  previous_flag_starts_with_dash = False
  current_flag_starts_with_dash = False

  for flag in flags:
    previous_flag_starts_with_dash = current_flag_starts_with_dash
    current_flag_starts_with_dash = flag.startswith( '-' )

    if skip_next:
      skip_next = False
      continue

    if flag in STATE_FLAGS_TO_SKIP:
      continue

    if flag in FILE_FLAGS_TO_SKIP:
      skip_next = True
      continue

    if flag == filename or os.path.realpath( flag ) == filename:
      continue

    # We want to make sure that we don't have any stray filenames in our flags;
    # filenames that are part of include flags are ok, but others are not. This
    # solves the case where we ask the compilation database for flags for
    # "foo.cpp" when we are compiling "foo.h" because the comp db doesn't have
    # flags for headers. The returned flags include "foo.cpp" and we need to
    # remove that.
    if ( not current_flag_starts_with_dash and
          ( not previous_flag_starts_with_dash or
            ( not previous_flag_is_include and '/' in flag ) ) ):
      continue

    new_flags.append( flag )
    previous_flag_is_include = flag in INCLUDE_FLAGS
  return new_flags


# There are 2 ways to get a development enviornment (as standard) on OS X:
#  - install XCode.app, or
#  - install the command-line tools (xcode-select --install)
#
# Most users have xcode installed, but in order to be as compatible as
# possible we consider both possible installation locations
MAC_CLANG_TOOLCHAIN_DIRS = [
  '/Applications/Xcode.app/Contents/Developer/Toolchains/'
    'XcodeDefault.xctoolchain',
  '/Library/Developer/CommandLineTools'
]


# Returns a list containing the supplied path as a suffix of each of the known
# Mac toolchains
def _PathsForAllMacToolchains( path ):
  return [ os.path.join( x, path ) for x in MAC_CLANG_TOOLCHAIN_DIRS ]


# Ultimately, this method exists only for testability
def _GetMacClangVersionList( candidates_dir ):
  try:
    return os.listdir( candidates_dir )
  except OSError:
    # Path might not exist, so just ignore
    return []


# Ultimately, this method exists only for testability
def _MacClangIncludeDirExists( candidate_include ):
  return os.path.exists( candidate_include )


# Add in any clang headers found in the installed toolchains. These are
# required for the same reasons as described below, but unfortuantely, these
# are in versioned directories and there is no easy way to find the "correct"
# version. We simply pick the highest version in the first toolchain that we
# find, as this is the most likely to be correct.
def _LatestMacClangIncludes():
  for path in MAC_CLANG_TOOLCHAIN_DIRS:
    # we use the first toolchain which actually contains any versions, rather
    # than trying all of the toolchains and picking the highest. We
    # favour Xcode over CommandLineTools as using Xcode is more common.
    # It might be possible to extrace this information from xcode-select, though
    # xcode-select -p does not point at the toolchain directly
    candidates_dir = os.path.join( path, 'usr', 'lib', 'clang' )
    versions = _GetMacClangVersionList( candidates_dir )

    for version in reversed( sorted( versions ) ):
      candidate_include = os.path.join( candidates_dir, version, 'include' )
      if _MacClangIncludeDirExists( candidate_include ):
        return [ candidate_include ]

  return []

MAC_INCLUDE_PATHS = []

if OnMac():
  # These are the standard header search paths that clang will use on Mac BUT
  # libclang won't, for unknown reasons. We add these paths when the user is on
  # a Mac because if we don't, libclang would fail to find <vector> etc.  This
  # should be fixed upstream in libclang, but until it does, we need to help
  # users out.
  # See Valloric/YouCompleteMe#303 for details.
  MAC_INCLUDE_PATHS = (
    _PathsForAllMacToolchains( 'usr/include/c++/v1' ) +
    [ '/usr/local/include' ] +
    _PathsForAllMacToolchains( 'usr/include' ) +
    [ '/usr/include', '/System/Library/Frameworks', '/Library/Frameworks' ] +
    _LatestMacClangIncludes()
  )


def _ExtraClangFlags():
  flags = _SpecialClangIncludes()
  if OnMac():
    for path in MAC_INCLUDE_PATHS:
      flags.extend( [ '-isystem', path ] )
  # On Windows, parsing of templates is delayed until instantiation time.
  # This makes GetType and GetParent commands fail to return the expected
  # result when the cursor is in a template.
  # Using the -fno-delayed-template-parsing flag disables this behavior.
  # See
  # http://clang.llvm.org/extra/PassByValueTransform.html#note-about-delayed-template-parsing # noqa
  # for an explanation of the flag and
  # https://code.google.com/p/include-what-you-use/source/detail?r=566
  # for a similar issue.
  if OnWindows():
    flags.append( '-fno-delayed-template-parsing' )
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


def _SpecialClangIncludes():
  libclang_dir = os.path.dirname( ycm_core.__file__ )
  path_to_includes = os.path.join( libclang_dir, 'clang_includes' )
  return [ '-resource-dir=' + path_to_includes ]
