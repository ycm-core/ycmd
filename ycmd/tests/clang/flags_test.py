# Copyright (C) 2011-2021 ycmd contributors
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

import contextlib
import os
from hamcrest import ( assert_that,
                       calling,
                       contains_exactly,
                       empty,
                       equal_to,
                       raises )
from unittest.mock import patch, MagicMock
from unittest import TestCase
from types import ModuleType

from ycmd.completers.cpp import flags
from ycmd.completers.cpp.flags import ShouldAllowWinStyleFlags, INCLUDE_FLAGS
from ycmd.tests.test_utils import ( MacOnly, TemporaryTestDir, WindowsOnly,
                                    TemporaryClangProject )
from ycmd.tests.clang import setUpModule # noqa
from ycmd.utils import CLANG_RESOURCE_DIR
from ycmd.responses import NoExtraConfDetected


@contextlib.contextmanager
def MockExtraConfModule( settings_function ):
  module = MagicMock( spec = ModuleType )
  module.is_global_ycm_extra_conf = False
  setattr( module, settings_function.__name__, settings_function )
  with patch( 'ycmd.extra_conf_store.ModuleForSourceFile',
              return_value = module ):
    yield


def _MakeRelativePathsInFlagsAbsoluteTest( test ):
  wd = test[ 'wd' ] if 'wd' in test else '/test_not'
  assert_that(
    flags._MakeRelativePathsInFlagsAbsolute( test[ 'flags' ], wd ),
    contains_exactly( *test[ 'expect' ] ) )


def _AddLanguageFlagWhenAppropriateTester( compiler, language_flag = [] ):
  to_removes = [
    [],
    [ '/usr/bin/ccache' ],
    [ 'some_command', 'another_command' ]
  ]
  expected = [ '-foo', '-bar' ]

  for to_remove in to_removes:
    assert_that( [ compiler ] + language_flag + expected,
                 equal_to( flags._AddLanguageFlagWhenAppropriate(
                             to_remove + [ compiler ] + expected,
                             ShouldAllowWinStyleFlags( to_remove +
                                                       [ compiler ] +
                                                       expected ) ) ) )


class FlagsTest( TestCase ):
  def test_FlagsForFile_NothingReturned( self ):
    flags_object = flags.Flags()

    def Settings( **kwargs ):
      pass

    with MockExtraConfModule( Settings ):
      flags_list, filename = flags_object.FlagsForFile( '/foo' )
      assert_that( flags_list, empty() )
      assert_that( filename, equal_to( '/foo' ) )


  def test_FlagsForFile_FlagsNotReady( self ):
    flags_object = flags.Flags()

    def Settings( **kwargs ):
      return {
        'flags': [],
        'flags_ready': False
      }

    with MockExtraConfModule( Settings ):
      flags_list, filename = flags_object.FlagsForFile( '/foo', False )
      assert_that( list( flags_list ), equal_to( [] ) )
      assert_that( filename, equal_to( '/foo' ) )


  def test_FlagsForFile_BadNonUnicodeFlagsAreAlsoRemoved( *args ):
    flags_object = flags.Flags()

    def Settings( **kwargs ):
      return {
        'flags': [ bytes( b'-c' ), '-c', bytes( b'-foo' ), '-bar' ]
      }

    with MockExtraConfModule( Settings ):
      flags_list, _ = flags_object.FlagsForFile( '/foo', False )
      assert_that( list( flags_list ), equal_to( [ '-foo', '-bar' ] ) )


  def test_FlagsForFile_FlagsCachedByDefault( self ):
    flags_object = flags.Flags()

    def Settings( **kwargs ):
      return {
        'flags': [ '-x', 'c' ]
      }

    with MockExtraConfModule( Settings ):
      flags_list, _ = flags_object.FlagsForFile( '/foo', False )
      assert_that( flags_list, contains_exactly( '-x', 'c' ) )

    def Settings( **kwargs ):
      return {
        'flags': [ '-x', 'c++' ]
      }

    with MockExtraConfModule( Settings ):
      flags_list, _ = flags_object.FlagsForFile( '/foo', False )
      assert_that( flags_list, contains_exactly( '-x', 'c' ) )


  def test_FlagsForFile_FlagsNotCachedWhenDoCacheIsFalse( self ):
    flags_object = flags.Flags()

    def Settings( **kwargs ):
      return {
        'flags': [ '-x', 'c' ],
        'do_cache': False
      }

    with MockExtraConfModule( Settings ):
      flags_list, _ = flags_object.FlagsForFile( '/foo', False )
      assert_that( flags_list, contains_exactly( '-x', 'c' ) )

    def Settings( **kwargs ):
      return {
        'flags': [ '-x', 'c++' ]
      }

    with MockExtraConfModule( Settings ):
      flags_list, _ = flags_object.FlagsForFile( '/foo', False )
      assert_that( flags_list, contains_exactly( '-x', 'c++' ) )


  def test_FlagsForFile_FlagsCachedWhenDoCacheIsTrue( self ):
    flags_object = flags.Flags()

    def Settings( **kwargs ):
      return {
        'flags': [ '-x', 'c' ],
        'do_cache': True
      }

    with MockExtraConfModule( Settings ):
      flags_list, _ = flags_object.FlagsForFile( '/foo', False )
      assert_that( flags_list, contains_exactly( '-x', 'c' ) )

    def Settings( **kwargs ):
      return {
        'flags': [ '-x', 'c++' ]
      }

    with MockExtraConfModule( Settings ):
      flags_list, _ = flags_object.FlagsForFile( '/foo', False )
      assert_that( flags_list, contains_exactly( '-x', 'c' ) )


  def test_FlagsForFile_DoNotMakeRelativePathsAbsoluteByDefault( self ):
    flags_object = flags.Flags()

    def Settings( **kwargs ):
      return {
        'flags': [ '-x', 'c', '-I', 'header' ]
      }

    with MockExtraConfModule( Settings ):
      flags_list, _ = flags_object.FlagsForFile( '/foo', False )
      assert_that( flags_list,
                   contains_exactly( '-x', 'c',
                             '-I', 'header' ) )


  def test_FlagsForFile_MakeRelativePathsAbsoluteIfOptionSpecified( self ):
    flags_object = flags.Flags()

    def Settings( **kwargs ):
      return {
        'flags': [ '-x', 'c', '-I', 'header' ],
        'include_paths_relative_to_dir': '/working_dir/'
      }

    with MockExtraConfModule( Settings ):
      flags_list, _ = flags_object.FlagsForFile( '/foo', False )
      assert_that( flags_list,
                   contains_exactly( '-x', 'c',
                             '-I', os.path.normpath( '/working_dir/header' ) ) )


  @MacOnly
  @patch( 'os.path.exists', lambda path:
    path in [
      '/usr/include/c++/v1',
      '/System/Library/Frameworks/Foundation.framework/Headers'
    ] )
  def test_FlagsForFile_AddMacIncludePaths_SysRoot_Default( self ):
    flags_object = flags.Flags()

    def Settings( **kwargs ):
      return {
        'flags': [ '-Wall' ]
      }

    with MockExtraConfModule( Settings ):
      flags_list, _ = flags_object.FlagsForFile( '/foo' )
      assert_that( flags_list, contains_exactly(
        '-Wall',
        '-resource-dir=' + CLANG_RESOURCE_DIR,
        '-isystem',    '/usr/include/c++/v1',
        '-isystem',    '/usr/local/include',
        '-isystem',    os.path.join( CLANG_RESOURCE_DIR, 'include' ),
        '-isystem',    '/usr/include',
        '-iframework', '/System/Library/Frameworks',
        '-iframework', '/Library/Frameworks',
        '-fspell-checking' ) )


  @MacOnly
  @patch( 'os.path.exists', lambda path:
    path in [
      '/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform'
            '/Developer/SDKs/MacOSX.sdk/System/Library/Frameworks'
            '/Foundation.framework/Headers'
    ] )
  def test_FlagsForFile_AddMacIncludePaths_SysRoot_Xcode_NoStdlib( self ):
    flags_object = flags.Flags()

    def Settings( **kwargs ):
      return {
        'flags': [ '-Wall' ]
      }

    with MockExtraConfModule( Settings ):
      flags_list, _ = flags_object.FlagsForFile( '/foo' )
      assert_that( flags_list, contains_exactly(
        '-Wall',
        '-resource-dir=' + CLANG_RESOURCE_DIR,
        '-isystem',    '/Applications/Xcode.app/Contents/Developer/Platforms'
                       '/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
                       '/usr/local/include',
        '-isystem',    '/usr/local/include',
        '-isystem',    os.path.join( CLANG_RESOURCE_DIR, 'include' ),
        '-isystem',    '/Applications/Xcode.app/Contents/Developer/Platforms'
                       '/MacOSX.platform/Developer/SDKs/MacOSX.sdk/usr/include',
        '-iframework', '/Applications/Xcode.app/Contents/Developer/Platforms'
                       '/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
                       '/System/Library/Frameworks',
        '-iframework', '/Applications/Xcode.app/Contents/Developer/Platforms'
                       '/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
                       '/Library/Frameworks',
        '-fspell-checking' ) )


  @MacOnly
  @patch( 'os.path.exists', lambda path:
    path in [
      '/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform'
            '/Developer/SDKs/MacOSX.sdk/usr/include/c++/v1',
      '/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform'
            '/Developer/SDKs/MacOSX.sdk/System/Library/Frameworks'
            '/Foundation.framework/Headers'
    ] )
  def test_FlagsForFile_AddMacIncludePaths_SysRoot_Xcode_WithStdlin( self ):
    flags_object = flags.Flags()

    def Settings( **kwargs ):
      return {
        'flags': [ '-Wall' ]
      }

    with MockExtraConfModule( Settings ):
      flags_list, _ = flags_object.FlagsForFile( '/foo' )
      assert_that( flags_list, contains_exactly(
        '-Wall',
        '-resource-dir=' + CLANG_RESOURCE_DIR,
        '-isystem',    '/Applications/Xcode.app/Contents/Developer/Platforms'
                       '/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
                       '/usr/include/c++/v1',
        '-isystem',    '/Applications/Xcode.app/Contents/Developer/Platforms'
                       '/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
                       '/usr/local/include',
        '-isystem',    '/usr/local/include',
        '-isystem',    os.path.join( CLANG_RESOURCE_DIR, 'include' ),
        '-isystem',    '/Applications/Xcode.app/Contents/Developer/Platforms'
                       '/MacOSX.platform/Developer/SDKs/MacOSX.sdk/usr/include',
        '-iframework', '/Applications/Xcode.app/Contents/Developer/Platforms'
                       '/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
                       '/System/Library/Frameworks',
        '-iframework', '/Applications/Xcode.app/Contents/Developer/Platforms'
                       '/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
                       '/Library/Frameworks',
        '-fspell-checking' ) )


  @MacOnly
  @patch( 'os.path.exists', lambda path:
    path in [
      '/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk'
            '/usr/include/c++/v1',
      '/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk'
            '/System/Library/Frameworks/Foundation.framework/Headers'
    ] )
  def test_FlagsForFile_AddMacIncludePaths_SysRoot_CommandLine_WithStdlib(
      self ):
    flags_object = flags.Flags()

    def Settings( **kwargs ):
      return {
        'flags': [ '-Wall' ]
      }

    with MockExtraConfModule( Settings ):
      flags_list, _ = flags_object.FlagsForFile( '/foo' )
      assert_that( flags_list, contains_exactly(
        '-Wall',
        '-resource-dir=' + CLANG_RESOURCE_DIR,
        '-isystem',    '/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk'
                       '/usr/include/c++/v1',
        '-isystem',    '/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk'
                       '/usr/local/include',
        '-isystem',    '/usr/local/include',
        '-isystem',    os.path.join( CLANG_RESOURCE_DIR, 'include' ),
        '-isystem',    '/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk'
                       '/usr/include',
        '-iframework', '/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk'
                       '/System/Library/Frameworks',
        '-iframework', '/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk'
                       '/Library/Frameworks',
        '-fspell-checking' ) )


  @MacOnly
  @patch( 'os.path.exists', lambda path:
    path in [
      '/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk'
            '/System/Library/Frameworks/Foundation.framework/Headers'
    ] )
  def test_FlagsForFile_AddMacIncludePaths_SysRoot_CommandLine_NoStdlib( self ):
    flags_object = flags.Flags()

    def Settings( **kwargs ):
      return {
        'flags': [ '-Wall' ]
      }

    with MockExtraConfModule( Settings ):
      flags_list, _ = flags_object.FlagsForFile( '/foo' )
      assert_that( flags_list, contains_exactly(
        '-Wall',
        '-resource-dir=' + CLANG_RESOURCE_DIR,
        '-isystem',    '/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk'
                       '/usr/local/include',
        '-isystem',    '/usr/local/include',
        '-isystem',    os.path.join( CLANG_RESOURCE_DIR, 'include' ),
        '-isystem',    '/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk'
                       '/usr/include',
        '-iframework', '/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk'
                       '/System/Library/Frameworks',
        '-iframework', '/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk'
                       '/Library/Frameworks',
        '-fspell-checking' ) )


  @MacOnly
  @patch( 'os.path.exists', lambda path:
          path in [
            '/path/to/second/sys/root/usr/include/c++/v1'
          ] )
  def test_FlagsForFile_AddMacIncludePaths_Sysroot_Custom_WithStdlib( self ):
    flags_object = flags.Flags()

    def Settings( **kwargs ):
      return {
        'flags': [ '-Wall',
                   '-isysroot/path/to/first/sys/root',
                   '-isysroot', '/path/to/second/sys/root/',
                   '--sysroot=/path/to/third/sys/root',
                   '--sysroot', '/path/to/fourth/sys/root' ]
      }

    with MockExtraConfModule( Settings ):
      flags_list, _ = flags_object.FlagsForFile( '/foo' )
      assert_that( flags_list, contains_exactly(
        '-Wall',
        '-isysroot/path/to/first/sys/root',
        '-isysroot', '/path/to/second/sys/root/',
        '--sysroot=/path/to/third/sys/root',
        '--sysroot', '/path/to/fourth/sys/root',
        '-resource-dir=' + CLANG_RESOURCE_DIR,
        '-isystem',    '/path/to/second/sys/root/usr/include/c++/v1',
        '-isystem',    '/path/to/second/sys/root/usr/local/include',
        '-isystem',    '/usr/local/include',
        '-isystem',    os.path.join( CLANG_RESOURCE_DIR, 'include' ),
        '-isystem',    '/path/to/second/sys/root/usr/include',
        '-iframework', '/path/to/second/sys/root/System/Library/Frameworks',
        '-iframework', '/path/to/second/sys/root/Library/Frameworks',
        '-fspell-checking' ) )


  @MacOnly
  @patch( 'os.path.exists', lambda path: False )
  def test_FlagsForFile_AddMacIncludePaths_Sysroot_Custom_NoStdlib( self ):
    flags_object = flags.Flags()

    def Settings( **kwargs ):
      return {
        'flags': [ '-Wall',
                   '-isysroot/path/to/first/sys/root',
                   '-isysroot', '/path/to/second/sys/root/',
                   '--sysroot=/path/to/third/sys/root',
                   '--sysroot', '/path/to/fourth/sys/root' ]
      }

    with MockExtraConfModule( Settings ):
      flags_list, _ = flags_object.FlagsForFile( '/foo' )
      assert_that( flags_list, contains_exactly(
        '-Wall',
        '-isysroot/path/to/first/sys/root',
        '-isysroot', '/path/to/second/sys/root/',
        '--sysroot=/path/to/third/sys/root',
        '--sysroot', '/path/to/fourth/sys/root',
        '-resource-dir=' + CLANG_RESOURCE_DIR,
        '-isystem',    '/path/to/second/sys/root/usr/local/include',
        '-isystem',    '/usr/local/include',
        '-isystem',    os.path.join( CLANG_RESOURCE_DIR, 'include' ),
        '-isystem',    '/path/to/second/sys/root/usr/include',
        '-iframework', '/path/to/second/sys/root/System/Library/Frameworks',
        '-iframework', '/path/to/second/sys/root/Library/Frameworks',
        '-fspell-checking' ) )


  @MacOnly
  @patch( 'os.path.exists', lambda path:
    path == '/Applications/Xcode.app/Contents/Developer/Toolchains/'
            'XcodeDefault.xctoolchain' )
  def test_FlagsForFile_AddMacIncludePaths_Toolchain_Xcode( self ):
    flags_object = flags.Flags()

    def Settings( **kwargs ):
      return {
        'flags': [ '-Wall' ]
      }

    with MockExtraConfModule( Settings ):
      flags_list, _ = flags_object.FlagsForFile( '/foo' )
      assert_that( flags_list, contains_exactly(
        '-Wall',
        '-resource-dir=' + CLANG_RESOURCE_DIR,
        '-isystem',    '/Applications/Xcode.app/Contents/Developer/Toolchains'
                       '/XcodeDefault.xctoolchain/usr/include/c++/v1',
        '-isystem',    '/usr/local/include',
        '-isystem',    os.path.join( CLANG_RESOURCE_DIR, 'include' ),
        '-isystem',    '/Applications/Xcode.app/Contents/Developer/Toolchains'
                       '/XcodeDefault.xctoolchain/usr/include',
        '-isystem',    '/usr/include',
        '-iframework', '/System/Library/Frameworks',
        '-iframework', '/Library/Frameworks',
        '-fspell-checking' ) )


  @MacOnly
  @patch( 'os.path.exists', lambda path:
    path in [
      '/usr/include/c++/v1',
      '/Applications/Xcode.app/Contents/Developer/Toolchains/'
            'XcodeDefault.xctoolchain'
    ] )
  def test_FlagsForFile_AddMacIncludePaths_Toolchain_Xcode_WithSysrootStdlib(
      self ):
    flags_object = flags.Flags()

    def Settings( **kwargs ):
      return {
        'flags': [ '-Wall' ]
      }

    with MockExtraConfModule( Settings ):
      flags_list, _ = flags_object.FlagsForFile( '/foo' )
      assert_that( flags_list, contains_exactly(
        '-Wall',
        '-resource-dir=' + CLANG_RESOURCE_DIR,
        '-isystem',    '/usr/include/c++/v1',
        '-isystem',    '/usr/local/include',
        '-isystem',    os.path.join( CLANG_RESOURCE_DIR, 'include' ),
        '-isystem',    '/Applications/Xcode.app/Contents/Developer/Toolchains'
                       '/XcodeDefault.xctoolchain/usr/include',
        '-isystem',    '/usr/include',
        '-iframework', '/System/Library/Frameworks',
        '-iframework', '/Library/Frameworks',
        '-fspell-checking' ) )


  @MacOnly
  @patch( 'os.path.exists', lambda path:
    path == '/Library/Developer/CommandLineTools' )
  def test_FlagsForFile_AddMacIncludePaths_Toolchain_CommandLine( self ):
    flags_object = flags.Flags()

    def Settings( **kwargs ):
      return {
        'flags': [ '-Wall' ]
      }

    with MockExtraConfModule( Settings ):
      flags_list, _ = flags_object.FlagsForFile( '/foo' )
      assert_that( flags_list, contains_exactly(
        '-Wall',
        '-resource-dir=' + CLANG_RESOURCE_DIR,
        '-isystem',    '/Library/Developer/CommandLineTools/usr/include/c++/v1',
        '-isystem',    '/usr/local/include',
        '-isystem',    os.path.join( CLANG_RESOURCE_DIR, 'include' ),
        '-isystem',    '/Library/Developer/CommandLineTools/usr/include',
        '-isystem',    '/usr/include',
        '-iframework', '/System/Library/Frameworks',
        '-iframework', '/Library/Frameworks',
        '-fspell-checking' ) )


  @MacOnly
  @patch( 'os.path.exists', lambda path:
    path in [ '/usr/include/c++/v1', '/Library/Developer/CommandLineTools' ] )
  def test_FlagsForFile_AddMacIncludePaths_Toolchain_CommandLine_SysrootStdlib(
      self ):
    flags_object = flags.Flags()

    def Settings( **kwargs ):
      return {
        'flags': [ '-Wall' ]
      }

    with MockExtraConfModule( Settings ):
      flags_list, _ = flags_object.FlagsForFile( '/foo' )
      assert_that( flags_list, contains_exactly(
        '-Wall',
        '-resource-dir=' + CLANG_RESOURCE_DIR,
        '-isystem',    '/usr/include/c++/v1',
        '-isystem',    '/usr/local/include',
        '-isystem',    os.path.join( CLANG_RESOURCE_DIR, 'include' ),
        '-isystem',    '/Library/Developer/CommandLineTools/usr/include',
        '-isystem',    '/usr/include',
        '-iframework', '/System/Library/Frameworks',
        '-iframework', '/Library/Frameworks',
        '-fspell-checking' ) )


  @MacOnly
  @patch( 'os.path.exists', lambda path: path == '/usr/include/c++/v1' )
  def test_FlagsForFile_AddMacIncludePaths_ObjCppLanguage( self ):
    flags_object = flags.Flags()

    def Settings( **kwargs ):
      return {
        'flags': [ '-Wall', '-x', 'c', '-xobjective-c++' ]
      }

    with MockExtraConfModule( Settings ):
      flags_list, _ = flags_object.FlagsForFile( '/foo' )
      assert_that( flags_list, contains_exactly(
        '-Wall',
        '-x', 'c',
        '-xobjective-c++',
        '-resource-dir=' + CLANG_RESOURCE_DIR,
        '-isystem',    '/usr/include/c++/v1',
        '-isystem',    '/usr/local/include',
        '-isystem',    os.path.join( CLANG_RESOURCE_DIR, 'include' ),
        '-isystem',    '/usr/include',
        '-iframework', '/System/Library/Frameworks',
        '-iframework', '/Library/Frameworks',
        '-fspell-checking' ) )


  @MacOnly
  @patch( 'os.path.exists', lambda path: False )
  def test_FlagsForFile_AddMacIncludePaths_ObjCppLanguage_NoSysrootStdbib(
      self ):
    flags_object = flags.Flags()

    def Settings( **kwargs ):
      return {
        'flags': [ '-Wall', '-x', 'c', '-xobjective-c++' ]
      }

    with MockExtraConfModule( Settings ):
      flags_list, _ = flags_object.FlagsForFile( '/foo' )
      assert_that( flags_list, contains_exactly(
        '-Wall',
        '-x', 'c',
        '-xobjective-c++',
        '-resource-dir=' + CLANG_RESOURCE_DIR,
        '-isystem',    '/usr/local/include',
        '-isystem',    os.path.join( CLANG_RESOURCE_DIR, 'include' ),
        '-isystem',    '/usr/include',
        '-iframework', '/System/Library/Frameworks',
        '-iframework', '/Library/Frameworks',
        '-fspell-checking' ) )


  @MacOnly
  @patch( 'os.path.exists', lambda path: path == '/usr/include/c++/v1' )
  def test_FlagsForFile_AddMacIncludePaths_CppLanguage( self ):
    flags_object = flags.Flags()

    def Settings( **kwargs ):
      return {
        'flags': [ '-Wall', '-x', 'c', '-xc++' ]
      }

    with MockExtraConfModule( Settings ):
      flags_list, _ = flags_object.FlagsForFile( '/foo' )
      assert_that( flags_list, contains_exactly(
        '-Wall',
        '-x', 'c',
        '-xc++',
        '-resource-dir=' + CLANG_RESOURCE_DIR,
        '-isystem',    '/usr/include/c++/v1',
        '-isystem',    '/usr/local/include',
        '-isystem',    os.path.join( CLANG_RESOURCE_DIR, 'include' ),
        '-isystem',    '/usr/include',
        '-iframework', '/System/Library/Frameworks',
        '-iframework', '/Library/Frameworks',
        '-fspell-checking' ) )


  @MacOnly
  @patch( 'os.path.exists', lambda path: False )
  def test_FlagsForFile_AddMacIncludePaths_CppLanguage_NoStdlib( self ):
    flags_object = flags.Flags()

    def Settings( **kwargs ):
      return {
        'flags': [ '-Wall', '-x', 'c', '-xc++' ]
      }

    with MockExtraConfModule( Settings ):
      flags_list, _ = flags_object.FlagsForFile( '/foo' )
      assert_that( flags_list, contains_exactly(
        '-Wall',
        '-x', 'c',
        '-xc++',
        '-resource-dir=' + CLANG_RESOURCE_DIR,
        '-isystem',    '/usr/local/include',
        '-isystem',    os.path.join( CLANG_RESOURCE_DIR, 'include' ),
        '-isystem',    '/usr/include',
        '-iframework', '/System/Library/Frameworks',
        '-iframework', '/Library/Frameworks',
        '-fspell-checking' ) )


  @MacOnly
  @patch( 'os.path.exists', lambda path: False )
  def test_FlagsForFile_AddMacIncludePaths_CLanguage( self ):
    flags_object = flags.Flags()

    def Settings( **kwargs ):
      return {
        'flags': [ '-Wall', '-xc++', '-xc' ]
      }

    with MockExtraConfModule( Settings ):
      flags_list, _ = flags_object.FlagsForFile( '/foo' )
      assert_that( flags_list, contains_exactly(
        '-Wall',
        '-xc++',
        '-xc',
        '-resource-dir=' + CLANG_RESOURCE_DIR,
        '-isystem',    '/usr/local/include',
        '-isystem',    os.path.join( CLANG_RESOURCE_DIR, 'include' ),
        '-isystem',    '/usr/include',
        '-iframework', '/System/Library/Frameworks',
        '-iframework', '/Library/Frameworks',
        '-fspell-checking' ) )


  @MacOnly
  @patch( 'os.path.exists', lambda path: False )
  def test_FlagsForFile_AddMacIncludePaths_NoLibCpp( self ):
    flags_object = flags.Flags()

    def Settings( **kwargs ):
      return {
        'flags': [ '-Wall', '-stdlib=libc++', '-stdlib=libstdc++' ]
      }

    with MockExtraConfModule( Settings ):
      flags_list, _ = flags_object.FlagsForFile( '/foo' )
      assert_that( flags_list, contains_exactly(
        '-Wall',
        '-stdlib=libc++',
        '-stdlib=libstdc++',
        '-resource-dir=' + CLANG_RESOURCE_DIR,
        '-isystem',    '/usr/local/include',
        '-isystem',    os.path.join( CLANG_RESOURCE_DIR, 'include' ),
        '-isystem',    '/usr/include',
        '-iframework', '/System/Library/Frameworks',
        '-iframework', '/Library/Frameworks',
        '-fspell-checking' ) )


  @MacOnly
  @patch( 'os.path.exists', lambda path: False )
  def test_FlagsForFile_AddMacIncludePaths_NoStandardCppIncludes( self ):
    flags_object = flags.Flags()

    def Settings( **kwargs ):
      return {
        'flags': [ '-Wall', '-nostdinc++' ]
      }

    with MockExtraConfModule( Settings ):
      flags_list, _ = flags_object.FlagsForFile( '/foo' )
      assert_that( flags_list, contains_exactly(
        '-Wall',
        '-nostdinc++',
        '-resource-dir=' + CLANG_RESOURCE_DIR,
        '-isystem',    '/usr/local/include',
        '-isystem',    os.path.join( CLANG_RESOURCE_DIR, 'include' ),
        '-isystem',    '/usr/include',
        '-iframework', '/System/Library/Frameworks',
        '-iframework', '/Library/Frameworks',
        '-fspell-checking' ) )


  @MacOnly
  @patch( 'os.path.exists', lambda path: False )
  def test_FlagsForFile_AddMacIncludePaths_NoStandardSystemIncludes( self ):
    flags_object = flags.Flags()

    def Settings( **kwargs ):
      return {
        'flags': [ '-Wall', '-nostdinc' ]
      }

    with MockExtraConfModule( Settings ):
      flags_list, _ = flags_object.FlagsForFile( '/foo' )
      assert_that( flags_list, contains_exactly(
        '-Wall',
        '-nostdinc',
        '-resource-dir=' + CLANG_RESOURCE_DIR,
        '-isystem', os.path.join( CLANG_RESOURCE_DIR, 'include' ),
        '-fspell-checking' ) )


  @MacOnly
  @patch( 'os.path.exists', lambda path: False )
  def test_FlagsForFile_AddMacIncludePaths_NoBuiltinIncludes( self ):
    flags_object = flags.Flags()

    def Settings( **kwargs ):
      return {
        'flags': [ '-Wall', '-nobuiltininc' ]
      }

    with MockExtraConfModule( Settings ):
      flags_list, _ = flags_object.FlagsForFile( '/foo' )
      assert_that( flags_list, contains_exactly(
        '-Wall',
        '-nobuiltininc',
        '-resource-dir=' + CLANG_RESOURCE_DIR,
        '-isystem',    '/usr/local/include',
        '-isystem',    '/usr/include',
        '-iframework', '/System/Library/Frameworks',
        '-iframework', '/Library/Frameworks',
        '-fspell-checking' ) )


  @MacOnly
  @patch( 'os.path.exists', lambda path: path == '/usr/include/c++/v1' )
  def test_FlagsForFile_AddMacIncludePaths_NoBuiltinIncludes_SysrootStdlib(
      self ):
    flags_object = flags.Flags()

    def Settings( **kwargs ):
      return {
        'flags': [ '-Wall', '-nobuiltininc' ]
      }

    with MockExtraConfModule( Settings ):
      flags_list, _ = flags_object.FlagsForFile( '/foo' )
      assert_that( flags_list, contains_exactly(
        '-Wall',
        '-nobuiltininc',
        '-resource-dir=' + CLANG_RESOURCE_DIR,
        '-isystem',    '/usr/include/c++/v1',
        '-isystem',    '/usr/local/include',
        '-isystem',    '/usr/include',
        '-iframework', '/System/Library/Frameworks',
        '-iframework', '/Library/Frameworks',
        '-fspell-checking' ) )


  def test_FlagsForFile_OverrideTranslationUnit( self ):
    flags_object = flags.Flags()

    def Settings( **kwargs ):
      return {
        'flags': [],
        'override_filename': 'changed:' + kwargs[ 'filename' ]
      }

    with MockExtraConfModule( Settings ):
      flags_list, filename = flags_object.FlagsForFile( '/foo' )
      assert_that( flags_list, contains_exactly() )
      assert_that( filename, equal_to( 'changed:/foo' ) )


    def Settings( **kwargs ):
      return {
        'flags': [],
        'override_filename': kwargs[ 'filename' ]
      }

    with MockExtraConfModule( Settings ):
      flags_list, filename = flags_object.FlagsForFile( '/foo' )
      assert_that( flags_list, contains_exactly() )
      assert_that( filename, equal_to( '/foo' ) )


    def Settings( **kwargs ):
      return {
        'flags': [],
        'override_filename': None
      }

    with MockExtraConfModule( Settings ):
      flags_list, filename = flags_object.FlagsForFile( '/foo' )
      assert_that( flags_list, contains_exactly() )
      assert_that( filename, equal_to( '/foo' ) )


    def Settings( **kwargs ):
      return {
        'flags': [],
      }

    with MockExtraConfModule( Settings ):
      flags_list, filename = flags_object.FlagsForFile( '/foo' )
      assert_that( flags_list, contains_exactly() )
      assert_that( filename, equal_to( '/foo' ) )


    def Settings( **kwargs ):
      return {
        'flags': [],
        'override_filename': ''
      }

    with MockExtraConfModule( Settings ):
      flags_list, filename = flags_object.FlagsForFile( '/foo' )
      assert_that( flags_list, contains_exactly() )
      assert_that( filename, equal_to( '/foo' ) )


    def Settings( **kwargs ):
      return {
        'flags': [],
        'override_filename': '0'
      }

    with MockExtraConfModule( Settings ):
      flags_list, filename = flags_object.FlagsForFile( '/foo' )
      assert_that( flags_list, contains_exactly() )
      assert_that( filename, equal_to( '0' ) )


  def test_FlagsForFile_Compatibility_KeywordArguments( self ):
    flags_object = flags.Flags()

    def FlagsForFile( filename, **kwargs ):
      return {
        'flags': [ '-x', 'c' ]
      }

    with MockExtraConfModule( FlagsForFile ):
      flags_list, _ = flags_object.FlagsForFile( '/foo', False )
      assert_that( flags_list, contains_exactly( '-x', 'c' ) )


  def test_FlagsForFile_Compatibility_NoKeywordArguments( self ):
    flags_object = flags.Flags()

    def FlagsForFile( filename ):
      return {
        'flags': [ '-x', 'c' ]
      }

    with MockExtraConfModule( FlagsForFile ):
      flags_list, _ = flags_object.FlagsForFile( '/foo', False )
      assert_that( flags_list, contains_exactly( '-x', 'c' ) )


  def test_RemoveUnusedFlags_Passthrough( self ):
    compiler_flags = [ '-foo', '-bar' ]
    assert_that( flags.RemoveUnusedFlags(
                    compiler_flags,
                    'file',
                    ShouldAllowWinStyleFlags( compiler_flags ) ),
                 contains_exactly( '-foo', '-bar' ) )


  def test_RemoveUnusedFlags_RemoveDashC( self ):
    expected = [ '-foo', '-bar' ]
    to_remove = [ '-c' ]
    filename = 'file'

    assert_that( expected,
                 equal_to( flags.RemoveUnusedFlags(
                   expected + to_remove,
                   filename,
                   ShouldAllowWinStyleFlags( expected + to_remove ) ) ) )
    assert_that( expected,
                 equal_to( flags.RemoveUnusedFlags(
                   to_remove + expected,
                   filename,
                   ShouldAllowWinStyleFlags( to_remove + expected ) ) ) )
    assert_that( expected,
                 equal_to( flags.RemoveUnusedFlags(
                   expected[ :1 ] + to_remove + expected[ -1: ],
                   filename,
                   ShouldAllowWinStyleFlags( expected[ :1 ] +
                                             to_remove +
                                             expected[ -1: ] ) ) ) )


  def test_RemoveUnusedFlags_RemoveColor( self ):
    expected = [ '-foo', '-bar' ]
    to_remove = [ '--fcolor-diagnostics' ]
    filename = 'file'

    assert_that( expected,
                 equal_to( flags.RemoveUnusedFlags(
                   expected + to_remove,
                   filename,
                   ShouldAllowWinStyleFlags( expected + to_remove ) ) ) )
    assert_that( expected,
                 equal_to( flags.RemoveUnusedFlags(
                   to_remove + expected,
                   filename,
                   ShouldAllowWinStyleFlags( to_remove + expected ) ) ) )
    assert_that( expected,
                 equal_to( flags.RemoveUnusedFlags(
                   expected[ :1 ] + to_remove + expected[ -1: ],
                   filename,
                   ShouldAllowWinStyleFlags( expected[ :1 ] +
                                             to_remove +
                                             expected[ -1: ] ) ) ) )


  def test_RemoveUnusedFlags_RemoveDashO( self ):
    expected = [ '-foo', '-bar' ]
    to_remove = [ '-o', 'output_name' ]
    filename = 'file'

    assert_that( expected,
                 equal_to( flags.RemoveUnusedFlags(
                   expected + to_remove,
                   filename,
                   ShouldAllowWinStyleFlags( expected + to_remove ) ) ) )
    assert_that( expected,
                 equal_to( flags.RemoveUnusedFlags(
                   to_remove + expected,
                   filename,
                   ShouldAllowWinStyleFlags( to_remove + expected ) ) ) )
    assert_that( expected,
                 equal_to( flags.RemoveUnusedFlags(
                   expected[ :1 ] + to_remove + expected[ -1: ],
                   filename,
                   ShouldAllowWinStyleFlags( expected[ :1 ] +
                                             to_remove +
                                             expected[ -1: ] ) ) ) )


  def test_RemoveUnusedFlags_RemoveMP( self ):
    expected = [ '-foo', '-bar' ]
    to_remove = [ '-MP' ]
    filename = 'file'

    assert_that( expected,
                 equal_to( flags.RemoveUnusedFlags(
                   expected + to_remove,
                   filename,
                   ShouldAllowWinStyleFlags( expected + to_remove ) ) ) )
    assert_that( expected,
                 equal_to( flags.RemoveUnusedFlags(
                   to_remove + expected,
                   filename,
                   ShouldAllowWinStyleFlags( to_remove + expected ) ) ) )
    assert_that( expected,
                 equal_to( flags.RemoveUnusedFlags(
                   expected[ :1 ] + to_remove + expected[ -1: ],
                   filename,
                   ShouldAllowWinStyleFlags( expected[ :1 ] +
                                             to_remove +
                                             expected[ -1: ] ) ) ) )


  def test_RemoveUnusedFlags_RemoveFilename( self ):
    expected = [ 'foo', '-bar' ]
    to_remove = [ 'file' ]
    filename = 'file'

    assert_that( expected,
                 equal_to( flags.RemoveUnusedFlags(
                   expected + to_remove,
                   filename,
                   ShouldAllowWinStyleFlags( expected + to_remove ) ) ) )
    assert_that( expected,
                 equal_to( flags.RemoveUnusedFlags(
                   expected[ :1 ] + to_remove + expected[ 1: ],
                   filename,
                   ShouldAllowWinStyleFlags( expected[ :1 ] +
                                             to_remove +
                                             expected[ 1: ] ) ) ) )
    assert_that( expected,
                 equal_to( flags.RemoveUnusedFlags(
                   expected[ :1 ] + to_remove + expected[ -1: ],
                   filename,
                   ShouldAllowWinStyleFlags( expected[ :1 ] +
                                             to_remove +
                                             expected[ -1: ] ) ) ) )


  def test_RemoveUnusedFlags_RemoveFlagWithoutPrecedingDashFlag( self ):
    expected = [ 'g++', '-foo', '-x', 'c++', '-bar', 'include_dir' ]
    to_remove = [ 'unrelated_file' ]
    filename = 'file'

    assert_that(
                 expected, equal_to(
                   flags.RemoveUnusedFlags( expected + to_remove,
                     filename,
                     ShouldAllowWinStyleFlags( expected + to_remove ) ) ) )
    assert_that( expected,
                 equal_to( flags.RemoveUnusedFlags(
                   expected[ :1 ] + to_remove + expected[ 1: ],
                   filename,
                   ShouldAllowWinStyleFlags( expected[ :1 ] +
                                             to_remove +
                                             expected[ 1: ] ) ) ) )


  @WindowsOnly
  def test_RemoveUnusedFlags_RemoveStrayFilenames_CLDriver( self ):
    # Only --driver-mode=cl specified.
    expected = [ 'g++', '-foo', '--driver-mode=cl', '-xc++', '-bar',
                 'include_dir', '/I', 'include_dir_other' ]
    to_remove = [ '..' ]
    filename = 'file'

    assert_that( expected,
                 equal_to( flags.RemoveUnusedFlags(
                   expected + to_remove,
                   filename,
                   ShouldAllowWinStyleFlags( expected + to_remove ) ) ) )
    assert_that( expected,
                 equal_to( flags.RemoveUnusedFlags(
                   expected[ :1 ] + to_remove + expected[ 1: ],
                   filename,
                   ShouldAllowWinStyleFlags( expected[ :1 ] +
                                             to_remove +
                                             expected[ 1: ] ) ) ) )

    # clang-cl and --driver-mode=cl
    expected = [ 'clang-cl.exe', '-foo', '--driver-mode=cl', '-xc++', '-bar',
                 'include_dir', '/I', 'include_dir_other' ]
    to_remove = [ 'unrelated_file' ]
    filename = 'file'

    assert_that( expected,
                 equal_to( flags.RemoveUnusedFlags(
                   expected + to_remove,
                   filename,
                   ShouldAllowWinStyleFlags( expected + to_remove ) ) ) )
    assert_that( expected,
                 equal_to( flags.RemoveUnusedFlags(
                   expected[ :1 ] + to_remove + expected[ 1: ],
                   filename,
                   ShouldAllowWinStyleFlags( expected[ :1 ] +
                                             to_remove +
                                             expected[ 1: ] ) ) ) )

    # clang-cl only
    expected = [ 'clang-cl.exe', '-foo', '-xc++', '-bar',
                 'include_dir', '/I', 'include_dir_other' ]
    to_remove = [ 'unrelated_file' ]
    filename = 'file'

    assert_that( expected,
                 equal_to( flags.RemoveUnusedFlags(
                   expected + to_remove,
                   filename,
                   ShouldAllowWinStyleFlags( expected + to_remove ) ) ) )
    assert_that( expected,
                 equal_to( flags.RemoveUnusedFlags(
                   expected[ :1 ] + to_remove + expected[ 1: ],
                   filename,
                   ShouldAllowWinStyleFlags( expected[ :1 ] +
                                             to_remove +
                                             expected[ 1: ] ) ) ) )

    # clang-cl and --driver-mode=gcc
    expected = [ 'clang-cl', '-foo', '-xc++', '--driver-mode=gcc',
                 '-bar', 'include_dir' ]
    to_remove = [ 'unrelated_file', '/I', 'include_dir_other' ]
    filename = 'file'

    assert_that( expected,
                 equal_to( flags.RemoveUnusedFlags(
                   expected + to_remove,
                   filename,
                   ShouldAllowWinStyleFlags( expected + to_remove ) ) ) )
    assert_that( expected,
                 equal_to( flags.RemoveUnusedFlags(
                   expected[ :1 ] + to_remove + expected[ 1: ],
                   filename,
                   ShouldAllowWinStyleFlags( expected[ :1 ] +
                                             to_remove +
                                             expected[ 1: ] ) ) ) )


    # cl only with extension
    expected = [ 'cl.EXE', '-foo', '-xc++', '-bar', 'include_dir' ]
    to_remove = [ '-c', 'path\\to\\unrelated_file' ]
    filename = 'file'

    assert_that( expected,
                 equal_to( flags.RemoveUnusedFlags(
                   expected + to_remove,
                   filename,
                   ShouldAllowWinStyleFlags( expected + to_remove ) ) ) )
    assert_that( expected,
                 equal_to( flags.RemoveUnusedFlags(
                   expected[ :1 ] + to_remove + expected[ 1: ],
                   filename,
                   ShouldAllowWinStyleFlags( expected[ :1 ] +
                                             to_remove +
                                             expected[ 1: ] ) ) ) )

    # cl path with Windows separators
    expected = [ 'path\\to\\cl',
                 '-foo',
                 '-xc++',
                 '/I',
                 'path\\to\\include\\dir' ]
    to_remove = [ '-c', 'path\\to\\unrelated_file' ]
    filename = 'file'

    assert_that( expected,
                 equal_to( flags.RemoveUnusedFlags(
                   expected + to_remove,
                   filename,
                   ShouldAllowWinStyleFlags( expected + to_remove ) ) ) )
    assert_that( expected,
                 equal_to( flags.RemoveUnusedFlags(
                   expected[ :1 ] + to_remove + expected[ 1: ],
                   filename,
                   ShouldAllowWinStyleFlags( expected[ :1 ] +
                                             to_remove +
                                             expected[ 1: ] ) ) ) )



  @WindowsOnly
  def test_RemoveUnusedFlags_MultipleDriverModeFlagsWindows( self ):
    expected = [ 'g++',
                 '--driver-mode=cl',
                 '/Zi',
                 '-foo',
                 '--driver-mode=gcc',
                 '--driver-mode=cl',
                 'include_dir' ]
    to_remove = [ 'unrelated_file', '/c' ]
    filename = 'file'

    assert_that( expected,
                 equal_to( flags.RemoveUnusedFlags(
                   expected + to_remove,
                   filename,
                   ShouldAllowWinStyleFlags( expected + to_remove ) ) ) )
    assert_that( expected,
                 equal_to( flags.RemoveUnusedFlags(
                   expected[ :1 ] + to_remove + expected[ 1: ],
                   filename,
                   ShouldAllowWinStyleFlags( expected[ :1 ] +
                                             to_remove +
                                             expected[ 1: ] ) ) ) )

    flags_expected = [ '/usr/bin/g++', '--driver-mode=cl', '--driver-mode=gcc' ]
    flags_all = [ '/usr/bin/g++',
                  '/Zi',
                  '--driver-mode=cl',
                  '/foo',
                  '--driver-mode=gcc' ]
    filename = 'file'

    assert_that( flags_expected,
                 equal_to( flags.RemoveUnusedFlags(
                   flags_all,
                   filename,
                   ShouldAllowWinStyleFlags( flags_all ) ) ) )


  def test_RemoveUnusedFlags_Depfiles( self ):
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

    assert_that( flags.RemoveUnusedFlags( full_flags,
                                          'test.m',
                                          ShouldAllowWinStyleFlags(
                                            full_flags ) ),
                 contains_exactly( *expected ) )


  def test_EnableTypoCorrection_Empty( self ):
    assert_that( flags._EnableTypoCorrection( [] ),
                 equal_to( [ '-fspell-checking' ] ) )


  def test_EnableTypoCorrection_Trivial( self ):
    assert_that( flags._EnableTypoCorrection( [ '-x', 'c++' ] ),
                 equal_to( [ '-x', 'c++', '-fspell-checking' ] ) )


  def test_EnableTypoCorrection_Reciprocal( self ):
    assert_that( flags._EnableTypoCorrection( [ '-fno-spell-checking' ] ),
                 equal_to( [ '-fno-spell-checking' ] ) )


  def test_EnableTypoCorrection_ReciprocalOthers( self ):
    compile_flags = [ '-x', 'c++', '-fno-spell-checking' ]
    assert_that( flags._EnableTypoCorrection( compile_flags ),
                 equal_to( compile_flags ) )


  def test_RemoveUnusedFlags_RemoveFilenameWithoutPrecedingInclude( self ):
    for flag in INCLUDE_FLAGS:
      with self.subTest( flag = flag ):
        to_remove = [ '/moo/boo' ]
        filename = 'file'
        expected = [ 'clang', flag, '/foo/bar', '-isystem/zoo/goo' ]

        assert_that( expected,
                     equal_to( flags.RemoveUnusedFlags(
                       expected + to_remove,
                       filename,
                       ShouldAllowWinStyleFlags( expected + to_remove ) ) ) )
        assert_that( expected,
                     equal_to( flags.RemoveUnusedFlags(
                       expected[ :1 ] + to_remove + expected[ 1: ],
                       filename,
                       ShouldAllowWinStyleFlags( expected[ :1 ] +
                                               to_remove +
                                               expected[ 1: ] ) ) ) )
        assert_that( expected + expected[ 1: ],
                     equal_to(
                       flags.RemoveUnusedFlags( expected +
                                                to_remove +
                                                expected[ 1: ],
                       filename,
                       ShouldAllowWinStyleFlags( expected +
                                                 to_remove +
                                                 expected[ 1: ] ) ) ) )


  def test_RemoveXclangFlags( self ):
    expected = [ '-I', '/foo/bar', '-DMACRO=Value' ]
    to_remove = [ '-Xclang', 'load', '-Xclang', 'libplugin.so',
                  '-Xclang', '-add-plugin', '-Xclang', 'plugin-name' ]

    assert_that( expected,
                 equal_to( flags._RemoveXclangFlags( expected + to_remove ) ) )

    assert_that( expected,
                 equal_to( flags._RemoveXclangFlags( to_remove + expected ) ) )

    assert_that( expected + expected,
                 equal_to( flags._RemoveXclangFlags( expected +
                                                     to_remove +
                                                     expected ) ) )


  def test_AddLanguageFlagWhenAppropriate_Passthrough( self ):
    compiler_flags = [ '-foo', '-bar' ]
    assert_that( flags._AddLanguageFlagWhenAppropriate(
                    compiler_flags,
                    ShouldAllowWinStyleFlags( compiler_flags ) ),
                 contains_exactly( '-foo', '-bar' ) )


  @WindowsOnly
  def test_AddLanguageFlagWhenAppropriate_CLDriver_Passthrough( self ):
    compiler_flags = [ '-foo', '-bar', '--driver-mode=cl' ]
    assert_that( flags._AddLanguageFlagWhenAppropriate(
                    compiler_flags,
                    ShouldAllowWinStyleFlags( compiler_flags ) ),
                 contains_exactly( '-foo', '-bar', '--driver-mode=cl' ) )


  def test_AddLanguageFlagWhenAppropriate_CCompiler( self ):
    for compiler in [ 'cc', 'gcc', 'clang',
                      '/usr/bin/cc', '/some/other/path', 'some_command' ]:
      with self.subTest( compiler = compiler ):
        _AddLanguageFlagWhenAppropriateTester( compiler )


  def test_AddLanguageFlagWhenAppropriate_CppCompiler( self ):
    for compiler in [ 'c++', 'g++', 'clang++', '/usr/bin/c++',
       '/some/other/path++', 'some_command++',
       'c++-5', 'g++-5.1', 'clang++-3.7.3', '/usr/bin/c++-5',
       'c++-5.11', 'g++-50.1.49', 'clang++-3.12.3', '/usr/bin/c++-10',
       '/some/other/path++-4.9.3', 'some_command++-5.1',
       '/some/other/path++-4.9.31', 'some_command++-5.10' ]:
      with self.subTest( compiler = compiler ):
        _AddLanguageFlagWhenAppropriateTester( compiler, [ '-x', 'c++' ] )


  def test_CompilationDatabase_NoDatabase( self ):
    with TemporaryTestDir() as tmp_dir:
      assert_that(
        calling( flags.Flags().FlagsForFile ).with_args(
          os.path.join( tmp_dir, 'test.cc' ) ),
        raises( NoExtraConfDetected ) )


  def test_CompilationDatabase_FileNotInDatabase( self ):
    compile_commands = []
    with TemporaryTestDir() as tmp_dir:
      with TemporaryClangProject( tmp_dir, compile_commands ):
        assert_that( flags.Flags().FlagsForFile(
                       os.path.join( tmp_dir, 'test.cc' ) ),
                     equal_to( ( [], os.path.join( tmp_dir, 'test.cc' ) ) ) )


  def test_CompilationDatabase_InvalidDatabase( self ):
    with TemporaryTestDir() as tmp_dir:
      with TemporaryClangProject( tmp_dir, 'this is junk' ):
        assert_that(
          calling( flags.Flags().FlagsForFile ).with_args(
            os.path.join( tmp_dir, 'test.cc' ) ),
          raises( NoExtraConfDetected ) )


  def test_CompilationDatabase_UseFlagsFromDatabase( self ):
    with TemporaryTestDir() as tmp_dir:
      compile_commands = [
        {
          'directory': tmp_dir,
          'command': 'clang++ -x c++ -I. -I/absolute/path -Wall',
          'file': os.path.join( tmp_dir, 'test.cc' ),
        },
      ]
      with TemporaryClangProject( tmp_dir, compile_commands ):
        assert_that(
          flags.Flags().FlagsForFile(
            os.path.join( tmp_dir, 'test.cc' ),
            add_extra_clang_flags = False )[ 0 ],
          contains_exactly( 'clang++',
                    '-x',
                    'c++',
                    '--driver-mode=g++',
                    '-x',
                    'c++',
                    '-I' + os.path.normpath( tmp_dir ),
                    '-I' + os.path.normpath( '/absolute/path' ),
                    '-Wall' ) )


  def test_CompilationDatabase_UseFlagsFromSameDir( self ):
    with TemporaryTestDir() as tmp_dir:
      compile_commands = [
        {
          'directory': tmp_dir,
          'command': 'clang++ -x c++ -Wall',
          'file': os.path.join( tmp_dir, 'test.cc' ),
        },
      ]

      with TemporaryClangProject( tmp_dir, compile_commands ):
        f = flags.Flags()

        # If we ask for a file that is not in the DB but is in the same
        # directory of another file present in the DB, we get its flags.
        assert_that(
          f.FlagsForFile(
            os.path.join( tmp_dir, 'test1.cc' ),
            add_extra_clang_flags = False ),
          contains_exactly(
            contains_exactly( 'clang++',
                      '-x',
                      'c++',
                      '--driver-mode=g++',
                      '-Wall' ),
            os.path.join( tmp_dir, 'test1.cc' )
          )
        )

        # If we ask for a file that is not in the DB but in a subdirectory
        # of another file present in the DB, we get its flags.
        assert_that(
          f.FlagsForFile(
            os.path.join( tmp_dir, 'some_dir', 'test1.cc' ),
            add_extra_clang_flags = False ),
          contains_exactly(
            contains_exactly( 'clang++',
                      '-x',
                      'c++',
                      '--driver-mode=g++',
                      '-Wall' ),
            os.path.join( tmp_dir, 'some_dir', 'test1.cc' )
          )
        )


  def test_CompilationDatabase_HeaderFile_SameNameAsSourceFile( self ):
    with TemporaryTestDir() as tmp_dir:
      compile_commands = [
        {
          'directory': tmp_dir,
          'command': 'clang++ -x c++ -Wall',
          'file': os.path.join( tmp_dir, 'test.cc' ),
        },
      ]

      with TemporaryClangProject( tmp_dir, compile_commands ):
        # If we ask for a header file with the same name as a source file, it
        # returns the flags of that cc file (and a special language flag for C++
        # headers).
        assert_that(
          flags.Flags().FlagsForFile(
            os.path.join( tmp_dir, 'test.h' ),
            add_extra_clang_flags = False )[ 0 ],
          contains_exactly( 'clang++',
                    '-x',
                    'c++',
                    '--driver-mode=g++',
                    '-Wall',
                    '-x',
                    'c++-header' ) )


  def test_CompilationDatabase_HeaderFile_DifferentNameFromSourceFile( self ):
    with TemporaryTestDir() as tmp_dir:
      compile_commands = [
        {
          'directory': tmp_dir,
          'command': 'clang++ -x c++ -Wall',
          'file': os.path.join( tmp_dir, 'test.cc' ),
        },
      ]

      with TemporaryClangProject( tmp_dir, compile_commands ):
        # Even if we ask for a header file with a different name than the source
        # file, it still returns the flags from the cc file (and a special
        # language flag for C++ headers).
        assert_that(
          flags.Flags().FlagsForFile(
            os.path.join( tmp_dir, 'not_in_the_db.h' ),
            add_extra_clang_flags = False )[ 0 ],
          contains_exactly( 'clang++',
                    '-x',
                    'c++',
                    '--driver-mode=g++',
                    '-Wall',
                    '-x',
                    'c++-header' ) )


  def test_CompilationDatabase_ExplicitHeaderFileEntry( self ):
    with TemporaryTestDir() as tmp_dir:
      # Have an explicit header file entry which should take priority over the
      # corresponding source file
      compile_commands = [
        {
          'directory': tmp_dir,
          'command': 'clang++ -x c++ -I. -I/absolute/path -Wall',
          'file': os.path.join( tmp_dir, 'test.cc' ),
        },
        {
          'directory': tmp_dir,
          'command': 'clang++ -I/absolute/path -Wall',
          'file': os.path.join( tmp_dir, 'test.h' ),
        },
      ]
      with TemporaryClangProject( tmp_dir, compile_commands ):
        assert_that(
          flags.Flags().FlagsForFile(
            os.path.join( tmp_dir, 'test.h' ),
            add_extra_clang_flags = False )[ 0 ],
          contains_exactly( 'clang++',
                    '-x',
                    'c++',
                    '--driver-mode=g++',
                    '-I' + os.path.normpath( '/absolute/path' ),
                    '-Wall' ) )


  def test_CompilationDatabase_CUDALanguageFlags( self ):
    with TemporaryTestDir() as tmp_dir:
      compile_commands = [
        {
          'directory': tmp_dir,
          'command': 'clang++ -Wall ./test.cu',
          'file': os.path.join( tmp_dir, 'test.cu' ),
        },
      ]

      with TemporaryClangProject( tmp_dir, compile_commands ):
        # If we ask for a header file, it returns the equivalent cu file
        assert_that(
          flags.Flags().FlagsForFile(
            os.path.join( tmp_dir, 'test.cuh' ),
            add_extra_clang_flags = False )[ 0 ],
          contains_exactly( 'clang++',
                            '--driver-mode=g++',
                            '-Wall',
                            '-x',
                            'cuda' ) )


  def test_MakeRelativePathsInFlagsAbsolute( self ):
    for test in [
      # Already absolute, positional arguments
      {
        'flags':  [ '-isystem', '/test' ],
        'expect': [ '-isystem', os.path.normpath( '/test' ) ],
      },
      {
        'flags':  [ '-I', '/test' ],
        'expect': [ '-I', os.path.normpath( '/test' ) ],
      },
      {
        'flags':  [ '-iquote', '/test' ],
        'expect': [ '-iquote', os.path.normpath( '/test' ) ],
      },
      {
        'flags':  [ '-isysroot', '/test' ],
        'expect': [ '-isysroot', os.path.normpath( '/test' ) ],
      },
      {
        'flags':  [ '-include-pch', '/test' ],
        'expect': [ '-include-pch', os.path.normpath( '/test' ) ],
      },
      {
        'flags':  [ '-idirafter', '/test' ],
        'expect': [ '-idirafter', os.path.normpath( '/test' ) ],
      },

      # Already absolute, single arguments
      {
        'flags':  [ '-isystem/test' ],
        'expect': [ '-isystem' + os.path.normpath( '/test' ) ],
      },
      {
        'flags':  [ '-I/test' ],
        'expect': [ '-I' + os.path.normpath( '/test' ) ],
      },
      {
        'flags':  [ '-iquote/test' ],
        'expect': [ '-iquote' + os.path.normpath( '/test' ) ],
      },
      {
        'flags':  [ '-isysroot/test' ],
        'expect': [ '-isysroot' + os.path.normpath( '/test' ) ],
      },
      {
        'flags':  [ '-include-pch/test' ],
        'expect': [ '-include-pch' + os.path.normpath( '/test' ) ],
      },
      {
        'flags':  [ '-idirafter/test' ],
        'expect': [ '-idirafter' + os.path.normpath( '/test' ) ],
      },


      # Already absolute, double-dash arguments
      {
        'flags':  [ '--isystem=/test' ],
        'expect': [ '--isystem=/test' ],
      },
      {
        'flags':  [ '--I=/test' ],
        'expect': [ '--I=/test' ],
      },
      {
        'flags':  [ '--iquote=/test' ],
        'expect': [ '--iquote=/test' ],
      },
      {
        'flags':  [ '--sysroot=/test' ],
        'expect': [ '--sysroot=' + os.path.normpath( '/test' ) ],
      },
      {
        'flags':  [ '--include-pch=/test' ],
        'expect': [ '--include-pch=/test' ],
      },
      {
        'flags':  [ '--idirafter=/test' ],
        'expect': [ '--idirafter=/test' ],
      },

      # Relative, positional arguments
      {
        'flags':  [ '-isystem', 'test' ],
        'expect': [ '-isystem', os.path.normpath( '/test/test' ) ],
        'wd':     '/test',
      },
      {
        'flags':  [ '-I', 'test' ],
        'expect': [ '-I', os.path.normpath( '/test/test' ) ],
        'wd':     '/test',
      },
      {
        'flags':  [ '-iquote', 'test' ],
        'expect': [ '-iquote', os.path.normpath( '/test/test' ) ],
        'wd':     '/test',
      },
      {
        'flags':  [ '-isysroot', 'test' ],
        'expect': [ '-isysroot', os.path.normpath( '/test/test' ) ],
        'wd':     '/test',
      },
      {
        'flags':  [ '-include-pch', 'test' ],
        'expect': [ '-include-pch', os.path.normpath( '/test/test' ) ],
        'wd':     '/test',
      },
      {
        'flags':  [ '-idirafter', 'test' ],
        'expect': [ '-idirafter', os.path.normpath( '/test/test' ) ],
        'wd':     '/test',
      },

      # Relative, single arguments
      {
        'flags':  [ '-isystemtest' ],
        'expect': [ '-isystem' + os.path.normpath( '/test/test' ) ],
        'wd':     '/test',
      },
      {
        'flags':  [ '-Itest' ],
        'expect': [ '-I' + os.path.normpath( '/test/test' ) ],
        'wd':     '/test',
      },
      {
        'flags':  [ '-iquotetest' ],
        'expect': [ '-iquote' + os.path.normpath( '/test/test' ) ],
        'wd':     '/test',
      },
      {
        'flags':  [ '-isysroottest' ],
        'expect': [ '-isysroot' + os.path.normpath( '/test/test' ) ],
        'wd':     '/test',
      },
      {
        'flags':  [ '-include-pchtest' ],
        'expect': [ '-include-pch' + os.path.normpath( '/test/test' ) ],
        'wd':     '/test',
      },
      {
        'flags':  [ '-idiraftertest' ],
        'expect': [ '-idirafter' + os.path.normpath( '/test/test' ) ],
        'wd':     '/test',
      },

      # Already absolute, double-dash arguments
      {
        'flags':  [ '--isystem=test' ],
        'expect': [ '--isystem=test' ],
        'wd':     '/test',
      },
      {
        'flags':  [ '--I=test' ],
        'expect': [ '--I=test' ],
        'wd':     '/test',
      },
      {
        'flags':  [ '--iquote=test' ],
        'expect': [ '--iquote=test' ],
        'wd':     '/test',
      },
      {
        'flags':  [ '--sysroot=test' ],
        'expect': [ '--sysroot=' + os.path.normpath( '/test/test' ) ],
        'wd':     '/test',
      },
      {
        'flags':  [ '--include-pch=test' ],
        'expect': [ '--include-pch=test' ],
        'wd':     '/test',
      },
      {
        'flags':  [ '--idirafter=test' ],
        'expect': [ '--idirafter=test' ],
        'wd':     '/test',
      },
    ]:
      with self.subTest( test = test ):
        _MakeRelativePathsInFlagsAbsoluteTest( test )


  def test_MakeRelativePathsInFlagsAbsolute_IgnoreUnknown( self ):
    for test in [
      {
        'flags': [
          'ignored',
          '-isystem',
          '/test',
          '-ignored',
          '-I',
          '/test',
          '--ignored=ignored'
        ],
        'expect': [
          'ignored',
          '-isystem', os.path.normpath( '/test' ),
          '-ignored',
          '-I', os.path.normpath( '/test' ),
          '--ignored=ignored'
        ]
      },
      {
        'flags': [
          'ignored',
          '-isystem/test',
          '-ignored',
          '-I/test',
          '--ignored=ignored'
        ],
        'expect': [
          'ignored',
          '-isystem' + os.path.normpath( '/test' ),
          '-ignored',
          '-I' + os.path.normpath( '/test/' ),
          '--ignored=ignored'
        ]
      },
      {
        'flags': [
          'ignored',
          '--isystem=/test',
          '-ignored',
          '--I=/test',
          '--ignored=ignored'
        ],
        'expect': [
          'ignored',
          '--isystem=/test',
          '-ignored',
          '--I=/test',
          '--ignored=ignored'
        ]
      },
      {
        'flags': [
          'ignored',
          '-isystem', 'test',
          '-ignored',
          '-I', 'test',
          '--ignored=ignored'
        ],
        'expect': [
          'ignored',
          '-isystem', os.path.normpath( '/test/test' ),
          '-ignored',
          '-I', os.path.normpath( '/test/test' ),
          '--ignored=ignored'
        ],
        'wd': '/test',
      },
      {
        'flags': [
          'ignored',
          '-isystemtest',
          '-ignored',
          '-Itest',
          '--ignored=ignored'
        ],
        'expect': [
          'ignored',
          '-isystem' + os.path.normpath( '/test/test' ),
          '-ignored',
          '-I' + os.path.normpath( '/test/test' ),
          '--ignored=ignored'
        ],
        'wd': '/test',
      },
      {
        'flags': [
          'ignored',
          '--isystem=test',
          '-ignored',
          '--I=test',
          '--ignored=ignored',
          '--sysroot=test'
        ],
        'expect': [
          'ignored',
          '--isystem=test',
          '-ignored',
          '--I=test',
          '--ignored=ignored',
          '--sysroot=' + os.path.normpath( '/test/test' ),
        ],
        'wd': '/test',
      },
    ]:
      with self.subTest( test = test ):
        _MakeRelativePathsInFlagsAbsoluteTest( test )


  def test_MakeRelativePathsInFlagsAbsolute_NoWorkingDir( self ):
    _MakeRelativePathsInFlagsAbsoluteTest( {
      'flags': [ 'list', 'of', 'flags', 'not', 'changed', '-Itest' ],
      'expect': [ 'list', 'of', 'flags', 'not', 'changed', '-Itest' ],
      'wd': ''
    } )
