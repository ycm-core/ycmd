# Copyright (C) 2016-2020 ycmd contributors.
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
import subprocess
import tempfile
from hamcrest import ( assert_that,
                       calling,
                       empty,
                       equal_to,
                       has_length,
                       has_property,
                       instance_of,
                       raises )
from unittest.mock import patch, call
from nose.tools import eq_, ok_
from types import ModuleType
from ycmd import utils
from ycmd.tests.test_utils import ( WindowsOnly, UnixOnly,
                                    CurrentWorkingDirectory,
                                    TemporaryExecutable )
from ycmd.tests import PathToTestFile
from ycmd.utils import ImportAndCheckCore

# NOTE: isinstance() vs type() is carefully used in this test file. Before
# changing things here, read the comments in utils.ToBytes.


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


def JoinLinesAsUnicode_Bytes_test():
  value = utils.JoinLinesAsUnicode( [ bytes( b'abc' ), bytes( b'xyz' ) ] )
  eq_( value, u'abc\nxyz' )
  ok_( isinstance( value, str ) )


def JoinLinesAsUnicode_Str_test():
  value = utils.JoinLinesAsUnicode( [ u'abc', u'xyz' ] )
  eq_( value, u'abc\nxyz' )
  ok_( isinstance( value, str ) )


def JoinLinesAsUnicode_EmptyList_test():
  value = utils.JoinLinesAsUnicode( [] )
  eq_( value, u'' )
  ok_( isinstance( value, str ) )


def JoinLinesAsUnicode_BadInput_test():
  assert_that(
    calling( utils.JoinLinesAsUnicode ).with_args( [ 42 ] ),
    raises( ValueError, 'lines must contain either strings or bytes' )
  )


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


def PathLeftSplit_test():
  # Tuples of ( path, expected_result ) for utils.PathLeftSplit.
  tests = [
    ( '',              ( '', '' ) ),
    ( 'foo',           ( 'foo', '' ) ),
    ( 'foo/bar',       ( 'foo', 'bar' ) ),
    ( 'foo/bar/xyz',   ( 'foo', 'bar/xyz' ) ),
    ( 'foo/bar/xyz/',  ( 'foo', 'bar/xyz' ) ),
    ( '/',             ( '/', '' ) ),
    ( '/foo',          ( '/', 'foo' ) ),
    ( '/foo/bar',      ( '/', 'foo/bar' ) ),
    ( '/foo/bar/xyz',  ( '/', 'foo/bar/xyz' ) ),
    ( '/foo/bar/xyz/', ( '/', 'foo/bar/xyz' ) )
  ]
  for test in tests:
    yield lambda test: eq_( utils.PathLeftSplit( test[ 0 ] ), test[ 1 ] ), test


@WindowsOnly
def PathLeftSplit_Windows_test():
  # Tuples of ( path, expected_result ) for utils.PathLeftSplit.
  tests = [
    ( 'foo\\bar',            ( 'foo', 'bar' ) ),
    ( 'foo\\bar\\xyz',       ( 'foo', 'bar\\xyz' ) ),
    ( 'foo\\bar\\xyz\\',     ( 'foo', 'bar\\xyz' ) ),
    ( 'C:\\',                ( 'C:\\', '' ) ),
    ( 'C:\\foo',             ( 'C:\\', 'foo' ) ),
    ( 'C:\\foo\\bar',        ( 'C:\\', 'foo\\bar' ) ),
    ( 'C:\\foo\\bar\\xyz',   ( 'C:\\', 'foo\\bar\\xyz' ) ),
    ( 'C:\\foo\\bar\\xyz\\', ( 'C:\\', 'foo\\bar\\xyz' ) )
  ]
  for test in tests:
    yield lambda test: eq_( utils.PathLeftSplit( test[ 0 ] ), test[ 1 ] ), test


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
    # Ignore \r on purpose.
    ( '\r', [ '\r' ] ),
    ( '\r ', [ '\r ' ] ),
    ( 'test\r', [ 'test\r' ] ),
    ( '\n\r', [ '', '\r' ] ),
    ( '\r\n', [ '\r', '' ] ),
    ( '\r\n\n', [ '\r', '', '' ] ),
    ( 'test\ntesting', [ 'test', 'testing' ] ),
    ( '\ntesting', [ '', 'testing' ] ),
    # Do not split lines on \f and \v characters.
    ( '\f\n\v', [ '\f', '\v' ] )
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


@patch( 'ycmd.utils.ProcessIsRunning', return_value = True )
def WaitUntilProcessIsTerminated_TimedOut_test( *args ):
  assert_that(
    calling( utils.WaitUntilProcessIsTerminated ).with_args( None,
                                                             timeout = 0 ),
    raises( RuntimeError,
            'Waited process to terminate for 0 seconds, aborting.' )
  )


def LoadPythonSource_UnicodePath_test():
  filename = PathToTestFile( u'uni¢𐍈d€.py' )
  module = utils.LoadPythonSource( 'module_name', filename )
  assert_that( module, instance_of( ModuleType ) )
  assert_that( module.__file__, equal_to( filename ) )
  assert_that( module.__name__, equal_to( 'module_name' ) )
  assert_that( module, has_property( 'SomeMethod' ) )
  assert_that( module.SomeMethod(), equal_to( True ) )


def GetCurrentDirectory_Py3NoCurrentDirectory_test():
  with patch( 'os.getcwd', side_effect = FileNotFoundError ): # noqa
    eq_( utils.GetCurrentDirectory(), tempfile.gettempdir() )


def HashableDict_Equality_test():
  dict1 = { 'key': 'value' }
  dict2 = { 'key': 'another_value' }
  ok_( utils.HashableDict( dict1 ) == utils.HashableDict( dict1 ) )
  ok_( not utils.HashableDict( dict1 ) != utils.HashableDict( dict1 ) )
  ok_( not utils.HashableDict( dict1 ) == dict1 )
  ok_( utils.HashableDict( dict1 ) != dict1 )
  ok_( not utils.HashableDict( dict1 ) == utils.HashableDict( dict2 ) )
  ok_( utils.HashableDict( dict1 ) != utils.HashableDict( dict2 ) )


@patch( 'ycmd.utils.LOGGER', autospec = True )
def RunImportAndCheckCoreException( test, logger ):
  with patch( 'ycmd.utils.ImportCore',
              side_effect = ImportError( test[ 'exception_message' ] ) ):
    assert_that( ImportAndCheckCore(), equal_to( test[ 'exit_status' ] ) )

  assert_that( logger.method_calls, has_length( 1 ) )
  logger.exception.assert_called_with( test[ 'logged_message' ] )


@patch( 'ycmd.utils.LOGGER', autospec = True )
def ImportAndCheckCore_Compatible_test( logger ):
  assert_that( ImportAndCheckCore(), equal_to( 0 ) )
  assert_that( logger.method_calls, empty() )


def ImportAndCheckCore_Unexpected_test():
  RunImportAndCheckCoreException( {
    'exception_message': 'unexpected import exception',
    'exit_status': 3,
    'logged_message': 'unexpected import exception'
  } )


def ImportAndCheckCore_Missing_test():
  import_errors = [ "No module named 'ycm_core'" ]

  for error in import_errors:
    yield RunImportAndCheckCoreException, {
      'exception_message': error,
      'exit_status': 4,
      'logged_message': 'ycm_core library not detected; you need to compile it '
                        'by running the build.py script. See the documentation '
                        'for more details.'
    }


@patch( 'ycm_core.YcmCoreVersion', side_effect = AttributeError() )
@patch( 'ycmd.utils.LOGGER', autospec = True )
def ImportAndCheckCore_Outdated_NoYcmCoreVersionMethod_test( logger,
                                                                    *args ):
  assert_that( ImportAndCheckCore(), equal_to( 7 ) )
  assert_that( logger.method_calls, has_length( 1 ) )
  logger.exception.assert_called_with(
    'ycm_core library too old; PLEASE RECOMPILE by running the build.py '
    'script. See the documentation for more details.' )


@patch( 'ycm_core.YcmCoreVersion', return_value = 10 )
@patch( 'ycmd.utils.ExpectedCoreVersion', return_value = 11 )
@patch( 'ycmd.utils.LOGGER', autospec = True )
def ImportAndCheckCore_Outdated_NoVersionMatch_test( logger, *args ):
  assert_that( ImportAndCheckCore(), equal_to( 7 ) )
  assert_that( logger.method_calls, has_length( 1 ) )
  logger.error.assert_called_with(
    'ycm_core library too old; PLEASE RECOMPILE by running the build.py '
    'script. See the documentation for more details.' )


@patch( 'ycmd.utils.ListDirectory', return_value = [] )
def GetClangResourceDir_NotFound_test( *args ):
  assert_that(
    calling( utils.GetClangResourceDir ),
    raises( RuntimeError, 'Cannot find Clang resource directory' )
  )


def MakeSafeFileNameString_test():
  tests = (
    ( 'this is a test 0123 -x', 'this_is_a_test_0123__x' ),
    ( 'This Is A Test 0123 -x', 'this_is_a_test_0123__x' ),
    ( 'T˙^ß ^ß å †´ß† 0123 -x', 't______________0123__x' ),
    ( 'contains/slashes',       'contains_slashes' ),
    ( 'contains/newline/\n',    'contains_newline__' ),
    ( '',                       '' ),
  )
  for t in tests:
    assert_that( utils.MakeSafeFileNameString( t[ 0 ] ),
                 equal_to( t[ 1 ] ) )
