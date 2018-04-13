# encoding: utf-8
#
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
# Not installing aliases from python-future; it's unreliable and slow.
# Intentionally not importing all builtins!

import os

from nose.tools import eq_
from future.types.newbytes import newbytes
from future.types.newstr import newstr
from future.utils import native

import ycm_core
from ycmd.tests.test_utils import ClangOnly, Py2Only, Py3Only
from ycmd.utils import ToBytes, ToUnicode, OnWindows


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


# unicode literals are identical to regular string literals on Python 3.
@Py2Only
def GetUtf8String_Unicode_test():
  eq_( b'fo\xc3\xb8', ycm_core.GetUtf8String( u'foø' ) )


# newstr is an emulation of Python 3 str on Python 2.
@Py2Only
def GetUtf8String_NewStr_test():
  eq_( b'fo\xc3\xb8', ycm_core.GetUtf8String( newstr( 'foø', 'utf8' ) ) )


# newbytes is an emulation of Python 3 bytes on Python 2.
@Py2Only
def GetUtf8String_NewBytes_test():
  eq_( b'fo\xc3\xb8', ycm_core.GetUtf8String( newbytes( 'foø' ) ) )


# bytes is identical to str on Python 2.
@Py3Only
def GetUtf8String_Bytes_test():
  eq_( b'fo\xc3\xb8', ycm_core.GetUtf8String( bytes( 'foø', 'utf8' ) ) )


def GetUtf8String_Int_test():
  eq_( b'123', ycm_core.GetUtf8String( 123 ) )


@ClangOnly
@Py2Only
def CompilationDatabase_Py2Str_test():
  cc_dir = native( ToBytes( PATH_TO_COMPILE_COMMANDS ) )
  cc_filename = native( ToBytes( os.path.join( COMPILE_COMMANDS_WORKING_DIR,
                                               'example.cc' ) ) )

  # Ctor reads ycmd/tests/testdata/[unix|windows]/compile_commands.json
  db = ycm_core.CompilationDatabase( cc_dir )
  info = db.GetCompilationInfoForFile( cc_filename )

  eq_( str( info.compiler_working_dir_ ), COMPILE_COMMANDS_WORKING_DIR )
  eq_( str( info.compiler_flags_[ 0 ] ), '/usr/bin/clang++' )
  eq_( str( info.compiler_flags_[ 1 ] ), 'example.cc' )


@ClangOnly
@Py2Only
def CompilationDatabase_Py2Unicode_test():
  cc_dir = native( ToUnicode( PATH_TO_COMPILE_COMMANDS ) )
  cc_filename = native( ToUnicode( os.path.join( COMPILE_COMMANDS_WORKING_DIR,
                                                 'example.cc' ) ) )

  # Ctor reads ycmd/tests/testdata/[unix|windows]/compile_commands.json
  db = ycm_core.CompilationDatabase( cc_dir )
  info = db.GetCompilationInfoForFile( cc_filename )

  eq_( str( info.compiler_working_dir_ ), COMPILE_COMMANDS_WORKING_DIR )
  eq_( str( info.compiler_flags_[ 0 ] ), '/usr/bin/clang++' )
  eq_( str( info.compiler_flags_[ 1 ] ), 'example.cc' )


@ClangOnly
@Py3Only
def CompilationDatabase_Py3Bytes_test():
  cc_dir = native( ToBytes( PATH_TO_COMPILE_COMMANDS ) )
  cc_filename = native( ToBytes( os.path.join( COMPILE_COMMANDS_WORKING_DIR,
                                               'example.cc' ) ) )

  # Ctor reads ycmd/tests/testdata/[unix|windows]/compile_commands.json
  db = ycm_core.CompilationDatabase( cc_dir )
  info = db.GetCompilationInfoForFile( cc_filename )

  eq_( str( info.compiler_working_dir_ ), COMPILE_COMMANDS_WORKING_DIR )
  eq_( str( info.compiler_flags_[ 0 ] ), '/usr/bin/clang++' )
  eq_( str( info.compiler_flags_[ 1 ] ), 'example.cc' )


@ClangOnly
def CompilationDatabase_NativeString_test():
  cc_dir = PATH_TO_COMPILE_COMMANDS
  cc_filename = os.path.join( COMPILE_COMMANDS_WORKING_DIR, 'example.cc' )

  # Ctor reads ycmd/tests/testdata/[unix|windows]/compile_commands.json
  db = ycm_core.CompilationDatabase( cc_dir )
  info = db.GetCompilationInfoForFile( cc_filename )

  eq_( str( info.compiler_working_dir_ ), COMPILE_COMMANDS_WORKING_DIR )
  eq_( str( info.compiler_flags_[ 0 ] ), '/usr/bin/clang++' )
  eq_( str( info.compiler_flags_[ 1 ] ), 'example.cc' )
