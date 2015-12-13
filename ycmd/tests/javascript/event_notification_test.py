#
# Copyright (C) 2015 ycmd contributors
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

from ycmd.server_utils import SetUpPythonPath
SetUpPythonPath()

import bottle, httplib, os, pprint

from webtest import TestApp
from nose.tools import ( eq_, with_setup )
from hamcrest import ( assert_that, empty )

from ycmd import handlers
from ycmd.tests.test_utils import ( BuildRequest, ErrorMatcher, Setup )

from .test_utils import ( with_cwd,
                          TEST_DATA_DIR,
                          PathToTestFile,
                          WaitForTernServerReady  )

bottle.debug( True )

@with_setup( Setup )
@with_cwd( os.path.join( TEST_DATA_DIR, '..' ) )
def OnFileReadyToParse_TernCompleter_No_TernProjectFile_test():
  """We raise an error if we can't detect a .tern-project file. We only do this
  on the first OnFileReadyToParse event after a server startup."""

  app = TestApp( handlers.app )
  WaitForTernServerReady( app )

  contents = open( PathToTestFile( 'simple_test.js' ) ).read()

  response = app.post_json( '/event_notification',
                            BuildRequest(
                              event_name = 'FileReadyToParse',
                              contents = contents,
                              filetype = 'javascript' ),
                            expect_errors = True)

  print 'event response: ' + pprint.pformat( response.json )

  eq_( response.status_code, httplib.INTERNAL_SERVER_ERROR )

  assert_that( response.json, ErrorMatcher( RuntimeError,
    'Warning: Unable to detect a .tern-project file '
    'in the hierarchy before ' + os.getcwd() + '. '
    'This is required for accurate JavaScript '
    'completion. Please see the User Guide for '
    'details.' ) )

  # Check that a subsequent call does *not* raise the error

  response = app.post_json( '/event_notification',
                            BuildRequest(
                              event_name = 'FileReadyToParse',
                              contents = contents,
                              filetype = 'javascript' ),
                            expect_errors = True)

  print 'event response: ' + pprint.pformat( response.json )

  eq_( response.status_code, httplib.OK )
  assert_that( response.json, empty() )

  # Restart the server and check that it raises it again

  app.post_json( '/run_completer_command',
                 BuildRequest( command_arguments = [ 'StopServer' ],
                               filetype = 'javascript',
                               contents = contents,
                               completer_target = 'filetype_default' ) )
  app.post_json( '/run_completer_command',
                 BuildRequest( command_arguments = [ 'StartServer' ],
                               filetype = 'javascript',
                               contents = contents,
                               completer_target = 'filetype_default' ) )

  WaitForTernServerReady( app )

  response = app.post_json( '/event_notification',
                            BuildRequest(
                              event_name = 'FileReadyToParse',
                              contents = contents,
                              filetype = 'javascript' ),
                            expect_errors = True)

  print 'event response: ' + pprint.pformat( response.json )

  eq_( response.status_code, httplib.INTERNAL_SERVER_ERROR )

  assert_that( response.json, ErrorMatcher( RuntimeError,
    'Warning: Unable to detect a .tern-project file '
    'in the hierarchy before ' + os.getcwd() + '. '
    'This is required for accurate JavaScript '
    'completion. Please see the User Guide for '
    'details.' ) )

