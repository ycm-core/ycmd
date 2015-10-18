#!/usr/bin/env python
#
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

import ycm_core
import os
import inspect
from ycmd import extra_conf_store
from ycmd.utils import ToUtf8IfNeeded, OnMac, OnWindows
from ycmd.responses import NoExtraConfDetected

INCLUDE_FLAGS = [ '-isystem', '-I', '-iquote', '--sysroot=', '-isysroot',
                  '-include', '-iframework', '-F', '-imacros' ]

# We need to remove --fcolor-diagnostics because it will cause shell escape
# sequences to show up in editors, which is bad. See Valloric/YouCompleteMe#1421
STATE_FLAGS_TO_SKIP = set(['-c', '-MP', '--fcolor-diagnostics'])

# The -M* flags spec:
#   https://gcc.gnu.org/onlinedocs/gcc-4.9.0/gcc/Preprocessor-Options.html
FILE_FLAGS_TO_SKIP = set(['-MD', '-MMD', '-MF', '-MT', '-MQ', '-o'])

# These are the standard header search paths that clang will use on Mac BUT
# libclang won't, for unknown reasons. We add these paths when the user is on a
# Mac because if we don't, libclang would fail to find <vector> etc.
# This should be fixed upstream in libclang, but until it does, we need to help
# users out.
# See Valloric/YouCompleteMe#303 for details.
MAC_INCLUDE_PATHS = [
 '/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/include/c++/v1',
 '/usr/local/include',
 '/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/include',
 '/usr/include',
 '/System/Library/Frameworks',
 '/Library/Frameworks',
]


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

      flags = list( results[ 'flags' ] )
      if not flags:
        return None

      if add_extra_clang_flags:
        flags += self.extra_clang_flags
      sanitized_flags = PrepareFlagsForClang( flags, filename )

      if results[ 'do_cache' ]:
        self.flags_for_file[ filename ] = sanitized_flags
      return sanitized_flags


  def UserIncludePaths( self, filename, client_data ):
    flags = self.FlagsForFile( filename, client_data = client_data )

    quoted_include_paths = [ os.path.dirname( filename ) ]
    include_paths = []

    if flags:
      quote_flag = '-iquote'
      path_flags = [ '-isystem', '-I' ]

      try:
        it = iter(flags)
        for flag in it:
          flag_len = len( flag )
          if flag.startswith( quote_flag ):
            quote_flag_len = len( quote_flag )
            # Add next flag to the include paths if current flag equals to
            # '-iquote', or add remaining string otherwise.
            quoted_include_paths.append( it.next() if flag_len == quote_flag_len
                                                 else flag[ quote_flag_len: ] )
          else:
            for path_flag in path_flags:
              if flag.startswith( path_flag ):
                path_flag_len = len( path_flag )
                include_paths.append( it.next() if flag_len == path_flag_len
                                              else flag[ path_flag_len: ] )
                break
      except StopIteration:
        pass

    return ( [ x for x in quoted_include_paths if x ],
             [ x for x in include_paths if x ] )


  def Clear( self ):
    self.flags_for_file.clear()


def _CallExtraConfFlagsForFile( module, filename, client_data ):
  filename = ToUtf8IfNeeded( filename )
  # For the sake of backwards compatibility, we need to first check whether the
  # FlagsForFile function in the extra conf module even allows keyword args.
  if inspect.getargspec( module.FlagsForFile ).keywords:
    return module.FlagsForFile( filename, client_data = client_data )
  else:
    return module.FlagsForFile( filename )


def PrepareFlagsForClang( flags, filename ):
  flags = _CompilerToLanguageFlag( flags )
  flags = _RemoveXclangFlags( flags )
  flags = _RemoveUnusedFlags( flags, filename )
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
    vector.append( ToUtf8IfNeeded( flag ) )
  return vector


def _CompilerToLanguageFlag( flags ):
  """When flags come from the compile_commands.json file, the first flag is
  usually the path to the compiler that should be invoked. We want to replace
  it with a corresponding language flag.
  E.g., -x c for gcc and -x c++ for g++."""

  # First flag doesn't start with a '-', so it's probably a compiler.
  if not flags[ 0 ].startswith( '-' ):

    # If the compiler ends with '++', it's probably a C++ compiler
    # (E.g., c++, g++, clang++, etc).
    if flags[ 0 ].endswith( '++' ):
        language = 'c++'
    else:
        language = 'c'

    flags = [ '-x', language ] + flags[ 1: ]

  return flags


def _RemoveUnusedFlags( flags, filename ):
  """Given an iterable object that produces strings (flags for Clang), removes
  the '-c' and '-o' options that Clang does not like to see when it's producing
  completions for a file. Same for '-MD' etc.

  We also try to remove any stray filenames in the flags that aren't include
  dirs."""

  new_flags = []

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
      skip_next = True;
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


def _ExtraClangFlags():
  flags = _SpecialClangIncludes()
  if OnMac():
    for path in MAC_INCLUDE_PATHS:
      flags.extend( [ '-isystem', path ] )
  # On Windows, parsing of templates is delayed until instantation time.
  # This makes GetType and GetParent commands not returning the expected
  # result when the cursor is in templates.
  # Using the -fno-delayed-template-parsing flag disables this behavior.
  # See http://clang.llvm.org/extra/PassByValueTransform.html#note-about-delayed-template-parsing
  # for an explanation of the flag and
  # https://code.google.com/p/include-what-you-use/source/detail?r=566
  # for a similar issue.
  if OnWindows():
    flags.append( '-fno-delayed-template-parsing' )
  return flags


def _SpecialClangIncludes():
  libclang_dir = os.path.dirname( ycm_core.__file__ )
  path_to_includes = os.path.join( libclang_dir, 'clang_includes' )
  return [ '-isystem', path_to_includes ]


