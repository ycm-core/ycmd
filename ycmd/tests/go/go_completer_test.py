# coding: utf-8
#
# Copyright (C) 2015 Google Inc.
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
from nose.tools import eq_, raises
from ycmd.completers.go.go_completer import GoCompleter, GO_BINARIES, FindBinary
from ycmd.request_wrap import RequestWrap
from ycmd import user_options_store
from ycmd.utils import ReadFile

TEST_DIR = os.path.dirname( os.path.abspath( __file__ ) )
DATA_DIR = os.path.join( TEST_DIR, 'testdata' )
PATH_TO_TEST_FILE = os.path.join( DATA_DIR, 'test2.go' )
# Use test file as dummy binary
DUMMY_BINARY = PATH_TO_TEST_FILE
PATH_TO_POS121_RES = os.path.join( DATA_DIR, 'gocode_output_offset_121.json' )
PATH_TO_POS215_RES = os.path.join( DATA_DIR, 'gocode_output_offset_215.json' )
PATH_TO_POS292_RES = os.path.join( DATA_DIR, 'gocode_output_offset_292.json' )
# Gocode output when a parsing error causes an internal panic.
PATH_TO_PANIC_OUTPUT_RES = os.path.join(
  DATA_DIR, 'gocode_dontpanic_output_offset_10.json' )

REQUEST_DATA = {
  'line_num': 1,
  'filepath' : PATH_TO_TEST_FILE,
  'file_data' : { PATH_TO_TEST_FILE : { 'filetypes' : [ 'go' ] } }
}


class GoCompleter_test( object ):
  def setUp( self ):
    user_options = user_options_store.DefaultOptions()
    user_options[ 'gocode_binary_path' ] = DUMMY_BINARY
    self._completer = GoCompleter( user_options )


  def _BuildRequest( self, line_num, column_num ):
    request = REQUEST_DATA.copy()
    request[ 'column_num' ] = column_num
    request[ 'line_num' ] = line_num
    request[ 'file_data' ][ PATH_TO_TEST_FILE ][ 'contents' ] = ReadFile(
      PATH_TO_TEST_FILE )
    return RequestWrap( request )


  def FindGoCodeBinary_test( self ):
    user_options = user_options_store.DefaultOptions()

    eq_( GO_BINARIES.get( "gocode" ), FindBinary( "gocode", user_options ) )

    user_options[ 'gocode_binary_path' ] = DUMMY_BINARY
    eq_( DUMMY_BINARY, FindBinary( "gocode", user_options ) )

    user_options[ 'gocode_binary_path' ] = DATA_DIR
    eq_( None, FindBinary( "gocode", user_options ) )


  # Test line-col to offset in the file before any unicode occurrences.
  def ComputeCandidatesInnerOffsetBeforeUnicode_test( self ):
    mock = MockPopen( returncode = 0,
                      stdout = ReadFile( PATH_TO_POS121_RES ),
                      stderr = '' )
    self._completer._popener = mock
    # Col 8 corresponds to cursor at log.Pr^int("Line 7 ...
    self._completer.ComputeCandidatesInner( self._BuildRequest( 7, 8 ) )
    eq_( mock.cmd, [
      DUMMY_BINARY, '-f=json', 'autocomplete', PATH_TO_TEST_FILE, '119' ] )


  # Test line-col to offset in the file after a unicode occurrences.
  def ComputeCandidatesInnerAfterUnicode_test( self ):
    mock = MockPopen( returncode = 0,
                      stdout = ReadFile( PATH_TO_POS215_RES ),
                      stderr = '' )
    self._completer._popener = mock
    # Col 9 corresponds to cursor at log.Pri^nt("Line 7 ...
    self._completer.ComputeCandidatesInner(self._BuildRequest(9, 9))
    eq_( mock.cmd, [
      DUMMY_BINARY, '-f=json', 'autocomplete', PATH_TO_TEST_FILE, '212' ] )


  # Test end to end parsing of completed results.
  def ComputeCandidatesInner_test( self ):
    mock = MockPopen( returncode = 0,
                      stdout = ReadFile( PATH_TO_POS292_RES ),
                      stderr = '' )
    self._completer._popener = mock
    # Col 40 corresponds to cursor at ..., log.Prefi^x ...
    result = self._completer.ComputeCandidatesInner(
      self._BuildRequest( 10, 40 ) )
    eq_( mock.cmd, [
      DUMMY_BINARY, '-f=json', 'autocomplete', PATH_TO_TEST_FILE, '287' ] )
    eq_( result, [ {
        'menu_text': u'Prefix',
        'insertion_text': u'Prefix',
        'extra_menu_info': u'func() string',
        'detailed_info': u'Prefix func() string func',
        'kind': u'func'
    } ] )


  # Test gocode failure.
  @raises( RuntimeError )
  def ComputeCandidatesInnerGoCodeFailure_test( self ):
    mock = MockPopen( returncode = 1, stdout = '', stderr = '' )
    self._completer._popener = mock
    self._completer.ComputeCandidatesInner( self._BuildRequest( 1, 1 ) )

  # Test JSON parsing failure.
  @raises( RuntimeError )
  def ComputeCandidatesInnerParseFailure_test( self ):
    mock = MockPopen( returncode = 0,
                      stdout = "{this isn't parseable",
                      stderr = '' )
    self._completer._popener = mock
    self._completer.ComputeCandidatesInner( self._BuildRequest( 1, 1 ) )

  # Test empty results error (different than no results).
  @raises( RuntimeError )
  def ComputeCandidatesInnerNoResultsFailure_test( self ):
    mock = MockPopen( returncode = 0, stdout = '[]', stderr = '' )
    self._completer._popener = mock
    self._completer.ComputeCandidatesInner( self._BuildRequest( 1, 1 ) )

  # Test empty results error (different than no results).
  @raises( RuntimeError )
  def ComputeCandidatesGoCodePanic_test( self ):
    mock = MockPopen( returncode = 0,
                      stdout = ReadFile( PATH_TO_PANIC_OUTPUT_RES ),
                      stderr = '' )
    self._completer._popener = mock
    self._completer.ComputeCandidatesInner( self._BuildRequest( 1, 1 ) )


class MockSubprocess( object ):
  def __init__( self, returncode, stdout, stderr ):
    self.returncode = returncode
    self.stdout = stdout
    self.stderr = stderr


  def communicate( self, stdin ):
    self.stdin = stdin
    return ( self.stdout, self.stderr )



class MockPopen( object ):
  def __init__( self, returncode = None, stdout = None, stderr = None ):
    self._returncode = returncode
    self._stdout = stdout
    self._stderr = stderr
    # cmd will be populated when a subprocess is created.
    self.cmd = None


  def __call__( self, cmd, stdout = None, stderr = None, stdin = None ):
    self.cmd = cmd
    return MockSubprocess( self._returncode, self._stdout, self._stderr )
