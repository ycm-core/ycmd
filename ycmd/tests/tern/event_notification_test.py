# Copyright (C) 2015-2021 ycmd contributors
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
                       empty,
                       equal_to,
                       has_entries,
                       none )
from unittest.mock import patch
from unittest import TestCase
from pprint import pformat
import os
import requests

from ycmd.tests.test_utils import BuildRequest, ErrorMatcher
from ycmd.tests.tern import IsolatedYcmd, PathToTestFile
from ycmd import utils


class EventNotificationTest( TestCase ):
  @IsolatedYcmd()
  def test_EventNotification_OnFileReadyToParse_ProjectFile_cwd( self, app ):
    response = app.post_json( '/event_notification',
                              BuildRequest(
                                filepath = PathToTestFile(),
                                event_name = 'FileReadyToParse',
                                filetype = 'javascript' ),
                              expect_errors = True )

    assert_that( response.status_code, equal_to( requests.codes.ok ) )
    assert_that( response.json, empty() )

    debug_info = app.post_json( '/debug_info',
                                BuildRequest( filetype = 'javascript' ) ).json
    assert_that(
      debug_info[ 'completer' ][ 'servers' ][ 0 ][ 'extras' ],
      contains_exactly(
        has_entries( {
          'key': 'configuration file',
          'value': PathToTestFile( '.tern-project' )
        } ),
        has_entries( {
          'key': 'working directory',
          'value': PathToTestFile()
        } )
      )
    )


  @IsolatedYcmd()
  def test_EventNotification_OnFileReadyToParse_ProjectFile_parentdir(
      self, app ):
    response = app.post_json( '/event_notification',
                              BuildRequest(
                                filepath = PathToTestFile( 'lamelib' ),
                                event_name = 'FileReadyToParse',
                                filetype = 'javascript' ),
                              expect_errors = True )

    assert_that( response.status_code, equal_to( requests.codes.ok ) )
    assert_that( response.json, empty() )

    debug_info = app.post_json( '/debug_info',
                                BuildRequest( filetype = 'javascript' ) ).json
    assert_that(
      debug_info[ 'completer' ][ 'servers' ][ 0 ][ 'extras' ],
      contains_exactly(
        has_entries( {
          'key': 'configuration file',
          'value': PathToTestFile( '.tern-project' )
        } ),
        has_entries( {
          'key': 'working directory',
          'value': PathToTestFile()
        } )
      )
    )


  @IsolatedYcmd()
  @patch( 'ycmd.completers.javascript.tern_completer.GlobalConfigExists',
          return_value = False )
  def test_EventNotification_OnFileReadyToParse_NoProjectFile(
      self, app, *args ):
    # We raise an error if we can't detect a .tern-project file.
    # We only do this on the first OnFileReadyToParse event after a
    # server startup.
    response = app.post_json( '/event_notification',
                              BuildRequest( filepath = PathToTestFile( '..' ),
                                            event_name = 'FileReadyToParse',
                                            filetype = 'javascript' ),
                              expect_errors = True )


    print( f'event response: { pformat( response.json ) }' )

    assert_that( response.status_code,
                 equal_to( requests.codes.internal_server_error ) )

    assert_that(
      response.json,
      ErrorMatcher( RuntimeError,
                    'Warning: Unable to detect a .tern-project file '
                    'in the hierarchy before ' + PathToTestFile( '..' ) +
                    ' and no global .tern-config file was found. '
                    'This is required for accurate JavaScript '
                    'completion. Please see the User Guide for '
                    'details.' )
    )

    debug_info = app.post_json( '/debug_info',
                                BuildRequest( filetype = 'javascript' ) ).json
    assert_that(
      debug_info[ 'completer' ][ 'servers' ][ 0 ][ 'extras' ],
      contains_exactly(
        has_entries( {
          'key': 'configuration file',
          'value': none()
        } ),
        has_entries( {
          'key': 'working directory',
          'value': utils.GetCurrentDirectory()
        } )
      )
    )

    # Check that a subsequent call does *not* raise the error.
    response = app.post_json( '/event_notification',
                              BuildRequest( event_name = 'FileReadyToParse',
                                            filetype = 'javascript' ),
                              expect_errors = True )

    print( f'event response: { pformat( response.json ) }' )

    assert_that( response.status_code, equal_to( requests.codes.ok ) )
    assert_that( response.json, empty() )

    # Restart the server and check that it raises it again.
    app.post_json( '/run_completer_command',
                   BuildRequest( filepath = PathToTestFile( '..' ),
                                 command_arguments = [ 'RestartServer' ],
                                 filetype = 'javascript' ) )

    response = app.post_json( '/event_notification',
                              BuildRequest( filepath = PathToTestFile( '..' ),
                                            event_name = 'FileReadyToParse',
                                            filetype = 'javascript' ),
                              expect_errors = True )

    print( f'event response: { pformat( response.json ) }' )

    assert_that( response.status_code,
                 equal_to( requests.codes.internal_server_error ) )

    assert_that(
      response.json,
      ErrorMatcher( RuntimeError,
                    'Warning: Unable to detect a .tern-project file '
                    'in the hierarchy before ' + PathToTestFile( '..' ) +
                    ' and no global .tern-config file was found. '
                    'This is required for accurate JavaScript '
                    'completion. Please see the User Guide for '
                    'details.' )
    )

    # Finally, restart the server in a folder containing a .tern-project file.
    # We expect no error in that case.
    app.post_json( '/run_completer_command',
                   BuildRequest( filepath = PathToTestFile(),
                                 command_arguments = [ 'RestartServer' ],
                                 filetype = 'javascript' ) )

    response = app.post_json( '/event_notification',
                              BuildRequest( filepath = PathToTestFile(),
                                            event_name = 'FileReadyToParse',
                                            filetype = 'javascript' ),
                              expect_errors = True )

    print( f'event response: { pformat( response.json ) }' )

    assert_that( response.status_code, equal_to( requests.codes.ok ) )
    assert_that( response.json, empty() )

    debug_info = app.post_json( '/debug_info',
                                BuildRequest( filetype = 'javascript' ) ).json
    assert_that(
      debug_info[ 'completer' ][ 'servers' ][ 0 ][ 'extras' ],
      contains_exactly(
        has_entries( {
          'key': 'configuration file',
          'value': PathToTestFile( '.tern-project' )
        } ),
        has_entries( {
          'key': 'working directory',
          'value': PathToTestFile()
        } )
      )
    )


  @IsolatedYcmd()
  @patch( 'ycmd.completers.javascript.tern_completer.GlobalConfigExists',
          return_value = True )
  def test_EventNotification_OnFileReadyToParse_UseGlobalConfig(
      self, app, *args ):
    # No working directory is given.
    response = app.post_json( '/event_notification',
                              BuildRequest( filepath = PathToTestFile( '..' ),
                                            event_name = 'FileReadyToParse',
                                            filetype = 'javascript' ),
                              expect_errors = True )

    print( f'event response: { pformat( response.json ) }' )

    assert_that( response.status_code, equal_to( requests.codes.ok ) )
    assert_that( response.json, empty() )

    debug_info = app.post_json( '/debug_info',
                                BuildRequest( filetype = 'javascript' ) ).json
    assert_that(
      debug_info[ 'completer' ][ 'servers' ][ 0 ][ 'extras' ],
      contains_exactly(
        has_entries( {
          'key': 'configuration file',
          'value': os.path.join( os.path.expanduser( '~' ), '.tern-config' )
        } ),
        has_entries( {
          'key': 'working directory',
          'value': utils.GetCurrentDirectory()
        } )
      )
    )

    # Restart the server with a working directory.
    app.post_json( '/run_completer_command',
                   BuildRequest( filepath = PathToTestFile( '..' ),
                                 command_arguments = [ 'RestartServer' ],
                                 filetype = 'javascript',
                                 working_dir = PathToTestFile() ) )

    debug_info = app.post_json( '/debug_info',
                                BuildRequest( filetype = 'javascript' ) ).json
    assert_that(
      debug_info[ 'completer' ][ 'servers' ][ 0 ][ 'extras' ],
      contains_exactly(
        has_entries( {
          'key': 'configuration file',
          'value': os.path.join( os.path.expanduser( '~' ), '.tern-config' )
        } ),
        has_entries( {
          'key': 'working directory',
          'value': PathToTestFile()
        } )
      )
    )
