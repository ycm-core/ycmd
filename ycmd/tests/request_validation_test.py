# Copyright (C) 2014 Google Inc.
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

from hamcrest import raises, assert_that, calling
from nose.tools import ok_
from ycmd.request_validation import EnsureRequestValid
from ycmd.responses import ServerError


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


def EnsureRequestValid_AllOk_test():
  ok_( EnsureRequestValid( BasicData() ) )


def EnsureRequestValid_MissingLineNum_test():
  data = BasicData()
  del data[ 'line_num' ]
  assert_that( calling( EnsureRequestValid ).with_args( data ),
               raises( ServerError, ".*line_num.*" ) )


def EnsureRequestValid_MissingColumnNum_test():
  data = BasicData()
  del data[ 'column_num' ]
  assert_that( calling( EnsureRequestValid ).with_args( data ),
               raises( ServerError, ".*column_num.*" ) )


def EnsureRequestValid_MissingFilepath_test():
  data = BasicData()
  del data[ 'filepath' ]
  assert_that( calling( EnsureRequestValid ).with_args( data ),
               raises( ServerError, ".*filepath.*" ) )


def EnsureRequestValid_MissingFileData_test():
  data = BasicData()
  del data[ 'file_data' ]
  assert_that( calling( EnsureRequestValid ).with_args( data ),
               raises( ServerError, ".*file_data.*" ) )


def EnsureRequestValid_MissingFileDataContents_test():
  data = BasicData()
  del data[ 'file_data' ][ '/foo' ][ 'contents' ]
  assert_that( calling( EnsureRequestValid ).with_args( data ),
               raises( ServerError, ".*contents.*" ) )


def EnsureRequestValid_MissingFileDataFiletypes_test():
  data = BasicData()
  del data[ 'file_data' ][ '/foo' ][ 'filetypes' ]
  assert_that( calling( EnsureRequestValid ).with_args( data ),
               raises( ServerError, ".*filetypes.*" ) )


def EnsureRequestValid_EmptyFileDataFiletypes_test():
  data = BasicData()
  del data[ 'file_data' ][ '/foo' ][ 'filetypes' ][ 0 ]
  assert_that( calling( EnsureRequestValid ).with_args( data ),
               raises( ServerError, ".*filetypes.*" ) )


def EnsureRequestValid_MissingEntryForFileInFileData_test():
  data = BasicData()
  data[ 'filepath' ] = '/bar'
  assert_that( calling( EnsureRequestValid ).with_args( data ),
               raises( ServerError, ".*/bar.*" ) )
