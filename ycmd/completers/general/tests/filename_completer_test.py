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

test_dir = os.path.dirname( os.path.abspath( __file__ ) )
data_dir = os.path.join( test_dir, "testdata", "filename_completer" )
file_path = os.path.join( data_dir, "test.cpp" )

fnc = FilenameCompleter( user_options_store.DefaultOptions() )

# We cache include flags for test.cpp file for unit testing.
fnc._flags.flags_for_file[ file_path ] = [
  "-I", os.path.join( data_dir, "include" ),
  "-I", os.path.join( data_dir, "include", "Qt" ),
  "-I", os.path.join( data_dir, "include", "QtGui" ),
]

REQUEST_DATA = {
  'line_num': 1,
  'filepath' : file_path,
  'file_data' : { file_path : { 'filetypes' : [ 'cpp' ] } }
}


def CompletionResultsForLine( contents ):
  request = REQUEST_DATA.copy()
  request[ 'start_column' ] = len( contents ) + 1
  request[ 'file_data' ][ file_path ][ 'contents' ] = contents
  request = RequestWrap( request )
  candidates = fnc.ComputeCandidatesInner( request )
  return [ ( c[ 'insertion_text' ], c[ 'extra_menu_info' ] )
           for c in candidates ]


def QuotedIncludeCompletion_test():
  data = CompletionResultsForLine( '#include "' )
  eq_( [
        ( 'include',  '[Dir]' ),
        ( 'Qt',       '[Dir]' ),
        ( 'QtGui',    '[File&Dir]' ),
        ( 'QDialog',  '[File]' ),
        ( 'QWidget',  '[File]' ),
        ( 'test.cpp', '[File]' ),
        ( 'test.hpp', '[File]' ),
       ], data )

  data = CompletionResultsForLine( '#include "include/' )
  eq_( [
        ( 'Qt',       '[Dir]' ),
        ( 'QtGui',    '[Dir]' ),
       ], data )


def IncludeCompletion_test():
  data = CompletionResultsForLine( '#include <' )
  eq_( [
        ( 'Qt',       '[Dir]' ),
        ( 'QtGui',    '[File&Dir]' ),
        ( 'QDialog',  '[File]' ),
        ( 'QWidget',  '[File]' ),
       ], data )

  data = CompletionResultsForLine( '#include <QtGui/' )
  eq_( [
        ( 'QDialog',  '[File]' ),
        ( 'QWidget',  '[File]' ),
       ], data )


def SystemPathCompletion_test():
  # Order of system path completion entries may differ
  # on different systems
  data = sorted( CompletionResultsForLine( 'const char* c = "./' ) )
  eq_( [
        ( 'include',  '[Dir]' ),
        ( 'test.cpp', '[File]' ),
        ( 'test.hpp', '[File]' ),
       ], data )

  data = sorted( CompletionResultsForLine( 'const char* c = "./include/' ) )
  eq_( [
        ( 'Qt',       '[Dir]' ),
        ( 'QtGui',    '[Dir]' ),
       ], data )
