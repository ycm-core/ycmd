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


REQUEST_TIMEOUT_COMPLETION = 1
REQUEST_TIMEOUT_INITIALISE = 30
REQUEST_TIMEOUT_COMMAND    = 30
CONNECTION_TIMEOUT         = 5
MESSAGE_POLL_TIMEOUT       = 10


class Response( object ):
  def __init__( self ):
    self._event = threading.Event()
    self._message = None


  def ResponseReceived( self, message ):
    self._message = message
    self._event.set()


  def AwaitResponse( self, timeout ):
    self._event.wait( timeout )

    if not self._event.isSet():
      raise RuntimeError( 'Response Timeout' )

    if 'error' in self._message:
      error = self._message[ 'error' ]
      raise RuntimeError( 'Request failed: {0}: {1}'.format(
        error.get( 'code', 0 ),
        error.get( 'message', 'No message' ) ) )

    return self._message


class LanguageServerConnectionTimeout( Exception ):
  pass


class LanguageServerConnectionStopped( Exception ):
  pass


class LanguageServerConnection( object ):
  """
    Abstract language server communication object.

    Implementations are required to provide the following methods:
      - _TryServerConnectionBlocking: Connect to the server and return when the
                                      connection is established
      - _Write: Write some data to the server
      - _Read: Read some data from the server, blocking until some data is
               available
  """
  def __init__( self, notification_handler = None ):
    super( LanguageServerConnection, self ).__init__()

    self._lastId = 0
    self._responses = {}
    self._responseMutex = threading.Lock()
    self._notifications = queue.Queue()

    self._connection_event = threading.Event()
    self._stop_event = threading.Event()
    self._notification_handler = notification_handler


  def stop( self ):
    # Note lowercase stop() to match threading.Thread.start()
    self._Stop()
    self._stop_event.set()


  def IsStopped( self ):
    return self._stop_event.is_set()


  def NextRequestId( self ):
    with self._responseMutex:
      self._lastId += 1
      return str( self._lastId )


  def GetResponse( self, request_id, message, timeout ):
    response = Response()

    with self._responseMutex:
      assert request_id not in self._responses
      self._responses[ request_id ] = response

    _logger.debug( 'TX: Sending message {0}'.format( message ) )

    self._Write( message )
    return response.AwaitResponse( timeout )


  def SendNotification( self, message ):
    _logger.debug( 'TX: Sending Notification {0}'.format( message ) )

    self._Write( message )


  def TryServerConnection( self ):
    self._connection_event.wait( timeout = CONNECTION_TIMEOUT )

    if not self._connection_event.isSet():
      raise LanguageServerConnectionTimeout(
        'Timed out waiting for server to connect' )


  def _run_loop( self ):
    # Wait for the connection to fully establish (this runs in the thread
    # context, so we block until a connection is received or there is a timeout,
    # which throws an exception)
    try:
      self._TryServerConnectionBlocking()

      self._connection_event.set()

      # Blocking loop which reads whole messages and calls _DespatchMessage
      self._ReadMessages( )
    except LanguageServerConnectionStopped:
      _logger.debug( 'Connection was closed cleanly' )
      pass


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
        raise RuntimeError( "Missing 'Content-Length' header" )

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
    else:
      self._notifications.put( message )

      if self._notification_handler:
        self._notification_handler( self, message )


  @abc.abstractmethod
  def _TryServerConnectionBlocking( self ):
    pass


  @abc.abstractmethod
  def _Stop( self ):
    pass


  @abc.abstractmethod
  def _Write( self, data ):
    pass


  @abc.abstractmethod
  def _Read( self, size=-1 ):
    pass


class StandardIOLanguageServerConnection( LanguageServerConnection,
                                          threading.Thread ):
  def __init__( self, server_stdin,
                server_stdout,
                notification_handler = None ):
    super( StandardIOLanguageServerConnection, self ).__init__(
      notification_handler )

    self.server_stdin = server_stdin
    self.server_stdout = server_stdout


  def run( self ):
    self._run_loop()


  def _TryServerConnectionBlocking( self ):
    # standard in/out don't need to wait for the server to connect to us
    return True


  def _Stop( self ):
    self.server_stdin.close()


  def _Write( self, data ):
    to_write = data + utils.ToBytes( '\r\n' )
    self.server_stdin.write( to_write )
    self.server_stdin.flush()


  def _Read( self, size=-1 ):
    if size > -1:
      data = self.server_stdout.read( size )
    else:
      data = self.server_stdout.readline()

    if self.IsStopped():
      raise LanguageServerConnectionStopped()

    if not data:
      # No data means the connection was severed. Connection severed when (not
      # self.IsStopped()) means the server died unexpectedly.
      raise RuntimeError( "Connection to server died" )

    return data


class LanguageServerCompleter( Completer ):
  def __init__( self, user_options):
    super( LanguageServerCompleter, self ).__init__( user_options )

    self._syncType = 'Full'

    self._serverFileState = {}
    self._fileStateMutex = threading.Lock()
    self._latest_diagnostics = collections.defaultdict( list )


  @abc.abstractmethod
  def GetServer( sefl ):
    """Method that must be implemented by derived classes to return an instance
    of LanguageServerConnection appropriate for the language server in
    question"""
    pass


  def ComputeCandidatesInner( self, request_data ):
    if not self.ServerIsHealthy():
      return None

    self._RefreshFiles( request_data )

    request_id = self.GetServer().NextRequestId()
    msg = lsapi.Completion( request_id, request_data )
    response = self.GetServer().GetResponse( request_id,
                                             msg,
                                             REQUEST_TIMEOUT_COMPLETION )

    do_resolve = (
      'completionProvider' in self._server_capabilities and
      self._server_capabilities[ 'completionProvider' ].get( 'resolveProvider',
                                                             False ) )

    def MakeCompletion( item ):
      # First, resolve the completion.
      # TODO: Maybe we need some way to do this based on a trigger
      # TODO: Need a better API around request IDs. We no longer care about them
      # _at all_ here.

      if do_resolve:
        resolve_id = self.GetServer().NextRequestId()
        resolve = lsapi.ResolveCompletion( resolve_id, item )
        response = self.GetServer().GetResponse( resolve_id,
                                                 resolve,
                                                 REQUEST_TIMEOUT_COMPLETION )
        item = response[ 'result' ]

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

      ( insertion_text, fixits ) = self._GetInsertionText( request_data, item )

      return responses.BuildCompletionData(
        insertion_text,
        extra_menu_info = item.get( 'detail', None ),
        detailed_info = ( item[ 'label' ] +
                          '\n\n' +
                          item.get( 'documentation', '' ) ),
        menu_text = item[ 'label' ],
        kind = ITEM_KIND[ item.get( 'kind', 0 ) ],
        extra_data = fixits )

    if isinstance( response[ 'result' ], list ):
      items = response[ 'result' ]
    else:
      items = response[ 'result' ][ 'items' ]
    return [ MakeCompletion( i ) for i in items ]


  def OnFileReadyToParse( self, request_data ):
    if self.ServerIsReady():
      self._RefreshFiles( request_data )

    # NOTE: We also return diagnostics asynchronously via the long-polling
    # mechanism to avoid timing issues with the servers asynchronous publication
    # of diagnostics.
    # However, we _also_ return them here to refresh diagnostics after, say
    # changing the active file in the editor.
    uri = lsapi.FilePathToUri( request_data[ 'filepath' ] )
    if self._latest_diagnostics[ uri ]:
      return [ BuildDiagnostic( request_data, uri, diag )
               for diag in self._latest_diagnostics[ uri ] ]


  def _PollForMessagesNoBlock( self, request_data, messages ):
    notification = self.GetServer()._notifications.get_nowait( )
    message = self._ConvertNotificationToMessage( request_data,
                                                  notification )
    if message:
      messages.append( message )


  def _PollForMessagesBlock( self, request_data ):
    try:
      while True:
        if not self.GetServer():
          # The server isn't running or something. Don't re-poll, as this will
          # just cause errors.
          return False

        notification = self.GetServer()._notifications.get(
          timeout = MESSAGE_POLL_TIMEOUT )
        message = self._ConvertNotificationToMessage( request_data,
                                                      notification )
        if message:
          return [ message ]
    except queue.Empty:
      return True


  def PollForMessagesInner( self, request_data ):

    # scoop up any pending messages into one big list
    messages = list()
    try:
      while True:
        if not self.GetServer():
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


  def HandleServerMessage( self, request_data, notification ):
    return None


  def _ConvertNotificationToMessage( self, request_data, notification ):
    response = self.HandleServerMessage( request_data, notification )

    if response:
      return response
    elif notification[ 'method' ] == 'window/showMessage':
      return responses.BuildDisplayMessageResponse(
        notification[ 'params' ][ 'message' ] )
    elif notification[ 'method' ] == 'textDocument/publishDiagnostics':
      # Diagnostics are a little special. We only return diagnostics for the
      # requested file, but store them for every file. Language servers can
      # return diagnostics for the whole project, but this request is
      # specifically for a particular file.
      # Any messages we handle which are for other files are returned in the
      # OnFileReadyToParse request.
      params = notification[ 'params' ]
      uri = params[ 'uri' ]
      self._latest_diagnostics[ uri ] = params[ 'diagnostics' ]

      # TODO(Ben): Does realpath break symlinks?
      # e.g. we putting symlinks in the testdata for the source does not work
      if os.path.realpath( lsapi.UriToFilePath( uri ) ) == os.path.realpath(
        request_data[ 'filepath' ] ):
        response = {
          'diagnostics': [ BuildDiagnostic( request_data, uri, x )
                           for x in params[ 'diagnostics' ] ]
        }
        return response

    return None


  def _RefreshFiles( self, request_data ):
    # FIXME: Provide a Reset method which clears this state. Restarting
    # downstream servers would leave this cache in the incorrect state.
    with self._fileStateMutex:
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
        self.GetServer().SendNotification( msg )

      stale_files = list()
      for file_name in iterkeys( self._serverFileState ):
        if file_name not in request_data[ 'file_data' ]:
          stale_files.append( file_name )

      # We can't change the dictionary entries while using iterkeys, so we do
      # that in a separate loop.
      # TODO(Ben): Is this better than just not using iterkeys?
      for file_name in stale_files:
          msg = lsapi.DidCloseTextDocument( file_name )
          self.GetServer().SendNotification( msg )
          del self._serverFileState[ file_name ]


  def _WaitForInitiliase( self ):
    request_id = self.GetServer().NextRequestId()

    msg = lsapi.Initialise( request_id )
    response = self.GetServer().GetResponse( request_id,
                                             msg,
                                             REQUEST_TIMEOUT_INITIALISE )

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


  def _GetHoverResponse( self, request_data ):
    request_id = self.GetServer().NextRequestId()
    response = self.GetServer().GetResponse(
      request_id,
      lsapi.Hover( request_id,
                   request_data ),
      REQUEST_TIMEOUT_COMMAND )

    return response[ 'result' ][ 'contents' ]


  def LocationListToGoTo( self, request_data, response ):
    if not response:
      raise RuntimeError( 'Cannot jump to location' )

    if len( response[ 'result' ] ) > 1:
      positions = response[ 'result' ]
      return [
        responses.BuildGoToResponseFromLocation(
          _PositionToLocation( request_data,
                               position ) ) for position in positions
      ]
    else:
      position = response[ 'result' ][ 0 ]
      return responses.BuildGoToResponseFromLocation(
        _PositionToLocation( request_data, position ) )


  def _GoToDeclaration( self, request_data ):
    request_id = self.GetServer().NextRequestId()
    response = self.GetServer().GetResponse(
      request_id,
      lsapi.Definition( request_id,
                        request_data ),
      REQUEST_TIMEOUT_COMMAND )

    if isinstance( response[ 'result' ], list ):
      return self.LocationListToGoTo( request_data, response )
    else:
      position = response[ 'result' ]
      return responses.BuildGoToResponseFromLocation(
        _PositionToLocation( request_data, position ) )


  def _GoToReferences( self, request_data ):
    request_id = self.GetServer().NextRequestId()
    response = self.GetServer().GetResponse(
      request_id,
      lsapi.References( request_id,
                        request_data ),
      REQUEST_TIMEOUT_COMMAND )

    return self.LocationListToGoTo( request_data, response )


  def _CodeAction( self, request_data, args ):
    # FIXME: We need to do this for all such requests
    self._RefreshFiles( request_data )

    line_num_ls = request_data[ 'line_num' ] - 1

    def WithinRange( diag ):
      start = diag[ 'range' ][ 'start' ]
      end = diag[ 'range' ][ 'end' ]

      if line_num_ls < start[ 'line' ] or line_num_ls > end[ 'line' ]:
        return False

      return True

    file_diagnostics = self._latest_diagnostics[
        lsapi.FilePathToUri( request_data[ 'filepath' ] ) ]

    matched_diagnostics = [
      d for d in file_diagnostics if WithinRange( d )
    ]

    request_id = self.GetServer().NextRequestId()
    if matched_diagnostics:
      code_actions = self.GetServer().GetResponse(
        request_id,
        lsapi.CodeAction( request_id,
                          request_data,
                          matched_diagnostics[ 0 ][ 'range' ],
                          matched_diagnostics ),
        REQUEST_TIMEOUT_COMMAND )

    else:
      code_actions = self.GetServer().GetResponse(
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

    # Else, show a list of actions to the user to select which one to apply.
    # This is (probably) a more common workflow for "code action".
    return responses.BuildFixItResponse( [ r for r in response if r ] )


  @abc.abstractmethod
  def HandleServerCommand( self, request_data, command ):
    _logger.debug( 'What is going on?' )
    return None


  def _Rename( self, request_data, args ):
    if len( args ) != 1:
      raise ValueError( 'Please specify a new name to rename it to.\n'
                        'Usage: RefactorRename <new name>' )

    new_name = args[ 0 ]

    request_id = self.GetServer().NextRequestId()
    response = self.GetServer().GetResponse(
      request_id,
      lsapi.Rename( request_id,
                    request_data,
                    new_name ),
      REQUEST_TIMEOUT_COMMAND )

    return responses.BuildFixItResponse(
      [ WorkspaceEditToFixIt( request_data, response[ 'result' ] ) ] )


  def _GetInsertionText( self, request_data, item ):
    # TODO: We probably need to implement this and (at least) strip out the
    # snippet parts?
    INSERT_TEXT_FORMAT = [
      None, # 1-based
      'PlainText',
      'Snippet'
    ]

    fixits = None

    # We will alwyas have one of insertText or label
    if 'insertText' in item and item[ 'insertText' ]:
      insertion_text = item[ 'insertText' ]
    else:
      insertion_text = item[ 'label' ]

    # Per the protocol, textEdit takes precedence over insertText, and must be
    # on the same line (and containing) the originally requested position
    if 'textEdit' in item and item[ 'textEdit' ]:
      new_range = item[ 'textEdit' ][ 'range' ]
      additional_text_edits = []

      if ( new_range[ 'start' ][ 'line' ] != new_range[ 'end' ][ 'line' ] or
           new_range[ 'start' ][ 'line' ] + 1 != request_data[ 'line_num' ] ):
        # We can't support completions that span lines. The protocol forbids it
        raise RuntimeError( 'Invalid textEdit supplied. Must be on a single '
                            'line' )
      elif '\n' in item[ 'textEdit' ][ 'newText' ]:
        # The insertion text contains newlines. This is tricky: most clients
        # (i.e. Vim) won't support this. So we cheat. Set the insertable text to
        # the simple text, and put and additionalTextEdit instead. We manipulate
        # the real textEdit so that it replaces the inserted text with the real
        # textEdit.
        fixup_textedit = dict( item[ 'textEdit' ] )
        fixup_textedit[ 'range' ][ 'end' ][ 'character' ] = (
          fixup_textedit[ 'range' ][ 'end' ][ 'character' ] + len(
            insertion_text ) )
        additional_text_edits.append( fixup_textedit )
      else:
        request_data[ 'start_codepoint' ] = (
          new_range[ 'start' ][ 'character' ] + 1 )
        insertion_text = item[ 'textEdit' ][ 'newText' ]

      additional_text_edits.extend( item.get( 'additionalTextEdits', [] ) )

      if additional_text_edits:
        chunks = [ responses.FixItChunk( e[ 'newText' ],
                                         BuildRange( request_data,
                                                     request_data[ 'filepath' ],
                                                     e[ 'range' ] ) )
                   for e in additional_text_edits ]

        fixits = responses.BuildFixItResponse(
          [ responses.FixIt( chunks[ 0].range.start_, chunks ) ] )


    if 'insertTextFormat' in item and item[ 'insertTextFormat' ]:
      text_format = INSERT_TEXT_FORMAT[ item[ 'insertTextFormat' ] ]
    else:
      text_format = 'PlainText'

    if text_format != 'PlainText':
      raise ValueError( 'Snippet completions are not supported and should not'
                        ' be returned by the language server.' )

    return ( insertion_text, fixits )


def _PositionToLocation( request_data, position ):
  return BuildLocation( request_data,
                        lsapi.UriToFilePath( position[ 'uri' ] ),
                        position[ 'range' ][ 'start' ] )


def BuildLocation( request_data, filename, loc ):
  line_contents = utils.SplitLines( GetFileContents( request_data, filename ) )
  return responses.Location(
    line = loc[ 'line' ] + 1,
    column = utils.CodepointOffsetToByteOffset( line_contents,
                                                loc[ 'character' ] + 1 ),
    # FIXME: Does realpath break symlinks?
    filename = os.path.realpath( filename ) )


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
