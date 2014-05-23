#!/usr/bin/env python
#
# Copyright (C) 2014 Google Inc.
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

from nose.tools import eq_
from ..request_wrap import RequestWrap


def LineValue_OneLine_test():
  request = {
    'line_num': 1,
    'filepath': '/foo',
    'file_data': {
      '/foo': {
        'contents': 'zoo'
      }
    }
  }

  eq_( 'zoo', RequestWrap( request )[ 'line_value' ] )


def LineValue_LastLine_test():
  request = {
    'line_num': 3,
    'filepath': '/foo',
    'file_data': {
      '/foo': {
        'contents': 'goo\nbar\nzoo'
      }
    }
  }

  eq_( 'zoo', RequestWrap( request )[ 'line_value' ] )


def LineValue_MiddleLine_test():
  request = {
    'line_num': 2,
    'filepath': '/foo',
    'file_data': {
      '/foo': {
        'contents': 'goo\nzoo\nbar'
      }
    }
  }

  eq_( 'zoo', RequestWrap( request )[ 'line_value' ] )


def LineValue_WindowsLines_test():
  request = {
    'line_num': 3,
    'filepath': '/foo',
    'file_data': {
      '/foo': {
        'contents': 'goo\r\nbar\r\nzoo'
      }
    }
  }

  eq_( 'zoo', RequestWrap( request )[ 'line_value' ] )


def LineValue_MixedFormatLines_test():
  request = {
    'line_num': 3,
    'filepath': '/foo',
    'file_data': {
      '/foo': {
        'contents': 'goo\nbar\r\nzoo'
      }
    }
  }

  eq_( 'zoo', RequestWrap( request )[ 'line_value' ] )
