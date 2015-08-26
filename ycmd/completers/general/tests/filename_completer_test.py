#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2014  Davit Samvelyan <davitsamvelyan@gmail.com>
#
# This file is part of YouCompleteMe.
#
# YouCompleteMe is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# YouCompleteMe is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with YouCompleteMe.  If not, see <http://www.gnu.org/licenses/>.

import os
from nose.tools import eq_
from ycmd.completers.general.filename_completer import FilenameCompleter
from ycmd.request_wrap import RequestWrap
from ycmd import user_options_store

TEST_DIR = os.path.dirname( os.path.abspath( __file__ ) )
DATA_DIR = os.path.join( TEST_DIR, "testdata", "filename_completer" )
PATH_TO_TEST_FILE = os.path.join( DATA_DIR, "test.cpp" )

REQUEST_DATA = {
  'line_num': 1,
  'filepath' : PATH_TO_TEST_FILE,
  'file_data' : { PATH_TO_TEST_FILE : { 'filetypes' : [ 'cpp' ] } }
}


def _CompletionResultsForLine( filename_completer, contents, extra_data=None ):
  request = REQUEST_DATA.copy()
  request[ 'column_num' ] = len( contents ) + 1
  request[ 'file_data' ][ PATH_TO_TEST_FILE ][ 'contents' ] = contents
  if extra_data:
    request.update( extra_data )

  request = RequestWrap( request )
  candidates = filename_completer.ComputeCandidatesInner( request )
  return [ ( c[ 'insertion_text' ], c[ 'extra_menu_info' ] )
          for c in candidates ]


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


  def _CompletionResultsForLine( self, contents ):
    return _CompletionResultsForLine( self._filename_completer, contents )


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
    # $YCM_TEST_DIR/testdata/filename_completer/ and the client filters based
    # on the additional characters.
    os.environ[ 'YCM_TEST_DIR' ] = TEST_DIR
    data = sorted( self._CompletionResultsForLine(
                    'set x = $YCM_TEST_DIR/testdata/filename_completer/te' ) )
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
                            'set x = $YCMTESTDIR/testdata/' ) )

    os.environ.pop( 'YCMTESTDIR' )

    eq_( [ ('filename_completer', '[Dir]') ], data )


  def EnvVar_AtStart_Dir_Partial_test( self ):
    os.environ[ 'ycm_test_dir' ] = TEST_DIR
    data = sorted( self._CompletionResultsForLine(
                            'set x = $ycm_test_dir/testdata/fil' ) )

    os.environ.pop( 'ycm_test_dir' )
    eq_( [ ('filename_completer', '[Dir]') ], data )


  def EnvVar_InMiddle_File_test( self ):
    os.environ[ 'YCM_TEST_filename_completer' ] = 'filename_completer'
    data = sorted( self._CompletionResultsForLine(
      'set x = ' + TEST_DIR + '/testdata/$YCM_TEST_filename_completer/' ) )
    os.environ.pop( 'YCM_TEST_filename_completer' )
    eq_( [
          ( u'foo漢字.txt', '[File]' ),
          ( 'include',    '[Dir]' ),
          ( 'test.cpp',   '[File]' ),
          ( 'test.hpp',   '[File]' ),
        ], data )


  def EnvVar_InMiddle_File_Partial_test( self ):
    os.environ[ 'YCM_TEST_filename_c0mpleter' ] = 'filename_completer'
    data = sorted( self._CompletionResultsForLine(
      'set x = ' + TEST_DIR + '/testdata/$YCM_TEST_filename_c0mpleter/te' ) )
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
                    'set x = ' + TEST_DIR + '/${YCM_TEST_td}ata/' ) )

    os.environ.pop( 'YCM_TEST_td' )
    eq_( [ ('filename_completer', '[Dir]') ], data )


  def EnvVar_InMiddle_Dir_Partial_test( self ):
    os.environ[ 'YCM_TEST_td' ] = 'tdata'
    data = sorted( self._CompletionResultsForLine(
                    'set x = ' + TEST_DIR + '/tes${YCM_TEST_td}/' ) )
    os.environ.pop( 'YCM_TEST_td' )

    eq_( [ ('filename_completer', '[Dir]') ], data )


  def EnvVar_Undefined_test( self ):
    data = sorted( self._CompletionResultsForLine(
                    'set x = ' + TEST_DIR + '/testdata${YCM_TEST_td}/' ) )

    eq_( [ ], data )


  def EnvVar_Empty_Matches_test( self ):
    os.environ[ 'YCM_empty_var' ] = ''
    data = sorted( self._CompletionResultsForLine(
                    'set x = ' + TEST_DIR + '/testdata${YCM_empty_var}/' ) )
    os.environ.pop( 'YCM_empty_var' )

    eq_( [ ('filename_completer', '[Dir]') ], data )


  def EnvVar_Undefined_Garbage_test( self ):
    os.environ[ 'YCM_TEST_td' ] = 'testdata'
    data = sorted( self._CompletionResultsForLine(
                    'set x = ' + TEST_DIR + '/$YCM_TEST_td}/' ) )

    os.environ.pop( 'YCM_TEST_td' )
    eq_( [ ], data )


  def EnvVar_Undefined_Garbage_2_test( self ):
    os.environ[ 'YCM_TEST_td' ] = 'testdata'
    data = sorted( self._CompletionResultsForLine(
                    'set x = ' + TEST_DIR + '/${YCM_TEST_td/' ) )

    os.environ.pop( 'YCM_TEST_td' )
    eq_( [ ], data )


  def EnvVar_Undefined_Garbage_3_test( self ):
    os.environ[ 'YCM_TEST_td' ] = 'testdata'
    data = sorted( self._CompletionResultsForLine(
                    'set x = ' + TEST_DIR + '/$ YCM_TEST_td/' ) )

    os.environ.pop( 'YCM_TEST_td' )
    eq_( [ ], data )


def WorkingDir_Use_File_Path_test():

  assert os.getcwd() != DATA_DIR, ( "Please run this test from a different "
                                    "directory" )

  options = user_options_store.DefaultOptions()
  options.update( {
    'filepath_completion_use_working_dir': 0
  } )
  completer = FilenameCompleter( options )

  data = sorted( _CompletionResultsForLine( completer, 'ls ./include/' ) )
  eq_( [
        ( 'Qt',       '[Dir]' ),
        ( 'QtGui',    '[Dir]' ),
      ], data )


def WorkingDir_Use_ycmd_WD_test():
  # Store the working directory so we can return to it
  wd = os.getcwd()

  test_dir = os.path.join( DATA_DIR, 'include' )
  assert wd != test_dir, "Please run this test from a different directory"

  try:
    options = user_options_store.DefaultOptions()
    options.update( {
      'filepath_completion_use_working_dir': 1
    } )

    completer = FilenameCompleter( options )

    # Change current directory to DATA_DIR/include (path to which we expect
    # results to be relative)
    os.chdir( test_dir )

    # We don't supply working_dir in the request, so the current working
    # directory is used.
    data = sorted( _CompletionResultsForLine( completer, 'ls ./' ) )
    eq_( [
          ( 'Qt',       '[Dir]' ),
          ( 'QtGui',    '[Dir]' ),
        ], data )

  finally:
    os.chdir( wd )


def WorkingDir_Use_Client_WD_test():
  # Store the working directory so we can return to it
  wd = os.getcwd()

  test_dir = os.path.join( DATA_DIR, 'include' )
  assert wd != test_dir, "Please run this test from a different directory"

  try:
    options = user_options_store.DefaultOptions()
    options.update( {
      'filepath_completion_use_working_dir': 1
    } )

    completer = FilenameCompleter( options )

    # We supply working_dir in the request, so we expect results to be relative
    # to the supplied path
    data = sorted( _CompletionResultsForLine( completer, 'ls ./', {
      'working_dir': os.path.join( DATA_DIR, 'include' )
    } ) )
    eq_( [
          ( 'Qt',       '[Dir]' ),
          ( 'QtGui',    '[Dir]' ),
        ], data )

  finally:
    os.chdir( wd )
