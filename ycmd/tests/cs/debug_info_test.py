# Copyright (C) 2016 ycmd contributors
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
from future import standard_library
standard_library.install_aliases()
from builtins import *  # noqa

from hamcrest import assert_that, matches_regexp

from ycmd.tests.cs import IsolatedYcmd, PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import ( BuildRequest, StopCompleterServer,
                                    UserOption, WaitUntilCompleterServerReady )
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
    matches_regexp( 'C# completer debug information:\n'
                    '  OmniSharp running at: http://localhost:\d+\n'
                    '  OmniSharp process ID: \d+\n'
                    '  OmniSharp executable: .+\n'
                    '  OmniSharp logfiles:\n'
                    '    .+\n'
                    '    .+\n'
                    '  OmniSharp solution: .+' ) )


@SharedYcmd
def DebugInfo_ServerIsNotRunning_NoSolution_test( app ):
  request_data = BuildRequest( filetype = 'cs' )
  assert_that(
    app.post_json( '/debug_info', request_data ).json,
    matches_regexp( 'C# completer debug information:\n'
                    '  OmniSharp not running\n'
                    '  OmniSharp executable: .+\n'
                    '  OmniSharp solution: not found' ) )


@IsolatedYcmd
def DebugInfo_ServerIsNotRunning_LogfilesExist_test( app ):
  with UserOption( 'server_keep_logfiles', True ):
    filepath = PathToTestFile( 'testy', 'Program.cs' )
    contents = ReadFile( filepath )
    event_data = BuildRequest( filepath = filepath,
                               filetype = 'cs',
                               contents = contents,
                               event_name = 'FileReadyToParse' )

    app.post_json( '/event_notification', event_data )
    WaitUntilCompleterServerReady( app, 'cs' )

    StopCompleterServer( app, 'cs', filepath )
    request_data = BuildRequest( filepath = filepath,
                                 filetype = 'cs' )
    assert_that(
      app.post_json( '/debug_info', request_data ).json,
      matches_regexp( 'C# completer debug information:\n'
                      '  OmniSharp no longer running\n'
                      '  OmniSharp executable: .+\n'
                      '  OmniSharp logfiles:\n'
                      '    .+\n'
                      '    .+\n'
                      '  OmniSharp solution: .+' ) )


@IsolatedYcmd
def DebugInfo_ServerIsNotRunning_LogfilesDoNotExist_test( app ):
  with UserOption( 'server_keep_logfiles', False ):
    filepath = PathToTestFile( 'testy', 'Program.cs' )
    contents = ReadFile( filepath )
    event_data = BuildRequest( filepath = filepath,
                               filetype = 'cs',
                               contents = contents,
                               event_name = 'FileReadyToParse' )

    app.post_json( '/event_notification', event_data )
    WaitUntilCompleterServerReady( app, 'cs' )

    StopCompleterServer( app, 'cs', filepath )
    request_data = BuildRequest( filepath = filepath,
                                 filetype = 'cs' )
    assert_that(
      app.post_json( '/debug_info', request_data ).json,
      matches_regexp( 'C# completer debug information:\n'
                      '  OmniSharp is not running\n'
                      '  OmniSharp executable: .+\n'
                      '  OmniSharp solution: .+' ) )
