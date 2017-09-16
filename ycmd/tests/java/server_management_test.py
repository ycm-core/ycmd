# Copyright (C) 2015 ycmd contributors
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

from hamcrest import ( assert_that,
                       contains,
                       has_entries,
                       has_entry,
                       instance_of )
from ycmd.tests.java import ( PathToTestFile,
                              IsolatedYcmdInDirectory,
                              WaitUntilCompleterServerReady )
from ycmd.tests.test_utils import BuildRequest


@IsolatedYcmdInDirectory( PathToTestFile( 'simple_eclipse_project' ) )
def Subcommands_RestartServer_test( app ):
  WaitUntilCompleterServerReady( app )

  eclipse_project = PathToTestFile( 'simple_eclipse_project' )
  maven_project = PathToTestFile( 'simple_maven_project' )

  # Run the debug info to check that we have the correct project dir
  request_data = BuildRequest( filetype = 'java' )
  assert_that(
    app.post_json( '/debug_info', request_data ).json,
    has_entry( 'completer', has_entries( {
      'name': 'Java',
      'servers': contains( has_entries( {
        'name': 'Java Language Server',
        'is_running': instance_of( bool ),
        'executable': instance_of( str ),
        'pid': instance_of( int ),
        'logfiles': contains( instance_of( str ),
                              instance_of( str ) ),
        'extras': contains(
          has_entries( { 'key': 'Java Path',
                         'value': instance_of( str ) } ),
          has_entries( { 'key': 'Launcher Config.',
                         'value': instance_of( str ) } ),
          has_entries( { 'key': 'Project Directory',
                         'value': eclipse_project } ),
          has_entries( { 'key': 'Workspace Path',
                         'value': instance_of( str ) } )
        )
      } ) )
    } ) )
  )

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
  assert_that(
    app.post_json( '/debug_info', request_data ).json,
    has_entry( 'completer', has_entries( {
      'name': 'Java',
      'servers': contains( has_entries( {
        'name': 'Java Language Server',
        'is_running': instance_of( bool ),
        'executable': instance_of( str ),
        'pid': instance_of( int ),
        'logfiles': contains( instance_of( str ),
                              instance_of( str ) ),
        'extras': contains(
          has_entries( { 'key': 'Java Path',
                         'value': instance_of( str ) } ),
          has_entries( { 'key': 'Launcher Config.',
                         'value': instance_of( str ) } ),
          has_entries( { 'key': 'Project Directory',
                         'value': maven_project } ),
          has_entries( { 'key': 'Workspace Path',
                         'value': instance_of( str ) } )
        )
      } ) )
    } ) )
  )


@IsolatedYcmdInDirectory( PathToTestFile( 'simple_eclipse_project', 'src' ) )
def Subcommands_ProjectDetection_EclipseParent( app ):
  WaitUntilCompleterServerReady( app )

  project = PathToTestFile( 'simple_eclipse_project' )

  # Run the debug info to check that we have the correct project dir
  request_data = BuildRequest( filetype = 'java' )
  assert_that(
    app.post_json( '/debug_info', request_data ).json,
    has_entry( 'completer', has_entries( {
      'name': 'Java',
      'servers': contains( has_entries( {
        'name': 'Java Language Server',
        'is_running': instance_of( bool ),
        'executable': instance_of( str ),
        'pid': instance_of( int ),
        'logfiles': contains( instance_of( str ),
                              instance_of( str ) ),
        'extras': contains(
          has_entries( { 'key': 'Java Path',
                         'value': instance_of( str ) } ),
          has_entries( { 'key': 'Launcher Config.',
                         'value': instance_of( str ) } ),
          has_entries( { 'key': 'Project Directory',
                         'value': project } ),
          has_entries( { 'key': 'Workspace Path',
                         'value': instance_of( str ) } )
        )
      } ) )
    } ) )
  )


@IsolatedYcmdInDirectory( PathToTestFile( 'simple_maven_project',
                                          'src',
                                          'java',
                                          'test' ) )
def Subcommands_ProjectDetection_MavenParent( app ):
  WaitUntilCompleterServerReady( app )

  project = PathToTestFile( 'simple_maven_project' )

  # Run the debug info to check that we have the correct project dir
  request_data = BuildRequest( filetype = 'java' )
  assert_that(
    app.post_json( '/debug_info', request_data ).json,
    has_entry( 'completer', has_entries( {
      'name': 'Java',
      'servers': contains( has_entries( {
        'name': 'Java Language Server',
        'is_running': instance_of( bool ),
        'executable': instance_of( str ),
        'pid': instance_of( int ),
        'logfiles': contains( instance_of( str ),
                              instance_of( str ) ),
        'extras': contains(
          has_entries( { 'key': 'Java Path',
                         'value': instance_of( str ) } ),
          has_entries( { 'key': 'Launcher Config.',
                         'value': instance_of( str ) } ),
          has_entries( { 'key': 'Project Directory',
                         'value': project } ),
          has_entries( { 'key': 'Workspace Path',
                         'value': instance_of( str ) } )
        )
      } ) )
    } ) )
  )


@IsolatedYcmdInDirectory( PathToTestFile( 'simple_gradle_project',
                                          'src',
                                          'java',
                                          'test' ) )
def Subcommands_ProjectDetection_GradleParent( app ):
  WaitUntilCompleterServerReady( app )

  project = PathToTestFile( 'simple_gradle_project' )

  # Run the debug info to check that we have the correct project dir
  request_data = BuildRequest( filetype = 'java' )
  assert_that(
    app.post_json( '/debug_info', request_data ).json,
    has_entry( 'completer', has_entries( {
      'name': 'Java',
      'servers': contains( has_entries( {
        'name': 'Java Language Server',
        'is_running': instance_of( bool ),
        'executable': instance_of( str ),
        'pid': instance_of( int ),
        'logfiles': contains( instance_of( str ),
                              instance_of( str ) ),
        'extras': contains(
          has_entries( { 'key': 'Java Path',
                         'value': instance_of( str ) } ),
          has_entries( { 'key': 'Launcher Config.',
                         'value': instance_of( str ) } ),
          has_entries( { 'key': 'Project Directory',
                         'value': project } ),
          has_entries( { 'key': 'Workspace Path',
                         'value': instance_of( str ) } )
        )
      } ) )
    } ) )
  )
