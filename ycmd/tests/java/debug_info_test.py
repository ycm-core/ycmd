# Copyright (C) 2017 ycmd contributors
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

from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import division
# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa

from hamcrest import ( assert_that,
                       contains,
                       equal_to,
                       has_entry,
                       has_entries,
                       instance_of )

from mock import patch
from ycmd.tests.java import ( DEFAULT_PROJECT_DIR,
                              IsolatedYcmd,
                              PathToTestFile,
                              SharedYcmd,
                              StartJavaCompleterServerInDirectory )
from ycmd.tests.test_utils import BuildRequest, WaitUntilCompleterServerReady
from ycmd.completers.language_server import language_server_completer as lsc

import json
import threading


@IsolatedYcmd()
def DebugInfo_HandleNotificationInPollThread_Throw_test( app ):
  filepath = PathToTestFile( DEFAULT_PROJECT_DIR,
                             'src',
                             'com',
                             'youcompleteme',
                             'Test.java' )
  StartJavaCompleterServerInDirectory( app, filepath )

  # This mock will be called in the message pump thread, so syncronize the
  # result (thrown) using an Event
  thrown = threading.Event()

  def ThrowOnLogMessage( msg ):
    thrown.set()
    raise RuntimeError( "ThrowOnLogMessage" )

  with patch.object( lsc.LanguageServerCompleter,
                     'HandleNotificationInPollThread',
                     side_effect = ThrowOnLogMessage ):
    app.post_json(
      '/run_completer_command',
      BuildRequest(
        filepath = filepath,
        filetype = 'java',
        command_arguments = [ 'RestartServer' ],
      ),
    )

    # Ensure that we still process and handle messages even though a
    # message-pump-thread-handler raised an error.
    WaitUntilCompleterServerReady( app, 'java' )

  # Prove that the exception was thrown.
  assert_that( thrown.is_set(), equal_to( True ) )


@SharedYcmd
def DebugInfo_test( app ):
  request_data = BuildRequest( filetype = 'java' )
  assert_that(
    app.post_json( '/debug_info', request_data ).json,
    has_entry( 'completer', has_entries( {
      'name': 'Java',
      'servers': contains( has_entries( {
        'name': 'jdt.ls Java Language Server',
        'is_running': instance_of( bool ),
        'executable': instance_of( str ),
        'pid': instance_of( int ),
        'logfiles': contains( instance_of( str ),
                              instance_of( str ) ),
        'extras': contains(
          has_entries( { 'key': 'Startup Status',
                         'value': 'Ready' } ),
          has_entries( { 'key': 'Java Path',
                         'value': instance_of( str ) } ),
          has_entries( { 'key': 'Launcher Config.',
                         'value': instance_of( str ) } ),
          has_entries( { 'key': 'Workspace Path',
                         'value': instance_of( str ) } ),
          has_entries( { 'key': 'Extension Path',
                         'value': contains( instance_of( str ) ) } ),
          has_entries( { 'key': 'Server State',
                         'value': 'Initialized' } ),
          has_entries( { 'key': 'Project Directory',
                         'value': PathToTestFile( DEFAULT_PROJECT_DIR ) } ),
          has_entries( {
            'key': 'Settings',
            'value': json.dumps( { 'bundles': [] },
                                 indent = 2,
                                 sort_keys = True )
          } )
        )
      } ) )
    } ) )
  )


@IsolatedYcmd( { 'extra_conf_globlist': PathToTestFile( 'extra_confs', '*' ) } )
def Subcommands_ExtraConf_SettingsValid_test( app ):
  StartJavaCompleterServerInDirectory(
    app,
    PathToTestFile( 'extra_confs', 'simple_extra_conf_project' ) )

  filepath = PathToTestFile( 'extra_confs',
                             'simple_extra_conf_project',
                             'src',
                             'ExtraConf.java' )

  request_data = BuildRequest( filepath = filepath,
                               filetype = 'java' )
  assert_that(
    app.post_json( '/debug_info', request_data ).json,
    has_entry( 'completer', has_entries( {
      'name': 'Java',
      'servers': contains( has_entries( {
        'name': 'jdt.ls Java Language Server',
        'is_running': instance_of( bool ),
        'executable': instance_of( str ),
        'pid': instance_of( int ),
        'logfiles': contains( instance_of( str ),
                              instance_of( str ) ),
        'extras': contains(
          has_entries( { 'key': 'Startup Status',
                         'value': 'Ready' } ),
          has_entries( { 'key': 'Java Path',
                         'value': instance_of( str ) } ),
          has_entries( { 'key': 'Launcher Config.',
                         'value': instance_of( str ) } ),
          has_entries( { 'key': 'Workspace Path',
                         'value': instance_of( str ) } ),
          has_entries( { 'key': 'Extension Path',
                         'value': contains( instance_of( str ) ) } ),
          has_entries( { 'key': 'Server State',
                         'value': 'Initialized' } ),
          has_entries( {
            'key': 'Project Directory',
            'value': PathToTestFile( 'extra_confs',
                                     'simple_extra_conf_project' )
          } ),
          has_entries( {
            'key': 'Settings',
            'value': json.dumps(
              { 'java.rename.enabled': False, 'bundles': [] },
              indent = 2,
              sort_keys = True )
          } ),
        )
      } ) )
    } ) )
  )
