# Copyright (C) 2021 ycmd contributors
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

from hamcrest import raises, assert_that, calling
from ycmd.request_validation import EnsureRequestValid
from ycmd.responses import ServerError
from unittest import TestCase


def BasicData():
  return {
    'line_num': 1,
    'column_num': 2,
    'filepath': '/foo',
    'file_data': {
      '/foo': {
        'filetypes': [ 'text' ],
        'contents': 'zoobar'
      }
    }
  }


class RequestValidationTest( TestCase ):
  def test_EnsureRequestValid_AllOk( self ):
    assert_that( EnsureRequestValid( BasicData() ) )


  def test_EnsureRequestValid_MissingLineNum( self ):
    data = BasicData()
    del data[ 'line_num' ]
    assert_that( calling( EnsureRequestValid ).with_args( data ),
                 raises( ServerError, ".*line_num.*" ) )


  def test_EnsureRequestValid_MissingColumnNum( self ):
    data = BasicData()
    del data[ 'column_num' ]
    assert_that( calling( EnsureRequestValid ).with_args( data ),
                 raises( ServerError, ".*column_num.*" ) )


  def test_EnsureRequestValid_MissingFilepath( self ):
    data = BasicData()
    del data[ 'filepath' ]
    assert_that( calling( EnsureRequestValid ).with_args( data ),
                 raises( ServerError, ".*filepath.*" ) )


  def test_EnsureRequestValid_MissingFileData( self ):
    data = BasicData()
    del data[ 'file_data' ]
    assert_that( calling( EnsureRequestValid ).with_args( data ),
                 raises( ServerError, ".*file_data.*" ) )


  def test_EnsureRequestValid_MissingFileDataContents( self ):
    data = BasicData()
    del data[ 'file_data' ][ '/foo' ][ 'contents' ]
    assert_that( calling( EnsureRequestValid ).with_args( data ),
                 raises( ServerError, ".*contents.*" ) )


  def test_EnsureRequestValid_MissingFileDataFiletypes( self ):
    data = BasicData()
    del data[ 'file_data' ][ '/foo' ][ 'filetypes' ]
    assert_that( calling( EnsureRequestValid ).with_args( data ),
                 raises( ServerError, ".*filetypes.*" ) )


  def test_EnsureRequestValid_EmptyFileDataFiletypes( self ):
    data = BasicData()
    del data[ 'file_data' ][ '/foo' ][ 'filetypes' ][ 0 ]
    assert_that( calling( EnsureRequestValid ).with_args( data ),
                 raises( ServerError, ".*filetypes.*" ) )


  def test_EnsureRequestValid_MissingEntryForFileInFileData( self ):
    data = BasicData()
    data[ 'filepath' ] = '/bar'
    assert_that( calling( EnsureRequestValid ).with_args( data ),
                 raises( ServerError, ".*/bar.*" ) )
