# Copyright (C) 2013-2018 ycmd contributors
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

import time
import copy
from threading import Lock
from ycmd.handlers import ServerShutdown
from ycmd.utils import LOGGER, StartThread


# This class implements the Bottle plugin API:
# http://bottlepy.org/docs/dev/plugindev.html
#
# The idea here is to decorate every route handler automatically so that on
# every request, we log when the request was made. Then a watchdog thread checks
# every check_interval_seconds whether the server has been idle for a time
# greater that the passed-in idle_suicide_seconds. If it has, we kill the
# server.
#
# We want to do this so that if something goes bonkers in Vim and the server
# never gets killed by the client, we don't end up with lots of zombie servers.
class WatchdogPlugin( object ):
  name = 'watchdog'
  api = 2

  def __init__( self,
                idle_suicide_seconds,
                check_interval_seconds ):
    self._check_interval_seconds = check_interval_seconds
    self._idle_suicide_seconds = idle_suicide_seconds

    # No need for a lock on wakeup time since only the watchdog thread ever
    # reads or sets it.
    self._last_wakeup_time = time.time()
    self._last_request_time = time.time()
    self._last_request_time_lock = Lock()
    if idle_suicide_seconds <= 0:
      return
    StartThread( self._WatchdogMain )


  def _GetLastRequestTime( self ):
    with self._last_request_time_lock:
      return copy.deepcopy( self._last_request_time )


  def _SetLastRequestTime( self, new_value ):
    with self._last_request_time_lock:
      self._last_request_time = new_value


  def _TimeSinceLastRequest( self ):
    return time.time() - self._GetLastRequestTime()


  def _TimeSinceLastWakeup( self ):
    return time.time() - self._last_wakeup_time


  def _UpdateLastWakeupTime( self ):
    self._last_wakeup_time = time.time()


  def _WatchdogMain( self ):
    while True:
      time.sleep( self._check_interval_seconds )

      # We make sure we don't terminate if we skipped a wakeup time. If we
      # skipped a check, that means the machine probably went to sleep and the
      # client might still actually be up. In such cases, we give it one more
      # wait interval to contact us before we die.
      if ( self._TimeSinceLastRequest() > self._idle_suicide_seconds and
           self._TimeSinceLastWakeup() < 2 * self._check_interval_seconds ):
        LOGGER.info( 'Shutting down server due to inactivity' )
        ServerShutdown()

      self._UpdateLastWakeupTime()


  def __call__( self, callback ):
    def wrapper( *args, **kwargs ):
      self._SetLastRequestTime( time.time() )
      return callback( *args, **kwargs )
    return wrapper
