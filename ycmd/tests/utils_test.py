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
import pytest
import subprocess
import tempfile
from hamcrest import ( assert_that,
                       calling,
                       contains_exactly,
                       empty,
                       equal_to,
                       has_length,
                       has_property,
                       instance_of,
                       raises )
from unittest.mock import patch, call
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
  assert_that( value, equal_to( bytes( b'abc' ) ) )
  assert_that( type( value ), equal_to( bytes ) )


def ToBytes_Str_test():
  value = utils.ToBytes( u'abc' )
  assert_that( value, equal_to( bytes( b'abc' ) ) )
  assert_that( type( value ), equal_to( bytes ) )


def ToBytes_Int_test():
  value = utils.ToBytes( 123 )
  assert_that( value, equal_to( bytes( b'123' ) ) )
  assert_that( type( value ), equal_to( bytes ) )


def ToBytes_None_test():
  value = utils.ToBytes( None )
  assert_that( value, equal_to( bytes( b'' ) ) )
  assert_that( type( value ), equal_to( bytes ) )


def ToUnicode_Bytes_test():
  value = utils.ToUnicode( bytes( b'abc' ) )
  assert_that( value, equal_to( u'abc' ) )
  assert_that( isinstance( value, str ) )


def ToUnicode_Str_test():
  value = utils.ToUnicode( u'abc' )
  assert_that( value, equal_to( u'abc' ) )
  assert_that( isinstance( value, str ) )


def ToUnicode_Int_test():
  value = utils.ToUnicode( 123 )
  assert_that( value, equal_to( u'123' ) )
  assert_that( isinstance( value, str ) )


def ToUnicode_None_test():
  value = utils.ToUnicode( None )
  assert_that( value, equal_to( u'' ) )
  assert_that( isinstance( value, str ) )


def JoinLinesAsUnicode_Bytes_test():
  value = utils.JoinLinesAsUnicode( [ bytes( b'abc' ), bytes( b'xyz' ) ] )
  assert_that( value, equal_to( u'abc\nxyz' ) )
  assert_that( isinstance( value, str ) )


def JoinLinesAsUnicode_Str_test():
  value = utils.JoinLinesAsUnicode( [ u'abc', u'xyz' ] )
  assert_that( value, equal_to( u'abc\nxyz' ) )
  assert_that( isinstance( value, str ) )


def JoinLinesAsUnicode_EmptyList_test():
  value = utils.JoinLinesAsUnicode( [] )
  assert_that( value, equal_to( u'' ) )
  assert_that( isinstance( value, str ) )


def JoinLinesAsUnicode_BadInput_test():
  assert_that(
    calling( utils.JoinLinesAsUnicode ).with_args( [ 42 ] ),
    raises( ValueError, 'lines must contain either strings or bytes' )
  )


def RemoveIfExists_Exists_test():
  tempfile = PathToTestFile( 'remove-if-exists' )
  open( tempfile, 'a' ).close()
  assert_that( os.path.exists( tempfile ) )
  utils.RemoveIfExists( tempfile )
  assert_that( not os.path.exists( tempfile ) )


def RemoveIfExists_DoesntExist_test():
  tempfile = PathToTestFile( 'remove-if-exists' )
  assert_that( not os.path.exists( tempfile ) )
  utils.RemoveIfExists( tempfile )
  assert_that( not os.path.exists( tempfile ) )


def PathToFirstExistingExecutable_Basic_test():
  if utils.OnWindows():
    assert_that( utils.PathToFirstExistingExecutable( [ 'notepad.exe' ] ) )
  else:
    assert_that( utils.PathToFirstExistingExecutable( [ 'cat' ] ) )


def PathToFirstExistingExecutable_Failure_test():
  assert_that( not utils.PathToFirstExistingExecutable( [ 'ycmd-foobar' ] ) )


@UnixOnly
@patch( 'subprocess.Popen' )
def SafePopen_RemoveStdinWindows_test( *args ):
  utils.SafePopen( [ 'foo' ], stdin_windows = 'bar' )
  assert_that( subprocess.Popen.call_args, equal_to( call( [ 'foo' ] ) ) )


@WindowsOnly
@patch( 'subprocess.Popen' )
def SafePopen_ReplaceStdinWindowsPIPEOnWindows_test( *args ):
  utils.SafePopen( [ 'foo' ], stdin_windows = subprocess.PIPE )
  assert_that( subprocess.Popen.call_args,
               equal_to( call( [ 'foo' ],
                               stdin = subprocess.PIPE,
                               creationflags = utils.CREATE_NO_WINDOW ) ) )


@WindowsOnly
@patch( 'subprocess.Popen' )
def SafePopen_WindowsPath_test( *args ):
  tempfile = PathToTestFile( 'safe-popen-file' )
  open( tempfile, 'a' ).close()

  try:
    utils.SafePopen( [ 'foo', tempfile ], stdin_windows = subprocess.PIPE )
    assert_that( subprocess.Popen.call_args,
                 equal_to( call( [ 'foo', tempfile ],
                                 stdin = subprocess.PIPE,
                                 creationflags = utils.CREATE_NO_WINDOW ) ) )
  finally:
    os.remove( tempfile )


def PathsToAllParentFolders_Basic_test():
  assert_that( utils.PathsToAllParentFolders( '/home/user/projects/test.c' ),
    contains_exactly(
      os.path.normpath( '/home/user/projects' ),
      os.path.normpath( '/home/user' ),
      os.path.normpath( '/home' ),
      os.path.normpath( '/' ),
    )
  )



@patch( 'os.path.isdir', return_value = True )
def PathsToAllParentFolders_IsDirectory_test( *args ):
  assert_that( utils.PathsToAllParentFolders( '/home/user/projects' ),
    contains_exactly(
      os.path.normpath( '/home/user/projects' ),
      os.path.normpath( '/home/user' ),
      os.path.normpath( '/home' ),
      os.path.normpath( '/' )
    )
  )


def PathsToAllParentFolders_FileAtRoot_test():
  assert_that( utils.PathsToAllParentFolders( '/test.c' ),
               contains_exactly( os.path.normpath( '/' ) ) )


@WindowsOnly
def PathsToAllParentFolders_WindowsPath_test():
  assert_that( utils.PathsToAllParentFolders( r'C:\\foo\\goo\\zoo\\test.c' ),
    contains_exactly(
      os.path.normpath( r'C:\\foo\\goo\\zoo' ),
      os.path.normpath( r'C:\\foo\\goo' ),
      os.path.normpath( r'C:\\foo' ),
      os.path.normpath( r'C:\\' )
    )
  )


@pytest.mark.parametrize( 'path,expected', [
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
  ] )
def PathLeftSplit_test( path, expected ):
  assert_that( utils.PathLeftSplit( path ), equal_to( expected ) )


@WindowsOnly
@pytest.mark.parametrize( 'path,expected', [
    ( 'foo\\bar',            ( 'foo', 'bar' ) ),
    ( 'foo\\bar\\xyz',       ( 'foo', 'bar\\xyz' ) ),
    ( 'foo\\bar\\xyz\\',     ( 'foo', 'bar\\xyz' ) ),
    ( 'C:\\',                ( 'C:\\', '' ) ),
    ( 'C:\\foo',             ( 'C:\\', 'foo' ) ),
    ( 'C:\\foo\\bar',        ( 'C:\\', 'foo\\bar' ) ),
    ( 'C:\\foo\\bar\\xyz',   ( 'C:\\', 'foo\\bar\\xyz' ) ),
    ( 'C:\\foo\\bar\\xyz\\', ( 'C:\\', 'foo\\bar\\xyz' ) )
  ] )
def PathLeftSplit_Windows_test( path, expected ):
  assert_that( utils.PathLeftSplit( path ), equal_to( expected ) )


def OpenForStdHandle_PrintDoesntThrowException_test():
  try:
    temp = PathToTestFile( 'open-for-std-handle' )
    with utils.OpenForStdHandle( temp ) as f:
      print( 'foo', file = f )
  finally:
    os.remove( temp )


# Tuples of ( ( unicode_line_value, codepoint_offset ), expected_result ).
@pytest.mark.parametrize( 'test,expected', [
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
  ] )
def CodepointOffsetToByteOffset_test( test, expected ):
  assert_that( utils.CodepointOffsetToByteOffset( *test ),
               equal_to( expected ) )


# Tuples of ( ( unicode_line_value, byte_offset ), expected_result ).
@pytest.mark.parametrize( 'test,expected', [
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
  ] )
def ByteOffsetToCodepointOffset_test( test, expected ):
  assert_that( utils.ByteOffsetToCodepointOffset( *test ),
               equal_to( expected ) )


@pytest.mark.parametrize( 'lines,expected', [
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
  ] )
def SplitLines_test( lines, expected ):
  assert_that( utils.SplitLines( lines ), expected )


def FindExecutable_AbsolutePath_test():
  with TemporaryExecutable() as executable:
    assert_that( executable, equal_to( utils.FindExecutable( executable ) ) )


def FindExecutable_RelativePath_test():
  with TemporaryExecutable() as executable:
    dirname, exename = os.path.split( executable )
    relative_executable = os.path.join( '.', exename )
    with CurrentWorkingDirectory( dirname ):
      assert_that( relative_executable,
                   equal_to( utils.FindExecutable( relative_executable ) ) )


@patch.dict( 'os.environ', { 'PATH': tempfile.gettempdir() } )
def FindExecutable_ExecutableNameInPath_test():
  with TemporaryExecutable() as executable:
    dirname, exename = os.path.split( executable )
    assert_that( executable, equal_to( utils.FindExecutable( exename ) ) )


def FindExecutable_ReturnNoneIfFileIsNotExecutable_test():
  with tempfile.NamedTemporaryFile() as non_executable:
    assert_that( None, equal_to( utils.FindExecutable( non_executable.name ) ) )


@WindowsOnly
def FindExecutable_CurrentDirectory_test():
  with TemporaryExecutable() as executable:
    dirname, exename = os.path.split( executable )
    with CurrentWorkingDirectory( dirname ):
      assert_that( executable, equal_to( utils.FindExecutable( exename ) ) )


@WindowsOnly
@patch.dict( 'os.environ', { 'PATHEXT': '.xyz' } )
def FindExecutable_AdditionalPathExt_test():
  with TemporaryExecutable( extension = '.xyz' ) as executable:
    assert_that( executable, equal_to( utils.FindExecutable( executable ) ) )


def FindExecutableWithFallback_Empty_test():
  with TemporaryExecutable() as fallback:
    assert_that( utils.FindExecutableWithFallback( '', fallback ),
                 equal_to( fallback ) )


@patch( 'ycmd.utils.FindExecutable', return_value = None )
def FindExecutableWithFallback_UserProvided_Invalid_test( find_executable ):
  with TemporaryExecutable() as executable:
    with TemporaryExecutable() as fallback:
      assert_that( utils.FindExecutableWithFallback( executable, fallback ),
                   equal_to( None ) )


def FindExecutableWithFallback_UserProvided_test():
  with TemporaryExecutable() as executable:
    with TemporaryExecutable() as fallback:
      assert_that( utils.FindExecutableWithFallback( executable, fallback ),
                   equal_to( executable ) )


@patch( 'ycmd.utils.ProcessIsRunning', return_value = True )
def WaitUntilProcessIsTerminated_TimedOut_test( *args ):
  assert_that(
    calling( utils.WaitUntilProcessIsTerminated ).with_args( None,
                                                             timeout = 0 ),
    raises( RuntimeError,
            'Waited process to terminate for 0 seconds, aborting.' )
  )


def LoadPythonSource_UnicodePath_test():
  filename = PathToTestFile( u'uni¢od€.py' )
  module = utils.LoadPythonSource( 'module_name', filename )
  assert_that( module, instance_of( ModuleType ) )
  assert_that( module.__file__, equal_to( filename ) )
  assert_that( module.__name__, equal_to( 'module_name' ) )
  assert_that( module, has_property( 'SomeMethod' ) )
  assert_that( module.SomeMethod(), equal_to( True ) )


def GetCurrentDirectory_Py3NoCurrentDirectory_test():
  with patch( 'os.getcwd', side_effect = FileNotFoundError ): # noqa
    assert_that( utils.GetCurrentDirectory(),
                 equal_to( tempfile.gettempdir() ) )


def HashableDict_Equality_test():
  dict1 = { 'key': 'value' }
  dict2 = { 'key': 'another_value' }
  assert_that( utils.HashableDict( dict1 ) == utils.HashableDict( dict1 ) )
  assert_that( not utils.HashableDict( dict1 ) != utils.HashableDict( dict1 ) )
  assert_that( not utils.HashableDict( dict1 ) == dict1 )
  assert_that( utils.HashableDict( dict1 ) != dict1 )
  assert_that( not utils.HashableDict( dict1 ) == utils.HashableDict( dict2 ) )
  assert_that( utils.HashableDict( dict1 ) != utils.HashableDict( dict2 ) )


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
  RunImportAndCheckCoreException( {
    'exception_message': "No module named 'ycm_core'",
    'exit_status': 4,
    'logged_message': 'ycm_core library not detected; you need to compile it '
                      'by running the build.py script. See the documentation '
                      'for more details.'
  } )


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
