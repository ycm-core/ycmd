# Copyright (C) 2024 ycmd contributors
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
                       has_items,
                       instance_of )
from unittest import TestCase

from ycmd.tests.cs import setUpModule, tearDownModule # noqa
from ycmd.tests.cs import PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import BuildRequest, is_json_string_matching


class DebugInfoTest( TestCase ):
  @SharedYcmd
  def test_DebugInfo( self, app ):
    request_data = BuildRequest( filetype = 'cs' )
    assert_that(
      app.post_json( '/debug_info', request_data ).json,
      has_entry( 'completer', has_entries( {
        'name': 'Csharp',
        'servers': contains_exactly( has_entries( {
          'name': 'OmniSharp-Roslyn',
          'is_running': instance_of( bool ),
          'executable': contains_exactly( instance_of( str ),
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
              'key': 'Open Workspaces',
              'value': has_items()
            } ),
            has_entries( {
              'key': 'Settings',
              'value': is_json_string_matching( has_entries( {} ) ),
            } ),
          )
        } ) ),
      } ) )
    )
