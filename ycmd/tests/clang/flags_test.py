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

from nose.tools import eq_, ok_
from ycmd.completers.cpp import flags
from mock import patch, Mock
from ycmd.tests.test_utils import MacOnly

from hamcrest import assert_that, contains


@patch( 'ycmd.extra_conf_store.ModuleForSourceFile', return_value = Mock() )
def FlagsForFile_BadNonUnicodeFlagsAreAlsoRemoved_test( *args ):
  fake_flags = {
    'flags': [ bytes( b'-c' ), '-c', bytes( b'-foo' ), '-bar' ]
  }

  with patch( 'ycmd.completers.cpp.flags._CallExtraConfFlagsForFile',
              return_value = fake_flags ):
    flags_object = flags.Flags()
    flags_list = flags_object.FlagsForFile( '/foo', False )
    eq_( list( flags_list ), [ '-foo', '-bar' ] )


@patch( 'ycmd.extra_conf_store.ModuleForSourceFile', return_value = Mock() )
def FlagsForFile_FlagsCachedByDefault_test( *args ):
  flags_object = flags.Flags()

  results = { 'flags': [ '-x', 'c' ] }
  with patch( 'ycmd.completers.cpp.flags._CallExtraConfFlagsForFile',
              return_value = results ):
    flags_list = flags_object.FlagsForFile( '/foo', False )
    assert_that( flags_list, contains( '-x', 'c' ) )

  results[ 'flags' ] = [ '-x', 'c++' ]
  with patch( 'ycmd.completers.cpp.flags._CallExtraConfFlagsForFile',
              return_value = results ):
    flags_list = flags_object.FlagsForFile( '/foo', False )
    assert_that( flags_list, contains( '-x', 'c' ) )


@patch( 'ycmd.extra_conf_store.ModuleForSourceFile', return_value = Mock() )
def FlagsForFile_FlagsNotCachedWhenDoCacheIsFalse_test( *args ):
  flags_object = flags.Flags()

  results = {
    'flags': [ '-x', 'c' ],
    'do_cache': False
  }
  with patch( 'ycmd.completers.cpp.flags._CallExtraConfFlagsForFile',
              return_value = results ):
    flags_list = flags_object.FlagsForFile( '/foo', False )
    assert_that( flags_list, contains( '-x', 'c' ) )

  results[ 'flags' ] = [ '-x', 'c++' ]
  with patch( 'ycmd.completers.cpp.flags._CallExtraConfFlagsForFile',
              return_value = results ):
    flags_list = flags_object.FlagsForFile( '/foo', False )
    assert_that( flags_list, contains( '-x', 'c++' ) )


@patch( 'ycmd.extra_conf_store.ModuleForSourceFile', return_value = Mock() )
def FlagsForFile_FlagsCachedWhenDoCacheIsTrue_test( *args ):
  flags_object = flags.Flags()

  results = {
    'flags': [ '-x', 'c' ],
    'do_cache': True
  }
  with patch( 'ycmd.completers.cpp.flags._CallExtraConfFlagsForFile',
              return_value = results ):
    flags_list = flags_object.FlagsForFile( '/foo', False )
    assert_that( flags_list, contains( '-x', 'c' ) )

  results[ 'flags' ] = [ '-x', 'c++' ]
  with patch( 'ycmd.completers.cpp.flags._CallExtraConfFlagsForFile',
              return_value = results ):
    flags_list = flags_object.FlagsForFile( '/foo', False )
    assert_that( flags_list, contains( '-x', 'c' ) )


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
  expected = [ 'foo', '-bar' ]
  to_remove = [ 'file' ]
  filename = 'file'

  eq_( expected,
       flags._RemoveUnusedFlags( expected + to_remove, filename ) )

  eq_( expected,
       flags._RemoveUnusedFlags( expected[ :1 ] + to_remove + expected[ 1: ],
                                 filename ) )

  eq_( expected,
       flags._RemoveUnusedFlags(
         expected[ :1 ] + to_remove + expected[ -1: ], filename ) )


def RemoveUnusedFlags_RemoveFlagWithoutPrecedingDashFlag_test():
  expected = [ 'g++', '-foo', '-x', 'c++', '-bar', 'include_dir' ]
  to_remove = [ 'unrelated_file' ]
  filename = 'file'

  eq_( expected,
       flags._RemoveUnusedFlags( expected + to_remove, filename ) )

  eq_( expected,
       flags._RemoveUnusedFlags( expected[ :1 ] + to_remove + expected[ 1: ],
                                 filename ) )


def RemoveUnusedFlags_Depfiles_test():
  full_flags = [
    '/bin/clang',
    '-x', 'objective-c',
    '-arch', 'armv7',
    '-MMD',
    '-MT', 'dependencies',
    '-MF', 'file',
    '--serialize-diagnostics', 'diagnostics'
  ]

  expected = [
    '/bin/clang',
    '-x', 'objective-c',
    '-arch', 'armv7',
  ]

  assert_that( flags._RemoveUnusedFlags( full_flags, 'test.m' ),
               contains( *expected ) )


def EnableTypoCorrection_Empty_test():
  eq_( flags._EnableTypoCorrection( [] ), [ '-fspell-checking' ] )


def EnableTypoCorrection_Trivial_test():
  eq_( flags._EnableTypoCorrection( [ '-x', 'c++' ] ),
                                    [ '-x', 'c++', '-fspell-checking' ] )


def EnableTypoCorrection_Reciprocal_test():
  eq_( flags._EnableTypoCorrection( [ '-fno-spell-checking' ] ),
                                    [ '-fno-spell-checking' ] )


def EnableTypoCorrection_ReciprocalOthers_test():
  eq_( flags._EnableTypoCorrection( [ '-x', 'c++', '-fno-spell-checking' ] ),
                                    [ '-x', 'c++', '-fno-spell-checking' ] )


def RemoveUnusedFlags_RemoveFilenameWithoutPrecedingInclude_test():
  def tester( flag ):
    expected = [ 'clang', flag, '/foo/bar', '-isystem/zoo/goo' ]

    eq_( expected,
         flags._RemoveUnusedFlags( expected + to_remove, filename ) )

    eq_( expected,
         flags._RemoveUnusedFlags( expected[ :1 ] + to_remove + expected[ 1: ],
                                   filename ) )

    eq_( expected + expected[ 1: ],
         flags._RemoveUnusedFlags( expected + to_remove + expected[ 1: ],
                                   filename ) )

  include_flags = [ '-isystem', '-I', '-iquote', '-isysroot', '--sysroot',
                    '-gcc-toolchain', '-include', '-include-pch',
                    '-iframework', '-F', '-imacros' ]
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


def _ReplaceCompilerTester( compiler, language ):
  to_removes = [
    [],
    [ '/usr/bin/ccache' ],
    [ 'some_command', 'another_command' ]
  ]
  expected = [ '-foo', '-bar' ]

  for to_remove in to_removes:
    eq_( [ compiler, '-x', language ] + expected,
         flags._CompilerToLanguageFlag( to_remove + [ compiler ] + expected ) )


def CompilerToLanguageFlag_ReplaceCCompiler_test():
  compilers = [ 'cc', 'gcc', 'clang', '/usr/bin/cc',
                '/some/other/path', 'some_command' ]

  for compiler in compilers:
    yield _ReplaceCompilerTester, compiler, 'c'


def CompilerToLanguageFlag_ReplaceCppCompiler_test():
  compilers = [ 'c++', 'g++', 'clang++', '/usr/bin/c++',
                '/some/other/path++', 'some_command++',
                'c++-5', 'g++-5.1', 'clang++-3.7.3', '/usr/bin/c++-5',
                'c++-5.11', 'g++-50.1.49', 'clang++-3.12.3', '/usr/bin/c++-10',
                '/some/other/path++-4.9.3', 'some_command++-5.1',
                '/some/other/path++-4.9.31', 'some_command++-5.10' ]

  for compiler in compilers:
    yield _ReplaceCompilerTester, compiler, 'c++'


def ExtraClangFlags_test():
  flags_object = flags.Flags()
  num_found = 0
  for flag in flags_object.extra_clang_flags:
    if flag.startswith( '-resource-dir=' ):
      ok_( flag.endswith( 'clang_includes' ) )
      num_found += 1

  eq_( 1, num_found )


@MacOnly
@patch( 'ycmd.completers.cpp.flags._GetMacClangVersionList',
        return_value = [ '1.0.0', '7.0.1', '7.0.2', '___garbage__' ] )
@patch( 'ycmd.completers.cpp.flags._MacClangIncludeDirExists',
        side_effect = [ False, True, True, True ] )
def Mac_LatestMacClangIncludes_test( *args ):
  eq_( flags._LatestMacClangIncludes(),
       [ '/Applications/Xcode.app/Contents/Developer/Toolchains/'
         'XcodeDefault.xctoolchain/usr/lib/clang/7.0.2/include' ] )


@MacOnly
def Mac_LatestMacClangIncludes_NoSuchDirectory_test():
  def RaiseOSError( x ):
    raise OSError( x )

  with patch( 'os.listdir', side_effect = RaiseOSError ):
    eq_( flags._LatestMacClangIncludes(), [] )


@MacOnly
def Mac_PathsForAllMacToolchains_test():
  eq_( flags._PathsForAllMacToolchains( 'test' ),
       [ '/Applications/Xcode.app/Contents/Developer/Toolchains/'
         'XcodeDefault.xctoolchain/test',
         '/Library/Developer/CommandLineTools/test' ] )
