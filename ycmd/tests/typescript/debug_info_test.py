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

from hamcrest import ( any_of,
                       assert_that,
                       contains_exactly,
                       has_entries,
                       has_entry,
                       instance_of )
from unittest import TestCase

from ycmd.tests.typescript import setUpModule, tearDownModule # noqa
from ycmd.tests.typescript import SharedYcmd
from ycmd.tests.test_utils import BuildRequest


class DebugInfoTest( TestCase ):
  @SharedYcmd
  def test_DebugInfo( self, app ):
    request_data = BuildRequest( filetype = 'typescript' )
    assert_that(
      app.post_json( '/debug_info', request_data ).json,
      has_entry( 'completer', has_entries( {
        'name': 'TypeScript',
        'servers': contains_exactly( has_entries( {
          'name': 'TSServer',
          'is_running': True,
          'executable': instance_of( str ),
          'pid': instance_of( int ),
          'address': None,
          'port': None,
          'logfiles': contains_exactly( instance_of( str ) ),
          'extras': contains_exactly( has_entries( {
            'key': 'version',
            'value': any_of( None, instance_of( str ) )
          } ) )
        } ) )
      } ) )
    )
