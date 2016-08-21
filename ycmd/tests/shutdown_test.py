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
from future import standard_library
standard_library.install_aliases()
from builtins import *  # noqa

from hamcrest import assert_that, equal_to

from ycmd.tests.client_test import Client_test


class Shutdown_test( Client_test ):

  @Client_test.CaptureLogfiles
  def FromHandlerWithoutSubserver_test( self ):
    self.Start()
    self.AssertServersAreRunning()

    response = self.PostRequest( 'shutdown' )
    self.AssertResponse( response )
    assert_that( response.json(), equal_to( True ) )
    self.AssertServersShutDown( timeout = 5 )
    self.AssertLogfilesAreRemoved()


  @Client_test.CaptureLogfiles
  def FromHandlerWithSubservers_test( self ):
    self.Start()

    filetypes = [ 'cs',
                  'go',
                  'javascript',
                  'python',
                  'typescript',
                  'rust' ]
    for filetype in filetypes:
      self.StartSubserverForFiletype( filetype )
    self.AssertServersAreRunning()

    response = self.PostRequest( 'shutdown' )
    self.AssertResponse( response )
    assert_that( response.json(), equal_to( True ) )
    self.AssertServersShutDown( timeout = 5 )
    self.AssertLogfilesAreRemoved()


  @Client_test.CaptureLogfiles
  def FromWatchdogWithoutSubserver_test( self ):
    self.Start( idle_suicide_seconds = 2, check_interval_seconds = 1 )
    self.AssertServersAreRunning()

    self.AssertServersShutDown( timeout = 5 )
    self.AssertLogfilesAreRemoved()


  @Client_test.CaptureLogfiles
  def FromWatchdogWithSubservers_test( self ):
    self.Start( idle_suicide_seconds = 5, check_interval_seconds = 1 )

    filetypes = [ 'cs',
                  'go',
                  'javascript',
                  'python',
                  'typescript',
                  'rust' ]
    for filetype in filetypes:
      self.StartSubserverForFiletype( filetype )
    self.AssertServersAreRunning()

    self.AssertServersShutDown( timeout = 15 )
    self.AssertLogfilesAreRemoved()
