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
import logging
import threading
import os
import queue
import json

from ycmd.completers.completer import Completer
from ycmd import utils
from ycmd import responses

from ycmd.completers.language_server import lsapi

_logger = logging.getLogger( __name__ )


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
  def __init__( self ):
    super( LanguageServerConnection, self ).__init__()

    self._lastId = 0
    self._responses = {}
    self._responseMutex = threading.Lock()
    self._notifications = queue.Queue()

    self._connection_event = threading.Event()
    self._stop_event = threading.Event()


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


  def GetResponse( self, request_id, message, timeout=1 ):
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
    self._connection_event.wait( timeout = 5 )

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
            _logger.debug( "Headers complete" )
            headers_complete = True
            read_bytes += 1
            break
          else:
            _logger.debug( "Header line: {0}".format( line ) )
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


  def _TryServerConnectionBlocking( self ):
    raise RuntimeError( 'Not implemented' )


  def _Stop( self ):
    raise RuntimeError( 'Not implemented' )


  def _Write( self, data ):
    raise RuntimeError( 'Not implemented' )


  def _Read( self, size=-1 ):
    raise RuntimeError( 'Not implemented' )


class StandardIOLanguageServerConnection( LanguageServerConnection,
                                          threading.Thread ):
  def __init__( self, server_stdin, server_stdout ):
    super( StandardIOLanguageServerConnection, self ).__init__()

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
    _logger.debug( 'Writing: ' + utils.ToUnicode( to_write ) )
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

    _logger.debug( "Data!!: {0}".format( data ) )
    return data


class LanguageServerCompleter( Completer ):
  def __init__( self, user_options):
    super( LanguageServerCompleter, self ).__init__( user_options )
    self._latest_diagnostics = {
      'uri': None,
      'diagnostics': []
    }
    self._syncType = 'Full'

    self._serverFileState = {}
    self._fileStateMutex = threading.Lock()


  def GetServer( sefl ):
    """Method that must be implemented by derived classes to return an instance
    of LanguageServerConnection appropriate for the language server in
    question"""
    # TODO: I feel like abc.abstractmethod could be used here, but I'm not sure
    # if it is totally python2/3 safe, and TBH it doesn't do a lot more than
    # this simple raise here, so...
    raise NameError( "GetServer must be implemented in LanguageServerCompleter "
                     "subclasses" )


  def ComputeCandidatesInner( self, request_data ):
    if not self.ServerIsHealthy():
      return None

    # Need to update the file contents. TODO: so inefficient (and doesn't work
    # for the eclipse based completer for some reason - possibly because it
    # is busy parsing the file when it actually should be providing
    # completions)!
    self._RefreshFiles( request_data )

    request_id = self.GetServer().NextRequestId()
    msg = lsapi.Completion( request_id, request_data )
    response = self.GetServer().GetResponse( request_id, msg )

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
        response = self.GetServer().GetResponse( resolve_id, resolve )
        item = response[ 'result' ]

      ITEM_KIND = [
        None,  # 1-based
        'Text',
        'Method',
        'Function',
        'Constructor',
        'Field',
        'Variable',
        'Class',
        'Interface',
        'Module',
        'Property',
        'Unit',
        'Value',
        'Enum',
        'Keyword',
        'Snippet',
        'Color',
        'File',
        'Reference',
      ]

      if 'textEdit' in item and item[ 'textEdit' ]:
        # TODO: This is a very annoying way to supply completions, but YCM could
        # technically support it via FixIt
        insertion_text = item[ 'textEdit' ][ 'newText' ]
      elif 'insertText' in item and item[ 'insertText' ]:
        insertion_text = item[ 'insertText' ]
      else:
        insertion_text = item[ 'label' ]

      return responses.BuildCompletionData(
        insertion_text,
        None,
        None,
        item[ 'label' ],
        ITEM_KIND[ item.get( 'kind', 0 ) ],
        None )

    if isinstance( response[ 'result' ], list ):
      items = response[ 'result' ]
    else:
      items = response[ 'result' ][ 'items' ]
    return [ MakeCompletion( i ) for i in items ]


  def OnFileReadyToParse( self, request_data ):
    if self.ServerIsReady():
      self._RefreshFiles( request_data )

    def BuildLocation( filename, loc ):
      # TODO: Look at tern complete, requires file contents to convert codepoint
      # offset to byte offset
      return responses.Location( line = loc[ 'line' ] + 1,
                                 column = loc[ 'character' ] + 1,
                                 filename = os.path.realpath( filename ) )

    def BuildRange( filename, r ):
      return responses.Range( BuildLocation( filename, r[ 'start' ] ),
                              BuildLocation( filename, r[ 'end' ] ) )


    def BuildDiagnostic( filename, diag ):
      filename = lsapi.UriToFilePath( filename )
      r = BuildRange( filename, diag[ 'range' ] )
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

    # TODO: Maybe we need to prevent duplicates? Anyway, handle all of the
    # notification messages
    latest_diagnostics = None
    try:
      while True:
        if not self.GetServer():
          # The server isn't running or something. Don't re-poll.
          return False

        notification = self._server._notifications.get_nowait()
        _logger.debug( 'notification {0}: {1}'.format(
          notification[ 'method' ],
          json.dumps( notification[ 'params' ], indent = 2 ) ) )

        if notification[ 'method' ] == 'textDocument/publishDiagnostics':
          _logger.debug( 'latest_diagnostics updated' )
          latest_diagnostics = notification
    except queue.Empty:
      pass

    if latest_diagnostics is not None:
      _logger.debug( 'new diagnostics, updating latest received' )
      self._latest_diagnostics = latest_diagnostics[ 'params' ]
    else:
      _logger.debug( 'No new diagnostics, using latest received' )

    diags = [ BuildDiagnostic( self._latest_diagnostics[ 'uri' ], x )
              for x in self._latest_diagnostics[ 'diagnostics' ] ]
    _logger.debug( 'Diagnostics: {0}'.format( diags ) )
    return diags


  def _RefreshFiles( self, request_data ):
    with self._fileStateMutex:
      for file_name, file_data in iteritems( request_data[ 'file_data' ] ):
        file_state = 'New'
        if file_name in self._serverFileState:
          file_state = self._serverFileState[ file_name ]

        if file_state == 'New' or self._syncType == 'Full':
          msg = lsapi.DidOpenTextDocument( file_name,
                                           file_data[ 'filetypes' ],
                                           file_data[ 'contents' ] )
        else:
          # FIXME: DidChangeTextDocument doesn't actally do anything different
          # from DidOpenTextDocument because we don't actually have a mechanism
          # for generating the diffs (which would just be a waste of time)
          #
          # One option would be to just replcae the entire file, but some
          # servers (i'm looking at you javac completer) don't update
          # diagnostics until you open or save a document. Sigh.
          msg = lsapi.DidChangeTextDocument( file_name,
                                             file_data[ 'filetypes' ],
                                             file_data[ 'contents' ] )

        self._serverFileState[ file_name ] = 'Open'
        self.GetServer().SendNotification( msg )

      for file_name in iterkeys(self._serverFileState ):
        if file_name not in request_data[ 'file_data' ]:
          msg = lsapi.DidCloseTextDocument( file_name )
          del self._serverFileState[ file_name ]
          self.GetServer().SendNotification( msg )


  def _WaitForInitiliase( self ):
    request_id = self.GetServer().NextRequestId()

    msg = lsapi.Initialise( request_id )
    response = self.GetServer().GetResponse( request_id,
                                             msg,
                                             timeout = 3 )

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
