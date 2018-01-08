# Copyright (C) 2016-2017 ycmd contributors
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

from hamcrest import ( assert_that, contains, empty, has_entries, has_entry,
                       instance_of )

from ycmd.tests.cs import PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import ( BuildRequest,
                                    WaitUntilCompleterServerReady )
from ycmd.utils import ReadFile


@SharedYcmd
def DebugInfo_ServerIsRunning_test( app ):
  filepath = PathToTestFile( 'testy', 'Program.cs' )
  contents = ReadFile( filepath )
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilCompleterServerReady( app, 'cs' )

  request_data = BuildRequest( filepath = filepath,
                               filetype = 'cs' )
  assert_that(
    app.post_json( '/debug_info', request_data ).json,
    has_entry( 'completer', has_entries( {
      'name': 'C#',
      'servers': contains( has_entries( {
        'name': 'OmniSharp',
        'is_running': True,
        'executable': instance_of( str ),
        'pid': instance_of( int ),
        'address': instance_of( str ),
        'port': instance_of( int ),
        'logfiles': contains( instance_of( str ),
                              instance_of( str ) ),
        'extras': contains( has_entries( {
          'key': 'solution',
          'value': instance_of( str )
        } ) )
      } ) ),
      'items': empty()
    } ) )
  )


@SharedYcmd
def DebugInfo_ServerIsNotRunning_NoSolution_test( app ):
  request_data = BuildRequest( filetype = 'cs' )
  assert_that(
    app.post_json( '/debug_info', request_data ).json,
    has_entry( 'completer', has_entries( {
      'name': 'C#',
      'servers': contains( has_entries( {
        'name': 'OmniSharp',
        'is_running': False,
        'executable': instance_of( str ),
        'pid': None,
        'address': None,
        'port': None,
        'logfiles': empty()
      } ) ),
      'items': empty()
    } ) )
  )
