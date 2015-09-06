#!/usr/bin/env python
#
# Copyright (C) 2015 Google Inc.
#
# This file is part of YouCompleteMe.
#
# YouCompleteMe is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# YouCompleteMe is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with YouCompleteMe.  If not, see <http://www.gnu.org/licenses/>.

import json
import logging
import os
import subprocess

from threading import Lock
from tempfile import NamedTemporaryFile

from ycmd import responses
from ycmd import utils
from ycmd.completers.completer import Completer

BINARY_NOT_FOUND_MESSAGE = ( 'tsserver not found. '
                             'TypeScript 1.5 or higher is required' )

MAX_DETAILED_COMPLETIONS = 100

_logger = logging.getLogger( __name__ )


class TypeScriptCompleter( Completer ):
  """
  Completer for TypeScript.

  It uses TSServer which is bundled with TypeScript 1.5

  See the protocol here:
  https://github.com/Microsoft/TypeScript/blob/2cb0dfd99dc2896958b75e44303d8a7a32e5dc33/src/server/protocol.d.ts
  """


  def __init__( self, user_options ):
    super( TypeScriptCompleter, self ).__init__( user_options )

    # Used to prevent threads from concurrently reading and writing to
    # the tsserver process' stdout and stdin
    self._lock = Lock()

    binarypath = utils.PathToFirstExistingExecutable( [ 'tsserver' ] )
    if not binarypath:
      _logger.error( BINARY_NOT_FOUND_MESSAGE )
      raise RuntimeError( BINARY_NOT_FOUND_MESSAGE )

    # Each request sent to tsserver must have a sequence id.
    # Responses contain the id sent in the corresponding request.
    self._sequenceid = 0

    # TSServer ignores the fact that newlines are two characters on Windows
    # (\r\n) instead of one on other platforms (\n), so we use the
    # universal_newlines option to convert those newlines to \n. See the issue
    # https://github.com/Microsoft/TypeScript/issues/3403
    # TODO: remove this option when the issue is fixed.
    # We also need to redirect the error stream to the output one on Windows.
    self._tsserver_handle = utils.SafePopen( binarypath,
                                             stdout = subprocess.PIPE,
                                             stdin = subprocess.PIPE,
                                             stderr = subprocess.STDOUT,
                                             universal_newlines = True )

    _logger.info( 'Enabling typescript completion' )


  def _SendRequest( self, command, arguments = None ):
    """Send a request message to TSServer."""

    seq = self._sequenceid
    self._sequenceid += 1
    request = {
      'seq':     seq,
      'type':    'request',
      'command': command
    }
    if arguments:
      request[ 'arguments' ] = arguments
    self._tsserver_handle.stdin.write( json.dumps( request ) )
    self._tsserver_handle.stdin.write( "\n" )
    return seq


  def _ReadResponse( self, expected_seq ):
    """Read a response message from TSServer."""

    # The headers are pretty similar to HTTP.
    # At the time of writing, 'Content-Length' is the only supplied header.
    headers = {}
    while True:
      headerline = self._tsserver_handle.stdout.readline().strip()
      if not headerline:
        break
      key, value = headerline.split( ':', 1 )
      headers[ key.strip() ] = value.strip()

    # The response message is a JSON object which comes back on one line.
    # Since this might change in the future, we use the 'Content-Length'
    # header.
    if 'Content-Length' not in headers:
      raise RuntimeError( "Missing 'Content-Length' header" )
    contentlength = int( headers[ 'Content-Length' ] )
    message = json.loads( self._tsserver_handle.stdout.read( contentlength ) )

    msgtype = message[ 'type' ]
    if msgtype == 'event':
      self._HandleEvent( message )
      return self._ReadResponse( expected_seq )

    if msgtype != 'response':
      raise RuntimeError( 'Unsuported message type {0}'.format( msgtype ) )
    if int( message[ 'request_seq' ] ) != expected_seq:
      raise RuntimeError( 'Request sequence mismatch' )
    if not message[ 'success' ]:
      raise RuntimeError( message[ 'message' ] )

    return message


  def _HandleEvent( self, event ):
    """Handle event message from TSServer."""

    # We ignore events for now since we don't have a use for them.
    eventname = event[ 'event' ]
    _logger.info( 'Recieved {0} event from tsserver'.format( eventname ) )


  def _Reload( self, request_data ):
    """
    Syncronize TSServer's view of the file to
    the contents of the unsaved buffer.
    """

    filename = request_data[ 'filepath' ]
    contents = request_data[ 'file_data' ][ filename ][ 'contents' ]
    tmpfile = NamedTemporaryFile( delete=False )
    tmpfile.write( utils.ToUtf8IfNeeded( contents ) )
    tmpfile.close()
    seq = self._SendRequest( 'reload', {
      'file':    filename,
      'tmpfile': tmpfile.name
    } )
    self._ReadResponse( seq )
    os.unlink( tmpfile.name )


  def SupportedFiletypes( self ):
    return [ 'typescript' ]


  def ComputeCandidatesInner( self, request_data ):
    with self._lock:
      self._Reload( request_data )
      seq = self._SendRequest( 'completions', {
        'file':   request_data[ 'filepath' ],
        'line':   request_data[ 'line_num' ],
        'offset': request_data[ 'column_num' ]
      } )
      entries = self._ReadResponse( seq )[ 'body' ]

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

      seq = self._SendRequest( 'completionEntryDetails', {
        'file':       request_data[ 'filepath' ],
        'line':       request_data[ 'line_num' ],
        'offset':     request_data[ 'column_num' ],
        'entryNames': names
      } )
      detailed_entries = self._ReadResponse( seq )[ 'body' ]
      return [ _ConvertDetailedCompletionData( e, namelength )
               for e in detailed_entries ]


  def OnBufferVisit( self, request_data ):
    filename = request_data[ 'filepath' ]
    with self._lock:
      self._SendRequest( 'open', { 'file': filename } )


  def OnBufferUnload( self, request_data ):
    filename = request_data[ 'filepath' ]
    with self._lock:
      self._SendRequest( 'close', { 'file': filename } )


  def OnFileReadyToParse( self, request_data ):
    with self._lock:
      self._Reload( request_data )


  def DefinedSubcommands( self ):
    return [ 'GoToDefinition',
             'GetType',
             'GetDoc' ]


  def OnUserCommand( self, arguments, request_data ):
    command = arguments[ 0 ]
    if command == 'GoToDefinition':
      return self._GoToDefinition( request_data )
    if command == 'GetType':
      return self._GetType( request_data )
    if command == 'GetDoc':
      return self._GetDoc( request_data )

    raise ValueError( self.UserCommandsHelpMessage() )


  def _GoToDefinition( self, request_data ):
    with self._lock:
      self._Reload( request_data )
      seq = self._SendRequest( 'definition', {
        'file':   request_data[ 'filepath' ],
        'line':   request_data[ 'line_num' ],
        'offset': request_data[ 'column_num' ]
      } )

      filespans = self._ReadResponse( seq )[ 'body' ]
      if not filespans:
        raise RuntimeError( 'Could not find definition' )

      span = filespans[ 0 ]
      return responses.BuildGoToResponse(
        filepath   = span[ 'file' ],
        line_num   = span[ 'start' ][ 'line' ],
        column_num = span[ 'start' ][ 'offset' ]
      )


  def _GetType( self, request_data ):
    with self._lock:
      self._Reload( request_data )
      seq = self._SendRequest( 'quickinfo', {
        'file':   request_data[ 'filepath' ],
        'line':   request_data[ 'line_num' ],
        'offset': request_data[ 'column_num' ]
      } )

      info = self._ReadResponse( seq )[ 'body' ]
      return responses.BuildDisplayMessageResponse( info[ 'displayString' ] )


  def _GetDoc( self, request_data ):
    with self._lock:
      self._Reload( request_data )
      seq = self._SendRequest( 'quickinfo', {
        'file':   request_data[ 'filepath' ],
        'line':   request_data[ 'line_num' ],
        'offset': request_data[ 'column_num' ]
      } )

      info = self._ReadResponse( seq )[ 'body' ]
      message = '{0}\n\n{1}'.format( info[ 'displayString' ],
                                     info[ 'documentation' ] )
      return responses.BuildDetailedInfoResponse( message )


  def Shutdown( self ):
    with self._lock:
      self._SendRequest( 'exit' )


def _ConvertCompletionData( completion_data ):
  return responses.BuildCompletionData(
    insertion_text = utils.ToUtf8IfNeeded( completion_data[ 'name' ] ),
    menu_text      = utils.ToUtf8IfNeeded( completion_data[ 'name' ] ),
    kind           = utils.ToUtf8IfNeeded( completion_data[ 'kind' ] ),
    extra_data     = utils.ToUtf8IfNeeded( completion_data[ 'kind' ] )
  )


def _ConvertDetailedCompletionData( completion_data, padding = 0 ):
  name = completion_data[ 'name' ]
  display_parts = completion_data[ 'displayParts' ]
  signature = ''.join( [ p[ 'text' ] for p in display_parts ] )
  menu_text = '{0} {1}'.format( name.ljust( padding ), signature )
  return responses.BuildCompletionData(
    insertion_text = utils.ToUtf8IfNeeded( name ),
    menu_text      = utils.ToUtf8IfNeeded( menu_text ),
    kind           = utils.ToUtf8IfNeeded( completion_data[ 'kind' ] )
  )
