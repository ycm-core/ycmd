#!/usr/bin/env python
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
    request = REQUEST_DATA.copy()
    request[ 'column_num' ] = len( contents ) + 1
    request[ 'file_data' ][ PATH_TO_TEST_FILE ][ 'contents' ] = contents
    request = RequestWrap( request )
    candidates = self._filename_completer.ComputeCandidatesInner( request )
    return [ ( c[ 'insertion_text' ], c[ 'extra_menu_info' ] )
            for c in candidates ]


  def QuotedIncludeCompletion_test( self ):
    data = self._CompletionResultsForLine( '#include "' )
    eq_( [
          ( 'include',  '[Dir]' ),
          ( 'Qt',       '[Dir]' ),
          ( 'QtGui',    '[File&Dir]' ),
          ( 'QDialog',  '[File]' ),
          ( 'QWidget',  '[File]' ),
          ( 'test.cpp', '[File]' ),
          ( 'test.hpp', '[File]' ),
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
          ( 'include',  '[Dir]' ),
          ( 'test.cpp', '[File]' ),
          ( 'test.hpp', '[File]' ),
        ], data )

    data = sorted(
      self._CompletionResultsForLine( 'const char* c = "./include/' ) )
    eq_( [
          ( 'Qt',       '[Dir]' ),
          ( 'QtGui',    '[Dir]' ),
        ], data )
