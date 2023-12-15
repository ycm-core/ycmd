# Copyright (C) 2017-2020 ycmd contributors
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

from functools import partial
import abc
import collections
import contextlib
import json
import logging
import os
import socket
import time
import queue
import subprocess
import threading
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer

from ycmd import extra_conf_store, responses, utils
from ycmd.completers.completer import Completer, CompletionsCache
from ycmd.completers.completer_utils import GetFileContents, GetFileLines
from ycmd.utils import LOGGER

from ycmd.completers.language_server import language_server_protocol as lsp

NO_HOVER_INFORMATION = 'No hover information.'

# All timeout values are in seconds
REQUEST_TIMEOUT_COMPLETION = 5
REQUEST_TIMEOUT_INITIALISE = 30
REQUEST_TIMEOUT_COMMAND    = 30
CONNECTION_TIMEOUT         = 5

# Size of the notification ring buffer
MAX_QUEUED_MESSAGES = 250

PROVIDERS_MAP = {
  'codeActionProvider': (
    lambda self, request_data, args: self.GetCodeActions( request_data )
  ),
  'declarationProvider': (
    lambda self, request_data, args: self.GoTo( request_data,
                                                [ 'Declaration' ] )
  ),
  'definitionProvider': (
    lambda self, request_data, args: self.GoTo( request_data, [ 'Definition' ] )
  ),
  ( 'definitionProvider', 'declarationProvider' ): (
    lambda self, request_data, args: self.GoTo( request_data,
                                                [ 'Definition',
                                                  'Declaration' ] )
  ),
  'documentFormattingProvider': (
    lambda self, request_data, args: self.Format( request_data )
  ),
  'executeCommandProvider': (
    lambda self, request_data, args: self.ExecuteCommand( request_data,
                                                          args )
  ),
  'implementationProvider': (
    lambda self, request_data, args: self.GoTo( request_data,
                                                [ 'Implementation' ] )
  ),
  'referencesProvider': (
    lambda self, request_data, args: self.GoTo( request_data,
                                                [ 'References' ] )
  ),
  'renameProvider': (
    lambda self, request_data, args: self.RefactorRename( request_data, args )
  ),
  'typeDefinitionProvider': (
    lambda self, request_data, args: self.GoTo( request_data,
                                                [ 'TypeDefinition' ] )
  ),
  'workspaceSymbolProvider': (
    lambda self, request_data, args: self.GoToSymbol( request_data, args )
  ),
  'documentSymbolProvider': (
    lambda self, request_data, args: self.GoToDocumentOutline( request_data )
  )
}

# Each command is mapped to a list of providers. This allows a command to use
# another provider if the LSP server doesn't support the main one. For instance,
# GoToDeclaration is mapped to the same provider as GoToDefinition if there is
# no declaration provider. A tuple of providers is also allowed for commands
# like GoTo where it's convenient to jump to the declaration if already on the
# definition and vice versa.
DEFAULT_SUBCOMMANDS_MAP = {
  'ExecuteCommand':      [ 'executeCommandProvider' ],
  'FixIt':               [ 'codeActionProvider' ],
  'GoToDefinition':      [ 'definitionProvider' ],
  'GoToDeclaration':     [ 'declarationProvider', 'definitionProvider' ],
  'GoTo':                [ ( 'definitionProvider', 'declarationProvider' ),
                           'definitionProvider' ],
  'GoToType':            [ 'typeDefinitionProvider' ],
  'GoToImplementation':  [ 'implementationProvider' ],
  'GoToReferences':      [ 'referencesProvider' ],
  'RefactorRename':      [ 'renameProvider' ],
  'Format':              [ 'documentFormattingProvider' ],
  'GoToSymbol':          [ 'workspaceSymbolProvider' ],
  'GoToDocumentOutline': [ 'documentSymbolProvider' ],
}


class NoHoverInfoException( Exception ):
  """ Raised instead of RuntimeError for empty hover responses, to allow
      completers to easily distinguish empty hover from other errors."""
  pass # pragma: no cover


class ResponseTimeoutException( Exception ):
  """Raised by LanguageServerConnection if a request exceeds the supplied
  time-to-live."""
  pass # pragma: no cover


class ResponseAbortedException( Exception ):
  """Raised by LanguageServerConnection if a request is canceled due to the
  server shutting down."""
  pass # pragma: no cover


class ResponseFailedException( Exception ):
  """Raised by LanguageServerConnection if a request returns an error"""
  def __init__( self, error ):
    self.error_code = error.get( 'code' ) or 0
    self.error_message = error.get( 'message' ) or "No message"
    super().__init__( f'Request failed: { self.error_code }: '
                      f'{ self.error_message }' )


class IncompatibleCompletionException( Exception ):
  """Internal exception returned when a completion item is encountered which is
  not supported by ycmd, or where the completion item is invalid."""
  pass # pragma: no cover


class LanguageServerConnectionTimeout( Exception ):
  """Raised by LanguageServerConnection if the connection to the server is not
  established with the specified timeout."""
  pass # pragma: no cover


class LanguageServerConnectionStopped( Exception ):
  """Internal exception raised by LanguageServerConnection when the server is
  successfully shut down according to user request."""
  pass # pragma: no cover


class Response:
  """Represents a blocking pending request.

  LanguageServerCompleter handles create an instance of this class for each
  request that expects a response and wait for its response synchronously by
  calling |AwaitResponse|.

  The LanguageServerConnection message pump thread calls |ResponseReceived| when
  the associated response is read, which triggers the |AwaitResponse| method to
  handle the actual response"""

  def __init__( self, response_callback=None ):
    """In order to receive a callback in the message pump thread context, supply
    a method taking ( response, message ) in |response_callback|. Note that
    |response| is _this object_, not the calling object, and message is the
    message that was received. NOTE: This should not normally be used. Instead
    users should synchronously wait on AwaitResponse."""
    self._event = threading.Event()
    self._message = None
    self._response_callback = response_callback


  def ResponseReceived( self, message ):
    """Called by the message pump thread when the response with corresponding ID
    is received from the server. Triggers the message received event and calls
    any configured message-pump-thread callback."""
    self._message = message
    self._event.set()
    if self._response_callback:
      self._response_callback( self, message )


  def Abort( self ):
    """Called when the server is shutting down."""
    self.ResponseReceived( None )


  def AwaitResponse( self, timeout ):
    """Called by clients to wait synchronously for either a response to be
    received or for |timeout| seconds to have passed.
    Returns the message, or:
        - throws ResponseFailedException if the request fails
        - throws ResponseTimeoutException in case of timeout
        - throws ResponseAbortedException in case the server is shut down."""
    self._event.wait( timeout )

    if not self._event.is_set():
      raise ResponseTimeoutException( 'Response Timeout' )

    if self._message is None:
      raise ResponseAbortedException( 'Response Aborted' )

    if 'error' in self._message:
      error = self._message[ 'error' ]
      raise ResponseFailedException( error )

    return self._message


class LanguageServerConnection( threading.Thread ):
  """
  Abstract language server communication object.

  This connection runs as a thread and is generally only used directly by
  LanguageServerCompleter, but is instantiated, started and stopped by
  concrete LanguageServerCompleter implementations.

  Implementations of this class are required to provide the following methods:
    - TryServerConnectionBlocking: Connect to the server and return when the
                                    connection is established
    - Shutdown: Close any sockets or channels prior to the thread exit
    - IsConnected: Whether the socket is connected
    - WriteData: Write some data to the server
    - ReadData: Read some data from the server, blocking until some data is
             available

  Threads:

  LSP is by its nature an asynchronous protocol. There are request-reply like
  requests and unsolicited notifications. Receipt of the latter is mandatory,
  so we cannot rely on there being a bottle thread executing a client request.

  So we need a message pump and dispatch thread. This is actually the
  LanguageServerConnection, which implements Thread. It's main method simply
  listens on the socket/stream and dispatches complete messages to the
  LanguageServerCompleter. It does this:

  - For requests: Using python event objects, wrapped in the Response class
  - For notifications: via a synchronized Queue.

  NOTE: Some handling is done in the dispatch thread. There are certain
  notifications which we have to handle when we get them, such as:

  - Initialization messages
  - Diagnostics

  In these cases, we allow some code to be executed inline within the dispatch
  thread, as there is no other thread guaranteed to execute. These are handled
  by callback functions and mutexes.

  Using this class in concrete LanguageServerCompleter implementations:

  Startup

  - Call Start() and AwaitServerConnection()
  - AwaitServerConnection() throws LanguageServerConnectionTimeout if the
    server fails to connect in a reasonable time.

  Shutdown

  - Call Stop() prior to shutting down the downstream server (see
    LanguageServerCompleter.ShutdownServer to do that part)
  - Call Close() to close any remaining streams. Do this in a request thread.
    DO NOT CALL THIS FROM THE DISPATCH THREAD. That is, Close() must not be
    called from a callback supplied to GetResponseAsync, or in any callback or
    method with a name like "*InPollThread". The result would be a deadlock.

  Footnote: Why does this interface exist?

  Language servers are at liberty to provide their communication interface
  over any transport. Typically, this is either stdio or a socket (though some
  servers require multiple sockets). This interface abstracts the
  implementation detail of the communication from the transport, allowing
  concrete completers to choose the right transport according to the
  downstream server (i.e. Whatever works best).

  If in doubt, use the StandardIOLanguageServerConnection as that is the
  simplest. Socket-based connections often require the server to connect back
  to us, which can lead to complexity and possibly blocking.
  """
  @abc.abstractmethod
  def TryServerConnectionBlocking( self ):
    pass # pragma: no cover


  def _CancelWatchdogThreads( self ):
    for observer in self._observers:
      observer.stop()
      observer.join()


  def Shutdown( self ):
    self._CancelWatchdogThreads()


  @abc.abstractmethod
  def IsConnected( self ):
    pass


  @abc.abstractmethod
  def WriteData( self, data ):
    pass # pragma: no cover


  @abc.abstractmethod
  def ReadData( self, size=-1 ):
    pass # pragma: no cover


  def __init__( self,
                project_directory,
                watchdog_factory,
                workspace_conf_handler,
                notification_handler = None ):
    super().__init__()

    self._watchdog_factory = watchdog_factory
    self._workspace_conf_handler = workspace_conf_handler
    self._project_directory = project_directory
    self._last_id = 0
    self._responses = {}
    self._response_mutex = threading.Lock()
    self._notifications = queue.Queue( maxsize=MAX_QUEUED_MESSAGES )

    self._connection_event = threading.Event()
    self._stop_event = threading.Event()
    self._notification_handler = notification_handler

    self._collector = RejectCollector()
    self._observers = []


  @contextlib.contextmanager
  def CollectApplyEdits( self, collector ):
    old_collector = self._collector
    self._collector = collector
    try:
      yield
    finally:
      self._collector = old_collector


  def run( self ):
    try:
      # Wait for the connection to fully establish (this runs in the thread
      # context, so we block until a connection is received or there is a
      # timeout, which throws an exception)
      self.TryServerConnectionBlocking()
      self._connection_event.set()

      # Blocking loop which reads whole messages and calls _DispatchMessage
      self._ReadMessages()
    except LanguageServerConnectionStopped:
      # Abort any outstanding requests
      with self._response_mutex:
        for _, response in self._responses.items():
          response.Abort()
        self._responses.clear()

      LOGGER.debug( 'Connection was closed cleanly' )
    except Exception:
      LOGGER.exception( 'The language server communication channel closed '
                        'unexpectedly. Issue a RestartServer command to '
                        'recover.' )

      # Abort any outstanding requests
      with self._response_mutex:
        for _, response in self._responses.items():
          response.Abort()
        self._responses.clear()

      # Close any remaining sockets or files
      self.Shutdown()


  def Start( self ):
    # Wraps the fact that this class inherits (privately, in a sense) from
    # Thread.
    self.start()


  def Stop( self ):
    self._stop_event.set()


  def Close( self ):
    self.Shutdown()
    try:
      self.join()
    except RuntimeError:
      LOGGER.exception( "Shutting down dispatch thread while it isn't active" )
      # This actually isn't a problem in practice.


  def IsStopped( self ):
    return self._stop_event.is_set()


  def NextRequestId( self ):
    with self._response_mutex:
      self._last_id += 1
      return self._last_id


  def GetResponseAsync( self, request_id, message, response_callback=None ):
    """Issue a request to the server and return immediately. If a response needs
    to be handled, supply a method taking ( response, message ) in
    response_callback. Note |response| is the instance of Response and message
    is the message received from the server.
    Returns the Response instance created."""
    response = Response( response_callback )

    with self._response_mutex:
      assert request_id not in self._responses
      self._responses[ request_id ] = response

    LOGGER.debug( 'TX: Sending message: %r', message )

    self.WriteData( message )
    return response


  def GetResponse( self, request_id, message, timeout ):
    """Issue a request to the server and await the response. See
    Response.AwaitResponse for return values and exceptions."""
    response = self.GetResponseAsync( request_id, message )
    return response.AwaitResponse( timeout )


  def SendNotification( self, message ):
    """Issue a notification to the server. A notification is "fire and forget";
    no response will be received and nothing is returned."""
    LOGGER.debug( 'TX: Sending notification: %r', message )

    self.WriteData( message )


  def SendResponse( self, message ):
    """Send a response message. This is a message which is not a notification,
    but still requires no further response from the server."""
    LOGGER.debug( 'TX: Sending response: %r', message )

    self.WriteData( message )


  def AwaitServerConnection( self ):
    """Language server completer implementations should call this after starting
    the server and the message pump (Start()) to await successful connection to
    the server being established.

    Returns no meaningful value, but may throw LanguageServerConnectionTimeout
    in the event that the server does not connect promptly. In that case,
    clients should shut down their server and reset their state."""
    self._connection_event.wait( timeout = CONNECTION_TIMEOUT )

    if not self._connection_event.is_set():
      raise LanguageServerConnectionTimeout(
        'Timed out waiting for server to connect' )


  def _ReadMessages( self ):
    """Main message pump. Within the message pump thread context, reads messages
    from the socket/stream by calling self.ReadData in a loop and dispatch
    complete messages by calling self._DispatchMessage.

    When the server is shut down cleanly, raises
    LanguageServerConnectionStopped"""

    data = bytes( b'' )
    while True:
      data, read_bytes, headers = self._ReadHeaders( data )

      if 'Content-Length' not in headers:
        # FIXME: We could try and recover this, but actually the message pump
        # just fails.
        raise ValueError( "Missing 'Content-Length' header" )

      content_length = int( headers[ 'Content-Length' ] )

      # We need to read content_length bytes for the payload of this message.
      # This may be in the remainder of `data`, but equally we may need to read
      # more data from the socket.
      content = bytes( b'' )
      content_read = 0
      if read_bytes < len( data ):
        # There are bytes left in data, use them
        data = data[ read_bytes: ]

        # Read up to content_length bytes from data
        content_to_read = min( content_length, len( data ) )
        content += data[ : content_to_read ]
        content_read += len( content )
        read_bytes = content_to_read

      while content_read < content_length:
        # There is more content to read, but data is exhausted - read more from
        # the socket
        data = self.ReadData( content_length - content_read )
        content_to_read = min( content_length - content_read, len( data ) )
        content += data[ : content_to_read ]
        content_read += len( content )
        read_bytes = content_to_read

      LOGGER.debug( 'RX: Received message: %r', content )

      # lsp will convert content to Unicode
      self._DispatchMessage( lsp.Parse( content ) )

      # We only consumed len( content ) of data. If there is more, we start
      # again with the remainder and look for headers
      data = data[ read_bytes : ]


  def _ReadHeaders( self, data ):
    """Starting with the data in |data| read headers from the stream/socket
    until a full set of headers has been consumed. Returns a tuple (
      - data: any remaining unused data from |data| or the socket
      - read_bytes: the number of bytes of returned data that have been consumed
      - headers: a dictionary whose keys are the header names and whose values
                 are the header values
    )"""
    # LSP defines only 2 headers, of which only 1 is useful (Content-Length).
    # Headers end with an empty line, and there is no guarantee that a single
    # socket or stream read will contain only a single message, or even a whole
    # message.

    headers_complete = False
    prefix = bytes( b'' )
    headers = {}

    while not headers_complete:
      read_bytes = 0
      last_line = 0
      if len( data ) == 0:
        data = self.ReadData()

      while read_bytes < len( data ):
        if utils.ToUnicode( data[ read_bytes: ] )[ 0 ] == '\n':
          line = prefix + data[ last_line : read_bytes ].strip()
          prefix = bytes( b'' )
          last_line = read_bytes

          if not line.strip():
            headers_complete = True
            read_bytes += 1
            break
          else:
            try:
              key, value = utils.ToUnicode( line ).split( ':', 1 )
              headers[ key.strip() ] = value.strip()
            except Exception:
              LOGGER.exception( 'Received invalid protocol data from server: '
                                 + str( line ) )
              raise

        read_bytes += 1

      if not headers_complete:
        prefix = data[ last_line : ]
        data = bytes( b'' )


    return data, read_bytes, headers


  def _HandleDynamicRegistrations( self, request ):
    for reg in request[ 'params' ][ 'registrations' ]:
      if reg[ 'method' ] == 'workspace/didChangeWatchedFiles':
        globs = []
        for watcher in reg[ 'registerOptions' ][ 'watchers' ]:
          # TODO: Take care of watcher kinds. Not everything needs
          # to be watched for create, modify *and* delete actions.
          pattern = os.path.join( self._project_directory,
                                  watcher[ 'globPattern' ] )
          if os.path.isdir( pattern ):
            pattern = os.path.join( pattern, '**' )
          globs.append( pattern )
        observer = Observer()
        observer.schedule( self._watchdog_factory( globs ),
                           self._project_directory,
                           recursive = True )
        observer.start()
        self._observers.append( observer )
    self.SendResponse( lsp.Void( request ) )


  def _ServerToClientRequest( self, request ):
    method = request[ 'method' ]
    try:
      if method == 'workspace/applyEdit':
        self._collector.CollectApplyEdit( request, self )
      elif method == 'workspace/configuration':
        response = self._workspace_conf_handler( request )
        if response is not None:
          self.SendResponse( lsp.Accept( request, response ) )
        else:
          self.SendResponse( lsp.Reject( request, lsp.Errors.MethodNotFound ) )
      elif method == 'client/registerCapability':
        self._HandleDynamicRegistrations( request )
      elif method == 'client/unregisterCapability':
        for reg in request[ 'params' ][ 'unregisterations' ]:
          if reg[ 'method' ] == 'workspace/didChangeWatchedFiles':
            self._CancelWatchdogThreads()
        self.SendResponse( lsp.Void( request ) )
      elif method == 'workspace/workspaceFolders':
        self.SendResponse(
          lsp.Accept( request,
                      lsp.WorkspaceFolders( self._project_directory ) ) )
      else: # method unknown - reject
        self.SendResponse( lsp.Reject( request, lsp.Errors.MethodNotFound ) )
      return
    except Exception:
      LOGGER.exception( "Handling server to client request failed for request "
                        "%s, rejecting it. This is probably a bug in ycmd.",
                        request )

    # unhandled, or failed; reject the request
    self.SendResponse( lsp.Reject( request, lsp.Errors.MethodNotFound ) )

  def _DispatchMessage( self, message ):
    """Called in the message pump thread context when a complete message was
    read. For responses, calls the Response object's ResponseReceived method, or
    for notifications (unsolicited messages from the server), simply accumulates
    them in a Queue which is polled by the long-polling mechanism in
    LanguageServerCompleter."""
    if 'id' in message:
      message_id = message[ 'id' ]
      if message_id is None:
        return
      if 'method' in message:
        # This is a server->client request, which requires a response.
        self._ServerToClientRequest( message )
      else:
        # This is a response to the message with id message[ 'id' ]
        with self._response_mutex:
          assert message_id in self._responses
          self._responses[ message_id ].ResponseReceived( message )
          del self._responses[ message_id ]
    else:
      # This is a notification
      self._AddNotificationToQueue( message )

      # If there is an immediate (in-message-pump-thread) handler configured,
      # call it.
      if self._notification_handler:
        try:
          self._notification_handler( self, message )
        except Exception:
          LOGGER.exception( 'Handling message in poll thread failed: %s',
                            message )


  def _AddNotificationToQueue( self, message ):
    while True:
      try:
        self._notifications.put_nowait( message )
        return
      except queue.Full:
        pass

      # The queue (ring buffer) is full.  This indicates either a slow
      # consumer or the message poll is not running. In any case, rather than
      # infinitely queueing, discard the oldest message and try again.
      try:
        self._notifications.get_nowait()
      except queue.Empty:
        # This is only a theoretical possibility to prevent this thread
        # blocking in the unlikely event that all elements are removed from
        # the queue between put_nowait and get_nowait. Unfortunately, this
        # isn't testable without a debugger, so coverage will show up red.
        pass # pragma: no cover


class StandardIOLanguageServerConnection( LanguageServerConnection ):
  """Concrete language server connection using stdin/stdout to communicate with
  the server. This should be the default choice for concrete completers."""

  def __init__( self,
                project_directory,
                watchdog_factory,
                server_stdin,
                server_stdout,
                workspace_conf_handler,
                notification_handler = None ):
    super().__init__( project_directory,
                      watchdog_factory,
                      workspace_conf_handler,
                      notification_handler )

    self._server_stdin = server_stdin
    self._server_stdout = server_stdout

    # NOTE: All access to the stdin/out objects must be synchronised due to the
    # long-running `read` operations that are done on stdout, and how our
    # shutdown request will come from another (arbitrary) thread. It is not
    # legal in Python to close a stdio file while there is a pending read. This
    # can lead to IOErrors due to "concurrent operations' on files.
    # See https://stackoverflow.com/q/29890603/2327209
    self._stdin_lock = threading.Lock()
    self._stdout_lock = threading.Lock()


  def TryServerConnectionBlocking( self ):
    # standard in/out don't need to wait for the server to connect to us
    return True


  def IsConnected( self ):
    # TODO ? self._server_stdin.closed / self._server_stdout.closed?
    return True


  def Shutdown( self ):
    super().Shutdown()
    with self._stdin_lock:
      if not self._server_stdin.closed:
        self._server_stdin.close()

    with self._stdout_lock:
      if not self._server_stdout.closed:
        self._server_stdout.close()


  def WriteData( self, data ):
    with self._stdin_lock:
      self._server_stdin.write( data )
      self._server_stdin.flush()


  def ReadData( self, size=-1 ):
    data = None
    with self._stdout_lock:
      if not self._server_stdout.closed:
        if size > -1:
          data = self._server_stdout.read( size )
        else:
          data = self._server_stdout.readline()

    if not data:
      # No data means the connection was severed. Connection severed when (not
      # self.IsStopped()) means the server died unexpectedly.
      if self.IsStopped():
        raise LanguageServerConnectionStopped()

      raise RuntimeError( "Connection to server died" )

    return data


class TCPSingleStreamConnection( LanguageServerConnection ):
  # Connection timeout in seconds
  TCP_CONNECT_TIMEOUT = 10

  def __init__( self,
                project_directory,
                watchdog_factory,
                port,
                workspace_conf_handler,
                notification_handler = None ):
    super().__init__( project_directory,
                      watchdog_factory,
                      workspace_conf_handler,
                      notification_handler )

    self.port = port
    self._client_socket = None


  def TryServerConnectionBlocking( self ):
    LOGGER.info( "Connecting to localhost:%s", self.port )
    expiration = time.time() + TCPSingleStreamConnection.TCP_CONNECT_TIMEOUT
    reason = RuntimeError( f"Timeout connecting to port { self.port }" )
    while True:
      if time.time() > expiration:
        LOGGER.error( "Timed out after %s seconds connecting to port %s",
                      TCPSingleStreamConnection.TCP_CONNECT_TIMEOUT,
                      self.port )
        raise reason

      try:
        self._client_socket = socket.create_connection( ( '127.0.0.1',
                                                          self.port ) )
        LOGGER.info( "Language server connection successful on port %s",
                     self.port )
        return True
      except IOError as e:
        reason = e

      time.sleep( 0.1 )

  def IsConnected( self ):
    return bool( self._client_socket )

  def Shutdown( self ):
    super().Shutdown()
    self._client_socket.close()


  def WriteData( self, data ):
    assert self._connection_event.is_set()
    assert self._client_socket

    total_sent = 0
    while total_sent < len( data ):
      try:
        sent = self._client_socket.send( data[ total_sent: ] )
      except OSError:
        sent = 0

      if sent == 0:
        raise RuntimeError( 'Socket was closed when writing' )

      total_sent += sent


  def ReadData( self, size=-1 ):
    assert self._connection_event.is_set()
    assert self._client_socket

    chunks = []
    bytes_read = 0
    while bytes_read < size or size < 0:
      try:
        if size < 0:
          chunk = self._client_socket.recv( 2048 )
        else:
          chunk = self._client_socket.recv( min( size - bytes_read , 2048 ) )
      except OSError:
        chunk = ''

      if chunk == '':
        # The socket was closed
        if self.IsStopped():
          raise LanguageServerConnectionStopped()

        raise RuntimeError( 'Scoket closed unexpectedly when reading' )

      if size < 0:
        # We just return whatever we read
        return chunk

      # Otherwise, keep reading if there's more data requested
      chunks.append( chunk )
      bytes_read += len( chunk )

    return b''.join( chunks )


class LanguageServerCompleter( Completer ):
  """
  Abstract completer implementation for Language Server Protocol. Concrete
  implementations are required to:
    - Handle downstream server state and create a LanguageServerConnection,
      returning it in GetConnection
      - Set its notification handler to self.GetDefaultNotificationHandler()
      - See below for Startup/Shutdown instructions
    - Optionally handle server-specific command responses in
      HandleServerCommandResponse
    - Optionally override GetCustomSubcommands to return subcommand handlers
      that cannot be detected from the capabilities response.
    - Optionally override AdditionalLogFiles for logs other than stderr
    - Optionally override ExtraDebugItems for anything that should be in the
      /debug_info response, that isn't covered by default
    - Optionally override GetServerEnvironment if the server needs to be run
      with specific environment variables.
    - Implement the following Completer abstract methods:
      - GetServerName
      - GetCommandLine
      - SupportedFiletypes
      - DebugInfo
      - Shutdown
      - ServerIsHealthy : Return True if the server is _running_
      - StartServer : Return True if the server was started.
    - Optionally override methods to customise behavior:
      - ConvertNotificationToMessage
      - GetCompleterName
      - GetProjectDirectory
      - GetProjectRootFiles
      - GetTriggerCharacters
      - GetDefaultNotificationHandler
      - HandleNotificationInPollThread
      - Language

  Startup

  - Startup is initiated for you in OnFileReadyToParse
  - The StartServer method is only called once (reset with ServerReset)
  - See also LanguageServerConnection requirements

  Shutdown

  - Call ShutdownServer and wait for the downstream server to exit
  - Call ServerReset to clear down state
  - See also LanguageServerConnection requirements

  Completions

  - The implementation should not require any code to support completions
  - (optional) Override GetCodepointForCompletionRequest if you wish to change
    the completion position (e.g. if you want to pass the "query" to the
    server)

  Diagnostics

  - The implementation should not require any code to support diagnostics

  Sub-commands

  - The sub-commands map is bespoke to the implementation, but generally, this
    class attempts to provide all of the pieces where it can generically.
  - By default, the subcommands are detected from the server's capabilities.
    The logic for this is in DEFAULT_SUBCOMMANDS_MAP (and implemented by
    _DiscoverSubcommandSupport).
  - By default FixIt should work, but for example, jdt.ls doesn't implement
    CodeActions correctly and forces clients to handle it differently.
    For these cases, completers can override any of:
    - CodeActionLiteralToFixIt
    - CodeActionCommandToFixIt
    - CommandToFixIt
  - Other commands not covered by DEFAULT_SUBCOMMANDS_MAP are bespoke to the
    completer and should be returned by GetCustomSubcommands:
    - GetType/GetDoc are bespoke to the downstream server, though this class
      provides GetHoverResponse which is useful in this context.
      GetCustomSubcommands needs not contain GetType/GetDoc if the member
      functions implementing GetType/GetDoc are named GetType/GetDoc.
  """
  def GetConnection( self ):
    """Method that can be implemented by derived classes to return an instance
    of LanguageServerConnection appropriate for the language server in
    question"""
    return self._connection


  def HandleServerCommandResponse( self,
                                   request_data,
                                   edits,
                                   command_response ):
    pass # pragma: no cover


  # Resolve all completion items up-front
  RESOLVE_ALL = True

  # Don't resolve any completion items, but prepare them for resolve
  RESOLVE_NONE = False


  def __init__( self, user_options, connection_type = 'stdio' ):
    super().__init__( user_options )

    self._connection_type = connection_type

    # _server_info_mutex synchronises access to the state of the
    # LanguageServerCompleter object. There are a number of threads at play
    # here which might want to change properties of this object:
    #   - Each client request (handled by concrete completers) executes in a
    #     separate thread and might call methods requiring us to synchronise the
    #     server's view of file state with our own. We protect from clobbering
    #     by doing all server-file-state operations under this mutex.
    #   - There are certain events that we handle in the message pump thread,
    #     like some parts of initialization. We must protect against concurrent
    #     access to our internal state (such as the server file state, and
    #     stored data about the server itself) when we are calling methods on
    #     this object from the message pump). We synchronise on this mutex for
    #     that.
    #   - We need to make sure that multiple client requests don't try to start
    #     or stop the server simultaneously, so we also do all server
    #     start/stop/etc. operations under this mutex
    #   - Acquiring this mutex from the poll thread can lead to deadlocks.
    #     Currently, this is avoided by using _latest_diagnostics_mutex to
    #     access _latest_diagnostics, as that is the only resource shared with
    #     the poll thread.
    self._server_info_mutex = threading.Lock()
    self.ServerReset()

    # LSP allows servers to return an incomplete list of completions. The cache
    # cannot be used in that case and the current column must be sent to the
    # language server for the subsequent completion requests; otherwise, the
    # server will return the same incomplete list. When that list is complete,
    # two cases are considered:
    #  - the starting column was sent to the server: cache is valid for the
    #    whole completion;
    #  - the current column was sent to the server: cache stays valid while the
    #    cached query is a prefix of the subsequent queries.
    self._completions_cache = LanguageServerCompletionsCache()

    self._completer_name = self.__class__.__name__.replace( 'Completer', '' )
    self._language = self._completer_name.lower()

    self._on_file_ready_to_parse_handlers = []
    self.RegisterOnFileReadyToParse(
      lambda self, request_data:
        self._UpdateServerWithFileContents( request_data ),
      True # once
    )

    self._signature_help_disabled = user_options[ 'disable_signature_help' ]

    self._server_keep_logfiles = user_options[ 'server_keep_logfiles' ]
    self._stdout_file = None
    self._stderr_file = None
    self._server_started = False

    self._Reset()


  def _Reset( self ):
    self.ServerReset()
    self._connection = None
    self._server_handle = None
    if not self._server_keep_logfiles and self._stdout_file:
      utils.RemoveIfExists( self._stdout_file )
      self._stdout_file = None
    if not self._server_keep_logfiles and self._stderr_file:
      utils.RemoveIfExists( self._stderr_file )
      self._stderr_file = None


  def ServerReset( self ):
    """Clean up internal state related to the running server instance.
    Implementations are required to call this after disconnection and killing
    the downstream server."""
    self._server_file_state = lsp.ServerFileStateStore()
    self._latest_diagnostics_mutex = threading.Lock()
    self._latest_diagnostics = collections.defaultdict( list )
    self._sync_type = 'Full'
    self._initialize_response = None
    self._initialize_event = threading.Event()
    self._on_initialize_complete_handlers = []
    self._server_capabilities = None
    self._is_completion_provider = False
    self._resolve_completion_items = False
    self._project_directory = None
    self._settings = {}
    self._extra_conf_dir = None
    self._semantic_token_atlas = None


  def GetCompleterName( self ):
    return self._completer_name


  def Language( self ):
    return self._language


  def StartServer( self, request_data ):
    try:
      with self._server_info_mutex:
        return self._StartServerNoLock( request_data )
    except LanguageServerConnectionTimeout:
      LOGGER.error( '%s failed to start, or did not connect successfully',
                    self.GetServerName() )
      self.Shutdown()
      return False


  def _StartServerNoLock( self, request_data ):
    LOGGER.info( 'Starting %s: %s',
                 self.GetServerName(),
                 self.GetCommandLine() )

    self._project_directory = self.GetProjectDirectory( request_data )

    if self._connection_type == 'tcp':
      if self.GetCommandLine():
        self._stderr_file = utils.CreateLogfile(
          f'{ utils.MakeSafeFileNameString( self.GetServerName() ) }_stderr' )
        self._stdout_file = utils.CreateLogfile(
          f'{ utils.MakeSafeFileNameString( self.GetServerName() ) }_stdout' )

        with utils.OpenForStdHandle( self._stderr_file ) as stderr:
          with utils.OpenForStdHandle( self._stdout_file ) as stdout:
            self._server_handle = utils.SafePopen(
              self.GetCommandLine(),
              stdin = subprocess.PIPE,
              stdout = stdout,
              stderr = stderr,
              env = self.GetServerEnvironment() )

      self._connection = TCPSingleStreamConnection(
        self._project_directory,
        lambda globs: WatchdogHandler( self, globs ),
        self._port,
        lambda request: self.WorkspaceConfigurationResponse( request ),
        self.GetDefaultNotificationHandler() )
    else:
      self._stderr_file = utils.CreateLogfile(
        f'{ utils.MakeSafeFileNameString( self.GetServerName() ) }_stderr' )

      with utils.OpenForStdHandle( self._stderr_file ) as stderr:
        self._server_handle = utils.SafePopen(
          self.GetCommandLine(),
          stdin = subprocess.PIPE,
          stdout = subprocess.PIPE,
          stderr = stderr,
          env = self.GetServerEnvironment() )

      self._connection = (
        StandardIOLanguageServerConnection(
          self._project_directory,
          lambda globs: WatchdogHandler( self, globs ),
          self._server_handle.stdin,
          self._server_handle.stdout,
          lambda request: self.WorkspaceConfigurationResponse( request ),
          self.GetDefaultNotificationHandler() )
      )

    self._connection.Start()

    self._connection.AwaitServerConnection()

    if self._server_handle:
      LOGGER.info( '%s started with PID %s',
                   self.GetServerName(),
                   self._server_handle.pid )

    return True


  def Shutdown( self ):
    with self._server_info_mutex:
      LOGGER.info( 'Shutting down %s...', self.GetServerName() )

      # Tell the connection to expect the server to disconnect
      if self._connection:
        self._connection.Stop()

      if not self.ServerIsHealthy():
        LOGGER.info( '%s is not running', self.GetServerName() )
        self._Reset()
        return

      if self._server_handle:
        LOGGER.info( 'Stopping %s with PID %s',
                     self.GetServerName(),
                     self._server_handle.pid )

    try:
      with self._server_info_mutex:
        self.ShutdownServer()

      # By this point, the server should have shut down and terminated. To
      # ensure that isn't blocked, we close all of our connections and wait
      # for the process to exit.
      #
      # If, after a small delay, the server has not shut down we do NOT kill
      # it; we expect that it will shut itself down eventually. This is
      # predominantly due to strange process behaviour on Windows.

      # NOTE: While waiting for the connection to close, we must _not_ hold any
      # locks (in fact, we must not hold locks that might be needed when
      # processing messages in the poll thread - i.e. notifications).
      # This is crucial, as the server closing (asynchronously) might
      # involve _other activities_ if there are messages in the queue (e.g. on
      # the socket) and we need to store/handle them in the message pump
      # (such as notifications) or even the initialise response.
      if self._connection:
        # Actually this sits around waiting for the connection thraed to exit
        self._connection.Close()

      if self._server_handle:
        for stream in [ self._server_handle.stdout,
                        self._server_handle.stdin ]:
          if stream and not stream.closed:
            stream.close()

        with self._server_info_mutex:
          utils.WaitUntilProcessIsTerminated( self._server_handle,
                                              timeout = 30 )

        LOGGER.info( '%s stopped', self.GetServerName() )
    except Exception:
      LOGGER.exception( 'Error while stopping %s', self.GetServerName() )
      # We leave the process running. Hopefully it will eventually die of its
      # own accord.

    with self._server_info_mutex:
      # Tidy up our internal state, even if the completer server didn't close
      # down cleanly.
      self._Reset()


  def ShutdownServer( self ):
    """Send the shutdown and possibly exit request to the server.
    Implementations must call this prior to closing the LanguageServerConnection
    or killing the downstream server."""

    # Language server protocol requires orderly shutdown of the downstream
    # server by first sending a shutdown request, and on its completion sending
    # and exit notification (which does not receive a response). Some buggy
    # servers exit on receipt of the shutdown request, so we handle that too.
    if self._ServerIsInitialized():
      request_id = self.GetConnection().NextRequestId()
      msg = lsp.Shutdown( request_id )

      try:
        self.GetConnection().GetResponse( request_id,
                                          msg,
                                          REQUEST_TIMEOUT_INITIALISE )
      except ResponseAbortedException:
        # When the language server (heinously) dies handling the shutdown
        # request, it is aborted. Just return - we're done.
        return
      except Exception:
        # Ignore other exceptions from the server and send the exit request
        # anyway
        LOGGER.exception( 'Shutdown request failed. Ignoring' )

    if self.ServerIsHealthy():
      self.GetConnection().SendNotification( lsp.Exit() )

    # If any threads are waiting for the initialize exchange to complete,
    # release them, as there is no chance of getting a response now.
    if ( self._initialize_response is not None and
         not self._initialize_event.is_set() ):
      self._initialize_response = None
      self._initialize_event.set()


  def _RestartServer( self, request_data, *args, **kwargs ):
    self.Shutdown()
    self._StartAndInitializeServer( request_data, *args, **kwargs )


  def _ServerIsInitialized( self ):
    """Returns True if the server is running and the initialization exchange has
    completed successfully. Implementations must not issue requests until this
    method returns True."""
    if not self.ServerIsHealthy():
      return False

    if self._initialize_event.is_set():
      # We already got the initialize response
      return True

    if self._initialize_response is None:
      # We never sent the initialize response
      return False

    # Initialize request in progress. Will be handled asynchronously.
    return False


  def ServerIsHealthy( self ):
    if not self.GetCommandLine():
      return self._connection and self._connection.IsConnected()
    else:
      return utils.ProcessIsRunning( self._server_handle )


  def ServerIsReady( self ):
    return self._ServerIsInitialized()


  def ShouldUseNowInner( self, request_data ):
    # We should only do _anything_ after the initialize exchange has completed.
    return ( self.ServerIsReady() and
             super().ShouldUseNowInner( request_data ) )


  def GetCodepointForCompletionRequest( self, request_data ):
    """Returns the 1-based codepoint offset on the current line at which to make
    the completion request"""
    return self._completions_cache.GetCodepointForCompletionRequest(
      request_data )


  def ComputeCandidatesInner( self, request_data, codepoint ):
    if not self._is_completion_provider:
      return None, False

    self._UpdateServerWithCurrentFileContents( request_data )

    request_id = self.GetConnection().NextRequestId()

    msg = lsp.Completion( request_id, request_data, codepoint )
    response = self.GetConnection().GetResponse( request_id,
                                                 msg,
                                                 REQUEST_TIMEOUT_COMPLETION )
    result = response.get( 'result' ) or []

    if isinstance( result, list ):
      items = result
      is_incomplete = False
    else:
      items = result[ 'items' ]
      is_incomplete = result[ 'isIncomplete' ]

    # Note: _CandidatesFromCompletionItems does a lot of work on the actual
    # completion text to ensure that the returned text and start_codepoint are
    # applicable to our model of a single start column.
    #
    # Unfortunately (perhaps) we have to do this both here and in
    # DetailCandidates when resolve is required. This is because the filtering
    # should be based on ycmd's version of the insertion_text. Fortunately it's
    # likely much quicker to do the simple calculations inline rather than a
    # series of potentially many blocking server round trips.
    return ( self._CandidatesFromCompletionItems(
              items,
              LanguageServerCompleter.RESOLVE_NONE,
              request_data ),
            is_incomplete )


  def _GetCandidatesFromSubclass( self, request_data ):
    cache_completions = self._completions_cache.GetCompletionsIfCacheValid(
      request_data )

    if cache_completions:
      return cache_completions

    codepoint = self.GetCodepointForCompletionRequest( request_data )
    raw_completions, is_incomplete = self.ComputeCandidatesInner( request_data,
                                                                  codepoint )
    self._completions_cache.Update( request_data,
                                    raw_completions,
                                    is_incomplete )
    return raw_completions


  def DetailCandidates( self, request_data, completions ):
    if not self._resolve_completion_items:
      return completions

    if not self.ShouldDetailCandidateList( completions ):
      return completions

    # Note: _CandidatesFromCompletionItems does a lot of work on the actual
    # completion text to ensure that the returned text and start_codepoint are
    # applicable to our model of a single start column.
    #
    # While we did this before, this time round we will have much better data to
    # do it on, and the new calculated value is dependent on the set of filtered
    # data, possibly leading to significantly smaller overlap with existing
    # text. See the fixup algorithm for more details on that.
    return self._CandidatesFromCompletionItems(
      [ c[ 'extra_data' ][ 'item' ] for c in completions ],
      LanguageServerCompleter.RESOLVE_ALL,
      request_data )


  def DetailSingleCandidate( self, request_data, completions, to_resolve ):
    completion = completions[ to_resolve ]
    if not self._resolve_completion_items:
      return completion

    return self._CandidatesFromCompletionItems(
      [ completion[ 'extra_data' ][ 'item' ] ],
      LanguageServerCompleter.RESOLVE_ALL,
      request_data )[ 0 ]


  def _ResolveCompletionItem( self, item ):
    try:
      resolve_id = self.GetConnection().NextRequestId()
      resolve = lsp.ResolveCompletion( resolve_id, item )
      response = self.GetConnection().GetResponse(
        resolve_id,
        resolve,
        REQUEST_TIMEOUT_COMPLETION )
      item.clear()
      item.update( response[ 'result' ] )
    except ResponseFailedException:
      LOGGER.exception( 'A completion item could not be resolved. Using '
                        'basic data' )

    return item


  def _ShouldResolveCompletionItems( self ):
    # We might not actually need to issue the resolve request if the server
    # claims that it doesn't support it. However, we still might need to fix up
    # the completion items.
    return ( self._server_capabilities.get( 'completionProvider' ) or {} ).get(
      'resolveProvider', False )


  def _CandidatesFromCompletionItems( self,
                                      items,
                                      resolve_completions,
                                      request_data ):
    """Issue the resolve request for each completion item in |items|, then fix
    up the items such that a single start codepoint is used."""

    #
    # Important note on the following logic:
    #
    # Language server protocol requires that clients support textEdits in
    # completion items. It imposes some restrictions on the textEdit, namely:
    #   * the edit range must cover at least the original requested position,
    #   * and that it is on a single line.
    #
    # We only get textEdits (usually) for items which were successfully
    # resolved. Otherwise we just get insertion text, which might overlap the
    # existing text.
    #
    # Importantly there is no restriction that all edits start and end at the
    # same point.
    #
    # ycmd protocol only supports a single start column, so we must post-process
    # the completion items to work out a single start column to use, as follows:
    #   * read all completion items text and start codepoint and store them
    #   * store the minimum start codepoint encountered
    #   * go back through the completion items and modify them so that they
    #     contain enough text to start from the minimum start codepoint
    #   * set the completion start codepoint to the minimum start point
    #
    # The last part involves reading the original source text and padding out
    # completion items so that they all start at the same point.
    #
    # This is neither particularly pretty nor efficient, but it is necessary.
    # Significant completions, such as imports, do not work without it in
    # jdt.ls.
    #
    completions = []
    start_codepoints = []
    unique_start_codepoints = []
    min_start_codepoint = request_data[ 'start_codepoint' ]

    # First generate all of the completion items and store their
    # start_codepoints. Then, we fix-up the completion texts to use the
    # earliest start_codepoint by borrowing text from the original line.
    for idx, item in enumerate( items ):
      this_tem_is_resolved = item.get( '_resolved', False )

      if ( resolve_completions and
           not this_tem_is_resolved and
           self._resolve_completion_items ):
        self._ResolveCompletionItem( item )
        item[ '_resolved' ] = True
        this_tem_is_resolved = True

      try:
        insertion_text, extra_data, start_codepoint = (
          _InsertionTextForItem( request_data, item ) )
      except IncompatibleCompletionException:
        LOGGER.exception( 'Ignoring incompatible completion suggestion %s',
                          item )
        continue

      if not resolve_completions and self._resolve_completion_items:
        extra_data = {} if extra_data is None else extra_data

        # Deferred resolve - the client must read this and send the
        # /resolve_completion request to update the candidate set
        extra_data[ 'resolve' ] = idx

        # Store the actual item in the extra_data area of the completion item.
        # We'll use this later to do the resolve.
        extra_data[ 'item' ] = item

      min_start_codepoint = min( min_start_codepoint, start_codepoint )

      # Build a ycmd-compatible completion for the text as we received it. Later
      # we might modify insertion_text should we see a lower start codepoint.
      completions.append( _CompletionItemToCompletionData(
        insertion_text,
        item,
        extra_data ) )
      start_codepoints.append( start_codepoint )
      if start_codepoint not in unique_start_codepoints:
        unique_start_codepoints.append( start_codepoint )

    if ( len( completions ) > 1 and
         len( unique_start_codepoints ) > 1 and
         min_start_codepoint != request_data[ 'start_codepoint' ] ):
      # We need to fix up the completions, go do that
      return _FixUpCompletionPrefixes( completions,
                                       start_codepoints,
                                       request_data,
                                       min_start_codepoint )

    request_data[ 'start_codepoint' ] = min_start_codepoint
    return completions


  def SignatureHelpAvailable( self ):
    if self._signature_help_disabled:
      return responses.SignatureHelpAvailalability.NOT_AVAILABLE

    if not self.ServerIsReady():
      return responses.SignatureHelpAvailalability.PENDING

    if _IsCapabilityProvided( self._server_capabilities,
                              'signatureHelpProvider' ):
      return responses.SignatureHelpAvailalability.AVAILABLE
    else:
      return responses.SignatureHelpAvailalability.NOT_AVAILABLE


  def ComputeSignaturesInner( self, request_data ):
    if not self.ServerIsReady():
      return {}

    if not _IsCapabilityProvided( self._server_capabilities,
                                  'signatureHelpProvider' ):
      return {}

    self._UpdateServerWithCurrentFileContents( request_data )

    request_id = self.GetConnection().NextRequestId()
    msg = lsp.SignatureHelp( request_id, request_data )
    response = self.GetConnection().GetResponse( request_id,
                                                 msg,
                                                 REQUEST_TIMEOUT_COMPLETION )

    result = response[ 'result' ]
    if result is None:
      return {}

    for sig in result[ 'signatures' ]:
      sig_label = sig[ 'label' ]
      end = 0
      if sig.get( 'parameters' ) is None:
        sig[ 'parameters' ] = []
      for arg in sig[ 'parameters' ]:
        arg_label = arg[ 'label' ]
        if not isinstance( arg_label, list ):
          begin = sig[ 'label' ].find( arg_label, end )
          end = begin + len( arg_label )
        else:
          begin, end = arg_label
        arg[ 'label' ] = [
          utils.CodepointOffsetToByteOffset( sig_label, begin + 1 ) - 1,
          utils.CodepointOffsetToByteOffset( sig_label, end + 1 ) - 1 ]
    result.setdefault( 'activeParameter', 0 )
    result.setdefault( 'activeSignature', 0 )
    return result


  def ComputeSemanticTokens( self, request_data ):
    if not self._initialize_event.wait( REQUEST_TIMEOUT_COMPLETION ):
      return {}

    if not self._ServerIsInitialized():
      return {}

    if not self._semantic_token_atlas:
      return {}

    range_supported = _IsCapabilityProvided(
        self._server_capabilities[ 'semanticTokensProvider' ],
        'range' )

    self._UpdateServerWithCurrentFileContents( request_data )

    request_id = self.GetConnection().NextRequestId()
    body = lsp.SemanticTokens( request_id, range_supported, request_data )

    for _ in RetryOnFailure( [ lsp.Errors.ContentModified ] ):
      response = self._connection.GetResponse(
        request_id,
        body,
        3 * REQUEST_TIMEOUT_COMPLETION )

    if response is None:
      return {}

    filename = request_data[ 'filepath' ]
    contents = GetFileLines( request_data, filename )
    result = response.get( 'result' ) or {}
    tokens = _DecodeSemanticTokens( self._semantic_token_atlas,
                                    result.get( 'data' ) or [],
                                    filename,
                                    contents )

    return {
      'tokens': tokens
    }


  def ComputeInlayHints( self, request_data ):
    if not self._initialize_event.wait( REQUEST_TIMEOUT_COMPLETION ):
      return []

    if not self._ServerIsInitialized():
      return []

    if not _IsCapabilityProvided( self._server_capabilities,
                                  'inlayHintProvider' ):
      return []

    self._UpdateServerWithCurrentFileContents( request_data )
    request_id = self.GetConnection().NextRequestId()
    body = lsp.InlayHints( request_id, request_data )

    for _ in RetryOnFailure( [ lsp.Errors.ContentModified ] ):
      response = self._connection.GetResponse(
        request_id,
        body,
        3 * REQUEST_TIMEOUT_COMPLETION )

    if response is None:
      return []

    file_contents = GetFileLines( request_data, request_data[ 'filepath' ] )

    def BuildLabel( label_or_labels ):
      if isinstance( label_or_labels, list ):
        return ' '.join( label[ 'value' ] for label in label_or_labels )
      return label_or_labels

    def BuildInlayHint( inlay_hint: dict ):
      try:
        kind = lsp.INLAY_HINT_KIND[ inlay_hint[ 'kind' ] ]
      except KeyError:
        kind = 'Unknown'

      return {
        'kind': kind,
        'position': responses.BuildLocationData(
          _BuildLocationAndDescription(
            request_data[ 'filepath' ],
            file_contents,
            inlay_hint[ 'position' ] )[ 0 ]
        ),
        'label': BuildLabel( inlay_hint[ 'label' ] ),
        'paddingLeft': inlay_hint.get( 'paddingLeft', False ),
        'paddingRight': inlay_hint.get( 'paddingRight', False ),
      }

    return [ BuildInlayHint( h ) for h in response.get( 'result' ) or [] ]


  def GetDetailedDiagnostic( self, request_data ):
    self._UpdateServerWithFileContents( request_data )

    current_line_lsp = request_data[ 'line_num' ] - 1
    current_file = request_data[ 'filepath' ]

    if not self._latest_diagnostics:
      return responses.BuildDisplayMessageResponse(
          'Diagnostics are not ready yet.' )

    with self._latest_diagnostics_mutex:
      diagnostics = list( self._latest_diagnostics[
          lsp.FilePathToUri( current_file ) ] )

    if not diagnostics:
      return responses.BuildDisplayMessageResponse(
          'No diagnostics for current file.' )

    current_column = lsp.CodepointsToUTF16CodeUnits(
        GetFileLines( request_data, current_file )[ current_line_lsp ],
        request_data[ 'column_codepoint' ] )
    minimum_distance = None

    message = 'No diagnostics for current line.'
    for diagnostic in diagnostics:
      start = diagnostic[ 'range' ][ 'start' ]
      end = diagnostic[ 'range' ][ 'end' ]
      if current_line_lsp < start[ 'line' ] or end[ 'line' ] < current_line_lsp:
        continue
      point = { 'line': current_line_lsp, 'character': current_column }
      distance = _DistanceOfPointToRange( point, diagnostic[ 'range' ] )
      if minimum_distance is None or distance < minimum_distance:
        message = diagnostic[ 'message' ]
        try:
          code = diagnostic[ 'code' ]
          message += f' [{ code }]'
        except KeyError:
          pass

        if distance == 0:
          break
        minimum_distance = distance

    return responses.BuildDisplayMessageResponse( message )


  @abc.abstractmethod
  def GetServerName( self ):
    """ A string representing a human readable name of the server."""
    pass # pragma: no cover


  def GetServerEnvironment( self ):
    """ None or a dictionary containing the environment variables. """
    return None


  @abc.abstractmethod
  def GetCommandLine( self ):
    """ An override in a concrete class needs to return a list of cli arguments
        for starting the LSP server."""
    pass # pragma: no cover


  def WorkspaceConfigurationResponse( self, request ):
    """If the concrete completer wants to respond to workspace/configuration
       requests, it should override this method."""
    return None


  def ExtraCapabilities( self ):
    """ If the server is a special snowflake that need special attention,
        override this to supply special snowflake capabilities."""
    return {}


  def AdditionalLogFiles( self ):
    """ Returns the list of server logs other than stderr. """
    return []


  def ExtraDebugItems( self, request_data ):
    """ A list of DebugInfoItems """
    return []


  def DebugInfo( self, request_data ):
    with self._server_info_mutex:
      extras = self.CommonDebugItems() + self.ExtraDebugItems( request_data )
      logfiles = [ self._stdout_file,
                   self._stderr_file ] + self.AdditionalLogFiles()
      server = responses.DebugInfoServer(
        name = self.GetServerName(),
        handle = self._server_handle,
        executable = self.GetCommandLine(),
        port = self._port if self._connection_type == 'tcp' else None,
        logfiles = logfiles,
        extras = extras )

    return responses.BuildDebugInfoResponse( name = self.GetCompleterName(),
                                             servers = [ server ] )


  def GetCustomSubcommands( self ):
    """Return a list of subcommand definitions to be used in conjunction with
    the subcommands detected by _DiscoverSubcommandSupport. The return is a dict
    whose keys are the subcommand and whose values are either:
       - a callable, as compatible with GetSubcommandsMap, or
       - a dict, compatible with DEFAULT_SUBCOMMANDS_MAP including a checker and
         a callable.
    If there are no custom subcommands, an empty dict should be returned."""
    return {}


  def GetSubcommandsMap( self ):
    commands = {}
    commands.update( DEFAULT_SUBCOMMANDS_MAP )
    commands.update( {
      'StopServer': (
        lambda self, request_data, args: self.Shutdown()
      ),
      'RestartServer': (
        lambda self, request_data, args: self._RestartServer( request_data )
      ),
    } )

    if hasattr( self, 'GetDoc' ):
      commands[ 'GetDoc' ] = (
        lambda self, request_data, args: self.GetDoc( request_data )
      )
    if hasattr( self, 'GetType' ):
      commands[ 'GetType' ] = (
        lambda self, request_data, args: self.GetType( request_data )
      )

    if ( self._server_capabilities and
         _IsCapabilityProvided( self._server_capabilities,
                                'callHierarchyProvider' ) ):
      commands[ 'GoToCallees' ] = (
        lambda self, request_data, args:
            self.CallHierarchy( request_data, [ 'outgoing' ] )
      )
      commands[ 'GoToCallers' ] = (
        lambda self, request_data, args:
            self.CallHierarchy( request_data, [ 'incoming' ] )
      )

    commands.update( self.GetCustomSubcommands() )

    return self._DiscoverSubcommandSupport( commands )


  def _GetSubcommandProvider( self, provider_list ):
    if not self._server_capabilities:
      LOGGER.warning( "Can't determine subcommands: not initialized yet" )
      capabilities = {}
    else:
      capabilities = self._server_capabilities

    for providers in provider_list:
      if isinstance( providers, tuple ):
        if all( _IsCapabilityProvided( capabilities, provider )
                for provider in providers ):
          return providers
      if _IsCapabilityProvided( capabilities, providers ):
        return providers
    return None


  def _DiscoverSubcommandSupport( self, commands ):
    subcommands_map = {}
    for command, handler in commands.items():
      if isinstance( handler, list ):
        provider = self._GetSubcommandProvider( handler )
        if provider:
          LOGGER.info( 'Found %s support for command %s in %s',
                        provider,
                        command,
                        self.Language() )

          subcommands_map[ command ] = PROVIDERS_MAP[ provider ]
        else:
          LOGGER.info( 'No support for %s command in server for %s',
                        command,
                        self.Language() )
      else:
        LOGGER.info( 'Always supporting %s for %s',
                      command,
                      self.Language() )
        subcommands_map[ command ] = handler

    return subcommands_map


  def DefaultSettings( self, request_data ):
    return {}


  def _GetSettingsFromExtraConf( self, request_data ):
    # The DefaultSettings method returns only the 'language server" ('ls')
    # settings, but self._settings is a wider dict containing a 'ls' key and any
    # other keys that we might want to add (e.g. 'project_directory',
    # 'capabilities', etc.)
    merged_ls_settings = self.DefaultSettings( request_data )

    # If there is no extra-conf, the total settings are just the defaults:
    self._settings = {
      'ls': merged_ls_settings
    }

    module = extra_conf_store.ModuleForSourceFile( request_data[ 'filepath' ] )
    if module:
      # The user-defined settings may contain a 'ls' key, which override (merge
      # with) the DefaultSettings, and any other keys we specify generically for
      # all LSP-based completers (such as 'project_directory').
      user_settings = self.GetSettings( module, request_data )

      # Merge any user-supplied 'ls' settings with the defaults
      if 'ls' in user_settings:
        merged_ls_settings.update( user_settings[ 'ls' ] )

      user_settings[ 'ls' ] = merged_ls_settings
      self._settings = user_settings

      # Only return the dir if it was found in the paths; we don't want to use
      # the path of the global extra conf as a project root dir.
      if not extra_conf_store.IsGlobalExtraConfModule( module ):
        LOGGER.debug( 'Using path %s for extra_conf_dir',
                      os.path.dirname( module.__file__ ) )
        return os.path.dirname( module.__file__ )

    # No local extra conf
    return None


  def _StartAndInitializeServer( self, request_data, *args, **kwargs ):
    """Starts the server and sends the initialize request, assuming the start is
    successful. |args| and |kwargs| are passed through to the underlying call to
    StartServer. In general, completers don't need to call this as it is called
    automatically in OnFileReadyToParse, but this may be used in completer
    subcommands that require restarting the underlying server."""
    self._server_started = False
    self._extra_conf_dir = self._GetSettingsFromExtraConf( request_data )

    # Only attempt to start the server once. Set this after above call as it may
    # throw an exception
    self._server_started = True

    if self.StartServer( request_data, *args, **kwargs ):
      self._SendInitialize( request_data )


  def OnFileReadyToParse( self, request_data ):
    if not self.ServerIsHealthy() and not self._server_started:
      # We have to get the settings before starting the server, as this call
      # might throw UnknownExtraConf.
      self._StartAndInitializeServer( request_data )

    if not self.ServerIsHealthy():
      return

    def ClearOneshotHandlers():
      self._on_file_ready_to_parse_handlers = [
        ( handler, once ) for handler, once
        in self._on_file_ready_to_parse_handlers if not once
      ]

    # If we haven't finished initializing yet, we need to queue up all functions
    # registered on the FileReadyToParse event and in particular
    # _UpdateServerWithFileContents in reverse order of registration. This
    # ensures that the server is up to date as soon as we are able to send more
    # messages. This is important because server start up can be quite slow and
    # we must not block the user, while we must keep the server synchronized.
    if not self._initialize_event.is_set():
      for handler, _ in reversed( self._on_file_ready_to_parse_handlers ):
        self._OnInitializeComplete( partial( handler,
                                             request_data = request_data ) )
      ClearOneshotHandlers()
      return

    for handler, _ in reversed( self._on_file_ready_to_parse_handlers ):
      handler( self, request_data )
    ClearOneshotHandlers()

    # Return the latest diagnostics that we have received.
    #
    # NOTE: We also return diagnostics asynchronously via the long-polling
    # mechanism to avoid timing issues with the servers asynchronous publication
    # of diagnostics.
    #
    # However, we _also_ return them here to refresh diagnostics after, say
    # changing the active file in the editor, or for clients not supporting the
    # polling mechanism.
    filepath = request_data[ 'filepath' ]
    uri = lsp.FilePathToUri( filepath )
    contents = GetFileLines( request_data, filepath )
    with self._latest_diagnostics_mutex:
      if uri in self._latest_diagnostics:
        diagnostics = [ _BuildDiagnostic( contents, uri, diag )
                        for diag in self._latest_diagnostics[ uri ] ]
        return responses.BuildDiagnosticResponse(
          diagnostics, filepath, self.max_diagnostics_to_display )


  def PollForMessagesInner( self, request_data, timeout ):
    # If there are messages pending in the queue, return them immediately
    messages = self._GetPendingMessages( request_data )
    if messages:
      return messages

    # Otherwise, block until we get one or we hit the timeout.
    return self._AwaitServerMessages( request_data, timeout )


  def _GetPendingMessages( self, request_data ):
    """Convert any pending notifications to messages and return them in a list.
    If there are no messages pending, returns an empty list. Returns False if an
    error occurred and no further polling should be attempted."""
    messages = []

    if not self._initialize_event.is_set():
      # The request came before we started up, there cannot be any messages
      # pending, and in any case they will be handled later.
      return messages

    try:
      while True:
        if not self.GetConnection():
          # The server isn't running or something. Don't re-poll.
          return False

        notification = self.GetConnection()._notifications.get_nowait()
        message = self.ConvertNotificationToMessage( request_data,
                                                     notification )

        if message:
          messages.append( message )
    except queue.Empty:
      # We drained the queue
      pass

    return messages


  def _AwaitServerMessages( self, request_data, timeout ):
    """Block until either we receive a notification, or a timeout occurs.
    Returns one of the following:
       - a list containing a single message
       - True if a timeout occurred, and the poll should be restarted
       - False if an error occurred, and no further polling should be attempted
    """
    try:
      while True:
        if not self._initialize_event.is_set():
          # The request came before we started up, wait for startup to complete,
          # then tell the client to re-send the request. Note, we perform this
          # check on every iteration, as the server may be legitimately
          # restarted while this loop is running.
          self._initialize_event.wait( timeout=timeout )

          # If the timeout is hit waiting for the server to be ready, after we
          # tried to start the server, we return False and kill the message
          # poll.
          return not self._server_started or self._initialize_event.is_set()

        if not self.GetConnection():
          # The server isn't running or something. Don't re-poll, as this will
          # just cause errors.
          return False

        notification = self.GetConnection()._notifications.get(
          timeout = timeout )
        message = self.ConvertNotificationToMessage( request_data,
                                                     notification )
        if message:
          return [ message ]
    except queue.Empty:
      return True


  def GetDefaultNotificationHandler( self ):
    """Return a notification handler method suitable for passing to
    LanguageServerConnection constructor"""
    def handler( server, notification ):
      self.HandleNotificationInPollThread( notification )
    return handler


  def HandleNotificationInPollThread( self, notification ):
    """Called by the LanguageServerConnection in its message pump context when a
    notification message arrives."""

    if notification[ 'method' ] == 'textDocument/publishDiagnostics':
      # Some clients might not use a message poll, so we must store the
      # diagnostics and return them in OnFileReadyToParse. We also need these
      # for correct FixIt handling, as they are part of the FixIt context.
      params = notification[ 'params' ]
      # Since percent-encoded strings are not canonical, they can choose to use
      # upper case or lower case letters, also there are some characters that
      # can be encoded or not. Therefore, we convert them back and forth
      # according to our implementation to make sure they are in a canonical
      # form for access later on.
      try:
        uri = lsp.FilePathToUri( lsp.UriToFilePath( params[ 'uri' ] ) )
      except lsp.InvalidUriException:
        # Ignore diagnostics for URIs we don't recognise
        LOGGER.debug(
          f'Ignoring diagnostics for unrecognized URI: { params[ "uri" ] }' )
        return
      with self._latest_diagnostics_mutex:
        self._latest_diagnostics[ uri ] = params[ 'diagnostics' ]


  def ConvertNotificationToMessage( self, request_data, notification ):
    """Convert the supplied server notification to a ycmd message. Returns None
    if the notification should be ignored.

    Implementations may override this method to handle custom notifications, but
    must always call the base implementation for unrecognized notifications."""

    if notification[ 'method' ] == 'window/showMessage':
      return responses.BuildDisplayMessageResponse(
        notification[ 'params' ][ 'message' ] )

    if notification[ 'method' ] == 'textDocument/publishDiagnostics':
      params = notification[ 'params' ]
      uri = params[ 'uri' ]

      try:
        filepath = lsp.UriToFilePath( uri )
      except lsp.InvalidUriException:
        LOGGER.debug( 'Ignoring diagnostics for unrecognized URI %s', uri )
        return None

      with self._server_info_mutex:
        if filepath in self._server_file_state:
          contents = utils.SplitLines(
            self._server_file_state[ filepath ].contents )
        else:
          contents = GetFileLines( request_data, filepath )
      diagnostics = [ _BuildDiagnostic( contents, uri, x )
                      for x in params[ 'diagnostics' ] ]
      return {
        'diagnostics': responses.BuildDiagnosticResponse(
          diagnostics, filepath, self.max_diagnostics_to_display ),
        'filepath': filepath
      }

    if notification[ 'method' ] == 'window/logMessage':
      log_level = [
        None, # 1-based enum from LSP
        logging.ERROR,
        logging.WARNING,
        logging.INFO,
        logging.DEBUG,
      ]

      params = notification[ 'params' ]
      LOGGER.log( log_level[ int( params[ 'type' ] ) ],
                  'Server reported: %s',
                  params[ 'message' ] )

    return None


  def _AnySupportedFileType( self, file_types ):
    for supported in self.SupportedFiletypes():
      if supported in file_types:
        return True
    return False


  def _UpdateServerWithCurrentFileContents( self, request_data ):
    file_name = request_data[ 'filepath' ]
    contents = GetFileContents( request_data, file_name )
    filetypes = request_data[ 'filetypes' ]
    with self._server_info_mutex:
      self._RefreshFileContentsUnderLock( file_name, contents, filetypes )


  def _UpdateServerWithFileContents( self, request_data ):
    """Update the server with the current contents of all open buffers, and
    close any buffers no longer open.

    This method should be called frequently and in any event before a
    synchronous operation."""
    with self._server_info_mutex:
      self._UpdateDirtyFilesUnderLock( request_data )
      files_to_purge = self._UpdateSavedFilesUnderLock( request_data )
      self._PurgeMissingFilesUnderLock( files_to_purge )


  def _RefreshFileContentsUnderLock( self, file_name, contents, file_types ):
    file_state: lsp.ServerFileState = self._server_file_state[ file_name ]
    old_state = file_state.state
    action = file_state.GetDirtyFileAction( contents )

    LOGGER.debug( 'Refreshing file %s: State is %s -> %s/action %s',
                  file_name,
                  old_state,
                  file_state.state,
                  action )

    if action == lsp.ServerFileState.OPEN_FILE:
      msg = lsp.DidOpenTextDocument( file_state, file_types, contents )

      self.GetConnection().SendNotification( msg )
    elif action == lsp.ServerFileState.CHANGE_FILE:
      # FIXME: DidChangeTextDocument doesn't actually do anything
      # different from DidOpenTextDocument other than send the right
      # message, because we don't actually have a mechanism for generating
      # the diffs. This isn't strictly necessary, but might lead to
      # performance problems.
      msg = lsp.DidChangeTextDocument( file_state, contents )
      self.GetConnection().SendNotification( msg )


  def _UpdateDirtyFilesUnderLock( self, request_data ):
    for file_name, file_data in request_data[ 'file_data' ].items():
      if not self._AnySupportedFileType( file_data[ 'filetypes' ] ):
        LOGGER.debug( 'Not updating file %s, it is not a supported filetype: '
                       '%s not in %s',
                       file_name,
                       file_data[ 'filetypes' ],
                       self.SupportedFiletypes() )
        continue

      self._RefreshFileContentsUnderLock( file_name,
                                          file_data[ 'contents' ],
                                          file_data[ 'filetypes' ] )



  def _UpdateSavedFilesUnderLock( self, request_data ):
    files_to_purge = []
    for file_name, file_state in self._server_file_state.items():
      if file_name in request_data[ 'file_data' ]:
        continue

      # We also need to tell the server the contents of any files we have said
      # are open, but are not 'dirty' in the editor. This is because after
      # sending a didOpen notification, we own the contents of the file.
      #
      # So for any file that is in the server map, and open, but not supplied in
      # the request, we check to see if its on-disk contents match the latest in
      # the server. If they don't, we send an update.
      #
      # FIXME: This is really inefficient currently, as it reads the entire file
      # on every update. It might actually be better to close files which have
      # been saved and are no longer "dirty", though that would likely be less
      # efficient for downstream servers which cache e.g. AST.
      try:
        contents = GetFileContents( request_data, file_name )
      except IOError:
        LOGGER.exception( 'Error getting contents for open file: %s',
                          file_name )

        # The file no longer exists (it might have been a temporary file name)
        # or it is no longer accessible, so we should state that it is closed.
        # If it were still open it would have been in the request_data.
        #
        # We have to do this in a separate loop because we can't change
        # self._server_file_state while iterating it.
        files_to_purge.append( file_name )
        continue

      action = file_state.GetSavedFileAction( contents )
      if action == lsp.ServerFileState.CHANGE_FILE:
        msg = lsp.DidChangeTextDocument( file_state, contents )
        self.GetConnection().SendNotification( msg )

    return files_to_purge


  def _PurgeMissingFilesUnderLock( self, files_to_purge ):
    # ycmd clients only send buffers which have changed, and are required to
    # send BufferUnload autocommand when files are closed.
    for file_name in files_to_purge:
      self._PurgeFileFromServer( file_name )


  def OnFileSave( self, request_data ):
    if not self.ServerIsReady():
      return

    sync = self._server_capabilities.get( 'textDocumentSync' )
    if sync is not None:
      if isinstance( sync, dict ) and _IsCapabilityProvided( sync, 'save' ):
        save = sync[ 'save' ]
        file_name = request_data[ 'filepath' ]
        contents = None
        if isinstance( save, dict ) and save.get( 'includeText' ):
          contents = request_data[ 'file_data' ][ file_name ][ 'contents' ]
        file_state = self._server_file_state[ file_name ]
        msg = lsp.DidSaveTextDocument( file_state, contents )
        self.GetConnection().SendNotification( msg )


  def OnBufferUnload( self, request_data ):
    if not self.ServerIsHealthy():
      return

    # If we haven't finished initializing yet, we need to queue up a call to
    # _PurgeFileFromServer. This ensures that the server is up to date
    # as soon as we are able to send more messages. This is important because
    # server start up can be quite slow and we must not block the user, while we
    # must keep the server synchronized.
    if not self._initialize_event.is_set():
      self._OnInitializeComplete(
        lambda self: self._PurgeFileFromServer( request_data[ 'filepath' ] ) )
      return

    self._PurgeFileFromServer( request_data[ 'filepath' ] )


  def _PurgeFileFromServer( self, file_path ):
    file_state = self._server_file_state[ file_path ]
    action = file_state.GetFileCloseAction()
    if action == lsp.ServerFileState.CLOSE_FILE:
      msg = lsp.DidCloseTextDocument( file_state )
      self.GetConnection().SendNotification( msg )

    del self._server_file_state[ file_state.filename ]


  def GetProjectRootFiles( self ):
    """Returns a list of files that indicate the root of the project.
    It should be easier to override just this method than the whole
    GetProjectDirectory."""
    return []


  def GetProjectDirectory( self, request_data ):
    """Return the directory in which the server should operate. Language server
    protocol and most servers have a concept of a 'project directory'. Where a
    concrete completer can detect this better, it should override this method,
    but otherwise, we default as follows:
      - If the user specified 'project_directory' in their extra conf
        'Settings', use that.
      - try to find files from GetProjectRootFiles and use the
        first directory from there
      - if there's an extra_conf file, use that directory
      - otherwise if we know the client's cwd, use that
      - otherwise use the directory of the file that we just opened
    Note: None of these are ideal. Ycmd doesn't really have a notion of project
    directory and therefore neither do any of our clients.

    NOTE: Must be called _after_ _GetSettingsFromExtraConf, as it uses
    self._settings and self._extra_conf_dir
    """

    if 'project_directory' in self._settings:
      return utils.AbsolutePath( self._settings[ 'project_directory' ],
                                  self._extra_conf_dir )

    project_root_files = self.GetProjectRootFiles()
    if project_root_files:
      for folder in utils.PathsToAllParentFolders( request_data[ 'filepath' ] ):
        for root_file in project_root_files:
          if os.path.isfile( os.path.join( folder, root_file ) ):
            return folder

    if self._extra_conf_dir:
      return self._extra_conf_dir

    if 'working_dir' in request_data:
      return request_data[ 'working_dir' ]

    return os.path.dirname( request_data[ 'filepath' ] )


  def _SendInitialize( self, request_data ):
    """Sends the initialize request asynchronously.
    This must be called immediately after establishing the connection with the
    language server. Implementations must not issue further requests to the
    server until the initialize exchange has completed. This can be detected by
    calling this class's implementation of _ServerIsInitialized.
    _GetSettingsFromExtraConf must be called before calling this method, as this
    method release on self._extra_conf_dir.
    It is called before starting the server in OnFileReadyToParse."""
    with self._server_info_mutex:
      assert not self._initialize_response

      request_id = self.GetConnection().NextRequestId()

      # FIXME: According to the discussion on
      # https://github.com/Microsoft/language-server-protocol/issues/567
      # the settings on the Initialize request are somehow subtly different from
      # the settings supplied in didChangeConfiguration, though it's not exactly
      # clear how/where that is specified.
      msg = lsp.Initialize( request_id,
                            self._project_directory,
                            self.ExtraCapabilities(),
                            self._settings.get( 'ls', {} ) )

      def response_handler( response, message ):
        if message is None:
          return

        self._HandleInitializeInPollThread( message )

      self._initialize_response = self.GetConnection().GetResponseAsync(
        request_id,
        msg,
        response_handler )


  def GetTriggerCharacters( self, server_trigger_characters ):
    """Given the server trigger characters supplied in the initialize response,
    returns the trigger characters to merge with the ycmd-defined ones. By
    default, all server trigger characters are merged in. Note this might not be
    appropriate in all cases as ycmd's own triggering mechanism is more
    sophisticated (regex based) than LSP's (single character). If the
    server-supplied single-character triggers are not useful, override this
    method to return an empty list or None."""
    return server_trigger_characters


  def GetSignatureTriggerCharacters( self, server_trigger_characters ):
    """Same as _GetTriggerCharacters but for signature help."""
    return server_trigger_characters


  def _SetUpSemanticTokenAtlas( self, capabilities: dict ):
    server_config = capabilities.get( 'semanticTokensProvider' )
    if server_config is None:
      return

    if not _IsCapabilityProvided( server_config, 'full' ):
      return

    self._semantic_token_atlas = TokenAtlas( server_config[ 'legend' ] )


  def _HandleInitializeInPollThread( self, response ):
    """Called within the context of the LanguageServerConnection's message pump
    when the initialize request receives a response."""
    with self._server_info_mutex:
      self._server_capabilities = response[ 'result' ][ 'capabilities' ]
      self._resolve_completion_items = self._ShouldResolveCompletionItems()

      if self._resolve_completion_items:
        LOGGER.info( '%s: Language server requires resolve request',
                     self.Language() )
      else:
        LOGGER.info( '%s: Language server does not require resolve request',
                     self.Language() )

      self._is_completion_provider = (
          'completionProvider' in self._server_capabilities )

      self._SetUpSemanticTokenAtlas( self._server_capabilities )

      sync = self._server_capabilities.get( 'textDocumentSync' )
      if sync is not None:
        SYNC_TYPE = [
          'None',
          'Full',
          'Incremental'
        ]

        # The sync type can either be a number or an object. Because it's
        # important to make things difficult.
        if isinstance( sync, dict ):
          if 'change' in sync:
            sync = sync[ 'change' ]
          else:
            sync = 1

        self._sync_type = SYNC_TYPE[ sync ]
        LOGGER.info( '%s: Language server requires sync type of %s',
                     self.Language(),
                     self._sync_type )

      # Update our semantic triggers if they are supplied by the server
      if self.completion_triggers is not None:
        server_trigger_characters = (
          ( self._server_capabilities.get( 'completionProvider' ) or {} )
                                     .get( 'triggerCharacters' ) or []
        )
        LOGGER.debug( '%s: Server declares trigger characters: %s',
                      self.Language(),
                      server_trigger_characters )

        trigger_characters = self.GetTriggerCharacters(
          server_trigger_characters )

        if trigger_characters:
          LOGGER.info( '%s: Using trigger characters for semantic triggers: %s',
                       self.Language(),
                       ','.join( trigger_characters ) )

          self.completion_triggers.SetServerSemanticTriggers(
            trigger_characters )

      if self._signature_triggers is not None:
        server_trigger_characters = (
          ( self._server_capabilities.get( 'signatureHelpProvider' ) or {} )
                                     .get( 'triggerCharacters' ) or []
        )
        LOGGER.debug( '%s: Server declares signature trigger characters: %s',
                      self.Language(),
                      server_trigger_characters )

        trigger_characters = self.GetSignatureTriggerCharacters(
          server_trigger_characters )

        if trigger_characters:
          LOGGER.info( '%s: Using characters for signature triggers: %s',
                       self.Language(),
                       ','.join( trigger_characters ) )
          self.SetSignatureHelpTriggers( trigger_characters )

      # We must notify the server that we received the initialize response (for
      # no apparent reason, other than that's what the protocol says).
      self.GetConnection().SendNotification( lsp.Initialized() )

      # Some language servers require the use of didChangeConfiguration event,
      # even though it is not clear in the specification that it is mandatory,
      # nor when it should be sent.  VSCode sends it immediately after
      # initialized notification, so we do the same.

      # FIXME: According to
      # https://github.com/Microsoft/language-server-protocol/issues/567 the
      # configuration should be send in response to a workspace/configuration
      # request?
      self.GetConnection().SendNotification(
          lsp.DidChangeConfiguration( self._settings.get( 'ls', {} ) ) )

      # Notify the other threads that we have completed the initialize exchange.
      self._initialize_response = None
      self._initialize_event.set()

    # Fire any events that are pending on the completion of the initialize
    # exchange. Typically, this will be calls to _UpdateServerWithFileContents
    # or something that occurred while we were waiting.
    for handler in self._on_initialize_complete_handlers:
      handler( self )

    self._on_initialize_complete_handlers = []


  def _OnInitializeComplete( self, handler ):
    """Register a function to be called when the initialize exchange completes.
    The function |handler| will be called on successful completion of the
    initialize exchange with a single argument |self|, which is the |self|
    passed to this method.
    If the server is shut down or reset, the callback is not called."""
    self._on_initialize_complete_handlers.append( handler )


  def RegisterOnFileReadyToParse( self, handler, once=False ):
    self._on_file_ready_to_parse_handlers.append( ( handler, once ) )


  def GetHoverResponse( self, request_data ):
    """Return the raw LSP response to the hover request for the supplied
    context. Implementations can use this for e.g. GetDoc and GetType requests,
    depending on the particular server response."""
    if not self._ServerIsInitialized():
      raise RuntimeError( 'Server is initializing. Please wait.' )

    self._UpdateServerWithFileContents( request_data )

    request_id = self.GetConnection().NextRequestId()
    response = self.GetConnection().GetResponse(
      request_id,
      lsp.Hover( request_id, request_data ),
      REQUEST_TIMEOUT_COMMAND )

    result = response[ 'result' ]
    if result:
      return result[ 'contents' ]
    raise NoHoverInfoException( NO_HOVER_INFORMATION )


  def _GoToRequest( self, request_data, handler ):
    request_id = self.GetConnection().NextRequestId()

    try:
      result = self.GetConnection().GetResponse(
        request_id,
        getattr( lsp, handler )( request_id, request_data ),
        REQUEST_TIMEOUT_COMMAND )[ 'result' ]
    except ResponseFailedException:
      result = None

    if not result:
      raise RuntimeError( 'Cannot jump to location' )
    if not isinstance( result, list ):
      return [ result ]
    return result


  def GoTo( self, request_data, handlers ):
    """Issues a GoTo request for each handler in |handlers| until it returns
    multiple locations or a location the cursor does not belong since the user
    wants to jump somewhere else. If that's the last handler, the location is
    returned anyway."""
    if not self.ServerIsReady():
      raise RuntimeError( 'Server is initializing. Please wait.' )

    self._UpdateServerWithFileContents( request_data )

    if len( handlers ) == 1:
      result = self._GoToRequest( request_data, handlers[ 0 ] )
    else:
      for handler in handlers:
        result = self._GoToRequest( request_data, handler )
        if len( result ) > 1 or not _CursorInsideLocation( request_data,
                                                           result[ 0 ] ):
          break

    return _LocationListToGoTo( request_data, result )


  def GoToSymbol( self, request_data, args ):
    if not self.ServerIsReady():
      raise RuntimeError( 'Server is initializing. Please wait.' )

    self._UpdateServerWithFileContents( request_data )

    if len( args ) < 1:
      raise RuntimeError( 'Must specify something to search for' )

    query = args[ 0 ]

    request_id = self.GetConnection().NextRequestId()
    response = self.GetConnection().GetResponse(
      request_id,
      lsp.WorkspaceSymbol( request_id, query ),
      REQUEST_TIMEOUT_COMMAND )

    result = response.get( 'result' ) or []
    return _SymbolInfoListToGoTo( request_data, result )


  def GoToDocumentOutline( self, request_data ):
    if not self.ServerIsReady():
      raise RuntimeError( 'Server is initializing. Please wait.' )

    self._UpdateServerWithFileContents( request_data )

    request_id = self.GetConnection().NextRequestId()
    message = lsp.DocumentSymbol( request_id, request_data )
    response = self.GetConnection().GetResponse( request_id,
                                                 message,
                                                 REQUEST_TIMEOUT_COMMAND )

    result = response.get( 'result' ) or []

    # We should only receive SymbolInformation (not DocumentSymbol)
    if any( 'range' in s for s in result ):
      raise ValueError(
        "Invalid server response; DocumentSymbol not supported" )

    return _SymbolInfoListToGoTo( request_data, result )



  def CallHierarchy( self, request_data, args ):
    if not self.ServerIsReady():
      raise RuntimeError( 'Server is initializing. Please wait.' )

    self._UpdateServerWithFileContents( request_data )
    request_id = self.GetConnection().NextRequestId()
    message = lsp.PrepareCallHierarchy( request_id, request_data )
    prepare_response = self.GetConnection().GetResponse(
        request_id,
        message,
        REQUEST_TIMEOUT_COMMAND )
    preparation_item = prepare_response.get( 'result' ) or []
    if not preparation_item:
      raise RuntimeError( f'No { args[ 0 ] } calls found.' )

    assert len( preparation_item ) == 1, (
             'Not available: Multiple hierarchies were received, '
             'this is not currently supported.' )

    preparation_item = preparation_item[ 0 ]

    request_id = self.GetConnection().NextRequestId()
    message = lsp.CallHierarchy( request_id, args[ 0 ], preparation_item )
    response = self.GetConnection().GetResponse( request_id,
                                                 message,
                                                 REQUEST_TIMEOUT_COMMAND )

    result = response.get( 'result' ) or []
    goto_response = []
    for hierarchy_item in result:
      description = hierarchy_item.get( 'from', hierarchy_item.get( 'to' ) )
      filepath = lsp.UriToFilePath( description[ 'uri' ] )
      start_position = hierarchy_item[ 'fromRanges' ][ 0 ][ 'start' ]
      goto_line = start_position[ 'line' ]
      try:
        line_value = GetFileLines( request_data, filepath )[ goto_line ]
      except IndexError:
        continue
      goto_column = utils.CodepointOffsetToByteOffset(
        line_value,
        lsp.UTF16CodeUnitsToCodepoints(
          line_value,
          start_position[ 'character' ] ) )
      goto_response.append( responses.BuildGoToResponse(
        filepath,
        goto_line + 1,
        goto_column + 1,
        description[ 'name' ] ) )

    if goto_response:
      return goto_response
    raise RuntimeError( f'No { args[ 0 ] } calls found.' )


  def GetCodeActions( self, request_data ):
    """Performs the codeAction request and returns the result as a FixIt
    response."""
    if not self.ServerIsReady():
      raise RuntimeError( 'Server is initializing. Please wait.' )

    self._UpdateServerWithFileContents( request_data )

    request_id = self.GetConnection().NextRequestId()

    cursor_range_ls = lsp.Range( request_data )

    with self._latest_diagnostics_mutex:
      # _latest_diagnostics contains LSP rnages, _not_ YCM ranges
      file_diagnostics = list( self._latest_diagnostics[
          lsp.FilePathToUri( request_data[ 'filepath' ] ) ] )

    matched_diagnostics = [
      d for d in file_diagnostics if lsp.RangesOverlap( d[ 'range' ],
                                                        cursor_range_ls )
    ]


    # If we didn't find any overlapping the strict range/character. Find any
    # that overlap line of the cursor.
    if not matched_diagnostics and 'range' not in request_data:
      matched_diagnostics = [
        d for d in file_diagnostics
        if lsp.RangesOverlapLines( d[ 'range' ], cursor_range_ls )
      ]

    code_actions = self.GetConnection().GetResponse(
      request_id,
      lsp.CodeAction( request_id,
                      request_data,
                      cursor_range_ls,
                      matched_diagnostics ),
      REQUEST_TIMEOUT_COMMAND )

    return self.CodeActionResponseToFixIts( request_data,
                                            code_actions[ 'result' ] )


  def CodeActionResponseToFixIts( self, request_data, code_actions ):
    if code_actions is None:
      return responses.BuildFixItResponse( [] )

    fixits = []
    for code_action in code_actions:
      if 'edit' in code_action:
        # TODO: Start supporting a mix of WorkspaceEdits and Commands
        # once there's a need for such
        assert 'command' not in code_action

        # This is a WorkspaceEdit literal
        fixits.append( self.CodeActionLiteralToFixIt( request_data,
                                                      code_action ) )
        continue

      # Either a CodeAction or a Command
      assert 'command' in code_action

      action_command = code_action[ 'command' ]
      if isinstance( action_command, dict ):
        # CodeAction with a 'command' rather than 'edit'
        fixits.append( self.CodeActionCommandToFixIt( request_data,
                                                      code_action ) )
        continue

      # It is a Command
      fixits.append( self.CommandToFixIt( request_data, code_action ) )

    # Show a list of actions to the user to select which one to apply.
    # This is (probably) a more common workflow for "code action".
    result = [ r for r in fixits if r ]
    if len( result ) == 1:
      fixit = result[ 0 ]
      if hasattr( fixit, 'resolve' ):
        # Be nice and resolve the fixit to save on roundtrips
        unresolved_fixit = {
          'command': fixit.command,
          'text': fixit.text,
          'resolve': fixit.resolve
        }
        return self._ResolveFixit( request_data, unresolved_fixit )
    return responses.BuildFixItResponse( result )


  def CodeActionLiteralToFixIt( self, request_data, code_action_literal ):
    return WorkspaceEditToFixIt(
        request_data,
        code_action_literal[ 'edit' ],
        code_action_literal[ 'title' ],
        code_action_literal.get( 'kind' ) )


  def CodeActionCommandToFixIt( self, request_data, code_action_command ):
    command = code_action_command[ 'command' ]
    return self.CommandToFixIt(
        request_data,
        command,
        code_action_command.get( 'kind' ) )


  def CommandToFixIt( self, request_data, command, kind = None ):
    return responses.UnresolvedFixIt( command,
                                      command[ 'title' ],
                                      kind )


  def RefactorRename( self, request_data, args ):
    """Issues the rename request and returns the result as a FixIt response."""
    if not self.ServerIsReady():
      raise RuntimeError( 'Server is initializing. Please wait.' )

    if len( args ) != 1:
      raise ValueError( 'Please specify a new name to rename it to.\n'
                        'Usage: RefactorRename <new name>' )

    self._UpdateServerWithFileContents( request_data )

    new_name = args[ 0 ]

    request_id = self.GetConnection().NextRequestId()
    try:
      response = self.GetConnection().GetResponse(
        request_id,
        lsp.Rename( request_id, request_data, new_name ),
        REQUEST_TIMEOUT_COMMAND )
    except ResponseFailedException:
      raise RuntimeError( 'Cannot rename the symbol under cursor.' )

    fixit = WorkspaceEditToFixIt( request_data, response[ 'result' ] )
    if not fixit:
      raise RuntimeError( 'Cannot rename the symbol under cursor.' )

    return responses.BuildFixItResponse( [ fixit ] )


  def Format( self, request_data ):
    """Issues the formatting or rangeFormatting request (depending on the
    presence of a range) and returns the result as a FixIt response."""
    if not self.ServerIsReady():
      raise RuntimeError( 'Server is initializing. Please wait.' )

    self._UpdateServerWithFileContents( request_data )

    request_data[ 'options' ].update(
      self.AdditionalFormattingOptions( request_data ) )
    request_id = self.GetConnection().NextRequestId()
    if 'range' in request_data:
      message = lsp.RangeFormatting( request_id, request_data )
    else:
      message = lsp.Formatting( request_id, request_data )

    response = self.GetConnection().GetResponse( request_id,
                                                 message,
                                                 REQUEST_TIMEOUT_COMMAND )
    filepath = request_data[ 'filepath' ]
    contents = GetFileLines( request_data, filepath )
    chunks = [ responses.FixItChunk( text_edit[ 'newText' ],
                                     _BuildRange( contents,
                                                  filepath,
                                                  text_edit[ 'range' ] ) )
               for text_edit in response[ 'result' ] or [] ]

    return responses.BuildFixItResponse( [ responses.FixIt(
      responses.Location( request_data[ 'line_num' ],
                          request_data[ 'column_num' ],
                          request_data[ 'filepath' ] ),
      chunks ) ] )


  def _ResolveFixit( self, request_data, fixit ):
    if not fixit[ 'resolve' ]:
      return { 'fixits': [ fixit ] }

    unresolved_fixit = fixit[ 'command' ]
    collector = EditCollector()
    with self.GetConnection().CollectApplyEdits( collector ):
      self.GetCommandResponse(
        request_data,
        unresolved_fixit[ 'command' ],
        unresolved_fixit[ 'arguments' ] )

    # Return a ycmd fixit
    response = collector.requests
    assert len( response ) < 2
    if not response:
      return responses.BuildFixItResponse( [ responses.FixIt(
        responses.Location( request_data[ 'line_num' ],
                            request_data[ 'column_num' ],
                            request_data[ 'filepath' ] ),
        [] ) ] )
    fixit = WorkspaceEditToFixIt(
      request_data,
      response[ 0 ][ 'edit' ],
      unresolved_fixit[ 'title' ] )
    return responses.BuildFixItResponse( [ fixit ] )


  def ResolveFixit( self, request_data ):
    return self._ResolveFixit( request_data, request_data[ 'fixit' ] )


  def ExecuteCommand( self, request_data, args ):
    if not self.ServerIsReady():
      raise RuntimeError( 'Server is initializing. Please wait.' )

    if not args:
      raise ValueError( 'Must specify a command to execute' )

    # We don't have any actual knowledge of the responses here. Unfortunately,
    # the LSP "commands" require client/server specific understanding of the
    # commands.
    collector = EditCollector()
    with self.GetConnection().CollectApplyEdits( collector ):
      command_response = self.GetCommandResponse( request_data,
                                                  args[ 0 ],
                                                  args[ 1: ] )

    edits = collector.requests
    response = self.HandleServerCommandResponse( request_data,
                                                 edits,
                                                 command_response )
    if response is not None:
      return response

    if len( edits ):
      fixits = [ WorkspaceEditToFixIt(
        request_data,
        e[ 'edit' ],
        '' ) for e in edits ]
      return responses.BuildFixItResponse( fixits )

    return responses.BuildDetailedInfoResponse( json.dumps( command_response,
                                                            indent = 2 ) )


  def GetCommandResponse( self, request_data, command, arguments ):
    if not self.ServerIsReady():
      raise RuntimeError( 'Server is initializing. Please wait.' )

    self._UpdateServerWithFileContents( request_data )

    request_id = self.GetConnection().NextRequestId()
    message = lsp.ExecuteCommand( request_id, command, arguments )
    response = self.GetConnection().GetResponse( request_id,
                                                 message,
                                                 REQUEST_TIMEOUT_COMMAND )
    return response[ 'result' ]


  def CommonDebugItems( self ):
    def ServerStateDescription():
      if not self.ServerIsHealthy():
        return 'Dead'

      if not self._ServerIsInitialized():
        return 'Starting...'

      return 'Initialized'

    return [ responses.DebugInfoItem( 'Server State',
                                      ServerStateDescription() ),
             responses.DebugInfoItem( 'Project Directory',
                                      self._project_directory ),
             responses.DebugInfoItem(
               'Settings',
               json.dumps( self._settings.get( 'ls', {} ),
                           indent = 2,
                           sort_keys = True ) ) ]


def _DistanceOfPointToRange( point, range ):
  """Calculate the distance from a point to a range.

  Assumes point is covered by lines in the range.
  Returns 0 if point is already inside range. """
  start = range[ 'start' ]
  end = range[ 'end' ]

  # Single-line range.
  if start[ 'line' ] == end[ 'line' ]:
    # 0 if point is within range, otherwise distance from start/end.
    return max( 0, point[ 'character' ] - end[ 'character' ],
                start[ 'character' ] - point[ 'character' ] )

  if start[ 'line' ] == point[ 'line' ]:
    return max( 0, start[ 'character' ] - point[ 'character' ] )
  if end[ 'line' ] == point[ 'line' ]:
    return max( 0, point[ 'character' ] - end[ 'character' ] )
  # If not on the first or last line, then point is within range for sure.
  return 0


def _CompletionItemToCompletionData( insertion_text, item, fixits ):
  # Since we send completionItemKind capabilities, we guarantee to handle
  # values outside our value set and fall back to a default.
  try:
    kind = lsp.ITEM_KIND[ item.get( 'kind' ) or 0 ]
  except IndexError:
    kind = lsp.ITEM_KIND[ 0 ] # Fallback to None for unsupported kinds.

  documentation = item.get( 'documentation' ) or ''
  if isinstance( documentation, dict ):
    documentation = documentation[ 'value' ]

  return responses.BuildCompletionData(
    insertion_text,
    extra_menu_info = item.get( 'detail' ),
    detailed_info = item[ 'label' ] + '\n\n' + documentation,
    menu_text = item[ 'label' ],
    kind = kind,
    extra_data = fixits )


def _FixUpCompletionPrefixes( completions,
                              start_codepoints,
                              request_data,
                              min_start_codepoint ):
  """Fix up the insertion texts so they share the same start_codepoint by
  borrowing text from the source."""
  line = request_data[ 'line_value' ]
  for completion, start_codepoint in zip( completions, start_codepoints ):
    to_borrow = start_codepoint - min_start_codepoint
    if to_borrow > 0:
      borrow = line[ start_codepoint - to_borrow - 1 : start_codepoint - 1 ]
      new_insertion_text = borrow + completion[ 'insertion_text' ]
      completion[ 'insertion_text' ] = new_insertion_text

  # Finally, remove any common prefix
  common_prefix_len = len( os.path.commonprefix(
    [ c[ 'insertion_text' ] for c in completions ] ) )
  for completion in completions:
    completion[ 'insertion_text' ] = completion[ 'insertion_text' ][
      common_prefix_len : ]

  # The start column is the earliest start point that we fixed up plus the
  # length of the common prefix that we subsequently removed.
  #
  # Phew! That was hard work.
  request_data[ 'start_codepoint' ] = min_start_codepoint + common_prefix_len
  return completions


def _InsertionTextForItem( request_data, item ):
  """Determines the insertion text for the completion item |item|, and any
  additional FixIts that need to be applied when selecting it.

  Returns a tuple (
     - insertion_text   = the text to insert
     - fixits           = ycmd fixit which needs to be applied additionally when
                          selecting this completion
     - start_codepoint  = the start column at which the text should be inserted
  )"""
  # We do not support completion types of "Snippet". This is implicit in that we
  # don't say it is a "capability" in the initialize request.
  # Abort this request if the server is buggy and ignores us.
  assert lsp.INSERT_TEXT_FORMAT[
    item.get( 'insertTextFormat' ) or 1 ] == 'PlainText'

  fixits = None

  start_codepoint = request_data[ 'start_codepoint' ]
  # We will always have one of insertText or label
  if 'insertText' in item and item[ 'insertText' ]:
    insertion_text = item[ 'insertText' ]
  else:
    insertion_text = item[ 'label' ]

  additional_text_edits = []

  # Per the protocol, textEdit takes precedence over insertText, and must be
  # on the same line (and containing) the originally requested position. These
  # are a pain, and require fixing up later in some cases, as most of our
  # clients won't be able to apply arbitrary edits (only 'completion', as
  # opposed to 'content assist').
  if 'textEdit' in item and item[ 'textEdit' ]:
    text_edit = item[ 'textEdit' ]
    start_codepoint = _GetCompletionItemStartCodepointOrReject( text_edit,
                                                                request_data )

    insertion_text = text_edit[ 'newText' ]

    if '\n' in insertion_text:
      # jdt.ls can return completions which generate code, such as
      # getters/setters and entire anonymous classes.
      #
      # In order to support this we would need to do something like:
      #  - invent some insertion_text based on label/insertText (or perhaps
      #    '<snippet>'
      #   - insert a textEdit in additionalTextEdits which deletes this
      #     insertion
      #   - or perhaps just modify this textEdit to undo that change?
      #   - or perhaps somehow support insertion_text of '' (this doesn't work
      #     because of filtering/sorting, etc.).
      #  - insert this textEdit in additionalTextEdits
      #
      # These textEdits would need a lot of fixing up and is currently out of
      # scope.
      #
      # These sorts of completions aren't really in the spirit of ycmd at the
      # moment anyway. So for now, we just ignore this candidate.
      raise IncompatibleCompletionException( insertion_text )
  else:
    # Calculate the start codepoint based on the overlapping text in the
    # insertion text and the existing text. This is the behavior of Visual
    # Studio Code and therefore de-facto undocumented required behavior of LSP
    # clients.
    start_codepoint -= FindOverlapLength( request_data[ 'prefix' ],
                                          insertion_text )

  additional_text_edits.extend( item.get( 'additionalTextEdits' ) or [] )

  if additional_text_edits:
    filepath = request_data[ 'filepath' ]
    contents = GetFileLines( request_data, filepath )
    chunks = [ responses.FixItChunk( e[ 'newText' ],
                                     _BuildRange( contents,
                                                  filepath,
                                                  e[ 'range' ] ) )
               for e in additional_text_edits ]

    fixits = responses.BuildFixItResponse(
      [ responses.FixIt( chunks[ 0 ].range.start_, chunks ) ] )

  return insertion_text, fixits, start_codepoint


def FindOverlapLength( line_value, insertion_text ):
  """Return the length of the longest suffix of |line_value| which is a prefix
  of |insertion_text|"""

  # Credit: https://neil.fraser.name/news/2010/11/04/

  # Example of what this does:
  # line_value:     import com.
  # insertion_text:        com.youcompleteme.test
  # Overlap:               ^..^
  # Overlap Len:           4

  # Calculated as follows:
  #   - truncate:
  #      line_value     = import com.
  #      insertion_text = com.youcomp
  #   - assume overlap length 1
  #      overlap_text = "."
  #      position     = 3
  #      overlap set to be 4
  #      com. compared with com.: longest_overlap = 4
  #   - assume overlap length 5
  #      overlap_text = " com."
  #      position     = -1
  #      return 4 (from previous iteration)

  # More complex example: 'Some CoCo' vs 'CoCo Bean'
  #   No truncation
  #   Iter 1 (overlap = 1): p('o') = 1, overlap = 2, Co==Co, best = 2 (++)
  #   Iter 2 (overlap = 3): p('oCo') = 1 overlap = 4, CoCo==CoCo, best = 4 (++)
  #   Iter 3 (overlap = 5): p(' CoCo') = -1, return 4

  # And the non-overlap case "aaab" "caab":
  #   Iter 1 (overlap = 1): p('b') = 3, overlap = 4, aaab!=caab, return 0

  line_value_len = len( line_value )
  insertion_text_len = len( insertion_text )

  # Bail early if either are empty
  if line_value_len == 0 or insertion_text_len == 0:
    return 0

  # Truncate so that they are the same length. Keep the overlapping sections
  # (suffix of line_value, prefix of insertion_text).
  if line_value_len > insertion_text_len:
    line_value = line_value[ -insertion_text_len : ]
  elif insertion_text_len > line_value_len:
    insertion_text = insertion_text[ : line_value_len ]

  # Worst case is full overlap, but that's trivial to check.
  if insertion_text == line_value:
    return min( line_value_len, insertion_text_len )

  longest_matching_overlap = 0

  # Assume a single-character of overlap, and find where this appears (if at
  # all) in the insertion_text
  overlap = 1
  while True:
    # Find the position of the overlap-length suffix of line_value within
    # insertion_text
    overlap_text = line_value[ -overlap : ]
    position = insertion_text.find( overlap_text )

    # If it isn't found, then we're done, return the last known overlap length.
    if position == -1:
      return longest_matching_overlap

    # Assume that all of the characters up to where this suffix was found
    # overlap. If they do, assume 1 more character of overlap, and continue.
    # Otherwise, we're done.
    overlap += position

    # If the overlap section matches, then we know this is the longest overlap
    # we've seen so far.
    if line_value[ -overlap : ] == insertion_text[ : overlap ]:
      longest_matching_overlap = overlap
      overlap += 1


def _GetCompletionItemStartCodepointOrReject( text_edit, request_data ):
  edit_range = text_edit[ 'range' ]

  # Conservatively rejecting candidates that breach the protocol
  if edit_range[ 'start' ][ 'line' ] != edit_range[ 'end' ][ 'line' ]:
    new_text = text_edit[ 'newText' ]
    raise IncompatibleCompletionException(
      f"The TextEdit '{ new_text }' spans multiple lines" )

  file_contents = GetFileLines( request_data, request_data[ 'filepath' ] )
  line_value = file_contents[ edit_range[ 'start' ][ 'line' ] ]

  start_codepoint = lsp.UTF16CodeUnitsToCodepoints(
    line_value,
    edit_range[ 'start' ][ 'character' ] + 1 )

  if start_codepoint > request_data[ 'start_codepoint' ]:
    new_text = text_edit[ 'newText' ]
    raise IncompatibleCompletionException(
      f"The TextEdit '{ new_text }' starts after the start position" )

  return start_codepoint


def _LocationListToGoTo( request_data, positions ):
  """Convert a LSP list of locations to a ycmd GoTo response."""
  try:
    if len( positions ) > 1:
      return [
        responses.BuildGoToResponseFromLocation(
          *_LspLocationToLocationAndDescription( request_data, position ) )
        for position in positions
      ]
    return responses.BuildGoToResponseFromLocation(
      *_LspLocationToLocationAndDescription( request_data, positions[ 0 ] ) )
  except ( IndexError, KeyError ):
    raise RuntimeError( 'Cannot jump to location' )


def _SymbolInfoListToGoTo( request_data, symbols ):
  """Convert a list of LSP SymbolInformation into a YCM GoTo response"""

  def BuildGoToLocationFromSymbol( symbol ):
    location, line_value = _LspLocationToLocationAndDescription(
      request_data,
      symbol[ 'location' ] )

    description = ( f'{ lsp.SYMBOL_KIND[ symbol[ "kind" ] ] }: '
                    f'{ symbol[ "name" ] }' )

    goto = responses.BuildGoToResponseFromLocation( location,
                                                    description )
    goto[ 'extra_data' ] = {
      'kind': lsp.SYMBOL_KIND[ symbol[ 'kind' ] ],
      'name': symbol[ 'name' ],
    }
    return goto

  locations = [ BuildGoToLocationFromSymbol( s ) for s in
                sorted( symbols,
                        key = lambda s: ( s[ 'kind' ], s[ 'name' ] ) ) ]

  if not locations:
    raise RuntimeError( "Symbol not found" )
  elif len( locations ) == 1:
    return locations[ 0 ]
  else:
    return locations


def _LspLocationToLocationAndDescription( request_data, location ):
  """Convert a LSP Location to a ycmd location."""
  try:
    filename = lsp.UriToFilePath( location[ 'uri' ] )
    file_contents = GetFileLines( request_data, filename )
  except lsp.InvalidUriException:
    LOGGER.debug( 'Invalid URI, file contents not available in GoTo' )
    filename = ''
    file_contents = []
  except IOError:
    # It's possible to receive positions for files which no longer exist (due to
    # race condition). UriToFilePath doesn't throw IOError, so we can assume
    # that filename is already set.
    LOGGER.exception( 'A file could not be found when determining a '
                      'GoTo location' )
    file_contents = []

  return _BuildLocationAndDescription( filename,
                                       file_contents,
                                       location[ 'range' ][ 'start' ] )


def _LspToYcmdLocation( file_contents, location ):
  """Converts a LSP location to a ycmd one. Returns a tuple of (
     - the contents of the line of |location|
     - the line number of |location|
     - the byte offset converted from the UTF-16 offset of |location|
  )"""
  line_num = location[ 'line' ] + 1
  try:
    line_value = file_contents[ location[ 'line' ] ]
    return line_value, line_num, utils.CodepointOffsetToByteOffset(
      line_value,
      lsp.UTF16CodeUnitsToCodepoints( line_value,
                                      location[ 'character' ] + 1 ) )
  except IndexError:
    # This can happen when there are stale diagnostics in OnFileReadyToParse,
    # just return the value as-is.
    return '', line_num, location[ 'character' ] + 1


def _CursorInsideLocation( request_data, location ):
  try:
    filepath = lsp.UriToFilePath( location[ 'uri' ] )
  except lsp.InvalidUriException:
    LOGGER.debug( 'Invalid URI, assume cursor is not inside the location' )
    return False

  if request_data[ 'filepath' ] != filepath:
    return False

  line = request_data[ 'line_num' ]
  column = request_data[ 'column_num' ]
  file_contents = GetFileLines( request_data, filepath )
  lsp_range = location[ 'range' ]

  _, start_line, start_column = _LspToYcmdLocation( file_contents,
                                                    lsp_range[ 'start' ] )
  if ( line < start_line or
       ( line == start_line and column < start_column ) ):
    return False

  _, end_line, end_column = _LspToYcmdLocation( file_contents,
                                                lsp_range[ 'end' ] )
  if ( line > end_line or
       ( line == end_line and column > end_column ) ):
    return False

  return True


def _BuildLocationAndDescription( filename, file_contents, location ):
  """Returns a tuple of (
    - ycmd Location for the supplied filename and LSP location
    - contents of the line at that location
  )
  Importantly, converts from LSP Unicode offset to ycmd byte offset."""
  line_value, line, column = _LspToYcmdLocation( file_contents, location )
  return responses.Location( line, column, filename = filename ), line_value


def _BuildRange( contents, filename, r ):
  """Returns a ycmd range from a LSP range |r|."""
  return responses.Range( _BuildLocationAndDescription( filename,
                                                        contents,
                                                        r[ 'start' ] )[ 0 ],
                          _BuildLocationAndDescription( filename,
                                                        contents,
                                                        r[ 'end' ] )[ 0 ] )


def _BuildDiagnostic( contents, uri, diag ):
  """Return a ycmd diagnostic from a LSP diagnostic."""
  try:
    filename = lsp.UriToFilePath( uri )
  except lsp.InvalidUriException:
    LOGGER.debug( 'Invalid URI received for diagnostic' )
    filename = ''

  r = _BuildRange( contents, filename, diag[ 'range' ] )
  diag_text = diag[ 'message' ]
  try:
    code = diag[ 'code' ]
    diag_text += " [" + str( code ) + "]"
  except KeyError:
    # code field doesn't exist.
    pass

  return responses.Diagnostic(
    ranges = [ r ],
    location = r.start_,
    location_extent = r,
    text = diag_text,
    kind = lsp.SEVERITY[ diag.get( 'severity' ) or 1 ].upper() )


def TextEditToChunks( request_data, uri, text_edit ):
  """Returns a list of FixItChunks from a LSP textEdit."""
  try:
    filepath = lsp.UriToFilePath( uri )
  except lsp.InvalidUriException:
    LOGGER.debug( 'Invalid filepath received in TextEdit' )
    filepath = ''

  contents = GetFileLines( request_data, filepath )
  return [
    responses.FixItChunk( change[ 'newText' ],
                          _BuildRange( contents,
                                       filepath,
                                       change[ 'range' ] ) )
    for change in text_edit
  ]


def WorkspaceEditToFixIt( request_data,
                          workspace_edit,
                          text='',
                          kind = None ):
  """Converts a LSP workspace edit to a ycmd FixIt suitable for passing to
  responses.BuildFixItResponse."""

  if not workspace_edit:
    return None

  if 'changes' in workspace_edit:
    chunks = []
    # We sort the filenames to make the response stable. Edits are applied in
    # strict sequence within a file, but apply to files in arbitrary order.
    # However, it's important for the response to be stable for the tests.
    for uri in sorted( workspace_edit[ 'changes' ].keys() ):
      chunks.extend( TextEditToChunks( request_data,
                                       uri,
                                       workspace_edit[ 'changes' ][ uri ] ) )
  else:
    chunks = []
    for text_document_edit in workspace_edit[ 'documentChanges' ]:
      uri = text_document_edit[ 'textDocument' ][ 'uri' ]
      edits = text_document_edit[ 'edits' ]
      chunks.extend( TextEditToChunks( request_data, uri, edits ) )
  return responses.FixIt(
    responses.Location( request_data[ 'line_num' ],
                        request_data[ 'column_num' ],
                        request_data[ 'filepath' ] ),
    chunks,
    text,
    kind )


class LanguageServerCompletionsCache( CompletionsCache ):
  """Cache of computed LSP completions for a particular request."""

  def Invalidate( self ):
    with self._access_lock:
      super().InvalidateNoLock()
      self._is_incomplete = False
      self._use_start_column = True


  def Update( self, request_data, completions, is_incomplete ):
    with self._access_lock:
      super().UpdateNoLock( request_data, completions )
      self._is_incomplete = is_incomplete
      if is_incomplete:
        self._use_start_column = False


  def GetCodepointForCompletionRequest( self, request_data ):
    with self._access_lock:
      if self._use_start_column:
        return request_data[ 'start_codepoint' ]
      return request_data[ 'column_codepoint' ]


  # Must be called under the lock.
  def _IsQueryPrefix( self, request_data ):
    return request_data[ 'query' ].startswith( self._request_data[ 'query' ] )


  def GetCompletionsIfCacheValid( self,
                                  request_data,
                                  **kwargs ):
    with self._access_lock:
      if ( ( not self._is_incomplete
             or kwargs.get( 'ignore_incomplete' ) ) and
           ( self._use_start_column or self._IsQueryPrefix( request_data ) ) ):
        return super().GetCompletionsIfCacheValidNoLock( request_data )
      return None


class RejectCollector:
  def CollectApplyEdit( self, request, connection ):
    connection.SendResponse( lsp.ApplyEditResponse( request, False ) )


class EditCollector:
  def __init__( self ):
    self.requests = []


  def CollectApplyEdit( self, request, connection ):
    self.requests.append( request[ 'params' ] )
    connection.SendResponse( lsp.ApplyEditResponse( request, True ) )


class WatchdogHandler( PatternMatchingEventHandler ):
  def __init__( self, server, patterns ):
    super().__init__( patterns )
    self._server = server


  def on_created( self, event ):
    if self._server.ServerIsReady():
      with self._server._server_info_mutex:
        msg = lsp.DidChangeWatchedFiles( event.src_path, 'create' )
        self._server.GetConnection().SendNotification( msg )


  def on_modified( self, event ):
    if self._server.ServerIsReady():
      with self._server._server_info_mutex:
        msg = lsp.DidChangeWatchedFiles( event.src_path, 'modify' )
        self._server.GetConnection().SendNotification( msg )


  def on_deleted( self, event ):
    if self._server.ServerIsReady():
      with self._server._server_info_mutex:
        msg = lsp.DidChangeWatchedFiles( event.src_path, 'delete' )
        self._server.GetConnection().SendNotification( msg )


class TokenAtlas:
  def __init__( self, legend ):
    self.tokenTypes = legend[ 'tokenTypes' ]
    self.tokenModifiers = legend[ 'tokenModifiers' ]


def _DecodeSemanticTokens( atlas, token_data, filename, contents ):
  # We decode the tokens on the server because that's not blocking the user,
  # whereas decoding in the client would be.
  assert len( token_data ) % 5 == 0

  class Token:
    line = 0
    start_character = 0
    num_characters = 0
    token_type = 0
    token_modifiers = 0

    def DecodeModifiers( self, tokenModifiers ):
      modifiers = []
      bit_index = 0
      while True:
        bit_value = pow( 2, bit_index )

        if bit_value > self.token_modifiers:
          break

        if self.token_modifiers & bit_value:
          modifiers.append( tokenModifiers[ bit_index ] )

        bit_index += 1

      return modifiers


  last_token = Token()
  tokens = []

  for token_index in range( 0, len( token_data ), 5 ):
    token = Token()

    token.line = last_token.line + token_data[ token_index ]

    token.start_character = token_data[ token_index + 1 ]
    if token.line == last_token.line:
      token.start_character += last_token.start_character

    token.num_characters = token_data[ token_index + 2 ]

    token.token_type = token_data[ token_index + 3 ]
    token.token_modifiers = token_data[ token_index + 4 ]

    tokens.append( {
      'range': responses.BuildRangeData( _BuildRange(
        contents,
        filename,
        {
          'start': {
            'line': token.line,
            'character': token.start_character,
          },
          'end': {
            'line': token.line,
            'character': token.start_character + token.num_characters,
          }
        }
      ) ),
      'type': atlas.tokenTypes[ token.token_type ],
      'modifiers': token.DecodeModifiers( atlas.tokenModifiers )
    } )

    last_token = token

  return tokens


def _IsCapabilityProvided( capabilities, query ):
  capability = capabilities.get( query )
  return bool( capability ) or capability == {}


def RetryOnFailure( expected_error_codes, num_retries = 3 ):
  for i in range( num_retries ):
    try:
      yield
      break
    except ResponseFailedException as e:
      if i < ( num_retries - 1 ) and e.error_code in expected_error_codes:
        continue
      else:
        raise
