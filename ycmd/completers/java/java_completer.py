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

import logging
import os
import threading
import glob

from shutil import rmtree
from subprocess import PIPE

from ycmd import ( utils, responses )

from ycmd.completers.language_server import language_server_completer

_logger = logging.getLogger( __name__ )

LANGUAGE_SERVER_HOME = os.path.join( os.path.dirname( __file__ ),
                                     '..',
                                     '..',
                                     '..',
                                     'third_party',
                                     'eclipse.jdt.ls',
                                     'org.eclipse.jdt.ls.product',
                                     'target',
                                     'repository')

PATH_TO_JAVA = utils.PathToFirstExistingExecutable( [ 'java' ] )

# TODO: If there are multiple instances of ycmd running, they will _share_ this
# path. I don't think (from memory) that eclipse actually supports that and
# probably aborts
WORKSPACE_PATH_BASE = os.path.join( os.path.dirname( __file__ ),
                                    '..',
                                    '..',
                                    '..',
                                    'third_party',
                                    'eclipse.jdt.ls-workspace' )


def ShouldEnableJavaCompleter():
  _logger.info( 'Looking for java language server (eclipse.jdt.ls)' )
  if not PATH_TO_JAVA:
    _logger.warning( "Not enabling java completion: Couldn't find java" )
    return False

  if not os.path.exists( LANGUAGE_SERVER_HOME ):
    _logger.warning( 'Not using java completion: not installed' )
    return False

  if not _PathToLauncherJar():
    _logger.warning( 'Not using java completion: jdt.ls is not built' )
    return False

  return True


def _PathToLauncherJar():
  # The file name changes between version of eclipse, so we use a glob as
  # recommended by the language server developers. There should only be one.
  # TODO: sort ?
  p = glob.glob(
    os.path.abspath(
      os.path.join(
        LANGUAGE_SERVER_HOME,
        'plugins',
        'org.eclipse.equinox.launcher_*.jar' ) ) )

  _logger.debug( 'Found launchers: {0}'.format( p ) )

  if not p:
    return None

  return p[ 0 ]


def _LauncherConfiguration():
  if utils.OnMac():
    config = 'config_mac'
  elif utils.OnWindows():
    config = 'config_win'
  else:
    config = 'config_linux'

  return os.path.abspath( os.path.join( LANGUAGE_SERVER_HOME, config ) )


class JavaCompleter( language_server_completer.LanguageServerCompleter ):
  def __init__( self, user_options ):
    super( JavaCompleter, self ).__init__( user_options )

    self._server_keep_logfiles = user_options[ 'server_keep_logfiles' ]

    # Used to ensure that starting/stopping of the server is synchronised
    self._server_state_mutex = threading.RLock()

    with self._server_state_mutex:
      self._server = None
      self._server_handle = None
      self._server_stderr = None
      self._workspace_path = os.path.join(
        os.path.abspath( WORKSPACE_PATH_BASE ),
        str( os.getpid() ) )

      self._Reset()

      try :
        self._StartServer()
      except:
        _logger.exception( "The java language server failed to start." )
        self._StopServer()


  def GetServer( self ):
    return self._server


  def SupportedFiletypes( self ):
    return [ 'java' ]


  def DebugInfo( self, request_data ):
    return responses.BuildDebugInfoResponse(
      name = "Java",
      servers = [
        responses.DebugInfoServer(
          name = "Java Language Server",
          handle = self._server_handle,
          executable = LANGUAGE_SERVER_HOME,
          logfiles = [
            self._server_stderr,
            os.path.join( self._workspace_path, '.metadata', '.log' )
          ] )
      ],
      items = [
        responses.DebugInfoItem( 'Workspace Path', self._workspace_path ),
        responses.DebugInfoItem( 'Java Path', PATH_TO_JAVA ),
        responses.DebugInfoItem( 'jdt.ls Path', _PathToLauncherJar() ),
        responses.DebugInfoItem( 'Launcher Config.', _LauncherConfiguration() ),
      ] )


  def Shutdown( self ):
    self._StopServer()


  def ServerIsHealthy( self, request_data = {} ):
    if not self._ServerIsRunning():
      return False

    return True


  def ServerIsReady( self ):
    return ( self.ServerIsHealthy() and
             self._received_ready_message.is_set() and
             super( JavaCompleter, self ).ServerIsReady() )


  def ShouldUseNowInner( self, request_data ):
    if not self.ServerIsReady():
      return False

    return super( JavaCompleter, self ).ShouldUseNowInner( request_data )


  def _Reset( self ):
    if not self._server_keep_logfiles:
      if self._server_stderr:
        utils.RemoveIfExists( self._server_stderr )
        self._server_stderr = None

    self._server_handle = None
    self._received_ready_message = threading.Event()

    try:
      rmtree( self._workspace_path )
    except OSError:
      # We actually just ignore the error because on startup it won't exist
      _logger.exception( 'Failed to remove workspace path: {0}'.format(
        self._workspace_path ) )

    self._server = None

    self._ServerReset()


  def _StartServer( self ):
    with self._server_state_mutex:
      _logger.info( 'Starting JDT Language Server...' )

      command = [
        PATH_TO_JAVA,
        '-Declipse.application=org.eclipse.jdt.ls.core.id1',
        '-Dosgi.bundles.defaultStartLevel=4',
        '-Declipse.product=org.eclipse.jdt.ls.core.product',
        '-Dlog.level=ALL',
        '-jar',
        _PathToLauncherJar(),
        '-configuration',
        _LauncherConfiguration(),
        '-data',
        self._workspace_path
      ]

      _logger.debug( 'Starting java-server with the following command: '
                     '{0}'.format( ' '.join( command ) ) )

      LOGFILE_FORMAT = 'java_language_server_{pid}_{std}_'

      self._server_stderr = utils.CreateLogfile(
          LOGFILE_FORMAT.format( pid = os.getpid(), std = 'stderr' ) )

      with utils.OpenForStdHandle( self._server_stderr ) as stderr:
        self._server_handle = utils.SafePopen( command,
                                               stdin = PIPE,
                                               stdout = PIPE,
                                               stderr = stderr )

      if self._ServerIsRunning():
        _logger.info( 'JDT Language Server started' )
      else:
        _logger.warning( 'JDT Language Server failed to start' )
        return

      self._server = (
        language_server_completer.StandardIOLanguageServerConnection(
          self._server_handle.stdin,
          self._server_handle.stdout,
          self._GetDefaultNotificationHandler() )
      )

      self._server.start()

      try:
        self._server.TryServerConnection()
      except language_server_completer.LanguageServerConnectionTimeout:
        _logger.warn( 'Java language server failed to start, or did not '
                      'connect successfully' )
        self._StopServer()
        return

    self._SendInitialiseAsync()


  def _StopServerCleanly( self ):
    # Try and shutdown cleanly
    if self._ServerIsRunning():
      _logger.info( 'Stopping java server with PID {0}'.format(
                        self._server_handle.pid ) )

      self._ShutdownServer()

      try:
        utils.WaitUntilProcessIsTerminated( self._server_handle,
                                            timeout = 5 )

        if self._server:
          self._server.join()

        _logger.info( 'JDT Language server stopped' )
      except Exception:
        _logger.exception( 'Error while stopping java server' )


  def _StopServerForecefully( self ):
    if self._ServerIsRunning():
      _logger.info( 'Killing java server with PID {0}'.format(
                        self._server_handle.pid ) )

      self._server_handle.terminate()

      try:
        utils.WaitUntilProcessIsTerminated( self._server_handle,
                                            timeout = 5 )

        if self._server:
          self._server.join()

        _logger.info( 'JDT Language server killed' )
      except Exception:
        _logger.exception( 'Error while killing java server' )


  def _StopServer( self ):
    with self._server_state_mutex:
      # We don't use utils.CloseStandardStreams, because the stdin/out is
      # connected to our server connector. Just close stderr.
      if self._server_handle and self._server_handle.stderr:
        self._server_handle.stderr.close()

      # Tell the connection to expect the server to disconnect
      if self._server:
        self._server.stop()

      # Tell the server to exit using the shutdown request.
      self._StopServerCleanly()

      # If the server is still running, e.g. due to erros, kill it
      self._StopServerForecefully()

      # Tidy up our internal state
      self._Reset()


  def GetSubcommandsMap( self ):
    return {
      'RestartServer': ( lambda self, request_data, args:
                            self._RestartServer() ),
      'StopServer': ( lambda self, request_data, args:
                            self._StopServer() ),

      # TODO: We should be able to determine the set of things available from
      # the capabilities supplied on initialise
      'GetDoc': ( lambda self, request_data, args:
                     self.GetDoc( request_data ) ),
      'GetType': ( lambda self, request_data, args:
                     self.GetType( request_data ) ),
      'GoToDeclaration': ( lambda self, request_data, args:
                             self._GoToDeclaration( request_data ) ),
      'GoTo': ( lambda self, request_data, args:
                             self._GoToDeclaration( request_data ) ),
      'GoToDefinition': ( lambda self, request_data, args:
                             self._GoToDeclaration( request_data ) ),
      'GoToReferences': ( lambda self, request_data, args:
                            self._GoToReferences( request_data ) ),
      'FixIt': ( lambda self, request_data, args:
                   self._CodeAction( request_data, args ) ),
      'RefactorRename': ( lambda self, request_data, args:
                            self._Rename( request_data, args ) ),
    }


  def _HandleNotificationInPollThread( self, notification ):
    if notification[ 'method' ] == 'language/status':
      message_type = notification[ 'params' ][ 'type' ]

      if message_type == 'Started':
        _logger.info( 'Java Language Server initialised successfully.' )
        self._received_ready_message.set()

    super( JavaCompleter, self )._HandleNotificationInPollThread( notification )


  def _ConvertNotificationToMessage( self, request_data, notification ):
    if notification[ 'method' ] == 'language/status':
      message = notification[ 'params' ][ 'message' ]
      return responses.BuildDisplayMessageResponse(
        'Initialising Java completer: {0}'.format( message ) )

    return super( JavaCompleter, self )._ConvertNotificationToMessage(
      request_data,
      notification )


  def GetType( self, request_data ):
    hover_response = self._GetHoverResponse( request_data )

    if isinstance( hover_response, list ):
      if len( hover_response ):
        get_type_java = hover_response[ 0 ][ 'value' ]
      else:
        raise RuntimeError( 'No information' )
    else:
      get_type_java = hover_response

    return responses.BuildDisplayMessageResponse( get_type_java )


  def GetDoc( self, request_data ):
    hover_response = self._GetHoverResponse( request_data )

    if isinstance( hover_response, list ):
      if len( hover_response ):
        get_doc_java = ''
        for docstring in hover_response:
          if not isinstance( docstring, dict ):
            get_doc_java += docstring + '\n'
      else:
        raise RuntimeError( 'No information' )
    else:
      get_doc_java = hover_response

    return responses.BuildDisplayMessageResponse( get_doc_java.rstrip() )


  def HandleServerCommand( self, request_data, command ):
    if command[ 'command' ] == "java.apply.workspaceEdit":
      return language_server_completer.WorkspaceEditToFixIt(
        request_data,
        command[ 'arguments' ][ 0 ],
        text = command[ 'title' ] )

    return None


  def _RestartServer( self ):
    with self._server_state_mutex:
      self._StopServer()
      self._StartServer()


  def _ServerIsRunning( self ):
    return utils.ProcessIsRunning( self._server_handle )
