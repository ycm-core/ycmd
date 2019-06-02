# Copyright (C) 2016-2019 ycmd contributors
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

from hamcrest import ( assert_that, contains, has_entries, has_entry,
                       instance_of, none )
from mock import patch

from ycmd.tests.rust import ( IsolatedYcmd,
                              PathToTestFile,
                              SharedYcmd,
                              StartRustCompleterServerInDirectory )
from ycmd.tests.test_utils import BuildRequest


@SharedYcmd
def DebugInfo_RlsVersion_test( app ):
  request_data = BuildRequest( filetype = 'rust' )
  assert_that(
    app.post_json( '/debug_info', request_data ).json,
    has_entry( 'completer', has_entries( {
      'name': 'Rust',
      'servers': contains( has_entries( {
        'name': 'Rust Language Server',
        'is_running': instance_of( bool ),
        'executable': instance_of( str ),
        'pid': instance_of( int ),
        'address': none(),
        'port': none(),
        'logfiles': contains( instance_of( str ) ),
        'extras': contains(
          has_entries( {
            'key': 'Server State',
            'value': instance_of( str )
          } ),
          has_entries( {
            'key': 'Project Directory',
            'value': instance_of( str )
          } ),
          has_entries( {
            'key': 'Settings',
            'value': '{}'
          } ),
          has_entries( {
            'key': 'Project State',
            'value': instance_of( str )
          } ),
          has_entries( {
            'key': 'Version',
            'value': instance_of( str )
          } )
        )
      } ) )
    } ) )
  )


@IsolatedYcmd
@patch( 'ycmd.completers.rust.rust_completer._GetCommandOutput',
        return_value = '' )
def DebugInfo_NoRlsVersion_test( app, *args ):
  StartRustCompleterServerInDirectory( app, PathToTestFile( 'common', 'src' ) )

  request_data = BuildRequest( filetype = 'rust' )
  assert_that(
    app.post_json( '/debug_info', request_data ).json,
    has_entry( 'completer', has_entries( {
      'name': 'Rust',
      'servers': contains( has_entries( {
        'name': 'Rust Language Server',
        'is_running': instance_of( bool ),
        'executable': instance_of( str ),
        'pid': instance_of( int ),
        'address': none(),
        'port': none(),
        'logfiles': contains( instance_of( str ) ),
        'extras': contains(
          has_entries( {
            'key': 'Server State',
            'value': instance_of( str )
          } ),
          has_entries( {
            'key': 'Project Directory',
            'value': instance_of( str )
          } ),
          has_entries( {
            'key': 'Settings',
            'value': '{}'
          } ),
          has_entries( {
            'key': 'Project State',
            'value': instance_of( str )
          } ),
          has_entries( {
            'key': 'Version',
            'value': none()
          } )
        )
      } ) )
    } ) )
  )
