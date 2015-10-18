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

from nose.tools import eq_
from .. import flags


def SanitizeFlags_Passthrough_test():
  eq_( [ '-foo', '-bar' ],
       list( flags._SanitizeFlags( [ '-foo', '-bar' ] ) ) )


def SanitizeFlags_ArchRemoved_test():
  expected = [ '-foo', '-bar' ]
  to_remove = [ '-arch', 'arch_of_evil' ]

  eq_( expected,
       list( flags._SanitizeFlags( expected + to_remove ) ) )

  eq_( expected,
       list( flags._SanitizeFlags( to_remove + expected ) ) )

  eq_( expected,
       list( flags._SanitizeFlags(
         expected[ :1 ] + to_remove + expected[ -1: ] ) ) )


def RemoveUnusedFlags_Passthrough_test():
  eq_( [ '-foo', '-bar' ],
       flags._RemoveUnusedFlags( [ '-foo', '-bar' ], 'file' ) )


def RemoveUnusedFlags_RemoveDashC_test():
  expected = [ '-foo', '-bar' ]
  to_remove = [ '-c' ]
  filename = 'file'

  eq_( expected,
       flags._RemoveUnusedFlags( expected + to_remove, filename ) )

  eq_( expected,
       flags._RemoveUnusedFlags( to_remove + expected, filename ) )

  eq_( expected,
       flags._RemoveUnusedFlags(
         expected[ :1 ] + to_remove + expected[ -1: ], filename ) )


def RemoveUnusedFlags_RemoveColor_test():
  expected = [ '-foo', '-bar' ]
  to_remove = [ '--fcolor-diagnostics' ]
  filename = 'file'

  eq_( expected,
       flags._RemoveUnusedFlags( expected + to_remove, filename ) )

  eq_( expected,
       flags._RemoveUnusedFlags( to_remove + expected, filename ) )

  eq_( expected,
       flags._RemoveUnusedFlags(
         expected[ :1 ] + to_remove + expected[ -1: ], filename ) )


def RemoveUnusedFlags_RemoveDashO_test():
  expected = [ '-foo', '-bar' ]
  to_remove = [ '-o', 'output_name' ]
  filename = 'file'

  eq_( expected,
       flags._RemoveUnusedFlags( expected + to_remove, filename ) )

  eq_( expected,
       flags._RemoveUnusedFlags( to_remove + expected, filename ) )

  eq_( expected,
       flags._RemoveUnusedFlags(
         expected[ :1 ] + to_remove + expected[ -1: ], filename ) )


def RemoveUnusedFlags_RemoveMP_test():
  expected = [ '-foo', '-bar' ]
  to_remove = [ '-MP' ]
  filename = 'file'

  eq_( expected,
       flags._RemoveUnusedFlags( expected + to_remove, filename ) )

  eq_( expected,
       flags._RemoveUnusedFlags( to_remove + expected, filename ) )

  eq_( expected,
       flags._RemoveUnusedFlags(
         expected[ :1 ] + to_remove + expected[ -1: ], filename ) )


def RemoveUnusedFlags_RemoveFilename_test():
  expected = [ '-foo', '-bar' ]
  to_remove = [ 'file' ]
  filename = 'file'

  eq_( expected,
       flags._RemoveUnusedFlags( expected + to_remove, filename ) )

  eq_( expected,
       flags._RemoveUnusedFlags( to_remove + expected, filename ) )

  eq_( expected,
       flags._RemoveUnusedFlags(
         expected[ :1 ] + to_remove + expected[ -1: ], filename ) )


def RemoveUnusedFlags_RemoveFlagWithoutPrecedingDashFlag_test():
  expected = [ '-foo', '-x', 'c++', '-bar', 'include_dir' ]
  to_remove = [ 'unrelated_file' ]
  filename = 'file'

  eq_( expected,
       flags._RemoveUnusedFlags( expected + to_remove, filename ) )

  eq_( expected,
       flags._RemoveUnusedFlags( to_remove + expected, filename ) )


def RemoveUnusedFlags_RemoveFilenameWithoutPrecedingInclude_test():
  def tester( flag ):
    expected = [ flag, '/foo/bar', '-isystem/zoo/goo' ]

    eq_( expected,
         flags._RemoveUnusedFlags( expected + to_remove, filename ) )

    eq_( expected,
         flags._RemoveUnusedFlags( to_remove + expected, filename ) )

    eq_( expected + expected,
         flags._RemoveUnusedFlags( expected + to_remove + expected,
                                   filename ) )

  include_flags = [ '-isystem', '-I', '-iquote', '--sysroot=', '-isysroot',
                    '-include', '-iframework', '-F', '-imacros' ]
  to_remove = [ '/moo/boo' ]
  filename = 'file'

  for flag in include_flags:
    yield tester, flag



def RemoveXclangFlags_test():
  expected = [ '-I', '/foo/bar', '-DMACRO=Value' ]
  to_remove = [ '-Xclang', 'load', '-Xclang', 'libplugin.so',
                '-Xclang', '-add-plugin', '-Xclang', 'plugin-name' ]

  eq_( expected,
       flags._RemoveXclangFlags( expected + to_remove ) )

  eq_( expected,
       flags._RemoveXclangFlags( to_remove + expected ) )

  eq_( expected + expected,
       flags._RemoveXclangFlags( expected + to_remove + expected ) )


def CompilerToLanguageFlag_Passthrough_test():
  eq_( [ '-foo', '-bar' ],
       flags._CompilerToLanguageFlag( [ '-foo', '-bar' ] ) )


def CompilerToLanguageFlag_ReplaceCCompiler_test():
  def tester( path ):
    eq_( [ '-x', 'c' ] + expected,
        flags._CompilerToLanguageFlag( [ path ] + expected ) )

  compiler_paths = [ 'cc', 'gcc', 'clang', '/usr/bin/cc',
                     '/some/other/path', 'some_command' ]
  expected = [ '-foo', '-bar' ]

  for compiler in compiler_paths:
    yield tester, compiler


def CompilerToLanguageFlag_ReplaceCppCompiler_test():
  def tester( path ):
    eq_( [ '-x', 'c++' ] + expected,
        flags._CompilerToLanguageFlag( [ path ] + expected ) )

  compiler_paths = [ 'c++', 'g++', 'clang++', '/usr/bin/c++',
                     '/some/other/path++', 'some_command++' ]
  expected = [ '-foo', '-bar' ]

  for compiler in compiler_paths:
    yield tester, compiler
