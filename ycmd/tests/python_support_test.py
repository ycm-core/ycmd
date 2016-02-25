# Copyright (C) 2016 ycmd contributors
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

# Intentionally not importing unicode_literals!
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()
# Intentionally not importing all builtins!

from nose.tools import eq_
from future.utils import native

import ycm_core
from ycmd.tests.test_utils import ClangOnly, Py2Only, Py3Only, PathToTestFile
from ycmd.utils import ToBytes, ToUnicode


@Py2Only
def GetUtf8String_Py2Str_test():
  eq_( 'foo', str( ycm_core.GetUtf8String( 'foo' ) ) )


@Py3Only
def GetUtf8String_Py3Bytes_test():
  eq_( 'foo', str( ycm_core.GetUtf8String( b'foo' ) ) )

# No test for `bytes` from builtins because it's very difficult to make
# GetUtf8String work with that and also it should never receive that type in the
# first place (only py2 str/unicode and py3 bytes/str).

def GetUtf8String_Unicode_test():
  eq_( 'foo', str( ycm_core.GetUtf8String( u'foo' ) ) )


@ClangOnly
@Py2Only
def CompilationDatabase_Py2Str_test():
  testdata_dir = native( ToBytes( PathToTestFile() ) )

  # Ctor reads ycmd/tests/testdata/compiled_commands.json
  db = ycm_core.CompilationDatabase( testdata_dir )
  info = db.GetCompilationInfoForFile( '/dir/example.cc' )

  eq_( str( info.compiler_working_dir_ ), '/dir' )
  eq_( str( info.compiler_flags_[ 0 ] ), '/usr/bin/clang++' )
  eq_( str( info.compiler_flags_[ 1 ] ), 'example.cc' )


@ClangOnly
@Py2Only
def CompilationDatabase_Py2Unicode_test():
  testdata_dir = native( ToUnicode( PathToTestFile() ) )

  # Ctor reads ycmd/tests/testdata/compiled_commands.json
  db = ycm_core.CompilationDatabase( testdata_dir )
  info = db.GetCompilationInfoForFile( u'/dir/example.cc' )

  eq_( str( info.compiler_working_dir_ ), '/dir' )
  eq_( str( info.compiler_flags_[ 0 ] ), '/usr/bin/clang++' )
  eq_( str( info.compiler_flags_[ 1 ] ), 'example.cc' )


@ClangOnly
@Py3Only
def CompilationDatabase_Py3Bytes_test():
  testdata_dir = native( ToBytes( PathToTestFile() ) )

  # Ctor reads ycmd/tests/testdata/compiled_commands.json
  db = ycm_core.CompilationDatabase( testdata_dir )
  info = db.GetCompilationInfoForFile( b'/dir/example.cc' )

  eq_( str( info.compiler_working_dir_ ), '/dir' )
  eq_( str( info.compiler_flags_[ 0 ] ), '/usr/bin/clang++' )
  eq_( str( info.compiler_flags_[ 1 ] ), 'example.cc' )


@ClangOnly
def CompilationDatabase_NativeString_test():
  testdata_dir = PathToTestFile()

  # Ctor reads ycmd/tests/testdata/compiled_commands.json
  db = ycm_core.CompilationDatabase( testdata_dir )
  info = db.GetCompilationInfoForFile( '/dir/example.cc' )

  eq_( str( info.compiler_working_dir_ ), '/dir' )
  eq_( str( info.compiler_flags_[ 0 ] ), '/usr/bin/clang++' )
  eq_( str( info.compiler_flags_[ 1 ] ), 'example.cc' )
