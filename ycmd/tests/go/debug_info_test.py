# Copyright (C) 2016-2020 ycmd contributors
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
                       matches_regexp )

from ycmd.tests.go import ( IsolatedYcmd,
                            PathToTestFile,
                            SharedYcmd,
                            StartGoCompleterServerInDirectory )
from ycmd.tests.test_utils import BuildRequest


@SharedYcmd
def DebugInfo_test( app ):
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
            'value': matches_regexp( '{\n  "hoverKind": "Structured"\n}' )
          } ),
        )
      } ) ),
    } ) )
  )


@IsolatedYcmd
def DebugInfo_ProjectDirectory_test( app ):
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
            'value': matches_regexp( '{\n  "hoverKind": "Structured"\n}' )
          } ),
        )
      } ) ),
    } ) )
  )


def Dummy_test():
  # Workaround for https://github.com/pytest-dev/pytest-rerunfailures/issues/51
  assert True
