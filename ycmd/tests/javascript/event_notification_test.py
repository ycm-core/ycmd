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

from nose.tools import eq_
from hamcrest import assert_that, empty

from javascript_handlers_test import Javascript_Handlers_test
from pprint import pformat
import httplib
import os
from mock import patch

class Javascript_EventNotification_test( Javascript_Handlers_test ):

  def OnFileReadyToParse_ProjectFile_cwd_test( self ):
    contents = open( self._PathToTestFile( 'simple_test.js' ) ).read()

    response = self._app.post_json( '/event_notification',
                                    self._BuildRequest(
                                      event_name = 'FileReadyToParse',
                                      contents = contents,
                                      filetype = 'javascript' ),
                                    expect_errors = True)

    eq_( response.status_code, httplib.OK )
    assert_that( response.json, empty() )


  def OnFileReadyToParse_ProjectFile_parentdir_test( self ):
    os.chdir( self._PathToTestFile( 'lamelib' ) )

    contents = open( self._PathToTestFile( 'simple_test.js' ) ).read()

    response = self._app.post_json( '/event_notification',
                                    self._BuildRequest(
                                      event_name = 'FileReadyToParse',
                                      contents = contents,
                                      filetype = 'javascript' ),
                                    expect_errors = True)

    eq_( response.status_code, httplib.OK )
    assert_that( response.json, empty() )


  @patch( 'ycmd.completers.javascript.tern_completer.GlobalConfigExists',
          return_value = False )
  def OnFileReadyToParse_NoProjectFile_test( self, *args ):
    # We raise an error if we can't detect a .tern-project file.
    # We only do this on the first OnFileReadyToParse event after a
    # server startup.
    os.chdir( self._PathToTestFile( '..' ) )

    contents = open( self._PathToTestFile( 'simple_test.js' ) ).read()

    response = self._app.post_json( '/event_notification',
                                    self._BuildRequest(
                                      event_name = 'FileReadyToParse',
                                      contents = contents,
                                      filetype = 'javascript' ),
                                    expect_errors = True )

    print( 'event response: {0}'.format( pformat( response.json ) ) )

    eq_( response.status_code, httplib.INTERNAL_SERVER_ERROR )

    assert_that(
      response.json,
      self._ErrorMatcher( RuntimeError,
                          'Warning: Unable to detect a .tern-project file '
                          'in the hierarchy before ' + os.getcwd() +
                          ' and no global .tern-config file was found. '
                          'This is required for accurate JavaScript '
                          'completion. Please see the User Guide for '
                          'details.' )
    )

    # Check that a subsequent call does *not* raise the error

    response = self._app.post_json( '/event_notification',
                                    self._BuildRequest(
                                      event_name = 'FileReadyToParse',
                                      contents = contents,
                                      filetype = 'javascript' ),
                                    expect_errors = True )

    print( 'event response: {0}'.format( pformat( response.json ) ) )

    eq_( response.status_code, httplib.OK )
    assert_that( response.json, empty() )

    # Restart the server and check that it raises it again

    self._app.post_json(
      '/run_completer_command',
      self._BuildRequest( command_arguments = [ 'StopServer' ],
                          filetype = 'javascript',
                          contents = contents,
                          completer_target = 'filetype_default' )
    )
    self._app.post_json(
      '/run_completer_command',
      self._BuildRequest( command_arguments = [ 'StartServer' ],
                          filetype = 'javascript',
                          contents = contents,
                          completer_target = 'filetype_default' ) )

    self._WaitUntilTernServerReady()

    response = self._app.post_json( '/event_notification',
                                    self._BuildRequest(
                                      event_name = 'FileReadyToParse',
                                      contents = contents,
                                      filetype = 'javascript' ),
                                    expect_errors = True)

    print( 'event response: {0}'.format( pformat( response.json ) ) )

    eq_( response.status_code, httplib.INTERNAL_SERVER_ERROR )

    assert_that(
      response.json,
      self._ErrorMatcher( RuntimeError,
                          'Warning: Unable to detect a .tern-project file '
                          'in the hierarchy before ' + os.getcwd() +
                          ' and no global .tern-config file was found. '
                          'This is required for accurate JavaScript '
                          'completion. Please see the User Guide for '
                          'details.' )
    )


  @patch( 'ycmd.completers.javascript.tern_completer.GlobalConfigExists',
          return_value = True )
  def OnFileReadyToParse_UseGlobalConfig_test( self, *args ):
    os.chdir( self._PathToTestFile( '..' ) )

    contents = open( self._PathToTestFile( 'simple_test.js' ) ).read()

    response = self._app.post_json( '/event_notification',
                                    self._BuildRequest(
                                      event_name = 'FileReadyToParse',
                                      contents = contents,
                                      filetype = 'javascript' ),
                                    expect_errors = True )

    print( 'event response: {0}'.format( pformat( response.json ) ) )

    eq_( response.status_code, httplib.OK )
