# Copyright (C) 2015-2016 Google Inc.
#               2016-2017 ycmd contributors
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

import json
import logging
import os
import re
import subprocess
import itertools
import threading

from tempfile import NamedTemporaryFile

from ycmd import responses
from ycmd import utils
from ycmd.completers.completer import Completer
from ycmd.completers.completer_utils import GetFileContents

BINARY_NOT_FOUND_MESSAGE = ( 'TSServer not found. '
                             'TypeScript 1.5 or higher is required.' )
SERVER_NOT_RUNNING_MESSAGE = 'TSServer is not running.'

MAX_DETAILED_COMPLETIONS = 100
RESPONSE_TIMEOUT_SECONDS = 10

PATH_TO_TSSERVER = utils.FindExecutable( 'tsserver' )

LOGFILE_FORMAT = 'tsserver_'

_logger = logging.getLogger( __name__ )


class DeferredResponse( object ):
  """
  A deferred that resolves to a response from TSServer.
  """

  def __init__( self, timeout = RESPONSE_TIMEOUT_SECONDS ):
    self._event = threading.Event()
    self._message = None
    self._timeout = timeout


  def resolve( self, message ):
    self._message = message
    self._event.set()


  def result( self ):
    self._event.wait( timeout = self._timeout )
    if not self._event.isSet():
      raise RuntimeError( 'Response Timeout' )
    message = self._message
    if not message[ 'success' ]:
      raise RuntimeError( message[ 'message' ] )
    if 'body' in message:
      return self._message[ 'body' ]


def ShouldEnableTypescriptCompleter():
  if not PATH_TO_TSSERVER:
    _logger.error( BINARY_NOT_FOUND_MESSAGE )
    return False

  _logger.info( 'Using TSServer located at {0}'.format( PATH_TO_TSSERVER ) )

  return True


class TypeScriptCompleter( Completer ):
  """
  Completer for TypeScript.

  It uses TSServer which is bundled with TypeScript 1.5

  See the protocol here:
  https://github.com/Microsoft/TypeScript/blob/2cb0dfd99dc2896958b75e44303d8a7a32e5dc33/src/server/protocol.d.ts
  """


  def __init__( self, user_options ):
    super( TypeScriptCompleter, self ).__init__( user_options )

    self._logfile = None

    self._tsserver_handle = None

    # Used to prevent threads from concurrently writing to
    # the tsserver process' stdin
    self._write_lock = threading.Lock()

    # Each request sent to tsserver must have a sequence id.
    # Responses contain the id sent in the corresponding request.
    self._sequenceid = itertools.count()

    # Used to prevent threads from concurrently accessing the sequence counter
    self._sequenceid_lock = threading.Lock()

    self._server_lock = threading.RLock()

    # Used to read response only if TSServer is running.
    self._tsserver_is_running = threading.Event()

    # Start a thread to read response from TSServer.
    self._thread = threading.Thread( target = self._ReaderLoop, args = () )
    self._thread.daemon = True
    self._thread.start()

    self._StartServer()

    # Used to map sequence id's to their corresponding DeferredResponse
    # objects. The reader loop uses this to hand out responses.
    self._pending = {}

    # Used to prevent threads from concurrently reading and writing to
    # the pending response dictionary
    self._pending_lock = threading.Lock()

    _logger.info( 'Enabling typescript completion' )


  def _StartServer( self ):
    with self._server_lock:
      if self._ServerIsRunning():
        return

      self._logfile = utils.CreateLogfile( LOGFILE_FORMAT )
      tsserver_log = '-file {path} -level {level}'.format( path = self._logfile,
                                                           level = _LogLevel() )
      # TSServer gets the configuration for the log file through the
      # environment variable 'TSS_LOG'. This seems to be undocumented but
      # looking at the source code it seems like this is the way:
      # https://github.com/Microsoft/TypeScript/blob/8a93b489454fdcbdf544edef05f73a913449be1d/src/server/server.ts#L136
      environ = os.environ.copy()
      utils.SetEnviron( environ, 'TSS_LOG', tsserver_log )

      _logger.info( 'TSServer log file: {0}'.format( self._logfile ) )

      # We need to redirect the error stream to the output one on Windows.
      self._tsserver_handle = utils.SafePopen( PATH_TO_TSSERVER,
                                               stdin = subprocess.PIPE,
                                               stdout = subprocess.PIPE,
                                               stderr = subprocess.STDOUT,
                                               env = environ )

      self._tsserver_is_running.set()


  def _ReaderLoop( self ):
    """
    Read responses from TSServer and use them to resolve
    the DeferredResponse instances.
    """

    while True:
      self._tsserver_is_running.wait()

      try:
        message = self._ReadMessage()
      except RuntimeError:
        _logger.exception( SERVER_NOT_RUNNING_MESSAGE )
        self._tsserver_is_running.clear()
        continue

      # We ignore events for now since we don't have a use for them.
      msgtype = message[ 'type' ]
      if msgtype == 'event':
        eventname = message[ 'event' ]
        _logger.info( 'Received {0} event from tsserver'.format( eventname ) )
        continue
      if msgtype != 'response':
        _logger.error( 'Unsupported message type {0}'.format( msgtype ) )
        continue

      seq = message[ 'request_seq' ]
      with self._pending_lock:
        if seq in self._pending:
          self._pending[ seq ].resolve( message )
          del self._pending[ seq ]


  def _ReadMessage( self ):
    """Read a response message from TSServer."""

    # The headers are pretty similar to HTTP.
    # At the time of writing, 'Content-Length' is the only supplied header.
    headers = {}
    while True:
      headerline = self._tsserver_handle.stdout.readline().strip()
      if not headerline:
        break
      key, value = utils.ToUnicode( headerline ).split( ':', 1 )
      headers[ key.strip() ] = value.strip()

    # The response message is a JSON object which comes back on one line.
    # Since this might change in the future, we use the 'Content-Length'
    # header.
    if 'Content-Length' not in headers:
      raise RuntimeError( "Missing 'Content-Length' header" )
    contentlength = int( headers[ 'Content-Length' ] )
    # TSServer adds a newline at the end of the response message and counts it
    # as one character (\n) towards the content length. However, newlines are
    # two characters on Windows (\r\n), so we need to take care of that. See
    # issue https://github.com/Microsoft/TypeScript/issues/3403
    content = self._tsserver_handle.stdout.read( contentlength )
    if utils.OnWindows() and content.endswith( b'\r' ):
      content += self._tsserver_handle.stdout.read( 1 )
    return json.loads( utils.ToUnicode( content ) )


  def _BuildRequest( self, command, arguments = None ):
    """Build TSServer request object."""

    with self._sequenceid_lock:
      seq = next( self._sequenceid )
    request = {
      'seq':     seq,
      'type':    'request',
      'command': command
    }
    if arguments:
      request[ 'arguments' ] = arguments
    return request


  def _WriteRequest( self, request ):
    """Write a request to TSServer stdin."""

    serialized_request = utils.ToBytes( json.dumps( request ) + '\n' )
    with self._write_lock:
      try:
        self._tsserver_handle.stdin.write( serialized_request )
        self._tsserver_handle.stdin.flush()
      # IOError is an alias of OSError in Python 3.
      except ( AttributeError, IOError ):
        _logger.exception( SERVER_NOT_RUNNING_MESSAGE )
        raise RuntimeError( SERVER_NOT_RUNNING_MESSAGE )


  def _SendCommand( self, command, arguments = None ):
    """
    Send a request message to TSServer but don't wait for the response.
    This function is to be used when we don't care about the response
    to the message that is sent.
    """

    request = self._BuildRequest( command, arguments )
    self._WriteRequest( request )


  def _SendRequest( self, command, arguments = None ):
    """
    Send a request message to TSServer and wait
    for the response.
    """

    request = self._BuildRequest( command, arguments )
    deferred = DeferredResponse()
    with self._pending_lock:
      seq = request[ 'seq' ]
      self._pending[ seq ] = deferred
    self._WriteRequest( request )
    return deferred.result()


  def _Reload( self, request_data ):
    """
    Syncronize TSServer's view of the file to
    the contents of the unsaved buffer.
    """

    filename = request_data[ 'filepath' ]
    contents = request_data[ 'file_data' ][ filename ][ 'contents' ]
    tmpfile = NamedTemporaryFile( delete = False )
    tmpfile.write( utils.ToBytes( contents ) )
    tmpfile.close()
    self._SendRequest( 'reload', {
      'file':    filename,
      'tmpfile': tmpfile.name
    } )
    utils.RemoveIfExists( tmpfile.name )


  def _ServerIsRunning( self ):
    with self._server_lock:
      return utils.ProcessIsRunning( self._tsserver_handle )


  def ServerIsHealthy( self ):
    return self._ServerIsRunning()


  def SupportedFiletypes( self ):
    return [ 'typescript' ]


  def ComputeCandidatesInner( self, request_data ):
    self._Reload( request_data )
    entries = self._SendRequest( 'completions', {
      'file':   request_data[ 'filepath' ],
      'line':   request_data[ 'line_num' ],
      'offset': request_data[ 'start_codepoint' ]
    } )

    # A less detailed version of the completion data is returned
    # if there are too many entries. This improves responsiveness.
    if len( entries ) > MAX_DETAILED_COMPLETIONS:
      return [ _ConvertCompletionData(e) for e in entries ]

    names = []
    namelength = 0
    for e in entries:
      name = e[ 'name' ]
      namelength = max( namelength, len( name ) )
      names.append( name )

    detailed_entries = self._SendRequest( 'completionEntryDetails', {
      'file':       request_data[ 'filepath' ],
      'line':       request_data[ 'line_num' ],
      'offset':     request_data[ 'start_codepoint' ],
      'entryNames': names
    } )
    return [ _ConvertDetailedCompletionData( e, namelength )
             for e in detailed_entries ]


  def GetSubcommandsMap( self ):
    return {
      'RestartServer'  : ( lambda self, request_data, args:
                           self._RestartServer( request_data ) ),
      'StopServer'     : ( lambda self, request_data, args:
                           self._StopServer() ),
      'GoToDefinition' : ( lambda self, request_data, args:
                           self._GoToDefinition( request_data ) ),
      'GoToReferences' : ( lambda self, request_data, args:
                           self._GoToReferences( request_data ) ),
      'GoToType'       : ( lambda self, request_data, args:
                           self._GoToType( request_data ) ),
      'GetType'        : ( lambda self, request_data, args:
                           self._GetType( request_data ) ),
      'GetDoc'         : ( lambda self, request_data, args:
                           self._GetDoc( request_data ) ),
      'RefactorRename' : ( lambda self, request_data, args:
                           self._RefactorRename( request_data, args ) ),
    }


  def OnBufferVisit( self, request_data ):
    filename = request_data[ 'filepath' ]
    self._SendCommand( 'open', { 'file': filename } )


  def OnBufferUnload( self, request_data ):
    filename = request_data[ 'filepath' ]
    self._SendCommand( 'close', { 'file': filename } )


  def OnFileReadyToParse( self, request_data ):
    self._Reload( request_data )


  def _GoToDefinition( self, request_data ):
    self._Reload( request_data )
    try:
      filespans = self._SendRequest( 'definition', {
        'file':   request_data[ 'filepath' ],
        'line':   request_data[ 'line_num' ],
        'offset': request_data[ 'column_codepoint' ]
      } )

      span = filespans[ 0 ]
      return responses.BuildGoToResponseFromLocation(
        _BuildLocation( utils.SplitLines( GetFileContents( request_data,
                                                           span[ 'file' ] ) ),
                        span[ 'file' ],
                        span[ 'start' ][ 'line' ],
                        span[ 'start' ][ 'offset' ] ) )
    except RuntimeError:
      raise RuntimeError( 'Could not find definition' )


  def _GoToReferences( self, request_data ):
    self._Reload( request_data )
    response = self._SendRequest( 'references', {
      'file':   request_data[ 'filepath' ],
      'line':   request_data[ 'line_num' ],
      'offset': request_data[ 'column_codepoint' ]
    } )
    return [
      responses.BuildGoToResponseFromLocation(
        _BuildLocation( utils.SplitLines( GetFileContents( request_data,
                                                           ref[ 'file' ] ) ),
                        ref[ 'file' ],
                        ref[ 'start' ][ 'line' ],
                        ref[ 'start' ][ 'offset' ] ),
        ref[ 'lineText' ] )
      for ref in response[ 'refs' ]
    ]


  def _GoToType( self, request_data ):
    self._Reload( request_data )
    try:
      filespans = self._SendRequest( 'typeDefinition', {
        'file':   request_data[ 'filepath' ],
        'line':   request_data[ 'line_num' ],
        'offset': request_data[ 'column_num' ]
      } )

      span = filespans[ 0 ]
      return responses.BuildGoToResponse(
        filepath   = span[ 'file' ],
        line_num   = span[ 'start' ][ 'line' ],
        column_num = span[ 'start' ][ 'offset' ]
      )
    except RuntimeError:
      raise RuntimeError( 'Could not find type definition' )


  def _GetType( self, request_data ):
    self._Reload( request_data )
    info = self._SendRequest( 'quickinfo', {
      'file':   request_data[ 'filepath' ],
      'line':   request_data[ 'line_num' ],
      'offset': request_data[ 'column_codepoint' ]
    } )
    return responses.BuildDisplayMessageResponse( info[ 'displayString' ] )


  def _GetDoc( self, request_data ):
    self._Reload( request_data )
    info = self._SendRequest( 'quickinfo', {
      'file':   request_data[ 'filepath' ],
      'line':   request_data[ 'line_num' ],
      'offset': request_data[ 'column_codepoint' ]
    } )

    message = '{0}\n\n{1}'.format( info[ 'displayString' ],
                                   info[ 'documentation' ] )
    return responses.BuildDetailedInfoResponse( message )


  def _RefactorRename( self, request_data, args ):
    if len( args ) != 1:
      raise ValueError( 'Please specify a new name to rename it to.\n'
                        'Usage: RefactorRename <new name>' )

    self._Reload( request_data )

    response = self._SendRequest( 'rename', {
      'file':   request_data[ 'filepath' ],
      'line':   request_data[ 'line_num' ],
      'offset': request_data[ 'column_codepoint' ],
      'findInComments': False,
      'findInStrings': False,
    } )

    if not response[ 'info' ][ 'canRename' ]:
      raise RuntimeError( 'Value cannot be renamed: {0}'.format(
        response[ 'info' ][ 'localizedErrorMessage' ] ) )

    # The format of the response is:
    #
    # body {
    #   info {
    #     ...
    #     triggerSpan: {
    #       length: original_length
    #     }
    #   }
    #
    #   locs [ {
    #     file: file_path
    #     locs: [
    #       start: {
    #         line: line_num
    #         offset: offset
    #       }
    #       end {
    #         line: line_num
    #         offset: offset
    #       }
    #     ] }
    #   ]
    # }
    #
    new_name = args[ 0 ]
    location = responses.Location( request_data[ 'line_num' ],
                                   request_data[ 'column_num' ],
                                   request_data[ 'filepath' ] )

    chunks = []
    for file_replacement in response[ 'locs' ]:
      chunks.extend( _BuildFixItChunksForFile( request_data,
                                               new_name,
                                               file_replacement ) )

    return responses.BuildFixItResponse( [
      responses.FixIt( location, chunks )
    ] )


  def _RestartServer( self, request_data ):
    with self._server_lock:
      self._StopServer()
      self._StartServer()
      # This is needed because after we restart the TSServer it would lose all
      # the information about the files we were working on. This means that the
      # newly started TSServer will know nothing about the buffer we're working
      # on after restarting the server. So if we restart the server and right
      # after that ask for completion in the buffer, the server will timeout.
      # So we notify the server that we're working on the current buffer.
      self.OnBufferVisit( request_data )


  def _StopServer( self ):
    with self._server_lock:
      if self._ServerIsRunning():
        _logger.info( 'Stopping TSServer with PID {0}'.format(
                          self._tsserver_handle.pid ) )
        self._SendCommand( 'exit' )
        try:
          utils.WaitUntilProcessIsTerminated( self._tsserver_handle,
                                              timeout = 5 )
          _logger.info( 'TSServer stopped' )
        except RuntimeError:
          _logger.exception( 'Error while stopping TSServer' )

      self._CleanUp()


  def _CleanUp( self ):
    utils.CloseStandardStreams( self._tsserver_handle )
    self._tsserver_handle = None
    if not self.user_options[ 'server_keep_logfiles' ]:
      utils.RemoveIfExists( self._logfile )
      self._logfile = None


  def Shutdown( self ):
    self._StopServer()


  def DebugInfo( self, request_data ):
    with self._server_lock:
      tsserver = responses.DebugInfoServer( name = 'TSServer',
                                            handle = self._tsserver_handle,
                                            executable = PATH_TO_TSSERVER,
                                            logfiles = [ self._logfile ] )

      return responses.BuildDebugInfoResponse( name = 'TypeScript',
                                               servers = [ tsserver ] )


def _LogLevel():
  return 'verbose' if _logger.isEnabledFor( logging.DEBUG ) else 'normal'


def _ConvertCompletionData( completion_data ):
  return responses.BuildCompletionData(
    insertion_text = completion_data[ 'name' ],
    menu_text      = completion_data[ 'name' ],
    kind           = completion_data[ 'kind' ],
    extra_data     = completion_data[ 'kind' ]
  )


def _ConvertDetailedCompletionData( completion_data, padding = 0 ):
  name = completion_data[ 'name' ]
  display_parts = completion_data[ 'displayParts' ]
  signature = ''.join( [ p[ 'text' ] for p in display_parts ] )

  # needed to strip new lines and indentation from the signature
  signature = re.sub( '\s+', ' ', signature )
  menu_text = '{0} {1}'.format( name.ljust( padding ), signature )
  return responses.BuildCompletionData(
    insertion_text = name,
    menu_text      = menu_text,
    kind           = completion_data[ 'kind' ]
  )


def _BuildFixItChunkForRange( new_name,
                              file_contents,
                              file_name,
                              source_range ):
  """ returns list FixItChunk for a tsserver source range """
  return responses.FixItChunk(
      new_name,
      responses.Range(
        start = _BuildLocation( file_contents,
                                file_name,
                                source_range[ 'start' ][ 'line' ],
                                source_range[ 'start' ][ 'offset' ] ),
        end   = _BuildLocation( file_contents,
                                file_name,
                                source_range[ 'end' ][ 'line' ],
                                source_range[ 'end' ][ 'offset' ] ) ) )


def _BuildFixItChunksForFile( request_data, new_name, file_replacement ):
  """ returns a list of FixItChunk for each replacement range for the
  supplied file"""

  # On windows, tsserver annoyingly returns file path as C:/blah/blah,
  # whereas all other paths in Python are of the C:\\blah\\blah form. We use
  # normpath to have python do the conversion for us.
  file_path = os.path.normpath( file_replacement[ 'file' ] )
  file_contents = utils.SplitLines( GetFileContents( request_data, file_path ) )
  return [ _BuildFixItChunkForRange( new_name, file_contents, file_path, r )
           for r in file_replacement[ 'locs' ] ]


def _BuildLocation( file_contents, filename, line, offset ):
  return responses.Location(
    line = line,
    # tsserver returns codepoint offsets, but we need byte offsets, so we must
    # convert
    column = utils.CodepointOffsetToByteOffset( file_contents[ line - 1 ],
                                                offset ),
    filename = filename )
