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

from future.utils import iteritems, iterkeys
import abc
import collections
import logging
import os
import queue
import threading

from ycmd.completers.completer import Completer
from ycmd.completers.completer_utils import GetFileContents
from ycmd import utils
from ycmd import responses

from ycmd.completers.language_server import lsapi

_logger = logging.getLogger( __name__ )

SERVER_LOG_PREFIX = 'Server reported: '

REQUEST_TIMEOUT_COMPLETION = 5
REQUEST_TIMEOUT_INITIALISE = 30
REQUEST_TIMEOUT_COMMAND    = 30
CONNECTION_TIMEOUT         = 5
MESSAGE_POLL_TIMEOUT       = 10


class ResponseTimeoutException( Exception ):
  pass


class ResponseAbortedException( Exception ):
  pass


class ResponseFailedException( Exception ):
  pass


class IncompatibleCompletionException( Exception ):
  pass


class Response( object ):
  def __init__( self, response_callback=None ):
    self._event = threading.Event()
    self._message = None
    self._response_callback = response_callback


  def ResponseReceived( self, message ):
    self._message = message
    self._event.set()
    if self._response_callback:
      self._response_callback( self, message )


  def Abort( self ):
    self.ResponseReceived( None )


  def AwaitResponse( self, timeout ):
    self._event.wait( timeout )

    if not self._event.isSet():
      raise ResponseTimeoutException( 'Response Timeout' )

    if self._message is None:
      raise ResponseAbortedException( 'Response Aborted' )

    if 'error' in self._message:
      error = self._message[ 'error' ]
      raise ResponseFailedException( 'Request failed: {0}: {1}'.format(
        error.get( 'code', 0 ),
        error.get( 'message', 'No message' ) ) )

    return self._message


class LanguageServerConnectionTimeout( Exception ):
  pass


class LanguageServerConnectionStopped( Exception ):
  pass


class LanguageServerConnection( threading.Thread ):
  """
    Abstract language server communication object.

    This connection runs as a thread and is generally only used directly by
    LanguageServerCompleter, but is instantiated, startd and stopped by Concrete
    LanguageServerCompleter implementations.

    Implementations of this class are required to provide the following methods:
      - _TryServerConnectionBlocking: Connect to the server and return when the
                                      connection is established
      - _Close: Close any sockets or channels prior to the thread exit
      - _Write: Write some data to the server
      - _Read: Read some data from the server, blocking until some data is
               available

    Using this class in concrete LanguageServerCompleter implementations:

    Startup

    - Call start() and AwaitServerConnection()
    - AwaitServerConnection() throws LanguageServerConnectionTimeout if the
      server fails to connect in a reasonable time.

    Shutdown

    - Call stop() prior to shutting down the downstream server (see
      LanguageServerCompleter.ShutdownServer to do that part)
    - Call join() after closing down the downstream server to wait for this
      thread to exit

    Footnote: Why does this interface exist?

    Language servers are at liberty to provide their communication interface
    over any transport. Typically, this is either stdio or a socket (though some
    servers require multiple sockets). This interface abstracts the
    implementation detail of the communication from the transport, allowing
    concrete completers to choose the right transport according to the
    downstream server (i.e. whatever works best).

    If in doubt, use the StandardIOLanguageServerConnection as that is the
    simplest. Socket-based connections often require the server to connect back
    to us, which can lead to complexity and possibly blocking.
  """
  @abc.abstractmethod
  def _TryServerConnectionBlocking( self ):
    pass


  @abc.abstractmethod
  def _Close( self ):
    pass


  @abc.abstractmethod
  def _Write( self, data ):
    pass


  @abc.abstractmethod
  def _Read( self, size=-1 ):
    pass


  def __init__( self, notification_handler = None ):
    super( LanguageServerConnection, self ).__init__()

    self._lastId = 0
    self._responses = {}
    self._responseMutex = threading.Lock()
    self._notifications = queue.Queue()

    self._connection_event = threading.Event()
    self._stop_event = threading.Event()
    self._notification_handler = notification_handler


  def run( self ):
    try:
      # Wait for the connection to fully establish (this runs in the thread
      # context, so we block until a connection is received or there is a
      # timeout, which throws an exception)
      self._TryServerConnectionBlocking()
      self._connection_event.set()

      # Blocking loop which reads whole messages and calls _DespatchMessage
      self._ReadMessages( )
    except LanguageServerConnectionStopped:
      # Abort any outstanding requests
      with self._responseMutex:
        for _, response in iteritems( self._responses ):
          response.Abort()
        self._responses.clear()

      _logger.debug( 'Connection was closed cleanly' )

    self._Close()


  def stop( self ):
    # Note lowercase stop() to match threading.Thread.start()
    self._stop_event.set()


  def IsStopped( self ):
    return self._stop_event.is_set()


  def NextRequestId( self ):
    with self._responseMutex:
      self._lastId += 1
      return str( self._lastId )


  def GetResponseAsync( self, request_id, message, response_callback=None ):
    response = Response( response_callback )

    with self._responseMutex:
      assert request_id not in self._responses
      self._responses[ request_id ] = response

    _logger.debug( 'TX: Sending message {0}'.format( message ) )

    self._Write( message )
    return response


  def GetResponse( self, request_id, message, timeout ):
    response = self.GetResponseAsync( request_id, message )
    return response.AwaitResponse( timeout )


  def SendNotification( self, message ):
    _logger.debug( 'TX: Sending Notification {0}'.format( message ) )

    self._Write( message )


  def AwaitServerConnection( self ):
    self._connection_event.wait( timeout = CONNECTION_TIMEOUT )

    if not self._connection_event.isSet():
      raise LanguageServerConnectionTimeout(
        'Timed out waiting for server to connect' )


  def _ReadHeaders( self, data ):
    headers_complete = False
    prefix = bytes( b'' )
    headers = {}

    while not headers_complete:
      read_bytes = 0
      last_line = 0
      if len( data ) == 0:
        data = self._Read()

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


    return ( data, read_bytes, headers )


  def _ReadMessages( self ):
    data = bytes( b'' )
    while True:
      ( data, read_bytes, headers ) = self._ReadHeaders( data )

      if 'Content-Length' not in headers:
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
        data = self._Read( content_length - content_read )
        content_to_read = min( content_length - content_read, len( data ) )
        content += data[ : content_to_read ]
        content_read += len( content )
        read_bytes = content_to_read

      # lsapi will convert content to unicode
      self._DespatchMessage( lsapi.Parse( content ) )

      # We only consumed len( content ) of data. If there is more, we start
      # again with the remainder and look for headers
      data = data[ read_bytes : ]


  def _DespatchMessage( self, message ):
    _logger.debug( 'RX: Received message: {0}'.format( message ) )
    if 'id' in message:
      with self._responseMutex:
        assert str( message[ 'id' ] ) in self._responses
        self._responses[ str( message[ 'id' ] ) ].ResponseReceived( message )
        del self._responses[ str( message[ 'id' ] ) ]
    else:
      self._notifications.put( message )

      if self._notification_handler:
        self._notification_handler( self, message )


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


  def _TryServerConnectionBlocking( self ):
    # standard in/out don't need to wait for the server to connect to us
    return True


  def _Close( self ):
    if not self._server_stdin.closed:
      self._server_stdin.close()

    if not self._server_stdout.closed:
      self._server_stdout.close()


  def _Write( self, data ):
    bytes_to_write = data + utils.ToBytes( '\r\n' )
    self._server_stdin.write( bytes_to_write )
    self._server_stdin.flush()


  def _Read( self, size=-1 ):
    if size > -1:
      data = self._server_stdout.read( size )
    else:
      data = self._server_stdout.readline()

    if self.IsStopped():
      raise LanguageServerConnectionStopped()

    if not data:
      # No data means the connection was severed. Connection severed when (not
      # self.IsStopped()) means the server died unexpectedly.
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
    - Implement the following Completer abstract methods:
      - SupportedFiletypes
      - DebugInfo
      - Shutdown
      - ServerIsHealthy : Return True if the server is _running_
      - GetSubcommandsMap

  Startup

  - After starting and connecting to the server, call SendInitialise
  - See also LanguageServerConnection requirements

  Shutdown

  - Call ShutdownServer and wait for the downstream server to exit
  - Call ServerReset to clear down state
  - See also LanguageServerConnection requirements

  Completions

  - The implementation should not require any code to support completions

  Diagnostics

  - The implementation should not require any code to support diagnostics

  Subcommands

  - The subcommands map is bespoke to the implementation, but generally, this
    class attempts to provide all of the pieces where it can generically.
  - The following commands typically don't require any special handling, just
    call the base implementation as below:
      Subcommands     -> Handler
    - GoToDeclaration -> GoToDeclaration
    - GoTo            -> GoToDeclaration
    - GoToReferences  -> GoToReferences
    - RefactorRename  -> Rename
  - GetType/GetDoc are bespoke to the downstream server, though this class
    provides GetHoverResponse which is useful in this context.
  - FixIt requests are handled by CodeAction, but the responses are passed to
    HandleServerCommand, which must return a FixIt. See WorkspaceEditToFixIt and
    TextEditToChunks for some helpers. If the server returns other types of
    command that aren't FixIt, either throw an exception or update the ycmd
    protocol to handle it :)
  """
  @abc.abstractmethod
  def GetConnection( sefl ):
    """Method that must be implemented by derived classes to return an instance
    of LanguageServerConnection appropriate for the language server in
    question"""
    pass


  @abc.abstractmethod
  def HandleServerCommand( self, request_data, command ):
    pass


  def __init__( self, user_options):
    super( LanguageServerCompleter, self ).__init__( user_options )
    self._mutex = threading.Lock()
    self.ServerReset()


  def ServerReset( self ):
    with self._mutex:
      self._serverFileState = {}
      self._latest_diagnostics = collections.defaultdict( list )
      self._syncType = 'Full'
      self._initialise_response = None
      self._initialise_event = threading.Event()


  def ShutdownServer( self ):
    if self.ServerIsReady():
      request_id = self.GetConnection().NextRequestId()
      msg = lsapi.Shutdown( request_id )

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
        _logger.exception( 'Shutdown request failed. Ignoring.' )

    if self.ServerIsHealthy():
      self.GetConnection().SendNotification( lsapi.Exit() )


  def ServerIsReady( self ):
    if not self.ServerIsHealthy():
      return False

    if self._initialise_event.is_set():
      # We already got the initialise response
      return True

    if self._initialise_response is None:
      # We never sent the initialise response
      return False

    # Initialise request in progress. Will be handled asynchronously.
    return False


  def ShouldUseNowInner( self, request_data ):
    return ( self.ServerIsReady() and
             super( LanguageServerCompleter, self ).ShouldUseNowInner(
               request_data ) )


  def ComputeCandidatesInner( self, request_data ):
    if not self.ServerIsReady():
      return None

    self._RefreshFiles( request_data )

    request_id = self.GetConnection().NextRequestId()
    msg = lsapi.Completion( request_id, request_data )
    response = self.GetConnection().GetResponse( request_id,
                                                 msg,
                                                 REQUEST_TIMEOUT_COMPLETION )

    do_resolve = (
      'completionProvider' in self._server_capabilities and
      self._server_capabilities[ 'completionProvider' ].get( 'resolveProvider',
                                                             False ) )

    if isinstance( response[ 'result' ], list ):
      items = response[ 'result' ]
    else:
      items = response[ 'result' ][ 'items' ]

    return self.ResolveCompletionItems( items, request_data, do_resolve )


  def ResolveCompletionItems( self, items, request_data, do_resolve ):
    _logger.debug( 'Completion Start: {0}'.format( request_data[
      'start_codepoint' ] ) )
    # Note Vim only displays the first character, so we map them to the
    # documented Vim kinds:
    #
    #   v variable
    #   f function or method
    #   m member of a struct or class
    #   t typedef
    #   d #define or macro
    #
    # FIXME: I'm not happy with this completely. We're losing useful info,
    # perhaps unnecessarily.
    ITEM_KIND = [
      None,  # 1-based
      'd',   # 'Text',
      'f',   # 'Method',
      'f',   # 'Function',
      'f',   # 'Constructor',
      'm',   # 'Field',
      'm',   # 'Variable',
      't',   # 'Class',
      't',   # 'Interface',
      't',   # 'Module',
      't',   # 'Property',
      't',   # 'Unit',
      'd',   # 'Value',
      't',   # 'Enum',
      'd',   # 'Keyword',
      'd',   # 'Snippet',
      'd',   # 'Color',
      'd',   # 'File',
      'd',   # 'Reference',
    ]

    completions = list()
    start_codepoints = list()
    min_start_codepoint = request_data[ 'start_codepoint' ]

    # First generate all of the completion items and store their
    # start_codepoints.  Then, we fix-up the completion texts to use the
    # earliest start_codepoint by borrowing text from the original line.
    for item in items:
      # First, resolve the completion.
      if do_resolve:
        try:
          resolve_id = self.GetConnection().NextRequestId()
          resolve = lsapi.ResolveCompletion( resolve_id, item )
          response = self.GetConnection().GetResponse(
            resolve_id,
            resolve,
            REQUEST_TIMEOUT_COMPLETION )
          item = response[ 'result' ]
        except ResponseFailedException:
          _logger.exception( 'A completion item could not be resolved. Using '
                             'basic data.' )

      try:
        ( insertion_text, fixits, start_codepoint ) = (
          InsertionTextForItem( request_data, item ) )
      except IncompatibleCompletionException:
        _logger.exception( 'Ignoring incompatible completion suggestion '
                           '{0}'.format( item ) )
        continue

      min_start_codepoint = min( min_start_codepoint, start_codepoint )

      completions.append( responses.BuildCompletionData(
        insertion_text,
        extra_menu_info = item.get( 'detail', None ),
        detailed_info = ( item[ 'label' ] +
                          '\n\n' +
                          item.get( 'documentation', '' ) ),
        menu_text = item[ 'label' ],
        kind = ITEM_KIND[ item.get( 'kind', 0 ) ],
        extra_data = fixits ) )
      start_codepoints.append( start_codepoint )

    if ( len( completions ) > 1 and
         min_start_codepoint != request_data[ 'start_codepoint' ] ):
      return FixUpCompletionPrefixes( completions,
                                      start_codepoints,
                                      request_data,
                                      min_start_codepoint )

    request_data[ 'start_codepoint' ] = min_start_codepoint
    return completions


  def OnFileReadyToParse( self, request_data ):
    if not self.ServerIsReady():
      return

    self._RefreshFiles( request_data )

    # NOTE: We also return diagnostics asynchronously via the long-polling
    # mechanism to avoid timing issues with the servers asynchronous publication
    # of diagnostics.
    # However, we _also_ return them here to refresh diagnostics after, say
    # changing the active file in the editor.
    uri = lsapi.FilePathToUri( request_data[ 'filepath' ] )
    with self._mutex:
      if uri in self._latest_diagnostics:
        return [ BuildDiagnostic( request_data, uri, diag )
                 for diag in self._latest_diagnostics[ uri ] ]


  def PollForMessagesInner( self, request_data ):
    # scoop up any pending messages into one big list
    messages = list()
    try:
      while True:
        if not self.GetConnection():
          # The server isn't running or something. Don't re-poll.
          return False

        self._PollForMessagesNoBlock( request_data, messages )
    except queue.Empty:
      # We drained the queue
      pass

    # If we found some messages, return them immediately
    if messages:
      return messages

    # otherwise, block until we get one
    return self._PollForMessagesBlock( request_data )


  def _PollForMessagesNoBlock( self, request_data, messages ):
    notification = self.GetConnection()._notifications.get_nowait( )
    message = self._ConvertNotificationToMessage( request_data,
                                                  notification )
    if message:
      messages.append( message )


  def _PollForMessagesBlock( self, request_data ):
    try:
      while True:
        if not self.GetConnection():
          # The server isn't running or something. Don't re-poll, as this will
          # just cause errors.
          return False

        notification = self.GetConnection()._notifications.get(
          timeout = MESSAGE_POLL_TIMEOUT )
        message = self._ConvertNotificationToMessage( request_data,
                                                      notification )
        if message:
          return [ message ]
    except queue.Empty:
      return True


  def GetDefaultNotificationHandler( self ):
    def handler( server, notification ):
      self._HandleNotificationInPollThread( notification )
    return handler


  def _HandleNotificationInPollThread( self, notification ):
    if notification[ 'method' ] == 'textDocument/publishDiagnostics':
      # Some clients might not use a message poll, so we must store the
      # diagnostics and return them in OnFileReadyToParse
      params = notification[ 'params' ]
      uri = params[ 'uri' ]
      with self._mutex:
        self._latest_diagnostics[ uri ] = params[ 'diagnostics' ]


  def _ConvertNotificationToMessage( self, request_data, notification ):
    if notification[ 'method' ] == 'window/showMessage':
      return responses.BuildDisplayMessageResponse(
        notification[ 'params' ][ 'message' ] )
    elif notification[ 'method' ] == 'window/logMessage':
      log_level = [
        None, # 1-based enum from LSP
        logging.ERROR,
        logging.WARNING,
        logging.INFO,
        logging.DEBUG,
      ]

      params = notification[ 'params' ]
      _logger.log( log_level[ int( params[ 'type' ] ) ],
                   SERVER_LOG_PREFIX + params[ 'message' ] )
    elif notification[ 'method' ] == 'textDocument/publishDiagnostics':
      params = notification[ 'params' ]
      uri = params[ 'uri' ]
      filepath = lsapi.UriToFilePath( uri )
      response = {
        'diagnostics': [ BuildDiagnostic( request_data, uri, x )
                         for x in params[ 'diagnostics' ] ],
        'filepath': filepath
      }
      return response

    return None


  def _RefreshFiles( self, request_data ):
    with self._mutex:
      for file_name, file_data in iteritems( request_data[ 'file_data' ] ):
        file_state = 'New'
        if file_name in self._serverFileState:
          file_state = self._serverFileState[ file_name ]

        _logger.debug( 'Refreshing file {0}: State is {1}'.format(
          file_name, file_state ) )
        if file_state == 'New' or self._syncType == 'Full':
          msg = lsapi.DidOpenTextDocument( file_name,
                                           file_data[ 'filetypes' ],
                                           file_data[ 'contents' ] )
        else:
          # FIXME: DidChangeTextDocument doesn't actually do anything different
          # from DidOpenTextDocument because we don't actually have a mechanism
          # for generating the diffs (which would just be a waste of time)
          #
          # One option would be to just replace the entire file, but some
          # servers (I'm looking at you javac completer) don't update
          # diagnostics until you open or save a document. Sigh.
          msg = lsapi.DidChangeTextDocument( file_name,
                                             file_data[ 'filetypes' ],
                                             file_data[ 'contents' ] )

        self._serverFileState[ file_name ] = 'Open'
        self.GetConnection().SendNotification( msg )

      stale_files = list()
      for file_name in iterkeys( self._serverFileState ):
        if file_name not in request_data[ 'file_data' ]:
          stale_files.append( file_name )

      # We can't change the dictionary entries while using iterkeys, so we do
      # that in a separate loop.
      # TODO(Ben): Isn't there a client->server event when a buffer is closed?
      for file_name in stale_files:
          msg = lsapi.DidCloseTextDocument( file_name )
          self.GetConnection().SendNotification( msg )
          del self._serverFileState[ file_name ]


  def _GetProjectDirectory( self ):
    return utils.GetCurrentDirectory()


  def SendInitialise( self ):
    with self._mutex:
      assert not self._initialise_response

      request_id = self.GetConnection().NextRequestId()
      msg = lsapi.Initialise( request_id, self._GetProjectDirectory() )

      def response_handler( response, message ):
        if message is None:
          raise ResponseAbortedException( 'Initialise request aborted' )

        self._HandleInitialiseInPollThread( message )

      self._initialise_response = self.GetConnection().GetResponseAsync(
        request_id,
        msg,
        response_handler )


  def _HandleInitialiseInPollThread( self, response ):
    with self._mutex:
      self._server_capabilities = response[ 'result' ][ 'capabilities' ]

      if 'textDocumentSync' in response[ 'result' ][ 'capabilities' ]:
        SYNC_TYPE = [
          'None',
          'Full',
          'Incremental'
        ]
        self._syncType = SYNC_TYPE[
          response[ 'result' ][ 'capabilities' ][ 'textDocumentSync' ] ]
        _logger.info( 'Language Server requires sync type of {0}'.format(
          self._syncType ) )

      self._initialise_response = None
      self._initialise_event.set()


  def GetHoverResponse( self, request_data ):
    if not self.ServerIsReady():
      raise RuntimeError( 'Server is initialising. Please wait.' )

    self._RefreshFiles( request_data )

    request_id = self.GetConnection().NextRequestId()
    response = self.GetConnection().GetResponse(
      request_id,
      lsapi.Hover( request_id,
                   request_data ),
      REQUEST_TIMEOUT_COMMAND )

    return response[ 'result' ][ 'contents' ]


  def GoToDeclaration( self, request_data ):
    if not self.ServerIsReady():
      raise RuntimeError( 'Server is initialising. Please wait.' )

    self._RefreshFiles( request_data )

    request_id = self.GetConnection().NextRequestId()
    response = self.GetConnection().GetResponse(
      request_id,
      lsapi.Definition( request_id,
                        request_data ),
      REQUEST_TIMEOUT_COMMAND )

    if isinstance( response[ 'result' ], list ):
      return LocationListToGoTo( request_data, response )
    else:
      position = response[ 'result' ]
      return responses.BuildGoToResponseFromLocation(
        PositionToLocation( request_data, position ) )


  def GoToReferences( self, request_data ):
    if not self.ServerIsReady():
      raise RuntimeError( 'Server is initialising. Please wait.' )

    self._RefreshFiles( request_data )

    request_id = self.GetConnection().NextRequestId()
    response = self.GetConnection().GetResponse(
      request_id,
      lsapi.References( request_id,
                        request_data ),
      REQUEST_TIMEOUT_COMMAND )

    return LocationListToGoTo( request_data, response )


  def CodeAction( self, request_data, args ):
    if not self.ServerIsReady():
      raise RuntimeError( 'Server is initialising. Please wait.' )

    self._RefreshFiles( request_data )

    line_num_ls = request_data[ 'line_num' ] - 1

    def WithinRange( diag ):
      start = diag[ 'range' ][ 'start' ]
      end = diag[ 'range' ][ 'end' ]

      if line_num_ls < start[ 'line' ] or line_num_ls > end[ 'line' ]:
        return False

      return True

    with self._mutex:
      file_diagnostics = list( self._latest_diagnostics[
          lsapi.FilePathToUri( request_data[ 'filepath' ] ) ] )

    matched_diagnostics = [
      d for d in file_diagnostics if WithinRange( d )
    ]

    request_id = self.GetConnection().NextRequestId()
    if matched_diagnostics:
      code_actions = self.GetConnection().GetResponse(
        request_id,
        lsapi.CodeAction( request_id,
                          request_data,
                          matched_diagnostics[ 0 ][ 'range' ],
                          matched_diagnostics ),
        REQUEST_TIMEOUT_COMMAND )

    else:
      code_actions = self.GetConnection().GetResponse(
        request_id,
        lsapi.CodeAction(
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
              'character': len( request_data[ 'line_value' ] ) - 1,
            }
          },
          [] ),
        REQUEST_TIMEOUT_COMMAND )

    response = [ self.HandleServerCommand( request_data, c )
                 for c in code_actions[ 'result' ] ]

    # Show a list of actions to the user to select which one to apply.
    # This is (probably) a more common workflow for "code action".
    return responses.BuildFixItResponse( [ r for r in response if r ] )


  def Rename( self, request_data, args ):
    if not self.ServerIsReady():
      raise RuntimeError( 'Server is initialising. Please wait.' )

    if len( args ) != 1:
      raise ValueError( 'Please specify a new name to rename it to.\n'
                        'Usage: RefactorRename <new name>' )


    self._RefreshFiles( request_data )

    new_name = args[ 0 ]

    request_id = self.GetConnection().NextRequestId()
    response = self.GetConnection().GetResponse(
      request_id,
      lsapi.Rename( request_id,
                    request_data,
                    new_name ),
      REQUEST_TIMEOUT_COMMAND )

    return responses.BuildFixItResponse(
      [ WorkspaceEditToFixIt( request_data, response[ 'result' ] ) ] )


def FixUpCompletionPrefixes( completions,
                             start_codepoints,
                             request_data,
                             min_start_codepoint ):
  # Fix up the insertion texts so they share the same start_codepoint by
  # borrowing text from the source
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
  # Phew. That was hard work.
  request_data[ 'start_codepoint' ] = min_start_codepoint + common_prefix_len
  return completions


def InsertionTextForItem( request_data, item ):
  INSERT_TEXT_FORMAT = [
    None, # 1-based
    'PlainText',
    'Snippet'
  ]
  assert INSERT_TEXT_FORMAT[ item.get( 'insertTextFormat', 1 ) ] == 'PlainText'

  fixits = None

  start_codepoint = request_data[ 'start_codepoint' ]
  # We will alwyas have one of insertText or label
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
    textEdit = item[ 'textEdit' ]
    edit_range = textEdit[ 'range' ]
    start_codepoint = edit_range[ 'start' ][ 'character' ] + 1
    end_codepoint = edit_range[ 'end' ][ 'character' ] + 1

    # Conservatively rejecting candidates that breach the protocol
    if edit_range[ 'start' ][ 'line' ] != edit_range[ 'end' ][ 'line' ]:
      raise IncompatibleCompletionException(
        "The TextEdit '{0}' spans multiple lines".format(
          textEdit[ 'newText' ] ) )

    if start_codepoint > request_data[ 'start_codepoint' ]:
      raise IncompatibleCompletionException(
        "The TextEdit '{0}' starts after the start position".format(
          textEdit[ 'newText' ] ) )

    if end_codepoint < request_data[ 'start_codepoint' ]:
      raise IncompatibleCompletionException(
        "The TextEdit '{0}' ends before the start position".format(
          textEdit[ 'newText' ] ) )


    insertion_text = textEdit[ 'newText' ]

    if '\n' in textEdit[ 'newText' ]:
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
      raise IncompatibleCompletionException( textEdit[ 'newText' ] )

  additional_text_edits.extend( item.get( 'additionalTextEdits', [] ) )

  if additional_text_edits:
    chunks = [ responses.FixItChunk( e[ 'newText' ],
                                     BuildRange( request_data,
                                                 request_data[ 'filepath' ],
                                                 e[ 'range' ] ) )
               for e in additional_text_edits ]

    fixits = responses.BuildFixItResponse(
      [ responses.FixIt( chunks[ 0 ].range.start_, chunks ) ] )

  return ( insertion_text, fixits, start_codepoint )


def LocationListToGoTo( request_data, response ):
  if not response:
    raise RuntimeError( 'Cannot jump to location' )

  try:
    if len( response[ 'result' ] ) > 1:
      positions = response[ 'result' ]
      return [
        responses.BuildGoToResponseFromLocation(
          PositionToLocation( request_data,
                               position ) ) for position in positions
      ]
    else:
      position = response[ 'result' ][ 0 ]
      return responses.BuildGoToResponseFromLocation(
        PositionToLocation( request_data, position ) )
  except( IndexError ):
    raise RuntimeError( 'Cannot jump to location' )


def PositionToLocation( request_data, position ):
  return BuildLocation( request_data,
                        lsapi.UriToFilePath( position[ 'uri' ] ),
                        position[ 'range' ][ 'start' ] )


def BuildLocation( request_data, filename, loc ):
  line_contents = utils.SplitLines( GetFileContents( request_data, filename ) )
  return responses.Location(
    line = loc[ 'line' ] + 1,
    column = utils.CodepointOffsetToByteOffset( line_contents,
                                                loc[ 'character' ] + 1 ),
    filename = filename )


def BuildRange( request_data, filename, r ):
  return responses.Range( BuildLocation( request_data, filename, r[ 'start' ] ),
                          BuildLocation( request_data, filename, r[ 'end' ] ) )


def BuildDiagnostic( request_data, uri, diag ):
  filename = lsapi.UriToFilePath( uri )
  r = BuildRange( request_data, filename, diag[ 'range' ] )
  SEVERITY = [
    None,
    'Error',
    'Warning',
    'Information',
    'Hint',
  ]
  SEVERITY_TO_YCM_SEVERITY = {
    'Error': 'ERROR',
    'Warning': 'WARNING',
    'Information': 'WARNING',
    'Hint': 'WARNING'
  }

  return responses.BuildDiagnosticData ( responses.Diagnostic(
    ranges = [ r ],
    location = r.start_,
    location_extent = r,
    text = diag[ 'message' ],
    kind = SEVERITY_TO_YCM_SEVERITY[ SEVERITY[ diag[ 'severity' ] ] ] ) )


def TextEditToChunks( request_data, uri, text_edit ):
  filepath = lsapi.UriToFilePath( uri )
  return [
    responses.FixItChunk( change[ 'newText' ],
                          BuildRange( request_data,
                                      filepath,
                                      change[ 'range' ] ) )
    for change in text_edit
  ]


def WorkspaceEditToFixIt( request_data, workspace_edit, text='' ):
  if 'changes' not in workspace_edit:
    return None

  chunks = list()
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
