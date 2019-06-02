# Copyright (C) 2019 ycmd contributors
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

from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa

from hamcrest import assert_that, contains, has_entry
from mock import patch

from ycmd.tests.go import ( PathToTestFile,
                            IsolatedYcmd,
                            StartGoCompleterServerInDirectory )
from ycmd.tests.test_utils import ( BuildRequest,
                                    MockProcessTerminationTimingOut,
                                    WaitUntilCompleterServerReady )


def AssertGoCompleterServerIsRunning( app, is_running ):
  request_data = BuildRequest( filetype = 'go' )
  assert_that( app.post_json( '/debug_info', request_data ).json,
               has_entry(
                 'completer',
                 has_entry( 'servers', contains(
                   has_entry( 'is_running', is_running )
                 ) )
               ) )


@IsolatedYcmd
def ServerManagement_RestartServer_test( app ):
  filepath = PathToTestFile( 'goto.go' )
  StartGoCompleterServerInDirectory( app, filepath )

  AssertGoCompleterServerIsRunning( app, True )

  app.post_json(
    '/run_completer_command',
    BuildRequest(
      filepath = filepath,
      filetype = 'go',
      command_arguments = [ 'RestartServer' ],
    ),
  )

  WaitUntilCompleterServerReady( app, 'go' )

  AssertGoCompleterServerIsRunning( app, True )


@IsolatedYcmd
@patch( 'shutil.rmtree', side_effect = OSError )
@patch( 'ycmd.utils.WaitUntilProcessIsTerminated',
        MockProcessTerminationTimingOut )
def ServerManagement_CloseServer_Unclean_test( app, *args ):
  StartGoCompleterServerInDirectory( app, PathToTestFile() )

  app.post_json(
    '/run_completer_command',
    BuildRequest(
      filetype = 'go',
      command_arguments = [ 'StopServer' ]
    )
  )

  request_data = BuildRequest( filetype = 'go' )
  assert_that( app.post_json( '/debug_info', request_data ).json,
               has_entry(
                 'completer',
                 has_entry( 'servers', contains(
                   has_entry( 'is_running', False )
                 ) )
               ) )


@IsolatedYcmd
def ServerManagement_StopServerTwice_test( app ):
  StartGoCompleterServerInDirectory( app, PathToTestFile() )

  app.post_json(
    '/run_completer_command',
    BuildRequest(
      filetype = 'go',
      command_arguments = [ 'StopServer' ],
    ),
  )

  AssertGoCompleterServerIsRunning( app, False )

  # Stopping a stopped server is a no-op
  app.post_json(
    '/run_completer_command',
    BuildRequest(
      filetype = 'go',
      command_arguments = [ 'StopServer' ],
    ),
  )

  AssertGoCompleterServerIsRunning( app, False )
