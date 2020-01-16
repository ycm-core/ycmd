# Copyright (C) 2020 ycmd contributors
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

from nose.tools import eq_

import ycm_core
from ycmd.tests.test_utils import ClangOnly
from ycmd.utils import ToBytes, OnWindows


# We don't use PathToTestFile from test_utils module because this module
# imports future modules that may change the path type.
PATH_TO_TESTDATA = os.path.abspath( os.path.join( os.path.dirname( __file__ ),
                                                  'testdata' ) )
PATH_TO_COMPILE_COMMANDS = (
  os.path.join( PATH_TO_TESTDATA, 'windows' ) if OnWindows() else
  os.path.join( PATH_TO_TESTDATA, 'unix' ) )
COMPILE_COMMANDS_WORKING_DIR = 'C:\\dir' if OnWindows() else '/dir'


def GetUtf8String_Str_test():
  eq_( b'fo\xc3\xb8', ycm_core.GetUtf8String( 'foø' ) )


def GetUtf8String_Bytes_test():
  eq_( b'fo\xc3\xb8', ycm_core.GetUtf8String( bytes( 'foø', 'utf8' ) ) )


def GetUtf8String_Int_test():
  eq_( b'123', ycm_core.GetUtf8String( 123 ) )


@ClangOnly
def CompilationDatabase_Py3Bytes_test():
  cc_dir = ToBytes( PATH_TO_COMPILE_COMMANDS )
  cc_filename = ToBytes( os.path.join( COMPILE_COMMANDS_WORKING_DIR,
                                       'example.cc' ) )

  # Ctor reads ycmd/tests/testdata/[unix|windows]/compile_commands.json
  db = ycm_core.CompilationDatabase( cc_dir )
  info = db.GetCompilationInfoForFile( cc_filename )

  eq_( str( info.compiler_working_dir_ ), COMPILE_COMMANDS_WORKING_DIR )
  eq_( str( info.compiler_flags_[ 0 ] ), '/usr/bin/clang++' )
  eq_( str( info.compiler_flags_[ 1 ] ), '--driver-mode=g++' )
  eq_( str( info.compiler_flags_[ 2 ] ), 'example.cc' )


@ClangOnly
def CompilationDatabase_NativeString_test():
  cc_dir = PATH_TO_COMPILE_COMMANDS
  cc_filename = os.path.join( COMPILE_COMMANDS_WORKING_DIR, 'example.cc' )

  # Ctor reads ycmd/tests/testdata/[unix|windows]/compile_commands.json
  db = ycm_core.CompilationDatabase( cc_dir )
  info = db.GetCompilationInfoForFile( cc_filename )

  eq_( str( info.compiler_working_dir_ ), COMPILE_COMMANDS_WORKING_DIR )
  eq_( str( info.compiler_flags_[ 0 ] ), '/usr/bin/clang++' )
  eq_( str( info.compiler_flags_[ 1 ] ), '--driver-mode=g++' )
  eq_( str( info.compiler_flags_[ 2 ] ), 'example.cc' )
