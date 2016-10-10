# coding: utf-8
#
# Copyright (C) 2014 Davit Samvelyan <davitsamvelyan@gmail.com>
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

import os
from hamcrest import assert_that, contains_inanyorder
from nose.tools import eq_, ok_
from ycmd.completers.general.filename_completer import FilenameCompleter
from ycmd.request_wrap import RequestWrap
from ycmd import user_options_store
from ycmd.tests.test_utils import CurrentWorkingDirectory, UserOption
from ycmd.utils import GetCurrentDirectory, ToBytes

TEST_DIR = os.path.dirname( os.path.abspath( __file__ ) )
DATA_DIR = os.path.join( TEST_DIR,
                         'testdata',
                         'filename_completer',
                         'inner_dir' )
PATH_TO_TEST_FILE = os.path.join( DATA_DIR, "test.cpp" )

REQUEST_DATA = {
  'line_num': 1,
  'filepath' : PATH_TO_TEST_FILE,
  'file_data' : { PATH_TO_TEST_FILE : { 'filetypes' : [ 'cpp' ] } }
}


def _CompletionResultsForLine( filename_completer,
                               contents,
                               extra_data = None,
                               column_num = None ):
  request = REQUEST_DATA.copy()

  # Strictly, column numbers are *byte* offsets, not character offsets. If
  # the contents of the file contain unicode characters, then we should manually
  # supply the correct byte offset.
  column_num = len( contents ) + 1 if not column_num else column_num

  request[ 'column_num' ] = column_num
  request[ 'file_data' ][ PATH_TO_TEST_FILE ][ 'contents' ] = contents
  if extra_data:
    request.update( extra_data )

  request = RequestWrap( request )
  candidates = filename_completer.ComputeCandidatesInner( request )
  return [ ( c[ 'insertion_text' ], c[ 'extra_menu_info' ] )
          for c in candidates ]


def _ShouldUseNowForLine( filename_completer,
                          contents,
                          extra_data = None,
                          column_num = None ):
  request = REQUEST_DATA.copy()

  # Strictly, column numbers are *byte* offsets, not character offsets. If
  # the contents of the file contain unicode characters, then we should manually
  # supply the correct byte offset.
  column_num = len( contents ) + 1 if not column_num else column_num

  request[ 'column_num' ] = column_num
  request[ 'file_data' ][ PATH_TO_TEST_FILE ][ 'contents' ] = contents
  if extra_data:
    request.update( extra_data )

  request = RequestWrap( request )
  return filename_completer.ShouldUseNow( request )


class FilenameCompleter_test( object ):
  def setUp( self ):
    self._filename_completer = FilenameCompleter(
      user_options_store.DefaultOptions() )

    # We cache include flags for test.cpp file for unit testing.
    self._filename_completer._flags.flags_for_file[ PATH_TO_TEST_FILE ] = [
      "-I", os.path.join( DATA_DIR, "include" ),
      "-I", os.path.join( DATA_DIR, "include", "Qt" ),
      "-I", os.path.join( DATA_DIR, "include", "QtGui" ),
    ]


  def _CompletionResultsForLine( self, contents, column_num=None ):
    return _CompletionResultsForLine( self._filename_completer,
                                      contents,
                                      column_num = column_num )


  def _ShouldUseNowForLine( self, contents, column_num=None ):
    return _ShouldUseNowForLine( self._filename_completer,
                                 contents,
                                 column_num = column_num )


  def QuotedIncludeCompletion_test( self ):
    data = self._CompletionResultsForLine( '#include "' )
    eq_( [
          ( u'foo漢字.txt', '[File]' ),
          ( 'include',    '[Dir]' ),
          ( 'Qt',         '[Dir]' ),
          ( 'QtGui',      '[File&Dir]' ),
          ( 'QDialog',    '[File]' ),
          ( 'QWidget',    '[File]' ),
          ( 'test.cpp',   '[File]' ),
          ( 'test.hpp',   '[File]' ),
        ], data )

    data = self._CompletionResultsForLine( '#include "include/' )
    eq_( [
          ( 'Qt',       '[Dir]' ),
          ( 'QtGui',    '[Dir]' ),
        ], data )


  def IncludeCompletion_test( self ):
    data = self._CompletionResultsForLine( '#include <' )
    eq_( [
          ( 'Qt',       '[Dir]' ),
          ( 'QtGui',    '[File&Dir]' ),
          ( 'QDialog',  '[File]' ),
          ( 'QWidget',  '[File]' ),
        ], data )

    data = self._CompletionResultsForLine( '#include <QtGui/' )
    eq_( [
          ( 'QDialog',  '[File]' ),
          ( 'QWidget',  '[File]' ),
        ], data )


  def SystemPathCompletion_test( self ):
    # Order of system path completion entries may differ
    # on different systems
    data = sorted( self._CompletionResultsForLine( 'const char* c = "./' ) )
    eq_( [
          ( u'foo漢字.txt', '[File]' ),
          ( 'include',    '[Dir]' ),
          ( 'test.cpp',   '[File]' ),
          ( 'test.hpp',   '[File]' ),
        ], data )

    data = sorted(
      self._CompletionResultsForLine( 'const char* c = "./include/' ) )
    eq_( [
          ( 'Qt',       '[Dir]' ),
          ( 'QtGui',    '[Dir]' ),
        ], data )


  def EnvVar_AtStart_File_test( self ):
    os.environ[ 'YCM_TEST_DATA_DIR' ] = DATA_DIR
    data = sorted( self._CompletionResultsForLine(
                            'set x = $YCM_TEST_DATA_DIR/include/QtGui/' ) )

    os.environ.pop( 'YCM_TEST_DATA_DIR' )
    eq_( [ ( 'QDialog', '[File]' ), ( 'QWidget', '[File]' ) ], data )


  def EnvVar_AtStart_File_Partial_test( self ):
    # The reason all entries in the directory are returned is that the
    # RequestWrapper tells the completer to effectively return results for
    # $YCM_TEST_DIR/testdata/filename_completer/inner_dir/ and the client
    # filters based on the additional characters.
    os.environ[ 'YCM_TEST_DIR' ] = TEST_DIR
    data = sorted( self._CompletionResultsForLine(
                    'set x = $YCM_TEST_DIR/testdata/filename_completer/'
                      'inner_dir/te' ) )
    os.environ.pop( 'YCM_TEST_DIR' )

    eq_( [
          ( u'foo漢字.txt', '[File]' ),
          ( 'include',    '[Dir]' ),
          ( 'test.cpp',   '[File]' ),
          ( 'test.hpp',   '[File]' ),
        ], data )


  def EnvVar_AtStart_Dir_test( self ):
    os.environ[ 'YCMTESTDIR' ] = TEST_DIR

    data = sorted( self._CompletionResultsForLine(
                      'set x = $YCMTESTDIR/testdata/filename_completer/' ) )

    os.environ.pop( 'YCMTESTDIR' )

    eq_( [ ( 'inner_dir', '[Dir]' ), ( '∂†∫', '[Dir]' ) ], data )


  def EnvVar_AtStart_Dir_Partial_test( self ):
    os.environ[ 'ycm_test_dir' ] = TEST_DIR
    data = sorted( self._CompletionResultsForLine(
                    'set x = $ycm_test_dir/testdata/filename_completer/inn' ) )

    os.environ.pop( 'ycm_test_dir' )
    eq_( [ ( 'inner_dir', '[Dir]' ), ( '∂†∫', '[Dir]' ) ], data )


  def EnvVar_InMiddle_File_test( self ):
    os.environ[ 'YCM_TEST_filename_completer' ] = 'inner_dir'
    data = sorted( self._CompletionResultsForLine(
      'set x = '
      + TEST_DIR
      + '/testdata/filename_completer/$YCM_TEST_filename_completer/' ) )
    os.environ.pop( 'YCM_TEST_filename_completer' )
    eq_( [
          ( u'foo漢字.txt', '[File]' ),
          ( 'include',    '[Dir]' ),
          ( 'test.cpp',   '[File]' ),
          ( 'test.hpp',   '[File]' ),
        ], data )


  def EnvVar_InMiddle_File_Partial_test( self ):
    os.environ[ 'YCM_TEST_filename_c0mpleter' ] = 'inner_dir'
    data = sorted( self._CompletionResultsForLine(
      'set x = '
      + TEST_DIR
      + '/testdata/filename_completer/$YCM_TEST_filename_c0mpleter/te' ) )
    os.environ.pop( 'YCM_TEST_filename_c0mpleter' )
    eq_( [
          ( u'foo漢字.txt', '[File]' ),
          ( 'include',    '[Dir]' ),
          ( 'test.cpp',   '[File]' ),
          ( 'test.hpp',   '[File]' ),
        ], data )


  def EnvVar_InMiddle_Dir_test( self ):
    os.environ[ 'YCM_TEST_td' ] = 'testd'
    data = sorted( self._CompletionResultsForLine(
          'set x = ' + TEST_DIR + '/${YCM_TEST_td}ata/filename_completer/' ) )

    os.environ.pop( 'YCM_TEST_td' )
    eq_( [ ( 'inner_dir', '[Dir]' ), ( '∂†∫', '[Dir]' ) ], data )


  def EnvVar_InMiddle_Dir_Partial_test( self ):
    os.environ[ 'YCM_TEST_td' ] = 'tdata'
    data = sorted( self._CompletionResultsForLine(
          'set x = ' + TEST_DIR + '/tes${YCM_TEST_td}/filename_completer/' ) )
    os.environ.pop( 'YCM_TEST_td' )

    eq_( [ ( 'inner_dir', '[Dir]' ), ( '∂†∫', '[Dir]' ) ], data )


  def EnvVar_Undefined_test( self ):
    data = sorted( self._CompletionResultsForLine(
      'set x = ' + TEST_DIR + '/testdata/filename_completer${YCM_TEST_td}/' ) )

    eq_( [ ], data )


  def EnvVar_Empty_Matches_test( self ):
    os.environ[ 'YCM_empty_var' ] = ''
    data = sorted( self._CompletionResultsForLine(
      'set x = '
      + TEST_DIR
      + '/testdata/filename_completer${YCM_empty_var}/' ) )
    os.environ.pop( 'YCM_empty_var' )

    eq_( [ ( 'inner_dir', '[Dir]' ), ( '∂†∫', '[Dir]' ) ], data )


  def EnvVar_Undefined_Garbage_test( self ):
    os.environ[ 'YCM_TEST_td' ] = 'testdata/filename_completer'
    data = sorted( self._CompletionResultsForLine(
                    'set x = ' + TEST_DIR + '/$YCM_TEST_td}/' ) )

    os.environ.pop( 'YCM_TEST_td' )
    eq_( [ ], data )


  def EnvVar_Undefined_Garbage_2_test( self ):
    os.environ[ 'YCM_TEST_td' ] = 'testdata/filename_completer'
    data = sorted( self._CompletionResultsForLine(
                    'set x = ' + TEST_DIR + '/${YCM_TEST_td/' ) )

    os.environ.pop( 'YCM_TEST_td' )
    eq_( [ ], data )


  def EnvVar_Undefined_Garbage_3_test( self ):
    os.environ[ 'YCM_TEST_td' ] = 'testdata/filename_completer'
    data = sorted( self._CompletionResultsForLine(
                    'set x = ' + TEST_DIR + '/$ YCM_TEST_td/' ) )

    os.environ.pop( 'YCM_TEST_td' )
    eq_( [ ], data )


  def Unicode_In_Line_Works_test( self ):
    eq_( True, self._ShouldUseNowForLine(
      contents = "var x = /†/testing",
      # The † character is 3 bytes in UTF-8
      column_num = 15 ) )
    eq_( [ ], self._CompletionResultsForLine(
      contents = "var x = /†/testing",
      # The † character is 3 bytes in UTF-8
      column_num = 15 ) )


  def Unicode_Paths_test( self ):
    contents = "test " + DATA_DIR + "/../∂"
    # The column number is the first byte of the ∂ character (1-based )
    column_num = ( len( ToBytes( "test" ) ) +
                   len( ToBytes( DATA_DIR ) ) +
                   len( ToBytes( '/../' ) ) +
                   1 + # 0-based offset of ∂
                   1 ) # Make it 1-based
    eq_( True, self._ShouldUseNowForLine( contents, column_num = column_num ) )
    assert_that( self._CompletionResultsForLine( contents,
                                                 column_num = column_num ),
                 contains_inanyorder( ( 'inner_dir', '[Dir]' ),
                                      ( '∂†∫', '[Dir]' )  ) )


def WorkingDir_UseFilePath_test():
  ok_( GetCurrentDirectory() != DATA_DIR, ( 'Please run this test from a '
                                            'different directory' ) )

  with UserOption( 'filepath_completion_use_working_dir', 0 ) as options:
    completer = FilenameCompleter( options )

    data = sorted( _CompletionResultsForLine( completer, 'ls ./include/' ) )
    eq_( [
      ( 'Qt',    '[Dir]' ),
      ( 'QtGui', '[Dir]' )
    ], data )


def WorkingDir_UseServerWorkingDirectory_test():
  test_dir = os.path.join( DATA_DIR, 'include' )
  with CurrentWorkingDirectory( test_dir ) as old_current_dir:
    ok_( old_current_dir != test_dir, ( 'Please run this test from a different '
                                        'directory' ) )

    with UserOption( 'filepath_completion_use_working_dir', 1 ) as options:
      completer = FilenameCompleter( options )

      # We don't supply working_dir in the request, so the current working
      # directory is used.
      data = sorted( _CompletionResultsForLine( completer, 'ls ./' ) )
      eq_( [
        ( 'Qt',    '[Dir]' ),
        ( 'QtGui', '[Dir]' )
      ], data )


def WorkingDir_UseServerWorkingDirectory_Unicode_test():
  test_dir = os.path.join( TEST_DIR, 'testdata', 'filename_completer', '∂†∫' )
  with CurrentWorkingDirectory( test_dir ) as old_current_dir:
    ok_( old_current_dir != test_dir, ( 'Please run this test from a different '
                                        'directory' ) )

    with UserOption( 'filepath_completion_use_working_dir', 1 ) as options:
      completer = FilenameCompleter( options )

      # We don't supply working_dir in the request, so the current working
      # directory is used.
      data = sorted( _CompletionResultsForLine( completer, 'ls ./' ) )
      eq_( [
        ( '†es†.txt', '[File]' )
      ], data )


def WorkingDir_UseClientWorkingDirectory_test():
  test_dir = os.path.join( DATA_DIR, 'include' )
  ok_( GetCurrentDirectory() != test_dir, ( 'Please run this test from a '
                                            'different directory' ) )

  with UserOption( 'filepath_completion_use_working_dir', 1 ) as options:
    completer = FilenameCompleter( options )

    # We supply working_dir in the request, so we expect results to be
    # relative to the supplied path.
    data = sorted( _CompletionResultsForLine( completer, 'ls ./', {
      'working_dir': test_dir
    } ) )
    eq_( [
      ( 'Qt',    '[Dir]' ),
      ( 'QtGui', '[Dir]' )
    ], data )
