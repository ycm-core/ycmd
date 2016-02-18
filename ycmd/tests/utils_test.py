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
from future.utils import PY2, native

from hamcrest import raises, assert_that, calling
from mock import patch, call
from nose.tools import eq_, ok_
from ycmd import utils
from ycmd.tests.test_utils import PathToTestFile
from shutil import rmtree
import os
import os.path
import subprocess

# NOTE: isinstance() vs type() is carefully used in this test file. Before
# changing things here, read the comments in utils.ToBytes.


if PY2:
  def ToBytes_Py2Bytes_test():
    value = utils.ToBytes( bytes( 'abc' ) )
    eq_( value, bytes( 'abc' ) )
    eq_( type( value ), bytes )


  def ToBytes_Py2Str_test():
    value = utils.ToBytes( 'abc' )
    eq_( value, bytes( 'abc' ) )
    eq_( type( value ), bytes )


  def ToBytes_Py2FutureStr_test():
    value = utils.ToBytes( str( 'abc' ) )
    eq_( value, bytes( 'abc' ) )
    eq_( type( value ), bytes )


  def ToBytes_Py2Unicode_test():
    value = utils.ToBytes( u'abc' )
    eq_( value, bytes( 'abc' ) )
    eq_( type( value ), bytes )


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


if PY2:
  def ToUnicode_Py2Bytes_test():
    value = utils.ToUnicode( bytes( 'abc' ) )
    eq_( value, u'abc' )
    ok_( isinstance( value, str ) )


  def ToUnicode_Py2Str_test():
    value = utils.ToUnicode( 'abc' )
    eq_( value, u'abc' )
    ok_( isinstance( value, str ) )


  def ToUnicode_Py2FutureStr_test():
    value = utils.ToUnicode( str( 'abc' ) )
    eq_( value, u'abc' )
    ok_( isinstance( value, str ) )


  def ToUnicode_Py2Unicode_test():
    value = utils.ToUnicode( u'abc' )
    eq_( value, u'abc' )
    ok_( isinstance( value, str ) )


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


if PY2:
  def ToCppStringCompatible_Py2Str_test():
    value = utils.ToCppStringCompatible( 'abc' )
    eq_( value, 'abc' )
    eq_( type( value ), type( '' ) )


  def ToCppStringCompatible_Py2Unicode_test():
    value = utils.ToCppStringCompatible( u'abc' )
    eq_( value, 'abc' )
    eq_( type( value ), type( '' ) )


  def ToCppStringCompatible_Py2Int_test():
    value = utils.ToCppStringCompatible( 123 )
    eq_( value, '123' )
    eq_( type( value ), type( '' ) )


def ToCppStringCompatible_Bytes_test():
  value = utils.ToCppStringCompatible( bytes( b'abc' ) )
  eq_( value, bytes( b'abc' ) )
  ok_( isinstance( value, bytes ) )


def ToCppStringCompatible_Unicode_test():
  value = utils.ToCppStringCompatible( u'abc' )
  eq_( value, bytes( b'abc' ) )
  ok_( isinstance( value, bytes ) )


def ToCppStringCompatible_Str_test():
  value = utils.ToCppStringCompatible( 'abc' )
  eq_( value, bytes( b'abc' ) )
  ok_( isinstance( value, bytes ) )


def ToCppStringCompatible_Int_test():
  value = utils.ToCppStringCompatible( 123 )
  eq_( value, bytes( b'123' ) )
  ok_( isinstance( value, bytes ) )


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


@patch( 'os.environ', { 'TRAVIS': 1 } )
def OnTravis_IsOnTravis_test():
  ok_( utils.OnTravis() )


@patch( 'os.environ', {} )
def OnTravis_IsNotOnTravis_test():
  ok_( not utils.OnTravis() )


@patch( 'ycmd.utils.OnWindows', return_value = False )
@patch( 'subprocess.Popen' )
def SafePopen_RemovesStdinWindows_test( *args ):
  utils.SafePopen( [ 'foo' ], stdin_windows = subprocess.PIPE )
  eq_( subprocess.Popen.call_args, call( [ 'foo' ] ) )


@patch( 'ycmd.utils.OnWindows', return_value = True )
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


@patch( 'ycmd.utils.OnWindows', return_value = False )
def ConvertArgsToShortPath_PassthroughOnUnix_test( *args ):
  eq_( 'foo', utils.ConvertArgsToShortPath( 'foo' ) )
  eq_( [ 'foo' ], utils.ConvertArgsToShortPath( [ 'foo' ] ) )


@patch( 'ycmd.utils.OnWindows', return_value = False )
def SetEnviron_UnicodeNotOnWindows_test( *args ):
  env = {}
  utils.SetEnviron( env, u'key', u'value' )
  eq_( env, { u'key': u'value' } )


if PY2:
  @patch( 'ycmd.utils.OnWindows', return_value = True )
  def SetEnviron_UnicodeOnWindows_test( *args ):
    env = {}
    utils.SetEnviron( env, u'key', u'value' )
    eq_( env, { native( bytes( b'key' ) ): native( bytes( b'value' ) ) } )


def PathToNearestThirdPartyFolder_Success_test():
  ok_( utils.PathToNearestThirdPartyFolder( os.path.abspath( __file__ ) ) )


def PathToNearestThirdPartyFolder_Failure_test():
  ok_( not utils.PathToNearestThirdPartyFolder( os.path.expanduser( '~' ) ) )


def AddNearestThirdPartyFoldersToSysPath_Failure_test():
  assert_that(
    calling( utils.AddNearestThirdPartyFoldersToSysPath ).with_args(
      os.path.expanduser( '~' ) ),
    raises( RuntimeError, '.*third_party folder.*' ) )
