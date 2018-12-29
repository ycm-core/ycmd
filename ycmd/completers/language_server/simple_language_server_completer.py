# Copyright (C) 2018 ycmd contributors
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

from ycmd.completers.language_server import language_server_completer as lsc

from ycmd import responses, utils
from ycmd.utils import LOGGER

import threading
import abc
import subprocess


class SimpleLSPCompleter( lsc.LanguageServerCompleter ):
  @abc.abstractmethod
  def GetServerName( self ):
    pass


  @abc.abstractmethod
  def GetCommandLine( self ):
    pass


  def GetCustomSubcommands( self ):
    return {}


  def __init__( self, user_options ):
    super( SimpleLSPCompleter, self ).__init__( user_options )

    self._server_state_mutex = threading.RLock()
    self._server_keep_logfiles = user_options[ 'server_keep_logfiles' ]
    self._stderr_file = None

    self._Reset()


  def _Reset( self ):
    with self._server_state_mutex:
      self.ServerReset()
      self._connection = None
      self._server_handle = None
      if not self._server_keep_logfiles and self._stderr_file:
        utils.RemoveIfExists( self._stderr_file )
        self._stderr_file = None


  def GetConnection( self ):
    with self._server_state_mutex:
      return self._connection


  def DebugInfo( self, request_data ):
    with self._server_state_mutex:
      server = responses.DebugInfoServer( name = self.GetServerName(),
                                          handle = self._server_handle,
                                          executable = self.GetCommandLine(),
                                          logfiles = [ self._stderr_file ],
                                          extras = self.CommonDebugItems() )

    return responses.BuildDebugInfoResponse( name = self.Language(),
                                             servers = [ server ] )


  def Language( self ):
    return self.GetServerName()


  def ServerIsHealthy( self ):
    with self._server_state_mutex:
      return utils.ProcessIsRunning( self._server_handle )


  def StartServer( self, request_data ):
    with self._server_state_mutex:
      LOGGER.info( 'Starting %s: %s',
                   self.GetServerName(),
                   self.GetCommandLine() )

      self._stderr_file = utils.CreateLogfile( '{}_stderr'.format(
        utils.MakeSafeFileNameString( self.GetServerName() ) ) )

      with utils.OpenForStdHandle( self._stderr_file ) as stderr:
        self._server_handle = utils.SafePopen( self.GetCommandLine(),
                                               stdin = subprocess.PIPE,
                                               stdout = subprocess.PIPE,
                                               stderr = stderr )

      self._connection = (
        lsc.StandardIOLanguageServerConnection(
          self._server_handle.stdin,
          self._server_handle.stdout,
          self.GetDefaultNotificationHandler() )
      )

      self._connection.Start()

      try:
        self._connection.AwaitServerConnection()
      except lsc.LanguageServerConnectionTimeout:
        LOGGER.error( '%s failed to start, or did not connect successfully',
                      self.GetServerName() )
        self.Shutdown()
        return False

    LOGGER.info( '%s started', self.GetServerName() )

    return True


  def Shutdown( self ):
    with self._server_state_mutex:
      LOGGER.info( 'Shutting down %s...', self.GetServerName() )

      # Tell the connection to expect the server to disconnect
      if self._connection:
        self._connection.Stop()

      if not self.ServerIsHealthy():
        LOGGER.info( '%s is not running', self.GetServerName() )
        self._Reset()
        return

      LOGGER.info( 'Stopping %s with PID %s',
                   self.GetServerName(),
                   self._server_handle.pid )

      try:
        self.ShutdownServer()

        # By this point, the server should have shut down and terminated. To
        # ensure that isn't blocked, we close all of our connections and wait
        # for the process to exit.
        #
        # If, after a small delay, the server has not shut down we do NOT kill
        # it; we expect that it will shut itself down eventually. This is
        # predominantly due to strange process behaviour on Windows.
        if self._connection:
          self._connection.Close()

        utils.WaitUntilProcessIsTerminated( self._server_handle,
                                            timeout = 15 )

        LOGGER.info( '%s stopped', self.GetServerName() )
      except Exception:
        LOGGER.exception( 'Error while stopping %s', self.GetServerName() )
        # We leave the process running. Hopefully it will eventually die of its
        # own accord.

      # Tidy up our internal state, even if the completer server didn't close
      # down cleanly.
      self._Reset()


  def _RestartServer( self, request_data ):
    with self._server_state_mutex:
      self.Shutdown()
      self._StartAndInitializeServer( request_data )


  def HandleServerCommand( self, request_data, command ):
    return None
