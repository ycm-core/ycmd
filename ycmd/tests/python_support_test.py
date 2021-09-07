# Copyright (C) 2021 ycmd contributors
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

import os

from hamcrest import assert_that, equal_to

from ycmd.tests.test_utils import ClangOnly
from ycmd.utils import ToBytes, OnWindows, ImportCore
from unittest import TestCase
ycm_core = ImportCore()


# We don't use PathToTestFile from test_utils module because this module
# imports future modules that may change the path type.
PATH_TO_TESTDATA = os.path.abspath( os.path.join( os.path.dirname( __file__ ),
                                                  'testdata' ) )
PATH_TO_COMPILE_COMMANDS = (
  os.path.join( PATH_TO_TESTDATA, 'windows' ) if OnWindows() else
  os.path.join( PATH_TO_TESTDATA, 'unix' ) )
COMPILE_COMMANDS_WORKING_DIR = 'C:\\dir' if OnWindows() else '/dir'


class PythonSupportTest( TestCase ):
  def test_GetUtf8String_Str( self ):
    assert_that( b'fo\xc3\xb8', equal_to( ycm_core.GetUtf8String( 'foø' ) ) )


  def test_GetUtf8String_Bytes( self ):
    assert_that( b'fo\xc3\xb8',
                 equal_to( ycm_core.GetUtf8String( bytes( 'foø', 'utf8' ) ) ) )


  def test_GetUtf8String_Int( self ):
    assert_that( b'123', equal_to( ycm_core.GetUtf8String( 123 ) ) )


  @ClangOnly
  def test_CompilationDatabase_Py3Bytes( self ):
    cc_dir = ToBytes( PATH_TO_COMPILE_COMMANDS )
    cc_filename = ToBytes( os.path.join( COMPILE_COMMANDS_WORKING_DIR,
                                         'example.cc' ) )

    # Ctor reads ycmd/tests/testdata/[unix|windows]/compile_commands.json
    db = ycm_core.CompilationDatabase( cc_dir )
    info = db.GetCompilationInfoForFile( cc_filename )

    assert_that( str( info.compiler_working_dir_ ),
                 equal_to( COMPILE_COMMANDS_WORKING_DIR ) )
    assert_that( str( info.compiler_flags_[ 0 ] ),
                 equal_to( '/usr/bin/clang++' ) )
    assert_that( str( info.compiler_flags_[ 1 ] ),
                 equal_to( '--driver-mode=g++' ) )
    assert_that( str( info.compiler_flags_[ 2 ] ),
                 equal_to( 'example.cc' ) )


  @ClangOnly
  def test_CompilationDatabase_NativeString( self ):
    cc_dir = PATH_TO_COMPILE_COMMANDS
    cc_filename = os.path.join( COMPILE_COMMANDS_WORKING_DIR, 'example.cc' )

    # Ctor reads ycmd/tests/testdata/[unix|windows]/compile_commands.json
    db = ycm_core.CompilationDatabase( cc_dir )
    info = db.GetCompilationInfoForFile( cc_filename )

    assert_that( str( info.compiler_working_dir_ ),
                 equal_to( COMPILE_COMMANDS_WORKING_DIR ) )
    assert_that( str( info.compiler_flags_[ 0 ] ),
                 equal_to( '/usr/bin/clang++' ) )
    assert_that( str( info.compiler_flags_[ 1 ] ),
                 equal_to( '--driver-mode=g++' ) )
    assert_that( str( info.compiler_flags_[ 2 ] ),
                 equal_to( 'example.cc' ) )
