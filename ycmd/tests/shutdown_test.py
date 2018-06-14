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
# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa

from hamcrest import assert_that, equal_to
from threading import Event
import time
import requests

from ycmd.tests.client_test import Client_test
from ycmd.utils import StartThread

# Time to wait for all the servers to shutdown. Tweak for the CI environment.
#
# NOTE: The timeout is 2 minutes. That is a long time, but the java sub-server
# (jdt.ls) takes a _long time_ to finally actually shut down. This is because it
# is based on eclipse, which must do whatever eclipse must do when it shuts down
# its workspace.
SUBSERVER_SHUTDOWN_TIMEOUT = 120


class Shutdown_test( Client_test ):

  @Client_test.CaptureLogfiles
  def FromHandlerWithoutSubserver_test( self ):
    self.Start()
    self.AssertServersAreRunning()

    response = self.PostRequest( 'shutdown' )
    self.AssertResponse( response )
    assert_that( response.json(), equal_to( True ) )
    self.AssertServersShutDown( timeout = SUBSERVER_SHUTDOWN_TIMEOUT )
    self.AssertLogfilesAreRemoved()


  @Client_test.CaptureLogfiles
  def FromHandlerWithSubservers_test( self ):
    self.Start()

    filetypes = [ 'cs',
                  'go',
                  'java',
                  'javascript',
                  'typescript',
                  'rust' ]
    for filetype in filetypes:
      self.StartSubserverForFiletype( filetype )
    self.AssertServersAreRunning()

    response = self.PostRequest( 'shutdown' )
    self.AssertResponse( response )
    assert_that( response.json(), equal_to( True ) )
    self.AssertServersShutDown( timeout = SUBSERVER_SHUTDOWN_TIMEOUT )
    self.AssertLogfilesAreRemoved()


  @Client_test.CaptureLogfiles
  def FromWatchdogWithoutSubserver_test( self ):
    self.Start( idle_suicide_seconds = 2, check_interval_seconds = 1 )
    self.AssertServersAreRunning()

    self.AssertServersShutDown( timeout = SUBSERVER_SHUTDOWN_TIMEOUT )
    self.AssertLogfilesAreRemoved()


  @Client_test.CaptureLogfiles
  def FromWatchdogWithSubservers_test( self ):
    all_servers_are_running = Event()

    def KeepServerAliveInAnotherThread():
      while not all_servers_are_running.is_set():
        try:
          self.GetRequest( 'ready' )
        except requests.exceptions.ConnectionError:
          pass
        finally:
          time.sleep( 0.1 )

    self.Start( idle_suicide_seconds = 2, check_interval_seconds = 1 )

    StartThread( KeepServerAliveInAnotherThread )

    try:
      filetypes = [ 'cs',
                    'go',
                    'java',
                    'javascript',
                    'typescript',
                    'rust' ]
      for filetype in filetypes:
        self.StartSubserverForFiletype( filetype )
      self.AssertServersAreRunning()
    finally:
      all_servers_are_running.set()

    self.AssertServersShutDown( timeout = SUBSERVER_SHUTDOWN_TIMEOUT + 10 )
    self.AssertLogfilesAreRemoved()
