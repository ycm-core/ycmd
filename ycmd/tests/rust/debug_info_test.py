# Copyright (C) 2016-2021 ycmd contributors
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

from hamcrest import ( assert_that, contains_exactly, has_entries, has_entry,
                       instance_of, none )
from unittest.mock import patch
from unittest import TestCase
from ycmd.tests.rust import setUpModule, tearDownModule # noqa
from ycmd.tests.rust import ( IsolatedYcmd,
                              PathToTestFile,
                              SharedYcmd,
                              StartRustCompleterServerInDirectory )
from ycmd.tests.test_utils import BuildRequest


class DebugInfoTest( TestCase ):
  @SharedYcmd
  def test_DebugInfo_RlsVersion( self, app ):
    request_data = BuildRequest( filetype = 'rust' )
    assert_that(
      app.post_json( '/debug_info', request_data ).json,
      has_entry( 'completer', has_entries( {
        'name': 'Rust',
        'servers': contains_exactly( has_entries( {
          'name': 'Rust Language Server',
          'is_running': instance_of( bool ),
          'executable': contains_exactly( instance_of( str ) ),
          'pid': instance_of( int ),
          'address': none(),
          'port': none(),
          'logfiles': contains_exactly( instance_of( str ) ),
          'extras': contains_exactly(
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
            } ),
            has_entries( {
              'key': 'Rust Root',
              'value': instance_of( str )
            } )
          )
        } ) )
      } ) )
    )


  @IsolatedYcmd()
  @patch( 'ycmd.completers.rust.rust_completer._GetCommandOutput',
          return_value = '' )
  def test_DebugInfo_NoRlsVersion( self, app, *args ):
    StartRustCompleterServerInDirectory( app,
                                         PathToTestFile( 'common', 'src' ) )

    request_data = BuildRequest( filetype = 'rust' )
    assert_that(
      app.post_json( '/debug_info', request_data ).json,
      has_entry( 'completer', has_entries( {
        'name': 'Rust',
        'servers': contains_exactly( has_entries( {
          'name': 'Rust Language Server',
          'is_running': instance_of( bool ),
          'executable': contains_exactly( instance_of( str ) ),
          'pid': instance_of( int ),
          'address': none(),
          'port': none(),
          'logfiles': contains_exactly( instance_of( str ) ),
          'extras': contains_exactly(
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
            } ),
            has_entries( {
              'key': 'Rust Root',
              'value': instance_of( str )
            } )
          )
        } ) )
      } ) )
    )
