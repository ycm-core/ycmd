# coding: utf-8
#
# Copyright (C) 2017 ycmd contributors
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

from ycmd.completers.language_server import language_server_protocol as lsp
from hamcrest import assert_that, equal_to, calling, is_not, raises
from ycmd.tests.test_utils import UnixOnly, WindowsOnly


def ServerFileStateStore_RetrieveDelete_test():
  store = lsp.ServerFileStateStore()

  # New state object created
  file1_state = store[ 'file1' ]
  assert_that( file1_state.version, equal_to( 0 ) )
  assert_that( file1_state.checksum, equal_to( None ) )
  assert_that( file1_state.state, equal_to( lsp.ServerFileState.CLOSED ) )

  # Retrieve again unchanged
  file1_state = store[ 'file1' ]
  assert_that( file1_state.version, equal_to( 0 ) )
  assert_that( file1_state.checksum, equal_to( None ) )
  assert_that( file1_state.state, equal_to( lsp.ServerFileState.CLOSED ) )

  # Retrieve/create another one (we don't actually open this one)
  file2_state = store[ 'file2' ]
  assert_that( file2_state.version, equal_to( 0 ) )
  assert_that( file2_state.checksum, equal_to( None ) )
  assert_that( file2_state.state, equal_to( lsp.ServerFileState.CLOSED ) )

  # Checking for refresh on closed file is no-op
  assert_that( file1_state.GetSavedFileAction( 'blah' ),
               equal_to( lsp.ServerFileState.NO_ACTION ) )
  assert_that( file1_state.version, equal_to( 0 ) )
  assert_that( file1_state.checksum, equal_to( None ) )
  assert_that( file1_state.state, equal_to( lsp.ServerFileState.CLOSED ) )


  # Checking the next action progresses the state
  assert_that( file1_state.GetDirtyFileAction( 'test contents' ),
               equal_to( lsp.ServerFileState.OPEN_FILE ) )
  assert_that( file1_state.version, equal_to( 1 ) )
  assert_that( file1_state.checksum, is_not( equal_to( None ) ) )
  assert_that( file1_state.state, equal_to( lsp.ServerFileState.OPEN ) )

  # Replacing the same file is no-op
  assert_that( file1_state.GetDirtyFileAction( 'test contents' ),
               equal_to( lsp.ServerFileState.NO_ACTION ) )
  assert_that( file1_state.version, equal_to( 1 ) )
  assert_that( file1_state.checksum, is_not( equal_to( None ) ) )
  assert_that( file1_state.state, equal_to( lsp.ServerFileState.OPEN ) )

  # Changing the file creates a new version
  assert_that( file1_state.GetDirtyFileAction( 'test contents changed' ),
               equal_to( lsp.ServerFileState.CHANGE_FILE ) )
  assert_that( file1_state.version, equal_to( 2 ) )
  assert_that( file1_state.checksum, is_not( equal_to( None ) ) )
  assert_that( file1_state.state, equal_to( lsp.ServerFileState.OPEN ) )

  # Replacing the same file is no-op
  assert_that( file1_state.GetDirtyFileAction( 'test contents changed' ),
               equal_to( lsp.ServerFileState.NO_ACTION ) )
  assert_that( file1_state.version, equal_to( 2 ) )
  assert_that( file1_state.checksum, is_not( equal_to( None ) ) )
  assert_that( file1_state.state, equal_to( lsp.ServerFileState.OPEN ) )

  # Checking for refresh without change is no-op
  assert_that( file1_state.GetSavedFileAction( 'test contents changed' ),
               equal_to( lsp.ServerFileState.NO_ACTION ) )
  assert_that( file1_state.version, equal_to( 2 ) )
  assert_that( file1_state.checksum, is_not( equal_to( None ) ) )
  assert_that( file1_state.state, equal_to( lsp.ServerFileState.OPEN ) )

  # Changing the same file is a new version
  assert_that( file1_state.GetDirtyFileAction( 'test contents changed again' ),
               equal_to( lsp.ServerFileState.CHANGE_FILE ) )
  assert_that( file1_state.version, equal_to( 3 ) )
  assert_that( file1_state.checksum, is_not( equal_to( None ) ) )
  assert_that( file1_state.state, equal_to( lsp.ServerFileState.OPEN ) )

  # Checking for refresh with change is a new version
  assert_that( file1_state.GetSavedFileAction( 'test changed back' ),
               equal_to( lsp.ServerFileState.CHANGE_FILE ) )
  assert_that( file1_state.version, equal_to( 4 ) )
  assert_that( file1_state.checksum, is_not( equal_to( None ) ) )
  assert_that( file1_state.state, equal_to( lsp.ServerFileState.OPEN ) )

  # Closing an open file progressed the state
  assert_that( file1_state.GetFileCloseAction(),
               equal_to( lsp.ServerFileState.CLOSE_FILE ) )
  assert_that( file1_state.version, equal_to( 4 ) )
  assert_that( file1_state.checksum, is_not( equal_to( None ) ) )
  assert_that( file1_state.state, equal_to( lsp.ServerFileState.CLOSED ) )

  # Replacing a closed file opens it
  assert_that( file1_state.GetDirtyFileAction( 'test contents again2' ),
               equal_to( lsp.ServerFileState.OPEN_FILE ) )
  assert_that( file1_state.version, equal_to( 1 ) )
  assert_that( file1_state.checksum, is_not( equal_to( None ) ) )
  assert_that( file1_state.state, equal_to( lsp.ServerFileState.OPEN ) )

  # Closing an open file progressed the state
  assert_that( file1_state.GetFileCloseAction(),
               equal_to( lsp.ServerFileState.CLOSE_FILE ) )
  assert_that( file1_state.version, equal_to( 1 ) )
  assert_that( file1_state.checksum, is_not( equal_to( None ) ) )
  assert_that( file1_state.state, equal_to( lsp.ServerFileState.CLOSED ) )

  # You can del a closed file
  del store[ file1_state.filename ]

  # Replacing a del'd file opens it again
  file1_state = store[ 'file1' ]
  assert_that( file1_state.GetDirtyFileAction( 'test contents again3' ),
               equal_to( lsp.ServerFileState.OPEN_FILE ) )
  assert_that( file1_state.version, equal_to( 1 ) )
  assert_that( file1_state.checksum, is_not( equal_to( None ) ) )
  assert_that( file1_state.state, equal_to( lsp.ServerFileState.OPEN ) )

  # You can del an open file (though you probably shouldn't)
  del store[ file1_state.filename ]

  # Closing a closed file is a noop
  assert_that( file2_state.GetFileCloseAction(),
               equal_to( lsp.ServerFileState.NO_ACTION ) )
  assert_that( file2_state.version, equal_to( 0 ) )
  assert_that( file2_state.checksum, equal_to( None ) )
  assert_that( file2_state.state, equal_to( lsp.ServerFileState.CLOSED ) )


@UnixOnly
def UriToFilePath_Unix_test():
  assert_that( calling( lsp.UriToFilePath ).with_args( 'test' ),
               raises( lsp.InvalidUriException ) )

  assert_that( lsp.UriToFilePath( 'file:/usr/local/test/test.test' ),
               equal_to( '/usr/local/test/test.test' ) )
  assert_that( lsp.UriToFilePath( 'file:///usr/local/test/test.test' ),
               equal_to( '/usr/local/test/test.test' ) )


@WindowsOnly
def UriToFilePath_Windows_test():
  assert_that( calling( lsp.UriToFilePath ).with_args( 'test' ),
               raises( lsp.InvalidUriException ) )

  assert_that( lsp.UriToFilePath( 'file:c:/usr/local/test/test.test' ),
               equal_to( 'C:\\usr\\local\\test\\test.test' ) )
  assert_that( lsp.UriToFilePath( 'file:c%3a/usr/local/test/test.test' ),
               equal_to( 'C:\\usr\\local\\test\\test.test' ) )
  assert_that( lsp.UriToFilePath( 'file:c%3A/usr/local/test/test.test' ),
               equal_to( 'C:\\usr\\local\\test\\test.test' ) )
  assert_that( lsp.UriToFilePath( 'file:///c:/usr/local/test/test.test' ),
               equal_to( 'C:\\usr\\local\\test\\test.test' ) )
  assert_that( lsp.UriToFilePath( 'file:///c%3a/usr/local/test/test.test' ),
               equal_to( 'C:\\usr\\local\\test\\test.test' ) )
  assert_that( lsp.UriToFilePath( 'file:///c%3A/usr/local/test/test.test' ),
               equal_to( 'C:\\usr\\local\\test\\test.test' ) )


@UnixOnly
def FilePathToUri_Unix_test():
  assert_that( lsp.FilePathToUri( '/usr/local/test/test.test' ),
               equal_to( 'file:///usr/local/test/test.test' ) )


@WindowsOnly
def FilePathToUri_Windows_test():
  assert_that( lsp.FilePathToUri( 'C:\\usr\\local\\test\\test.test' ),
               equal_to( 'file:///C:/usr/local/test/test.test' ) )


def CodepointsToUTF16CodeUnitsAndReverse_test():
  def Test( line_value, codepoints, code_units ):
    assert_that( lsp.CodepointsToUTF16CodeUnits( line_value, codepoints ),
                 equal_to( code_units ) )
    assert_that( lsp.UTF16CodeUnitsToCodepoints( line_value, code_units ),
                 equal_to( codepoints ) )

  tests = (
    ( '', 0, 0 ),
    ( 'abcdef', 1, 1 ),
    ( 'abcdef', 2, 2 ),
    ( 'abc', 4, 4 ),
    ( '😉test', len( '😉' ), 2 ),
    ( '😉', len( '😉' ), 2 ),
    ( '😉test', len( '😉' ) + 1, 3 ),
    ( 'te😉st', 1, 1 ),
    ( 'te😉st', 2 + len( '😉' ) + 1, 5 ),
  )

  for test in tests:
    yield Test, test[ 0 ], test[ 1 ], test[ 2 ]
