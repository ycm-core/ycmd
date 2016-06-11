# encoding: utf-8
#
# Copyright (C) 2016  ycmd contributors.
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
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()
from builtins import *  # noqa

import os
import subprocess
import tempfile
from shutil import rmtree
import ycm_core
from future.utils import native
from mock import patch, call
from nose.tools import eq_, ok_
from ycmd import utils
from ycmd.tests.test_utils import ( Py2Only, Py3Only, WindowsOnly, UnixOnly,
                                    CurrentWorkingDirectory,
                                    TemporaryExecutable )
from ycmd.tests import PathToTestFile

# NOTE: isinstance() vs type() is carefully used in this test file. Before
# changing things here, read the comments in utils.ToBytes.


@Py2Only
def ToBytes_Py2Bytes_test():
  value = utils.ToBytes( bytes( 'abc' ) )
  eq_( value, bytes( 'abc' ) )
  eq_( type( value ), bytes )


@Py2Only
def ToBytes_Py2Str_test():
  value = utils.ToBytes( 'abc' )
  eq_( value, bytes( 'abc' ) )
  eq_( type( value ), bytes )


@Py2Only
def ToBytes_Py2FutureStr_test():
  value = utils.ToBytes( str( 'abc' ) )
  eq_( value, bytes( 'abc' ) )
  eq_( type( value ), bytes )


@Py2Only
def ToBytes_Py2Unicode_test():
  value = utils.ToBytes( u'abc' )
  eq_( value, bytes( 'abc' ) )
  eq_( type( value ), bytes )


@Py2Only
def ToBytes_Py2Int_test():
  value = utils.ToBytes( 123 )
  eq_( value, bytes( '123' ) )
  eq_( type( value ), bytes )


def ToBytes_Bytes_test():
  value = utils.ToBytes( bytes( b'abc' ) )
  eq_( value, bytes( b'abc' ) )
  eq_( type( value ), bytes )


def ToBytes_Str_test():
  value = utils.ToBytes( u'abc' )
  eq_( value, bytes( b'abc' ) )
  eq_( type( value ), bytes )


def ToBytes_Int_test():
  value = utils.ToBytes( 123 )
  eq_( value, bytes( b'123' ) )
  eq_( type( value ), bytes )


def ToBytes_None_test():
  value = utils.ToBytes( None )
  eq_( value, bytes( b'' ) )
  eq_( type( value ), bytes )


@Py2Only
def ToUnicode_Py2Bytes_test():
  value = utils.ToUnicode( bytes( 'abc' ) )
  eq_( value, u'abc' )
  ok_( isinstance( value, str ) )


@Py2Only
def ToUnicode_Py2Str_test():
  value = utils.ToUnicode( 'abc' )
  eq_( value, u'abc' )
  ok_( isinstance( value, str ) )


@Py2Only
def ToUnicode_Py2FutureStr_test():
  value = utils.ToUnicode( str( 'abc' ) )
  eq_( value, u'abc' )
  ok_( isinstance( value, str ) )


@Py2Only
def ToUnicode_Py2Unicode_test():
  value = utils.ToUnicode( u'abc' )
  eq_( value, u'abc' )
  ok_( isinstance( value, str ) )


@Py2Only
def ToUnicode_Py2Int_test():
  value = utils.ToUnicode( 123 )
  eq_( value, u'123' )
  ok_( isinstance( value, str ) )


def ToUnicode_Bytes_test():
  value = utils.ToUnicode( bytes( b'abc' ) )
  eq_( value, u'abc' )
  ok_( isinstance( value, str ) )


def ToUnicode_Str_test():
  value = utils.ToUnicode( u'abc' )
  eq_( value, u'abc' )
  ok_( isinstance( value, str ) )


def ToUnicode_Int_test():
  value = utils.ToUnicode( 123 )
  eq_( value, u'123' )
  ok_( isinstance( value, str ) )


def ToUnicode_None_test():
  value = utils.ToUnicode( None )
  eq_( value, u'' )
  ok_( isinstance( value, str ) )


@Py2Only
def ToCppStringCompatible_Py2Str_test():
  value = utils.ToCppStringCompatible( 'abc' )
  eq_( value, 'abc' )
  eq_( type( value ), type( '' ) )

  vector = ycm_core.StringVector()
  vector.append( value )
  eq_( vector[ 0 ], 'abc' )


@Py2Only
def ToCppStringCompatible_Py2Bytes_test():
  value = utils.ToCppStringCompatible( bytes( b'abc' ) )
  eq_( value, 'abc' )
  eq_( type( value ), type( '' ) )

  vector = ycm_core.StringVector()
  vector.append( value )
  eq_( vector[ 0 ], 'abc' )


@Py2Only
def ToCppStringCompatible_Py2Unicode_test():
  value = utils.ToCppStringCompatible( u'abc' )
  eq_( value, 'abc' )
  eq_( type( value ), type( '' ) )

  vector = ycm_core.StringVector()
  vector.append( value )
  eq_( vector[ 0 ], 'abc' )


@Py2Only
def ToCppStringCompatible_Py2Int_test():
  value = utils.ToCppStringCompatible( 123 )
  eq_( value, '123' )
  eq_( type( value ), type( '' ) )

  vector = ycm_core.StringVector()
  vector.append( value )
  eq_( vector[ 0 ], '123' )


@Py3Only
def ToCppStringCompatible_Py3Bytes_test():
  value = utils.ToCppStringCompatible( bytes( b'abc' ) )
  eq_( value, bytes( b'abc' ) )
  ok_( isinstance( value, bytes ) )

  vector = ycm_core.StringVector()
  vector.append( value )
  eq_( vector[ 0 ], 'abc' )


@Py3Only
def ToCppStringCompatible_Py3Str_test():
  value = utils.ToCppStringCompatible( 'abc' )
  eq_( value, bytes( b'abc' ) )
  ok_( isinstance( value, bytes ) )

  vector = ycm_core.StringVector()
  vector.append( value )
  eq_( vector[ 0 ], 'abc' )


@Py3Only
def ToCppStringCompatible_Py3Int_test():
  value = utils.ToCppStringCompatible( 123 )
  eq_( value, bytes( b'123' ) )
  ok_( isinstance( value, bytes ) )

  vector = ycm_core.StringVector()
  vector.append( value )
  eq_( vector[ 0 ], '123' )


def PathToCreatedTempDir_DirDoesntExist_test():
  tempdir = PathToTestFile( 'tempdir' )
  rmtree( tempdir, ignore_errors = True )

  try:
    eq_( utils.PathToCreatedTempDir( tempdir ), tempdir )
  finally:
    rmtree( tempdir, ignore_errors = True )


def PathToCreatedTempDir_DirDoesExist_test():
  tempdir = PathToTestFile( 'tempdir' )
  os.makedirs( tempdir )

  try:
    eq_( utils.PathToCreatedTempDir( tempdir ), tempdir )
  finally:
    rmtree( tempdir, ignore_errors = True )


def RemoveIfExists_Exists_test():
  tempfile = PathToTestFile( 'remove-if-exists' )
  open( tempfile, 'a' ).close()
  ok_( os.path.exists( tempfile ) )
  utils.RemoveIfExists( tempfile )
  ok_( not os.path.exists( tempfile ) )


def RemoveIfExists_DoesntExist_test():
  tempfile = PathToTestFile( 'remove-if-exists' )
  ok_( not os.path.exists( tempfile ) )
  utils.RemoveIfExists( tempfile )
  ok_( not os.path.exists( tempfile ) )


def PathToFirstExistingExecutable_Basic_test():
  if utils.OnWindows():
    ok_( utils.PathToFirstExistingExecutable( [ 'notepad.exe' ] ) )
  else:
    ok_( utils.PathToFirstExistingExecutable( [ 'cat' ] ) )


def PathToFirstExistingExecutable_Failure_test():
  ok_( not utils.PathToFirstExistingExecutable( [ 'ycmd-foobar' ] ) )


@UnixOnly
@patch( 'subprocess.Popen' )
def SafePopen_RemoveStdinWindows_test( *args ):
  utils.SafePopen( [ 'foo' ], stdin_windows = 'bar' )
  eq_( subprocess.Popen.call_args, call( [ 'foo' ] ) )


@WindowsOnly
@patch( 'subprocess.Popen' )
def SafePopen_ReplaceStdinWindowsPIPEOnWindows_test( *args ):
  utils.SafePopen( [ 'foo' ], stdin_windows = subprocess.PIPE )
  eq_( subprocess.Popen.call_args,
       call( [ 'foo' ],
             stdin = subprocess.PIPE,
             creationflags = utils.CREATE_NO_WINDOW ) )


@WindowsOnly
@patch( 'ycmd.utils.GetShortPathName', side_effect = lambda x: x )
@patch( 'subprocess.Popen' )
def SafePopen_WindowsPath_test( *args ):
  tempfile = PathToTestFile( 'safe-popen-file' )
  open( tempfile, 'a' ).close()

  try:
    utils.SafePopen( [ 'foo', tempfile ], stdin_windows = subprocess.PIPE )
    eq_( subprocess.Popen.call_args,
         call( [ 'foo', tempfile ],
               stdin = subprocess.PIPE,
               creationflags = utils.CREATE_NO_WINDOW ) )
  finally:
    os.remove( tempfile )


@UnixOnly
def ConvertArgsToShortPath_PassthroughOnUnix_test( *args ):
  eq_( 'foo', utils.ConvertArgsToShortPath( 'foo' ) )
  eq_( [ 'foo' ], utils.ConvertArgsToShortPath( [ 'foo' ] ) )


@UnixOnly
def SetEnviron_UnicodeOnUnix_test( *args ):
  env = {}
  utils.SetEnviron( env, u'key', u'value' )
  eq_( env, { u'key': u'value' } )


@Py2Only
@WindowsOnly
def SetEnviron_UnicodeOnWindows_test( *args ):
  env = {}
  utils.SetEnviron( env, u'key', u'value' )
  eq_( env, { native( bytes( b'key' ) ): native( bytes( b'value' ) ) } )


def PathsToAllParentFolders_Basic_test():
  eq_( [
    os.path.normpath( '/home/user/projects' ),
    os.path.normpath( '/home/user' ),
    os.path.normpath( '/home' ),
    os.path.normpath( '/' )
  ], list( utils.PathsToAllParentFolders( '/home/user/projects/test.c' ) ) )


@patch( 'os.path.isdir', return_value = True )
def PathsToAllParentFolders_IsDirectory_test( *args ):
  eq_( [
    os.path.normpath( '/home/user/projects' ),
    os.path.normpath( '/home/user' ),
    os.path.normpath( '/home' ),
    os.path.normpath( '/' )
  ], list( utils.PathsToAllParentFolders( '/home/user/projects' ) ) )


def PathsToAllParentFolders_FileAtRoot_test():
  eq_( [ os.path.normpath( '/' ) ],
       list( utils.PathsToAllParentFolders( '/test.c' ) ) )


@WindowsOnly
def PathsToAllParentFolders_WindowsPath_test():
  eq_( [
    os.path.normpath( r'C:\\foo\\goo\\zoo' ),
    os.path.normpath( r'C:\\foo\\goo' ),
    os.path.normpath( r'C:\\foo' ),
    os.path.normpath( r'C:\\' )
  ], list( utils.PathsToAllParentFolders( r'C:\\foo\\goo\\zoo\\test.c' ) ) )


def OpenForStdHandle_PrintDoesntThrowException_test():
  try:
    temp = PathToTestFile( 'open-for-std-handle' )
    with utils.OpenForStdHandle( temp ) as f:
      print( 'foo', file = f )
  finally:
    os.remove( temp )


def CodepointOffsetToByteOffset_test():
  # Tuples of ( ( unicode_line_value, codepoint_offset ), expected_result ).
  tests = [
    # Simple ascii strings.
    ( ( 'test', 1 ), 1 ),
    ( ( 'test', 4 ), 4 ),
    ( ( 'test', 5 ), 5 ),

    # Unicode char at beginning.
    ( ( '†est', 1 ), 1 ),
    ( ( '†est', 2 ), 4 ),
    ( ( '†est', 4 ), 6 ),
    ( ( '†est', 5 ), 7 ),

    # Unicode char at end.
    ( ( 'tes†', 1 ), 1 ),
    ( ( 'tes†', 2 ), 2 ),
    ( ( 'tes†', 4 ), 4 ),
    ( ( 'tes†', 5 ), 7 ),

    # Unicode char in middle.
    ( ( 'tes†ing', 1 ), 1 ),
    ( ( 'tes†ing', 2 ), 2 ),
    ( ( 'tes†ing', 4 ), 4 ),
    ( ( 'tes†ing', 5 ), 7 ),
    ( ( 'tes†ing', 7 ), 9 ),
    ( ( 'tes†ing', 8 ), 10 ),

    # Converts bytes to Unicode.
    ( ( utils.ToBytes( '†est' ), 2 ), 4 )
  ]

  for test in tests:
    yield lambda: eq_( utils.CodepointOffsetToByteOffset( *test[ 0 ] ),
                       test[ 1 ] )


def ByteOffsetToCodepointOffset_test():
  # Tuples of ( ( unicode_line_value, byte_offset ), expected_result ).
  tests = [
    # Simple ascii strings.
    ( ( 'test', 1 ), 1 ),
    ( ( 'test', 4 ), 4 ),
    ( ( 'test', 5 ), 5 ),

    # Unicode char at beginning.
    ( ( '†est', 1 ), 1 ),
    ( ( '†est', 4 ), 2 ),
    ( ( '†est', 6 ), 4 ),
    ( ( '†est', 7 ), 5 ),

    # Unicode char at end.
    ( ( 'tes†', 1 ), 1 ),
    ( ( 'tes†', 2 ), 2 ),
    ( ( 'tes†', 4 ), 4 ),
    ( ( 'tes†', 7 ), 5 ),

    # Unicode char in middle.
    ( ( 'tes†ing', 1 ), 1 ),
    ( ( 'tes†ing', 2 ), 2 ),
    ( ( 'tes†ing', 4 ), 4 ),
    ( ( 'tes†ing', 7 ), 5 ),
    ( ( 'tes†ing', 9 ), 7 ),
    ( ( 'tes†ing', 10 ), 8 ),
  ]

  for test in tests:
    yield lambda: eq_( utils.ByteOffsetToCodepointOffset( *test[ 0 ] ),
                       test[ 1 ] )


def SplitLines_test():
  # Tuples of ( input, expected_output ) for utils.SplitLines.
  tests = [
    ( '', [ '' ] ),
    ( ' ', [ ' ' ] ),
    ( '\n', [ '', '' ] ),
    ( ' \n', [ ' ', '' ] ),
    ( ' \n ', [ ' ', ' ' ] ),
    ( 'test\n', [ 'test', '' ] ),
    ( '\r', [ '', '' ] ),
    ( '\r ', [ '', ' ' ] ),
    ( 'test\r', [ 'test', '' ] ),
    ( '\n\r', [ '', '', '' ] ),
    ( '\r\n', [ '', '' ] ),
    ( '\r\n\n', [ '', '', '' ] ),
    # Other behaviors are just the behavior of splitlines, so just a couple of
    # tests to prove that we don't mangle it.
    ( 'test\ntesting', [ 'test', 'testing' ] ),
    ( '\ntesting', [ '', 'testing' ] ),
  ]

  for test in tests:
    yield lambda: eq_( utils.SplitLines( test[ 0 ] ), test[ 1 ] )


def FindExecutable_AbsolutePath_test():
  with TemporaryExecutable() as executable:
    eq_( executable, utils.FindExecutable( executable ) )


def FindExecutable_RelativePath_test():
  with TemporaryExecutable() as executable:
    dirname, exename = os.path.split( executable )
    relative_executable = os.path.join( '.', exename )
    with CurrentWorkingDirectory( dirname ):
      eq_( relative_executable, utils.FindExecutable( relative_executable ) )


@patch.dict( 'os.environ', { 'PATH': tempfile.gettempdir() } )
def FindExecutable_ExecutableNameInPath_test():
  with TemporaryExecutable() as executable:
    dirname, exename = os.path.split( executable )
    eq_( executable, utils.FindExecutable( exename ) )


def FindExecutable_ReturnNoneIfFileIsNotExecutable_test():
  with tempfile.NamedTemporaryFile() as non_executable:
    eq_( None, utils.FindExecutable( non_executable.name ) )


@WindowsOnly
def FindExecutable_CurrentDirectory_test():
  with TemporaryExecutable() as executable:
    dirname, exename = os.path.split( executable )
    with CurrentWorkingDirectory( dirname ):
      eq_( executable, utils.FindExecutable( exename ) )


@WindowsOnly
@patch.dict( 'os.environ', { 'PATHEXT': '.xyz' } )
def FindExecutable_AdditionalPathExt_test():
  with TemporaryExecutable( extension = '.xyz' ) as executable:
    eq_( executable, utils.FindExecutable( executable ) )
