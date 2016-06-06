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

from ycmd.tests.go import IsolatedYcmd, SharedYcmd, StopGoCodeServer
from ycmd.tests.test_utils import BuildRequest, UserOption


@SharedYcmd
def DebugInfo_ServerIsRunning_test( app ):
  subcommands_data = BuildRequest( completer_target = 'go' )
  assert_that(
    app.post_json( '/debug_info', subcommands_data ).json,
    matches_regexp( 'Go completer debug information:\n'
                    '  Gocode running at: http://127.0.0.1:\d+\n'
                    '  Gocode process ID: \d+\n'
                    '  Gocode binary: .+\n'
                    '  Gocode logfiles:\n'
                    '    .+\n'
                    '    .+\n'
                    '  Godef binary: .+' ) )


@IsolatedYcmd
def DebugInfo_ServerIsNotRunning_LogfilesExist_test( app ):
  with UserOption( 'server_keep_logfiles', True ):
    StopGoCodeServer( app )
    subcommands_data = BuildRequest( completer_target = 'go' )
    assert_that(
      app.post_json( '/debug_info', subcommands_data ).json,
      matches_regexp( 'Go completer debug information:\n'
                      '  Gocode no longer running\n'
                      '  Gocode binary: .+\n'
                      '  Gocode logfiles:\n'
                      '    .+\n'
                      '    .+\n'
                      '  Godef binary: .+' ) )


@IsolatedYcmd
def DebugInfo_ServerIsNotRunning_LogfilesDoNotExist_test( app ):
  with UserOption( 'server_keep_logfiles', False ):
    StopGoCodeServer( app )
    subcommands_data = BuildRequest( completer_target = 'go' )
    assert_that(
      app.post_json( '/debug_info', subcommands_data ).json,
      matches_regexp( 'Go completer debug information:\n'
                      '  Gocode is not running\n'
                      '  Gocode binary: .+\n'
                      '  Godef binary: .+' ) )
