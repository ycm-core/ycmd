# Copyright (C) 2017 ycmd contributors
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

from mock import patch
from hamcrest import ( assert_that,
                       contains,
                       has_entries,
                       has_entry,
                       has_item )
from ycmd.tests.java import ( PathToTestFile,
                              IsolatedYcmdInDirectory,
                              WaitUntilCompleterServerReady )
from ycmd.tests.test_utils import BuildRequest, TemporaryTestDir
from ycmd import utils


def _ProjectDirectoryMatcher( project_directory ):
  return has_entry(
    'completer',
    has_entry( 'servers', contains(
      has_entry( 'extras', has_item(
        has_entries( {
          'key': 'Project Directory',
          'value': project_directory,
        } )
      ) )
    ) )
  )


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


@IsolatedYcmdInDirectory( PathToTestFile( 'simple_eclipse_project' ) )
def Subcommands_RestartServer_test( app ):
  WaitUntilCompleterServerReady( app )

  eclipse_project = PathToTestFile( 'simple_eclipse_project' )
  maven_project = PathToTestFile( 'simple_maven_project' )

  # Run the debug info to check that we have the correct project dir
  request_data = BuildRequest( filetype = 'java' )
  assert_that( app.post_json( '/debug_info', request_data ).json,
               _ProjectDirectoryMatcher( eclipse_project ) )

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

  WaitUntilCompleterServerReady( app )

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
               _ProjectDirectoryMatcher( maven_project ) )


@IsolatedYcmdInDirectory( PathToTestFile( 'simple_eclipse_project', 'src' ) )
def Subcommands_ProjectDetection_EclipseParent_test( app ):
  WaitUntilCompleterServerReady( app )

  project = PathToTestFile( 'simple_eclipse_project' )

  # Run the debug info to check that we have the correct project dir
  request_data = BuildRequest( filetype = 'java' )
  assert_that( app.post_json( '/debug_info', request_data ).json,
               _ProjectDirectoryMatcher( project ) )


@TidyJDTProjectFiles( PathToTestFile( 'simple_maven_project' ) )
@IsolatedYcmdInDirectory( PathToTestFile( 'simple_maven_project',
                                          'src',
                                          'main',
                                          'java',
                                          'com',
                                          'test' ) )
def Subcommands_ProjectDetection_MavenParent_test( app ):
  WaitUntilCompleterServerReady( app )

  project = PathToTestFile( 'simple_maven_project' )

  # Run the debug info to check that we have the correct project dir
  request_data = BuildRequest( filetype = 'java' )
  assert_that( app.post_json( '/debug_info', request_data ).json,
               _ProjectDirectoryMatcher( project ) )


@TidyJDTProjectFiles( PathToTestFile( 'simple_maven_project' ) )
@IsolatedYcmdInDirectory( PathToTestFile( 'simple_gradle_project',
                                          'src',
                                          'main',
                                          'java',
                                          'com',
                                          'test' ) )
def Subcommands_ProjectDetection_GradleParent_test( app ):
  WaitUntilCompleterServerReady( app )

  project = PathToTestFile( 'simple_gradle_project' )

  # Run the debug info to check that we have the correct project dir
  request_data = BuildRequest( filetype = 'java' )
  assert_that( app.post_json( '/debug_info', request_data ).json,
               _ProjectDirectoryMatcher( project ) )


def Subcommands_ProjectDetection_NoParent_test():
  with TemporaryTestDir() as tmp_dir:

    @IsolatedYcmdInDirectory( tmp_dir )
    def Test( app ):
      WaitUntilCompleterServerReady( app )

      # Run the debug info to check that we have the correct project dir (cwd)
      request_data = BuildRequest( filetype = 'java' )
      assert_that( app.post_json( '/debug_info', request_data ).json,
                   _ProjectDirectoryMatcher( os.path.realpath( tmp_dir ) ) )

    yield Test


@IsolatedYcmdInDirectory( PathToTestFile( 'simple_eclipse_project' ) )
@patch( 'ycmd.completers.java.java_completer.JavaCompleter.ShutdownServer',
        side_effect = AssertionError )
def CloseServer_Unclean_test( app,
                              stop_server_cleanly ):
  WaitUntilCompleterServerReady( app )

  filepath = PathToTestFile( 'simple_maven_project',
                             'src',
                             'main',
                             'java',
                             'com',
                             'test',
                             'TestFactory.java' )

  app.post_json(
    '/event_notification',
    BuildRequest(
      filepath = filepath,
      filetype = 'java',
      working_dir = PathToTestFile( 'simple_eclipse_project' ),
      event_name = 'FileReadyToParse',
    )
  )

  WaitUntilCompleterServerReady( app )

  app.post_json(
    '/run_completer_command',
    BuildRequest(
      filepath = filepath,
      filetype = 'java',
      working_dir = PathToTestFile( 'simple_eclipse_project' ),
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
