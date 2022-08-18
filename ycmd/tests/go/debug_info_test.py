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

from hamcrest import ( assert_that,
                       contains_exactly,
                       has_entries,
                       has_entry,
                       instance_of,
                       is_not,
                       empty )
from unittest import TestCase

from ycmd.tests.go import setUpModule, tearDownModule # noqa
from ycmd.tests.go import ( IsolatedYcmd,
                            PathToTestFile,
                            SharedYcmd,
                            StartGoCompleterServerInDirectory )
from ycmd.tests.test_utils import BuildRequest, is_json_string_matching


class DebugInfoTest( TestCase ):
  @SharedYcmd
  def test_DebugInfo( self, app ):
    request_data = BuildRequest( filetype = 'go' )
    assert_that(
      app.post_json( '/debug_info', request_data ).json,
      has_entry( 'completer', has_entries( {
        'name': 'Go',
        'servers': contains_exactly( has_entries( {
          'name': 'gopls',
          'is_running': instance_of( bool ),
          'executable': contains_exactly( instance_of( str ),
                                          instance_of( str ),
                                          instance_of( str ),
                                          instance_of( str ) ),
          'address': None,
          'port': None,
          'pid': instance_of( int ),
          'logfiles': contains_exactly( instance_of( str ) ),
          'extras': contains_exactly(
            has_entries( {
              'key': 'Server State',
              'value': instance_of( str ),
            } ),
            has_entries( {
              'key': 'Project Directory',
              'value': PathToTestFile(),
            } ),
            has_entries( {
              'key': 'Settings',
              'value': is_json_string_matching( has_entries( {
                'hints': is_not( empty() ),
                'hoverKind': 'Structured',
                'semanticTokens': True
              } ) ),
            } ),
          )
        } ) ),
      } ) )
    )


  @IsolatedYcmd()
  def test_DebugInfo_ProjectDirectory( self, app ):
    project_dir = PathToTestFile( 'td' )
    StartGoCompleterServerInDirectory( app, project_dir )
    assert_that(
      app.post_json( '/debug_info', BuildRequest( filetype = 'go' ) ).json,
      has_entry( 'completer', has_entries( {
        'name': 'Go',
        'servers': contains_exactly( has_entries( {
          'name': 'gopls',
          'is_running': instance_of( bool ),
          'executable': contains_exactly( instance_of( str ),
                                          instance_of( str ),
                                          instance_of( str ),
                                          instance_of( str ) ),
          'address': None,
          'port': None,
          'pid': instance_of( int ),
          'logfiles': contains_exactly( instance_of( str ) ),
          'extras': contains_exactly(
            has_entries( {
              'key': 'Server State',
              'value': instance_of( str ),
            } ),
            has_entries( {
              'key': 'Project Directory',
              'value': PathToTestFile(),
            } ),
            has_entries( {
              'key': 'Settings',
              'value': is_json_string_matching( has_entries( {
                'hints': is_not( empty() ),
                'hoverKind': 'Structured',
                'semanticTokens': True
              } ) ),
            } ),
          )
        } ) ),
      } ) )
    )
