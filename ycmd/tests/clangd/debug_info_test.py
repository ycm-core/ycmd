# Copyright (C) 2011-2012 Google Inc.
#               2018      ycmd contributors
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

from hamcrest import assert_that, contains, empty, has_entries, has_entry

from ycmd.tests.clangd import ( IsolatedYcmd, PathToTestFile, SharedYcmd,
                                RunAfterInitialized )
from ycmd.tests.test_utils import BuildRequest


@IsolatedYcmd()
def DebugInfo_NotInitialized_test( app ):
  request_data = BuildRequest( filepath = PathToTestFile( 'basic.cpp' ),
                               filetype = 'cpp' )
  assert_that(
    app.post_json( '/debug_info', request_data ).json,
    has_entry( 'completer', has_entries( {
      'name': 'clangd',
      'servers': contains( has_entries( {
        'name': 'clangd',
        'pid': None,
        'is_running': False,
        'extras': contains(
          has_entries( {
            'key': 'Server State',
            'value': 'Dead',
          } ),
          has_entries( {
            'key': 'Project Directory',
            'value': None,
          } ),
          has_entries( {
            'key': 'Settings',
            'value': '{}',
          } ),
        ),
      } ) ),
      'items': empty(),
    } ) )
  )


@SharedYcmd
def DebugInfo_Initialized_test( app ):
  request_data = BuildRequest( filepath = PathToTestFile( 'basic.cpp' ),
                               filetype = 'cpp' )
  test = { 'request': request_data }
  RunAfterInitialized( app, test )
  assert_that(
    app.post_json( '/debug_info', request_data ).json,
    has_entry( 'completer', has_entries( {
      'name': 'clangd',
      'servers': contains( has_entries( {
        'name': 'clangd',
        'is_running': True,
        'extras': contains(
          has_entries( {
            'key': 'Server State',
            'value': 'Initialized',
          } ),
          has_entries( {
            'key': 'Project Directory',
            'value': PathToTestFile(),
          } ),
          has_entries( {
            'key': 'Settings',
            'value': '{}',
          } ),
        ),
      } ) ),
      'items': empty()
    } ) )
  )
