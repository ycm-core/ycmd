# Copyright (C) 2017-2018 ycmd contributors
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

from future.utils import iteritems, iterkeys
import abc
import collections
import logging
import os
import queue
import threading

from ycmd import extra_conf_store, responses, utils
from ycmd.completers.completer import Completer
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

DEFAULT_SUBCOMMANDS_MAP = {
  'GoToDefinition': {
    'checker': lambda caps: caps.get( 'definitionProvider', False ),
    'handler': (
      lambda self, request_data, args: self.GoToDeclaration( request_data )
    ),
  },
  'GoToDeclaration': {
    'checker': lambda caps: caps.get( 'definitionProvider', False ),
    'handler': (
      lambda self, request_data, args: self.GoToDeclaration( request_data )
    ),
  },
  'GoTo': {
    'checker': lambda caps: caps.get( 'definitionProvider', False ),
    'handler': (
      lambda self, request_data, args: self.GoToDeclaration( request_data )
    ),
  },
  'GoToImprecise': {
    'checker': lambda caps: caps.get( 'definitionProvider', False ),
    'handler': (
      lambda self, request_data, args: self.GoToDeclaration( request_data )
    ),
  },
  'GoToReferences': {
    'checker': lambda caps: caps.get( 'referencesProvider', False ),
    'handler': (
      lambda self, request_data, args: self.GoToReferences( request_data )
    ),
  },
  'RefactorRename': {
    # This can be boolean | RenameOptions. But either way a simple if
    # works (i.e. if RenameOptions is supplied and nonempty, then boom we have
    # truthiness).
    'checker': lambda caps: caps.get( 'renameProvider', False ),
    'handler': (
      lambda self, request_data, args: self.RefactorRename( request_data,
                                                            args )
    ),
  },
  'Format': {
    'checker': lambda caps: caps.get( 'documentFormattingProvider', False ),
    'handler': (
      lambda self, request_data, args: self.Format( request_data )
    ),
  }
}


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
  pass # pragma: no cover


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


class Response( object ):
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
      raise ResponseFailedException( 'Request failed: {0}: {1}'.format(
        error.get( 'code', 0 ),
        error.get( 'message', 'No message' ) ) )

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


  @abc.abstractmethod
  def Shutdown( self ):
    pass # pragma: no cover


  @abc.abstractmethod
  def WriteData( self, data ):
    pass # pragma: no cover


  @abc.abstractmethod
  def ReadData( self, size=-1 ):
    pass # pragma: no cover


  def __init__( self, notification_handler = None ):
    super( LanguageServerConnection, self ).__init__()

    self._last_id = 0
    self._responses = {}
    self._response_mutex = threading.Lock()
    self._notifications = queue.Queue( maxsize=MAX_QUEUED_MESSAGES )

    self._connection_event = threading.Event()
    self._stop_event = threading.Event()
    self._notification_handler = notification_handler


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
        for _, response in iteritems( self._responses ):
          response.Abort()
        self._responses.clear()

      LOGGER.debug( 'Connection was closed cleanly' )
    except Exception:
      LOGGER.exception( 'The language server communication channel closed '
                        'unexpectedly. Issue a RestartServer command to '
                        'recover.' )

      # Abort any outstanding requests
      with self._response_mutex:
        for _, response in iteritems( self._responses ):
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
      return str( self._last_id )


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
            key, value = utils.ToUnicode( line ).split( ':', 1 )
            headers[ key.strip() ] = value.strip()

        read_bytes += 1

      if not headers_complete:
        prefix = data[ last_line : ]
        data = bytes( b'' )


    return data, read_bytes, headers


  def _DispatchMessage( self, message ):
    """Called in the message pump thread context when a complete message was
    read. For responses, calls the Response object's ResponseReceived method, or
    for notifications (unsolicited messages from the server), simply accumulates
    them in a Queue which is polled by the long-polling mechanism in
    LanguageServerCompleter."""
    if 'id' in message:
      with self._response_mutex:
        message_id = str( message[ 'id' ] )
        assert message_id in self._responses
        self._responses[ message_id ].ResponseReceived( message )
        del self._responses[ message_id ]
    else:
      self._AddNotificationToQueue( message )

      # If there is an immediate (in-message-pump-thread) handler configured,
      # call it.
      if self._notification_handler:
        self._notification_handler( self, message )


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
                server_stdin,
                server_stdout,
                notification_handler = None ):
    super( StandardIOLanguageServerConnection, self ).__init__(
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


  def Shutdown( self ):
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


class LanguageServerCompleter( Completer ):
  """
  Abstract completer implementation for Language Server Protocol. Concrete
  implementations are required to:
    - Handle downstream server state and create a LanguageServerConnection,
      returning it in GetConnection
      - Set its notification handler to self.GetDefaultNotificationHandler()
      - See below for Startup/Shutdown instructions
    - Implement any server-specific Commands in HandleServerCommand
    - Optionally override GetCustomSubcommands to return subcommand handlers
      that cannot be detected from the capabilities response.
    - Implement the following Completer abstract methods:
      - SupportedFiletypes
      - DebugInfo
      - Shutdown
      - ServerIsHealthy : Return True if the server is _running_
      - StartServer : Return True if the server was started.
      - Language : a string used to identify the language in user's extra conf
    - Optionally override methods to customise behavior:
      - _GetProjectDirectory
      - _GetTriggerCharacters
      - GetDefaultNotificationHandler
      - HandleNotificationInPollThread
      - ConvertNotificationToMessage

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
  - Other commands not covered by DEFAULT_SUBCOMMANDS_MAP are bespoke to the
    completer and should be returned by GetCustomSubcommands:
    - GetType/GetDoc are bespoke to the downstream server, though this class
      provides GetHoverResponse which is useful in this context.
    - FixIt requests are handled by GetCodeActions, but the responses are passed
      to HandleServerCommand, which must return a FixIt. See
      WorkspaceEditToFixIt and TextEditToChunks for some helpers. If the server
      returns other types of command that aren't FixIt, either throw an
      exception or update the ycmd protocol to handle it :)
  """
  @abc.abstractmethod
  def GetConnection( sefl ):
    """Method that must be implemented by derived classes to return an instance
    of LanguageServerConnection appropriate for the language server in
    question"""
    pass # pragma: no cover


  @abc.abstractmethod
  def HandleServerCommand( self, request_data, command ):
    pass # pragma: no cover


  def __init__( self, user_options ):
    super( LanguageServerCompleter, self ).__init__( user_options )

    # _server_info_mutex synchronises access to the state of the
    # LanguageServerCompleter object. There are a number of threads at play
    # here which might want to change properties of this object:
    #   - Each client request (handled by concrete completers) executes in a
    #     separate thread and might call methods requiring us to synchronise the
    #     server's view of file state with our own. We protect from clobbering
    #     by doing all server-file-state operations under this mutex.
    #   - There are certain events that we handle in the message pump thread.
    #     These include diagnostics and some parts of initialization. We must
    #     protect against concurrent access to our internal state (such as the
    #     server file state, and stored data about the server itself) when we
    #     are calling methods on this object from the message pump). We
    #     synchronise on this mutex for that.
    self._server_info_mutex = threading.Lock()
    self.ServerReset()


  def ServerReset( self ):
    """Clean up internal state related to the running server instance.
    Implementations are required to call this after disconnection and killing
    the downstream server."""
    with self._server_info_mutex:
      self._server_file_state = lsp.ServerFileStateStore()
      self._latest_diagnostics = collections.defaultdict( list )
      self._sync_type = 'Full'
      self._initialize_response = None
      self._initialize_event = threading.Event()
      self._on_initialize_complete_handlers = []
      self._server_capabilities = None
      self._resolve_completion_items = False
      self._project_directory = None
      self._settings = {}
      self._server_started = False

  @abc.abstractmethod
  def Language( self ):
    pass # pragma: no cover


  @abc.abstractmethod
  def StartServer( self, request_data, **kwargs ):
    pass # pragma: no cover


  def ShutdownServer( self ):
    """Send the shutdown and possibly exit request to the server.
    Implementations must call this prior to closing the LanguageServerConnection
    or killing the downstream server."""

    # Language server protocol requires orderly shutdown of the downstream
    # server by first sending a shutdown request, and on its completion sending
    # and exit notification (which does not receive a response). Some buggy
    # servers exit on receipt of the shutdown request, so we handle that too.
    if self.ServerIsReady():
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
      with self._server_info_mutex:
        self._initialize_response = None
        self._initialize_event.set()


  def ServerIsReady( self ):
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


  def ShouldUseNowInner( self, request_data ):
    # We should only do _anything_ after the initialize exchange has completed.
    return ( self.ServerIsReady() and
             super( LanguageServerCompleter, self ).ShouldUseNowInner(
               request_data ) )


  def GetCodepointForCompletionRequest( self, request_data ):
    """Returns the 1-based codepoint offset on the current line at which to make
    the completion request"""
    return request_data[ 'start_codepoint' ]


  def ComputeCandidatesInner( self, request_data ):
    if not self.ServerIsReady():
      return None

    self._UpdateServerWithFileContents( request_data )

    request_id = self.GetConnection().NextRequestId()

    msg = lsp.Completion(
      request_id,
      request_data,
      self.GetCodepointForCompletionRequest( request_data ) )
    response = self.GetConnection().GetResponse( request_id,
                                                 msg,
                                                 REQUEST_TIMEOUT_COMPLETION )

    if isinstance( response[ 'result' ], list ):
      items = response[ 'result' ]
    else:
      items = response[ 'result' ][ 'items' ]

    # Note: _CandidatesFromCompletionItems does a lot of work on the actual
    # completion text to ensure that the returned text and start_codepoint are
    # applicable to our model of a single start column.
    #
    # Unfortunately (perhaps) we have to do this both here and in
    # DetailCandidates when resolve is required. This is because the filtering
    # should be based on ycmd's version of the insertion_text. Fortunately it's
    # likely much quicker to do the simple calculations inline rather than a
    # series of potentially many blocking server round trips.
    return self._CandidatesFromCompletionItems( items,
                                                False, # don't do resolve
                                                request_data )


  def DetailCandidates( self, request_data, completions ):
    if not self._resolve_completion_items:
      # We already did all of the work.
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
      True, # Do a full resolve
      request_data )


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
    return self._server_capabilities.get( 'completionProvider', {} ).get(
      'resolveProvider',
      False )


  def _CandidatesFromCompletionItems( self, items, resolve, request_data ):
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
    for item in items:
      if resolve and not item.get( '_resolved', False ):
        self._ResolveCompletionItem( item )
        item[ '_resolved' ] = True

      try:
        insertion_text, extra_data, start_codepoint = (
          _InsertionTextForItem( request_data, item ) )
      except IncompatibleCompletionException:
        LOGGER.exception( 'Ignoring incompatible completion suggestion %s',
                          item )
        continue

      if not resolve and self._resolve_completion_items:
        # Store the actual item in the extra_data area of the completion item.
        # We'll use this later to do the full resolve.
        extra_data = {} if extra_data is None else extra_data
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
    } )
    commands.update( self.GetCustomSubcommands() )

    return self._DiscoverSubcommandSupport( commands )


  def _DiscoverSubcommandSupport( self, commands ):
    if not self._server_capabilities:
      LOGGER.warning( "Can't determine subcommands: not initialized yet" )
      capabilities = {}
    else:
      capabilities = self._server_capabilities

    subcommands_map = {}
    for command, handler in iteritems( commands ):
      if isinstance( handler, dict ):
        if handler[ 'checker' ]( capabilities ):
          LOGGER.info( 'Found support for command %s in %s',
                        command,
                        self.Language() )

          subcommands_map[ command ] = handler[ 'handler' ]
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


  def _GetSettings( self, module, client_data ):
    if hasattr( module, 'Settings' ):
      settings = module.Settings( language = self.Language(),
                                  client_data = client_data )
      if settings is not None:
        return settings

    LOGGER.debug( 'No Settings function defined in %s', module.__file__ )

    return {}


  def _GetSettingsFromExtraConf( self, request_data ):
    module = extra_conf_store.ModuleForSourceFile( request_data[ 'filepath' ] )
    if module:
      settings = self._GetSettings( module, request_data[ 'extra_conf_data' ] )
      self._settings = settings.get( 'ls', {} )
      # Only return the dir if it was found in the paths; we don't want to use
      # the path of the global extra conf as a project root dir.
      if not extra_conf_store.IsGlobalExtraConfModule( module ):
        LOGGER.debug( 'Using path %s for extra_conf_dir',
                      os.path.dirname( module.__file__ ) )
        return os.path.dirname( module.__file__ )

    return None


  def _StartAndInitializeServer( self, request_data, *args, **kwargs ):
    """Starts the server and sends the initialize request, assuming the start is
    successful. |args| and |kwargs| are passed through to the underlying call to
    StartServer. In general, completers don't need to call this as it is called
    automatically in OnFileReadyToParse, but this may be used in completer
    subcommands that require restarting the underlying server."""
    extra_conf_dir = self._GetSettingsFromExtraConf( request_data )

    # Only attempt to start the server once. Set this after above call as it may
    # throw an exception
    self._server_started = True

    if self.StartServer( request_data, *args, **kwargs ):
      self._SendInitialize( request_data, extra_conf_dir )


  def OnFileReadyToParse( self, request_data ):
    if not self.ServerIsHealthy() and not self._server_started:
      # We have to get the settings before starting the server, as this call
      # might throw UnknownExtraConf.
      self._StartAndInitializeServer( request_data )

    if not self.ServerIsHealthy():
      return

    # If we haven't finished initializing yet, we need to queue up a call to
    # _UpdateServerWithFileContents. This ensures that the server is up to date
    # as soon as we are able to send more messages. This is important because
    # server start up can be quite slow and we must not block the user, while we
    # must keep the server synchronized.
    if not self._initialize_event.is_set():
      self._OnInitializeComplete(
        lambda self: self._UpdateServerWithFileContents( request_data ) )
      return

    self._UpdateServerWithFileContents( request_data )

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
    with self._server_info_mutex:
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

          # If the timeout is hit waiting for the server to be ready, we return
          # False and kill the message poll.
          return self._initialize_event.is_set()

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
      # Since percent-encoded strings are not cannonical, they can choose to use
      # upper case or lower case letters, also there are some characters that
      # can be encoded or not. Therefore, we convert them back and forth
      # according to our implementation to make sure they are in a cannonical
      # form for access later on.
      uri = lsp.FilePathToUri( lsp.UriToFilePath( params[ 'uri' ] ) )
      with self._server_info_mutex:
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
        LOGGER.exception( 'Ignoring diagnostics for unrecognized URI' )
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


  def _UpdateServerWithFileContents( self, request_data ):
    """Update the server with the current contents of all open buffers, and
    close any buffers no longer open.

    This method should be called frequently and in any event before a
    synchronous operation."""
    with self._server_info_mutex:
      self._UpdateDirtyFilesUnderLock( request_data )
      files_to_purge = self._UpdateSavedFilesUnderLock( request_data )
      self._PurgeMissingFilesUnderLock( files_to_purge )


  def _UpdateDirtyFilesUnderLock( self, request_data ):
    for file_name, file_data in iteritems( request_data[ 'file_data' ] ):
      if not self._AnySupportedFileType( file_data[ 'filetypes' ] ):
        continue

      file_state = self._server_file_state[ file_name ]
      action = file_state.GetDirtyFileAction( file_data[ 'contents' ] )

      LOGGER.debug( 'Refreshing file %s: State is %s/action %s',
                    file_name,
                    file_state.state,
                    action )

      if action == lsp.ServerFileState.OPEN_FILE:
        msg = lsp.DidOpenTextDocument( file_state,
                                       file_data[ 'filetypes' ],
                                       file_data[ 'contents' ] )

        self.GetConnection().SendNotification( msg )
      elif action == lsp.ServerFileState.CHANGE_FILE:
        # FIXME: DidChangeTextDocument doesn't actually do anything
        # different from DidOpenTextDocument other than send the right
        # message, because we don't actually have a mechanism for generating
        # the diffs. This isn't strictly necessary, but might lead to
        # performance problems.
        msg = lsp.DidChangeTextDocument( file_state, file_data[ 'contents' ] )

        self.GetConnection().SendNotification( msg )


  def _UpdateSavedFilesUnderLock( self, request_data ):
    files_to_purge = []
    for file_name, file_state in iteritems( self._server_file_state ):
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


  def _GetProjectDirectory( self, request_data, extra_conf_dir ):
    """Return the directory in which the server should operate. Language server
    protocol and most servers have a concept of a 'project directory'. Where a
    concrete completer can detect this better, it should override this method,
    but otherwise, we default as follows:
      - if there's an extra_conf file, use that directory
      - otherwise if we know the client's cwd, use that
      - otherwise use the diretory of the file that we just opened
    Note: None of these are ideal. Ycmd doesn't really have a notion of project
    directory and therefore neither do any of our clients."""

    if extra_conf_dir:
      return extra_conf_dir

    if 'working_dir' in request_data:
      return request_data[ 'working_dir' ]

    return os.path.dirname( request_data[ 'filepath' ] )


  def _SendInitialize( self, request_data, extra_conf_dir ):
    """Sends the initialize request asynchronously.
    This must be called immediately after establishing the connection with the
    language server. Implementations must not issue further requests to the
    server until the initialize exchange has completed. This can be detected by
    calling this class's implementation of ServerIsReady.
    The extra_conf_dir parameter is the value returned from
    _GetSettingsFromExtraConf, which must be called before calling this method.
    It is called before starting the server in OnFileReadyToParse."""

    with self._server_info_mutex:
      assert not self._initialize_response

      self._project_directory = self._GetProjectDirectory( request_data,
                                                           extra_conf_dir )
      request_id = self.GetConnection().NextRequestId()

      # FIXME: According to the discussion on
      # https://github.com/Microsoft/language-server-protocol/issues/567
      # the settings on the Initialize request are somehow subtly different from
      # the settings supplied in didChangeConfiguration, though it's not exactly
      # clear how/where that is specified.
      msg = lsp.Initialize( request_id,
                            self._project_directory,
                            self._settings )

      def response_handler( response, message ):
        if message is None:
          return

        self._HandleInitializeInPollThread( message )

      self._initialize_response = self.GetConnection().GetResponseAsync(
        request_id,
        msg,
        response_handler )


  def _GetTriggerCharacters( self, server_trigger_characters ):
    """Given the server trigger characters supplied in the initialize response,
    returns the trigger characters to merge with the ycmd-defined ones. By
    default, all server trigger characters are merged in. Note this might not be
    appropriate in all cases as ycmd's own triggering mechanism is more
    sophisticated (regex based) than LSP's (single character). If the
    server-supplied single-character triggers are not useful, override this
    method to return an empty list or None."""
    return server_trigger_characters


  def _HandleInitializeInPollThread( self, response ):
    """Called within the context of the LanguageServerConnection's message pump
    when the initialize request receives a response."""
    with self._server_info_mutex:
      self._server_capabilities = response[ 'result' ][ 'capabilities' ]
      self._resolve_completion_items = self._ShouldResolveCompletionItems()

      if 'textDocumentSync' in self._server_capabilities:
        sync = self._server_capabilities[ 'textDocumentSync' ]
        SYNC_TYPE = [
          'None',
          'Full',
          'Incremental'
        ]

        # The sync type can either be a number or an object. Because it's
        # important to make things difficult.
        if isinstance( sync, dict ):
          # FIXME: We should really actually check all of the other things that
          # could exist in this structure.
          if 'change' in sync:
            sync = sync[ 'change' ]
          else:
            sync = 1

        self._sync_type = SYNC_TYPE[ sync ]
        LOGGER.info( 'Language server requires sync type of %s',
                     self._sync_type )

      # Update our semantic triggers if they are supplied by the server
      if self.prepared_triggers is not None:
        server_trigger_characters = (
          ( self._server_capabilities.get( 'completionProvider' ) or {} )
                                     .get( 'triggerCharacters' ) or []
        )
        LOGGER.debug( '%s: Server declares trigger characters: %s',
                      self.Language(),
                      server_trigger_characters )

        trigger_characters = self._GetTriggerCharacters(
          server_trigger_characters )

        if trigger_characters:
          LOGGER.info( '%s: Using trigger characters for semantic triggers: %s',
                       self.Language(),
                       ','.join( trigger_characters ) )

          self.prepared_triggers.SetServerSemanticTriggers(
            trigger_characters )

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
          lsp.DidChangeConfiguration( self._settings ) )

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


  def GetHoverResponse( self, request_data ):
    """Return the raw LSP response to the hover request for the supplied
    context. Implementations can use this for e.g. GetDoc and GetType requests,
    depending on the particular server response."""
    if not self.ServerIsReady():
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
    raise RuntimeError( NO_HOVER_INFORMATION )


  def GoToDeclaration( self, request_data ):
    """Issues the definition request and returns the result as a GoTo
    response."""
    if not self.ServerIsReady():
      raise RuntimeError( 'Server is initializing. Please wait.' )

    self._UpdateServerWithFileContents( request_data )

    request_id = self.GetConnection().NextRequestId()
    response = self.GetConnection().GetResponse(
      request_id,
      lsp.Definition( request_id, request_data ),
      REQUEST_TIMEOUT_COMMAND )

    if isinstance( response[ 'result' ], list ):
      return _LocationListToGoTo( request_data, response )
    elif response[ 'result' ]:
      position = response[ 'result' ]
      try:
        return responses.BuildGoToResponseFromLocation(
          *_PositionToLocationAndDescription( request_data, position ) )
      except KeyError:
        raise RuntimeError( 'Cannot jump to location' )
    else:
      raise RuntimeError( 'Cannot jump to location' )


  def GoToReferences( self, request_data ):
    """Issues the references request and returns the result as a GoTo
    response."""
    if not self.ServerIsReady():
      raise RuntimeError( 'Server is initializing. Please wait.' )

    self._UpdateServerWithFileContents( request_data )

    request_id = self.GetConnection().NextRequestId()
    response = self.GetConnection().GetResponse(
      request_id,
      lsp.References( request_id, request_data ),
      REQUEST_TIMEOUT_COMMAND )

    return _LocationListToGoTo( request_data, response )


  def GetCodeActions( self, request_data, args ):
    """Performs the codeAction request and returns the result as a FixIt
    response."""
    if not self.ServerIsReady():
      raise RuntimeError( 'Server is initializing. Please wait.' )

    self._UpdateServerWithFileContents( request_data )

    line_num_ls = request_data[ 'line_num' ] - 1

    def WithinRange( diag ):
      start = diag[ 'range' ][ 'start' ]
      end = diag[ 'range' ][ 'end' ]

      if line_num_ls < start[ 'line' ] or line_num_ls > end[ 'line' ]:
        return False

      return True

    with self._server_info_mutex:
      file_diagnostics = list( self._latest_diagnostics[
          lsp.FilePathToUri( request_data[ 'filepath' ] ) ] )

    matched_diagnostics = [
      d for d in file_diagnostics if WithinRange( d )
    ]

    request_id = self.GetConnection().NextRequestId()
    if matched_diagnostics:
      code_actions = self.GetConnection().GetResponse(
        request_id,
        lsp.CodeAction( request_id,
                        request_data,
                        matched_diagnostics[ 0 ][ 'range' ],
                        matched_diagnostics ),
        REQUEST_TIMEOUT_COMMAND )

    else:
      line_value = request_data[ 'line_value' ]

      code_actions = self.GetConnection().GetResponse(
        request_id,
        lsp.CodeAction(
          request_id,
          request_data,
          # Use the whole line
          {
            'start': {
              'line': line_num_ls,
              'character': 0,
            },
            'end': {
              'line': line_num_ls,
              'character': lsp.CodepointsToUTF16CodeUnits(
                line_value,
                len( line_value ) + 1 ) - 1,
            }
          },
          [] ),
        REQUEST_TIMEOUT_COMMAND )

    response = [ self.HandleServerCommand( request_data, c )
                 for c in code_actions[ 'result' ] ]

    # Show a list of actions to the user to select which one to apply.
    # This is (probably) a more common workflow for "code action".
    return responses.BuildFixItResponse( [ r for r in response if r ] )


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
    response = self.GetConnection().GetResponse(
      request_id,
      lsp.Rename( request_id, request_data, new_name ),
      REQUEST_TIMEOUT_COMMAND )

    return responses.BuildFixItResponse(
      [ WorkspaceEditToFixIt( request_data, response[ 'result' ] ) ] )


  def Format( self, request_data ):
    """Issues the formatting or rangeFormatting request (depending on the
    presence of a range) and returns the result as a FixIt response."""
    if not self.ServerIsReady():
      raise RuntimeError( 'Server is initializing. Please wait.' )

    self._UpdateServerWithFileContents( request_data )

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

      if not self.ServerIsReady():
        return 'Starting...'

      return 'Initialized'

    return [ responses.DebugInfoItem( 'Server State',
                                      ServerStateDescription() ),
             responses.DebugInfoItem( 'Project Directory',
                                      self._project_directory ) ]


def _CompletionItemToCompletionData( insertion_text, item, fixits ):
  # Since we send completionItemKind capabilities, we guarantee to handle
  # values outside our value set and fall back to a default.
  try:
    kind = lsp.ITEM_KIND[ item.get( 'kind', 0 ) ]
  except IndexError:
    kind = lsp.ITEM_KIND[ 0 ] # Fallback to None for unsupported kinds.
  return responses.BuildCompletionData(
    insertion_text,
    extra_menu_info = item.get( 'detail', None ),
    detailed_info = ( item[ 'label' ] +
                      '\n\n' +
                      item.get( 'documentation', '' ) ),
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
    item.get( 'insertTextFormat', 1 ) ] == 'PlainText'

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

  additional_text_edits.extend( item.get( 'additionalTextEdits', [] ) )

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
    raise IncompatibleCompletionException(
      "The TextEdit '{0}' spans multiple lines".format(
        text_edit[ 'newText' ] ) )

  file_contents = GetFileLines( request_data, request_data[ 'filepath' ] )
  line_value = file_contents[ edit_range[ 'start' ][ 'line' ] ]

  start_codepoint = lsp.UTF16CodeUnitsToCodepoints(
    line_value,
    edit_range[ 'start' ][ 'character' ] + 1 )

  if start_codepoint > request_data[ 'start_codepoint' ]:
    raise IncompatibleCompletionException(
      "The TextEdit '{0}' starts after the start position".format(
        text_edit[ 'newText' ] ) )

  return start_codepoint


def _LocationListToGoTo( request_data, response ):
  """Convert a LSP list of locations to a ycmd GoTo response."""
  if not response:
    raise RuntimeError( 'Cannot jump to location' )

  try:
    if len( response[ 'result' ] ) > 1:
      positions = response[ 'result' ]
      return [
        responses.BuildGoToResponseFromLocation(
          *_PositionToLocationAndDescription( request_data,
                                              position ) )
        for position in positions
      ]
    else:
      position = response[ 'result' ][ 0 ]
      return responses.BuildGoToResponseFromLocation(
        *_PositionToLocationAndDescription( request_data, position ) )
  except ( IndexError, KeyError ):
    raise RuntimeError( 'Cannot jump to location' )


def _PositionToLocationAndDescription( request_data, position ):
  """Convert a LSP position to a ycmd location."""
  try:
    filename = lsp.UriToFilePath( position[ 'uri' ] )
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
                                       position[ 'range' ][ 'start' ] )


def _BuildLocationAndDescription( filename, file_contents, loc ):
  """Returns a tuple of (
    - ycmd Location for the supplied filename and LSP location
    - contents of the line at that location
  )
  Importantly, converts from LSP Unicode offset to ycmd byte offset."""

  try:
    line_value = file_contents[ loc[ 'line' ] ]
    column = utils.CodepointOffsetToByteOffset(
      line_value,
      lsp.UTF16CodeUnitsToCodepoints( line_value, loc[ 'character' ] + 1 ) )
  except IndexError:
    # This can happen when there are stale diagnostics in OnFileReadyToParse,
    # just return the value as-is.
    line_value = ""
    column = loc[ 'character' ] + 1

  return ( responses.Location( loc[ 'line' ] + 1,
                               column,
                               filename = filename ),
           line_value )


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

  return responses.Diagnostic(
    ranges = [ r ],
    location = r.start_,
    location_extent = r,
    text = diag[ 'message' ],
    kind = lsp.SEVERITY[ diag[ 'severity' ] ].upper() )


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


def WorkspaceEditToFixIt( request_data, workspace_edit, text='' ):
  """Converts a LSP workspace edit to a ycmd FixIt suitable for passing to
  responses.BuildFixItResponse."""

  if 'changes' not in workspace_edit:
    return None

  chunks = []
  # We sort the filenames to make the response stable. Edits are applied in
  # strict sequence within a file, but apply to files in arbitrary order.
  # However, it's important for the response to be stable for the tests.
  for uri in sorted( iterkeys( workspace_edit[ 'changes' ] ) ):
    chunks.extend( TextEditToChunks( request_data,
                                     uri,
                                     workspace_edit[ 'changes' ][ uri ] ) )

  return responses.FixIt(
    responses.Location( request_data[ 'line_num' ],
                        request_data[ 'column_num' ],
                        request_data[ 'filepath' ] ),
    chunks,
    text )
