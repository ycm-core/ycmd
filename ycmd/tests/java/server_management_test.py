# Copyright (C) 2017-2018 ycmd contributors
# encoding: utf-8
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

import functools
import os
import psutil
import requests
import time

from mock import patch
from hamcrest import assert_that, contains, equal_to, has_entry
from ycmd.tests.java import ( PathToTestFile,
                              IsolatedYcmd,
                              SharedYcmd,
                              StartJavaCompleterServerInDirectory )
from ycmd.tests.test_utils import ( BuildRequest,
                                    CompleterProjectDirectoryMatcher,
                                    ErrorMatcher,
                                    MockProcessTerminationTimingOut,
                                    TemporaryTestDir,
                                    WaitUntilCompleterServerReady )
from ycmd import utils, handlers


def TidyJDTProjectFiles( dir_name ):
  """Defines a test decorator which deletes the .project etc. files that are
  created by the jdt.ls server when it detects a project. This ensures the tests
  actually check that jdt.ls detects the project."""
  def decorator( test ):
    @functools.wraps( test )
    def Wrapper( *args, **kwargs ):
      utils.RemoveIfExists( os.path.join( dir_name, '.project' ) )
      utils.RemoveIfExists( os.path.join( dir_name, '.classpath' ) )
      utils.RemoveDirIfExists( os.path.join( dir_name, '.settings' ) )
      try:
        test( *args, **kwargs )
      finally:
        utils.RemoveIfExists( os.path.join( dir_name, '.project' ) )
        utils.RemoveIfExists( os.path.join( dir_name, '.classpath' ) )
        utils.RemoveDirIfExists( os.path.join( dir_name, '.settings' ) )

    return Wrapper

  return decorator


@IsolatedYcmd()
def ServerManagement_RestartServer_test( app ):
  StartJavaCompleterServerInDirectory(
    app, PathToTestFile( 'simple_eclipse_project' ) )

  eclipse_project = PathToTestFile( 'simple_eclipse_project' )
  maven_project = PathToTestFile( 'simple_maven_project' )

  # Run the debug info to check that we have the correct project dir
  request_data = BuildRequest( filetype = 'java' )
  assert_that( app.post_json( '/debug_info', request_data ).json,
               CompleterProjectDirectoryMatcher( eclipse_project ) )

  # Restart the server with a different client working directory
  filepath = PathToTestFile( 'simple_maven_project',
                             'src',
                             'main',
                             'java',
                             'com',
                             'test',
                             'TestFactory.java' )

  app.post_json(
    '/run_completer_command',
    BuildRequest(
      filepath = filepath,
      filetype = 'java',
      working_dir = maven_project,
      command_arguments = [ 'RestartServer' ],
    ),
  )

  WaitUntilCompleterServerReady( app, 'java' )

  app.post_json(
    '/event_notification',
    BuildRequest(
      filepath = filepath,
      filetype = 'java',
      working_dir = maven_project,
      event_name = 'FileReadyToParse',
    )
  )

  # Run the debug info to check that we have the correct project dir
  request_data = BuildRequest( filetype = 'java' )
  assert_that( app.post_json( '/debug_info', request_data ).json,
               CompleterProjectDirectoryMatcher( maven_project ) )


@IsolatedYcmd()
def ServerManagement_ProjectDetection_EclipseParent_test( app ):
  StartJavaCompleterServerInDirectory(
    app, PathToTestFile( 'simple_eclipse_project', 'src' ) )

  project = PathToTestFile( 'simple_eclipse_project' )

  # Run the debug info to check that we have the correct project dir
  request_data = BuildRequest( filetype = 'java' )
  assert_that( app.post_json( '/debug_info', request_data ).json,
               CompleterProjectDirectoryMatcher( project ) )


@TidyJDTProjectFiles( PathToTestFile( 'simple_maven_project' ) )
@IsolatedYcmd()
def ServerManagement_ProjectDetection_MavenParent_test( app ):
  StartJavaCompleterServerInDirectory( app,
                                       PathToTestFile( 'simple_maven_project',
                                                       'src',
                                                       'main',
                                                       'java',
                                                       'com',
                                                       'test' ) )

  project = PathToTestFile( 'simple_maven_project' )

  # Run the debug info to check that we have the correct project dir
  request_data = BuildRequest( filetype = 'java' )
  assert_that( app.post_json( '/debug_info', request_data ).json,
               CompleterProjectDirectoryMatcher( project ) )


@TidyJDTProjectFiles( PathToTestFile( 'simple_maven_project',
                                      'simple_submodule' ) )
@TidyJDTProjectFiles( PathToTestFile( 'simple_maven_project' ) )
@IsolatedYcmd()
def ServerManagement_ProjectDetection_MavenParent_Submodule_test( app ):
  StartJavaCompleterServerInDirectory( app,
                                       PathToTestFile( 'simple_maven_project',
                                                       'simple_submodule',
                                                       'src',
                                                       'main',
                                                       'java',
                                                       'com',
                                                       'test' ) )

  project = PathToTestFile( 'simple_maven_project' )

  # Run the debug info to check that we have the correct project dir
  request_data = BuildRequest( filetype = 'java' )
  assert_that( app.post_json( '/debug_info', request_data ).json,
               CompleterProjectDirectoryMatcher( project ) )


@TidyJDTProjectFiles( PathToTestFile( 'simple_gradle_project' ) )
@IsolatedYcmd()
def ServerManagement_ProjectDetection_GradleParent_test( app ):
  StartJavaCompleterServerInDirectory( app,
                                       PathToTestFile( 'simple_gradle_project',
                                                       'src',
                                                       'main',
                                                       'java',
                                                       'com',
                                                       'test' ) )

  project = PathToTestFile( 'simple_gradle_project' )

  # Run the debug info to check that we have the correct project dir
  request_data = BuildRequest( filetype = 'java' )
  assert_that( app.post_json( '/debug_info', request_data ).json,
               CompleterProjectDirectoryMatcher( project ) )


@TidyJDTProjectFiles( PathToTestFile( 'simple_gradle_project' ) )
@TidyJDTProjectFiles( PathToTestFile( 'simple_maven_project' ) )
@IsolatedYcmd()
def ServerManagement_OpenProject_AbsolutePath_test( app ):
  StartJavaCompleterServerInDirectory( app,
                                       PathToTestFile( 'simple_gradle_project',
                                                       'src',
                                                       'main',
                                                       'java',
                                                       'com',
                                                       'test' ) )

  # Initially, we detect the gradle project...
  gradle_project = PathToTestFile( 'simple_gradle_project' )
  maven_project = PathToTestFile( 'simple_maven_project' )

  # Run the debug info to check that we have the correct project dir
  request_data = BuildRequest( filetype = 'java' )
  assert_that( app.post_json( '/debug_info', request_data ).json,
               CompleterProjectDirectoryMatcher( gradle_project ) )


  # We then force it to reload the maven project
  app.post_json(
    '/run_completer_command',
    BuildRequest(
      filetype = 'java',
      command_arguments = [ 'OpenProject', maven_project ],
    ),
  )

  # Run the debug info to check that we now have the maven project, without
  # changing anything else
  request_data = BuildRequest( filetype = 'java' )
  assert_that( app.post_json( '/debug_info', request_data ).json,
               CompleterProjectDirectoryMatcher( maven_project ) )


@TidyJDTProjectFiles( PathToTestFile( 'simple_gradle_project' ) )
@TidyJDTProjectFiles( PathToTestFile( 'simple_maven_project' ) )
@IsolatedYcmd()
def ServerManagement_OpenProject_RelativePath_test( app ):
  StartJavaCompleterServerInDirectory( app,
                                       PathToTestFile( 'simple_gradle_project',
                                                       'src',
                                                       'main',
                                                       'java',
                                                       'com',
                                                       'test' ) )

  # Initially, we detect the gradle project...
  gradle_project = PathToTestFile( 'simple_gradle_project' )
  maven_project = PathToTestFile( 'simple_maven_project' )

  # Run the debug info to check that we have the correct project dir
  request_data = BuildRequest( filetype = 'java' )
  assert_that( app.post_json( '/debug_info', request_data ).json,
               CompleterProjectDirectoryMatcher( gradle_project ) )


  # We then force it to reload the maven project
  app.post_json(
    '/run_completer_command',
    BuildRequest(
      filetype = 'java',
      command_arguments = [
        'OpenProject',
        os.path.join( '..', 'simple_maven_project' ),
      ],
      working_dir = gradle_project,
    ),
  )

  # Run the debug info to check that we now have the maven project, without
  # changing anything else
  request_data = BuildRequest( filetype = 'java' )
  assert_that( app.post_json( '/debug_info', request_data ).json,
               CompleterProjectDirectoryMatcher( maven_project ) )



@SharedYcmd
def ServerManagement_OpenProject_RelativePathNoWD_test( app ):
  response = app.post_json(
    '/run_completer_command',
    BuildRequest(
      filetype = 'java',
      command_arguments = [
        'OpenProject',
        os.path.join( '..', 'simple_maven_project' ),
      ],
    ),
    expect_errors = True,
  )
  assert_that( response.status_code,
               equal_to( requests.codes.internal_server_error ) )
  assert_that( response.json,
               ErrorMatcher( ValueError,
                             'Project directory must be absolute' ) )


@SharedYcmd
def ServerManagement_OpenProject_RelativePathNoPath_test( app ):
  response = app.post_json(
    '/run_completer_command',
    BuildRequest(
      filetype = 'java',
      command_arguments = [
        'OpenProject',
      ],
    ),
    expect_errors = True,
  )
  assert_that( response.status_code,
               equal_to( requests.codes.internal_server_error ) )
  assert_that( response.json,
               ErrorMatcher( ValueError,
                             'Usage: OpenProject <project directory>' ) )


def ServerManagement_ProjectDetection_NoParent_test():
  with TemporaryTestDir() as tmp_dir:

    @IsolatedYcmd()
    def Test( app ):
      StartJavaCompleterServerInDirectory( app, tmp_dir )

      # Run the debug info to check that we have the correct project dir (cwd)
      request_data = BuildRequest( filetype = 'java' )
      assert_that( app.post_json( '/debug_info', request_data ).json,
                   CompleterProjectDirectoryMatcher( tmp_dir ) )

    yield Test


@IsolatedYcmd()
@patch( 'shutil.rmtree', side_effect = OSError )
@patch( 'ycmd.utils.WaitUntilProcessIsTerminated',
        MockProcessTerminationTimingOut )
def ServerManagement_CloseServer_Unclean_test( app, *args ):
  StartJavaCompleterServerInDirectory(
    app, PathToTestFile( 'simple_eclipse_project' ) )

  app.post_json(
    '/run_completer_command',
    BuildRequest(
      filetype = 'java',
      command_arguments = [ 'StopServer' ]
    )
  )

  request_data = BuildRequest( filetype = 'java' )
  assert_that( app.post_json( '/debug_info', request_data ).json,
               has_entry(
                 'completer',
                 has_entry( 'servers', contains(
                   has_entry( 'is_running', False )
                 ) )
               ) )


@IsolatedYcmd()
def ServerManagement_StopServerTwice_test( app ):
  StartJavaCompleterServerInDirectory(
    app, PathToTestFile( 'simple_eclipse_project' ) )

  app.post_json(
    '/run_completer_command',
    BuildRequest(
      filetype = 'java',
      command_arguments = [ 'StopServer' ],
    ),
  )

  request_data = BuildRequest( filetype = 'java' )
  assert_that( app.post_json( '/debug_info', request_data ).json,
               has_entry(
                 'completer',
                 has_entry( 'servers', contains(
                   has_entry( 'is_running', False )
                 ) )
               ) )


  # Stopping a stopped server is a no-op
  app.post_json(
    '/run_completer_command',
    BuildRequest(
      filetype = 'java',
      command_arguments = [ 'StopServer' ],
    ),
  )

  request_data = BuildRequest( filetype = 'java' )
  assert_that( app.post_json( '/debug_info', request_data ).json,
               has_entry(
                 'completer',
                 has_entry( 'servers', contains(
                   has_entry( 'is_running', False )
                 ) )
               ) )


@IsolatedYcmd()
def ServerManagement_ServerDies_test( app ):
  StartJavaCompleterServerInDirectory(
    app,
    PathToTestFile( 'simple_eclipse_project' ) )

  request_data = BuildRequest( filetype = 'java' )
  debug_info = app.post_json( '/debug_info', request_data ).json
  print( 'Debug info: {0}'.format( debug_info ) )
  pid = debug_info[ 'completer' ][ 'servers' ][ 0 ][ 'pid' ]
  print( 'pid: {0}'.format( pid ) )
  process = psutil.Process( pid )
  process.terminate()

  for tries in range( 0, 10 ):
    request_data = BuildRequest( filetype = 'java' )
    debug_info = app.post_json( '/debug_info', request_data ).json
    if not debug_info[ 'completer' ][ 'servers' ][ 0 ][ 'is_running' ]:
      break

    time.sleep( 0.5 )

  assert_that( debug_info,
               has_entry(
                 'completer',
                 has_entry( 'servers', contains(
                   has_entry( 'is_running', False )
                 ) )
               ) )


@IsolatedYcmd()
def ServerManagement_ServerDiesWhileShuttingDown_test( app ):
  StartJavaCompleterServerInDirectory(
    app,
    PathToTestFile( 'simple_eclipse_project' ) )

  request_data = BuildRequest( filetype = 'java' )
  debug_info = app.post_json( '/debug_info', request_data ).json
  print( 'Debug info: {0}'.format( debug_info ) )
  pid = debug_info[ 'completer' ][ 'servers' ][ 0 ][ 'pid' ]
  print( 'pid: {0}'.format( pid ) )
  process = psutil.Process( pid )


  def StopServerInAnotherThread():
    app.post_json(
      '/run_completer_command',
      BuildRequest(
        filetype = 'java',
        command_arguments = [ 'StopServer' ],
      ),
    )

  completer = handlers._server_state.GetFiletypeCompleter( [ 'java' ] )

  # In this test we mock out the sending method so that we don't actually send
  # the shutdown request. We then assisted-suicide the downstream server, which
  # causes the shutdown request to be aborted. This is interpreted by the
  # shutdown code as a successful shutdown. We need to do the shutdown and
  # terminate in parallel as the post_json is a blocking call.
  with patch.object( completer.GetConnection(), 'WriteData' ):
    stop_server_task = utils.StartThread( StopServerInAnotherThread )
    process.terminate()
    stop_server_task.join()

  request_data = BuildRequest( filetype = 'java' )
  debug_info = app.post_json( '/debug_info', request_data ).json
  assert_that( debug_info,
               has_entry(
                 'completer',
                 has_entry( 'servers', contains(
                   has_entry( 'is_running', False )
                 ) )
               ) )


@IsolatedYcmd()
def ServerManagement_ConnectionRaisesWhileShuttingDown_test( app ):
  StartJavaCompleterServerInDirectory(
    app,
    PathToTestFile( 'simple_eclipse_project' ) )

  request_data = BuildRequest( filetype = 'java' )
  debug_info = app.post_json( '/debug_info', request_data ).json
  print( 'Debug info: {0}'.format( debug_info ) )
  pid = debug_info[ 'completer' ][ 'servers' ][ 0 ][ 'pid' ]
  print( 'pid: {0}'.format( pid ) )
  process = psutil.Process( pid )

  completer = handlers._server_state.GetFiletypeCompleter( [ 'java' ] )

  # In this test we mock out the GetResponse method, which is used to send the
  # shutdown request. This means we only send the exit notification. It's
  # possible that the server won't like this, but it seems reasonable for it to
  # actually exit at that point.
  with patch.object( completer.GetConnection(),
                     'GetResponse',
                     side_effect = RuntimeError ):
    app.post_json(
      '/run_completer_command',
      BuildRequest(
        filetype = 'java',
        command_arguments = [ 'StopServer' ],
      ),
    )

  request_data = BuildRequest( filetype = 'java' )
  debug_info = app.post_json( '/debug_info', request_data ).json
  assert_that( debug_info,
               has_entry(
                 'completer',
                 has_entry( 'servers', contains(
                   has_entry( 'is_running', False )
                 ) )
               ) )

  if process.is_running():
    process.terminate()
    raise AssertionError( 'jst.ls process is still running after exit handler' )
