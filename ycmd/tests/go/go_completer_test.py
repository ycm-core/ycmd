# coding: utf-8
#
# Copyright (C) 2015 Google Inc.
#               2017 ycmd contributors
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
# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa

from hamcrest import assert_that, calling, raises
from mock import patch
from nose.tools import eq_
import functools
import os

from ycmd.completers.go.go_completer import ( _ComputeOffset, GoCompleter,
                                              GO_BINARIES, FindBinary )
from ycmd.request_wrap import RequestWrap
from ycmd import user_options_store
from ycmd.utils import ReadFile, ToBytes

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


def BuildRequest( line_num, column_num ):
  request = REQUEST_DATA.copy()
  request[ 'line_num' ] = line_num
  request[ 'column_num' ] = column_num
  request[ 'file_data' ][ PATH_TO_TEST_FILE ][ 'contents' ] = ReadFile(
    PATH_TO_TEST_FILE )
  return RequestWrap( request )


def SetUpGoCompleter( test ):
  @functools.wraps( test )
  def Wrapper( *args, **kwargs ):
    user_options = user_options_store.DefaultOptions()
    user_options[ 'gocode_binary_path' ] = DUMMY_BINARY
    with patch( 'ycmd.utils.SafePopen' ):
      completer = GoCompleter( user_options )
      return test( completer, *args, **kwargs )
  return Wrapper


def FindGoCodeBinary_test():
  user_options = user_options_store.DefaultOptions()

  eq_( GO_BINARIES.get( "gocode" ), FindBinary( "gocode", user_options ) )

  user_options[ 'gocode_binary_path' ] = DUMMY_BINARY
  eq_( DUMMY_BINARY, FindBinary( "gocode", user_options ) )

  user_options[ 'gocode_binary_path' ] = DATA_DIR
  eq_( None, FindBinary( "gocode", user_options ) )


def ComputeOffset_OutOfBoundsOffset_test():
  assert_that(
    calling( _ComputeOffset ).with_args( 'test', 2, 1 ),
    raises( RuntimeError, 'Go completer could not compute byte offset '
                          'corresponding to line 2 and column 1.' ) )


# Test line-col to offset in the file before any unicode occurrences.
@SetUpGoCompleter
@patch( 'ycmd.completers.go.go_completer.GoCompleter._ExecuteCommand',
        return_value = ReadFile( PATH_TO_POS215_RES ) )
def ComputeCandidatesInner_BeforeUnicode_test( completer, execute_command ):
  # Col 8 corresponds to cursor at log.Pr^int("Line 7 ...
  completer.ComputeCandidatesInner( BuildRequest( 7, 8 ) )
  execute_command.assert_called_once_with(
    [ DUMMY_BINARY, '-sock', 'tcp', '-addr', completer._gocode_host,
      '-f=json', 'autocomplete', PATH_TO_TEST_FILE, '119' ],
    contents = ToBytes( ReadFile( PATH_TO_TEST_FILE ) ) )


# Test line-col to offset in the file after a unicode occurrences.
@SetUpGoCompleter
@patch( 'ycmd.completers.go.go_completer.GoCompleter._ExecuteCommand',
        return_value = ReadFile( PATH_TO_POS215_RES ) )
def ComputeCandidatesInner_AfterUnicode_test( completer, execute_command ):
  # Col 9 corresponds to cursor at log.Pri^nt("Line 7 ...
  completer.ComputeCandidatesInner( BuildRequest( 9, 9 ) )
  execute_command.assert_called_once_with(
    [ DUMMY_BINARY, '-sock', 'tcp', '-addr', completer._gocode_host,
      '-f=json', 'autocomplete', PATH_TO_TEST_FILE, '212' ],
    contents = ToBytes( ReadFile( PATH_TO_TEST_FILE ) ) )


# Test end to end parsing of completed results.
@SetUpGoCompleter
@patch( 'ycmd.completers.go.go_completer.GoCompleter._ExecuteCommand',
        return_value = ReadFile( PATH_TO_POS292_RES ) )
def ComputeCandidatesInner_test( completer, execute_command ):
  # Col 40 corresponds to cursor at ..., log.Prefi^x ...
  candidates = completer.ComputeCandidatesInner( BuildRequest( 10, 40 ) )
  result = completer.DetailCandidates( {}, candidates )
  execute_command.assert_called_once_with(
    [ DUMMY_BINARY, '-sock', 'tcp', '-addr', completer._gocode_host,
      '-f=json', 'autocomplete', PATH_TO_TEST_FILE, '287' ],
    contents = ToBytes( ReadFile( PATH_TO_TEST_FILE ) ) )
  eq_( result, [ {
      'menu_text': u'Prefix',
      'insertion_text': u'Prefix',
      'extra_menu_info': u'func() string',
      'detailed_info': u'Prefix func() string func',
      'kind': u'func'
  } ] )


# Test Gocode failure.
@SetUpGoCompleter
@patch( 'ycmd.completers.go.go_completer.GoCompleter._ExecuteCommand',
        return_value = '' )
def ComputeCandidatesInner_GoCodeFailure_test( completer, *args ):
  assert_that(
    calling( completer.ComputeCandidatesInner ).with_args(
      BuildRequest( 1, 1 ) ),
    raises( RuntimeError, 'Gocode returned invalid JSON response.' ) )


# Test JSON parsing failure.
@SetUpGoCompleter
@patch( 'ycmd.completers.go.go_completer.GoCompleter._ExecuteCommand',
        return_value = "{this isn't parseable" )
def ComputeCandidatesInner_ParseFailure_test( completer, *args ):
  assert_that(
    calling( completer.ComputeCandidatesInner ).with_args(
      BuildRequest( 1, 1 ) ),
    raises( RuntimeError, 'Gocode returned invalid JSON response.' ) )


# Test empty results error.
@SetUpGoCompleter
@patch( 'ycmd.completers.go.go_completer.GoCompleter._ExecuteCommand',
        return_value = '[]' )
def ComputeCandidatesInner_NoResultsFailure_EmptyList_test( completer, *args ):
  assert_that(
    calling( completer.ComputeCandidatesInner ).with_args(
      BuildRequest( 1, 1 ) ),
    raises( RuntimeError, 'No completions found.' ) )


@SetUpGoCompleter
@patch( 'ycmd.completers.go.go_completer.GoCompleter._ExecuteCommand',
        return_value = 'null\n' )
def ComputeCandidatesInner_NoResultsFailure_Null_test( completer, *args ):
  assert_that(
    calling( completer.ComputeCandidatesInner ).with_args(
      BuildRequest( 1, 1 ) ),
    raises( RuntimeError, 'No completions found.' ) )


# Test panic error.
@SetUpGoCompleter
@patch( 'ycmd.completers.go.go_completer.GoCompleter._ExecuteCommand',
        return_value = ReadFile( PATH_TO_PANIC_OUTPUT_RES ) )
def ComputeCandidatesInner_GoCodePanic_test( completer, *args ):
  assert_that(
    calling( completer.ComputeCandidatesInner ).with_args(
      BuildRequest( 1, 1 ) ),
    raises( RuntimeError,
            'Gocode panicked trying to find completions, '
            'you likely have a syntax error.' ) )
