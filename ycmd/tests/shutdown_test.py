# Copyright (C) 2021 ycmd contributors
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

from hamcrest import assert_that, equal_to
from threading import Event
import time
import requests
import os
import unittest

from ycmd.tests.client_test import ClientTest
from ycmd.utils import StartThread

# Time to wait (int seconds) for all the servers to shutdown. Tweak for the CI
# environment.
SUBSERVER_SHUTDOWN_TIMEOUT = 120


class ShutdownTest( ClientTest ):

  @ClientTest.CaptureLogfiles
  def test_FromHandlerWithoutSubserver( self ):
    self.Start()
    self.AssertServersAreRunning()

    try:
      response = self.PostRequest( 'shutdown' )
      response.raise_for_status()
      self.AssertResponse( response )
      assert_that( response.json(), equal_to( True ) )
    except requests.exceptions.ConnectionError:
      pass

    self.AssertServersShutDown( timeout = SUBSERVER_SHUTDOWN_TIMEOUT )
    self.AssertLogfilesAreRemoved()


  @ClientTest.CaptureLogfiles
  def test_FromHandlerWithSubservers( self ):
    self.Start()

    filetypes = [ 'cpp',
                  'cs',
                  'go',
                  'javascript',
                  'typescript',
                  'rust' ]
    for filetype in filetypes:
      self.StartSubserverForFiletype( filetype )
    self.AssertServersAreRunning()

    try:
      response = self.PostRequest( 'shutdown' )
      response.raise_for_status()
      self.AssertResponse( response )
      assert_that( response.json(), equal_to( True ) )
    except requests.exceptions.ConnectionError:
      pass

    self.AssertServersShutDown( timeout = SUBSERVER_SHUTDOWN_TIMEOUT )
    self.AssertLogfilesAreRemoved()


  @ClientTest.CaptureLogfiles
  def test_FromWatchdogWithoutSubserver( self ):
    self.Start( idle_suicide_seconds = 2, check_interval_seconds = 1 )
    self.AssertServersAreRunning()

    self.AssertServersShutDown( timeout = SUBSERVER_SHUTDOWN_TIMEOUT )
    self.AssertLogfilesAreRemoved()


  @ClientTest.CaptureLogfiles
  def test_FromWatchdogWithSubservers( self ):
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
      filetypes = [ 'cpp',
                    'cs',
                    'go',
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


def load_tests( loader: unittest.TestLoader, tests, pattern ):
  suite = unittest.TestSuite()
  test_names = loader.getTestCaseNames( ShutdownTest )
  if os.environ.get( 'YCM_VALGRIND_RUN' ):
    def allowed_tests( name: str ):
      return 'WithoutSubserver' in name
  else:
    def allowed_tests( name: str ):
      return True
  tests = loader.loadTestsFromNames( filter( allowed_tests, test_names ),
                                     ShutdownTest )
  suite.addTests( tests )
  return suite
