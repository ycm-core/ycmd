# Copyright (C) 2015-2020 ycmd contributors
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

import json
import logging
import os
import subprocess
import itertools
import threading
from collections import defaultdict
from functools import partial

from tempfile import NamedTemporaryFile

from ycmd import extra_conf_store
from ycmd import responses
from ycmd import utils
from ycmd.completers.completer import Completer
from ycmd.completers.completer_utils import GetFileLines, GetFileContents
from ycmd.utils import LOGGER, re

SERVER_NOT_RUNNING_MESSAGE = 'TSServer is not running.'
NO_DIAGNOSTIC_MESSAGE = 'No diagnostic for current line!'

RESPONSE_TIMEOUT_SECONDS = 20

TSSERVER_DIR = os.path.abspath(
  os.path.join( os.path.dirname( __file__ ), '..', '..', '..', 'third_party',
                'tsserver' ) )

LOGFILE_FORMAT = 'tsserver_'


class DeferredResponse:
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
    if not self._event.is_set():
      raise RuntimeError( 'Response Timeout' )
    message = self._message
    if not message[ 'success' ]:
      raise RuntimeError( message[ 'message' ] )
    if 'body' in message:
      return self._message[ 'body' ]


def FindTSServer( user_options_path ):
  tsserver = utils.FindExecutableWithFallback( user_options_path , None )
  if tsserver and os.path.isfile( tsserver ):
    return tsserver
  # The TSServer executable is installed at the root directory on Windows while
  # it's installed in the bin folder on other platforms.
  for executable in [ os.path.join( TSSERVER_DIR,
                                    'node_modules',
                                    '.bin',
                                    'tsserver' ),
                      'tsserver' ]:
    tsserver = utils.FindExecutable( executable )
    if tsserver:
      return tsserver
  return None


def ShouldEnableTypeScriptCompleter( user_options ):
  tsserver = FindTSServer( user_options[ 'tsserver_binary_path' ] )
  if not tsserver:
    LOGGER.error( 'Not using TypeScript completer: TSServer not installed '
                  'in %s', TSSERVER_DIR )
    return False
  LOGGER.info( 'Using TypeScript completer with %s', tsserver )
  return True


def IsLineInTsDiagnosticRange( line, ts_diagnostic ):
  ts_start_line = ts_diagnostic[ 'startLocation' ][ 'line' ]
  ts_end_line = ts_diagnostic[ 'endLocation' ][ 'line' ]

  return ts_start_line <= line and ts_end_line >= line


def GetByteOffsetDistanceFromTsDiagnosticRange(
      byte_offset,
      line_value,
      ts_diagnostic ):
  ts_start_offset = ts_diagnostic[ 'startLocation' ][ 'offset' ]
  ts_end_offset = ts_diagnostic[ 'endLocation' ][ 'offset' ]

  codepoint_offset = utils.ByteOffsetToCodepointOffset( line_value,
                                                        byte_offset )

  start_difference = codepoint_offset - ts_start_offset
  end_difference = codepoint_offset - ( ts_end_offset - 1 )

  if start_difference >= 0 and end_difference <= 0:
    return 0

  return min( abs( start_difference ), abs( end_difference ) )


class TypeScriptCompleter( Completer ):
  """
  Completer for TypeScript.

  It uses TSServer which is bundled with TypeScript 1.5

  See the protocol here:
  https://github.com/microsoft/TypeScript/blob/master/src/server/protocol.ts
  """


  def __init__( self, user_options ):
    super().__init__( user_options )

    self._logfile = None

    self._tsserver_lock = threading.Lock()
    self._tsserver_handle = None
    self._tsserver_version = None
    self._tsserver_executable = FindTSServer(
        user_options[ 'tsserver_binary_path' ] )
    # Used to read response only if TSServer is running.
    self._tsserver_is_running = threading.Event()

    # Used to prevent threads from concurrently writing to
    # the tsserver process's stdin
    self._write_lock = threading.Lock()

    # Each request sent to tsserver must have a sequence id.
    # Responses contain the id sent in the corresponding request.
    self._sequenceid = itertools.count()

    # Used to prevent threads from concurrently accessing the sequence counter
    self._sequenceid_lock = threading.Lock()

    # Start a thread to read response from TSServer.
    utils.StartThread( self._ReaderLoop )

    # Used to map sequence id's to their corresponding DeferredResponse
    # objects. The reader loop uses this to hand out responses.
    self._pending = {}

    # Used to prevent threads from concurrently reading and writing to
    # the pending response dictionary
    self._pending_lock = threading.Lock()

    self._StartServer()

    self._latest_diagnostics_for_file_lock = threading.Lock()
    self._latest_diagnostics_for_file = defaultdict( list )

    # There's something in the API that lists the trigger characters, but
    # there is no way to request that from the server, so we just hard-code
    # the signature triggers.
    self.SetSignatureHelpTriggers( [ '(', ',', '<' ] )

    LOGGER.info( 'Enabling TypeScript completion' )

  def _SetServerVersion( self ):
    version = self._SendRequest( 'status' )[ 'version' ]
    with self._tsserver_lock:
      self._tsserver_version = version

    # TODO: We should probably make this configurable in ycm_extra_conf.py along
    # with all the other preferences
    self._SendCommand( 'configure',  {
      'preferences': {
        'includeInlayParameterNameHints': "all",
        'includeInlayParameterNameHintsWhenArgumentMatchesName': True,
        'includeInlayFunctionParameterTypeHints': True,
        'includeInlayVariableTypeHints': True,
        'includeInlayVariableTypeHintsWhenTypeMatchesName': True,
        'includeInlayPropertyDeclarationTypeHints': True,
        'includeInlayFunctionLikeReturnTypeHints': True,
        'includeInlayEnumMemberValueHints': True,
      }
    } )


  def _StartServer( self ):
    with self._tsserver_lock:
      self._StartServerNoLock()


  def _StartServerNoLock( self ):
    if self._ServerIsRunning():
      return

    self._logfile = utils.CreateLogfile( LOGFILE_FORMAT )
    tsserver_log = f'-file { self._logfile } -level { _LogLevel() }'
    # TSServer gets the configuration for the log file through the
    # environment variable 'TSS_LOG'. This seems to be undocumented but
    # looking at the source code it seems like this is the way:
    # https://github.com/Microsoft/TypeScript/blob/8a93b489454fdcbdf544edef05f73a913449be1d/src/server/server.ts#L136
    environ = os.environ.copy()
    environ[ 'TSS_LOG' ] = tsserver_log

    # TSServer runs out of memory on larger projects. This is the value that
    # VSCode uses.
    environ[ 'NODE_OPTIONS' ] = '--max_old_space_size=3072'

    LOGGER.info( 'TSServer log file: %s', self._logfile )

    # We need to redirect the error stream to the output one on Windows.
    self._tsserver_handle = utils.SafePopen( self._tsserver_executable,
                                             stdin = subprocess.PIPE,
                                             stdout = subprocess.PIPE,
                                             stderr = subprocess.STDOUT,
                                             env = environ )

    LOGGER.info( "TSServer started with PID %s", self._tsserver_handle.pid )
    self._tsserver_is_running.set()

    utils.StartThread( self._SetServerVersion )


  def _ReaderLoop( self ):
    """
    Read responses from TSServer and use them to resolve
    the DeferredResponse instances.
    """

    while True:
      self._tsserver_is_running.wait()

      try:
        message = self._ReadMessage()
      except ( RuntimeError, ValueError ):
        LOGGER.exception( 'Error while reading message from server' )
        if not self._ServerIsRunning():
          self._tsserver_is_running.clear()
        continue

      # We ignore events for now since we don't have a use for them.
      msgtype = message[ 'type' ]
      if msgtype == 'event':
        eventname = message[ 'event' ]
        LOGGER.info( 'Received %s event from TSServer',  eventname )
        continue
      if msgtype != 'response':
        LOGGER.error( 'Unsupported message type', msgtype )
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
    content_length = int( headers[ 'Content-Length' ] )
    # TSServer adds a newline at the end of the response message and counts it
    # as one character (\n) towards the content length. However, newlines are
    # two characters on Windows (\r\n), so we need to take care of that. See
    # issue https://github.com/Microsoft/TypeScript/issues/3403
    content = self._tsserver_handle.stdout.read( content_length )
    if utils.OnWindows() and content.endswith( b'\r' ):
      content += self._tsserver_handle.stdout.read( 1 )

    LOGGER.debug( "RX (tsserver): %s", content )
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


    req = json.dumps( request, separators = ( ',', ':' ) )
    LOGGER.debug( 'TX (tsserver): %s', req )
    serialized_request = utils.ToBytes( req + '\n' )

    with self._write_lock:
      try:
        self._tsserver_handle.stdin.write( serialized_request )
        self._tsserver_handle.stdin.flush()
      # IOError is an alias of OSError in Python 3.
      except ( AttributeError, IOError ):
        LOGGER.exception( SERVER_NOT_RUNNING_MESSAGE )
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
    Synchronize TSServer's view of the file to
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
    return utils.ProcessIsRunning( self._tsserver_handle )


  def Language( self ):
    return 'typescript'


  def ServerIsHealthy( self ):
    return self._ServerIsRunning()


  def SupportedFiletypes( self ):
    return [ 'javascript', 'typescript', 'typescriptreact', 'javascriptreact' ]


  def SignatureHelpAvailable( self ):
    return responses.SignatureHelpAvailalability.AVAILABLE


  def ComputeCandidatesInner( self, request_data ):
    self._Reload( request_data )
    entries = self._SendRequest( 'completionInfo', {
      'file':                         request_data[ 'filepath' ],
      'line':                         request_data[ 'line_num' ],
      'offset':                       request_data[ 'start_codepoint' ],
      'includeExternalModuleExports': True
    } )[ 'entries' ]
    # Ignore entries with the "warning" kind. They are identifiers from the
    # current file that TSServer returns sometimes in JavaScript.
    return [ responses.BuildCompletionData(
      insertion_text = entry[ 'name' ],
      # We store the entries returned by TSServer in the extra_data field to
      # detail the candidates once the filtering is done.
      extra_data = entry
    ) for entry in entries if entry[ 'kind' ] != 'warning' ]


  def DetailCandidates( self, request_data, candidates ):
    undetailed_entries = []
    map_entries_to_candidates = {}
    for candidate in candidates:
      undetailed_entry = candidate[ 'extra_data' ]
      if 'name' not in undetailed_entry:
        # This candidate is already detailed.
        continue
      map_entries_to_candidates[ undetailed_entry[ 'name' ] ] = candidate
      undetailed_entries.append( undetailed_entry )

    if not undetailed_entries:
      # All candidates are already detailed.
      return candidates

    detailed_entries = self._SendRequest( 'completionEntryDetails', {
      'file':       request_data[ 'filepath' ],
      'line':       request_data[ 'line_num' ],
      'offset':     request_data[ 'start_codepoint' ],
      'entryNames': undetailed_entries
    } )
    for entry in detailed_entries:
      candidate = map_entries_to_candidates[ entry[ 'name' ] ]
      extra_menu_info, detailed_info = _BuildCompletionExtraMenuAndDetailedInfo(
        request_data, entry )
      if extra_menu_info:
        candidate[ 'extra_menu_info' ] = extra_menu_info
      if detailed_info:
        candidate[ 'detailed_info' ] = detailed_info
      candidate[ 'kind' ] = entry[ 'kind' ]
      candidate[ 'extra_data' ] = _BuildCompletionFixIts( request_data, entry )
    return candidates


  def GetSubcommandsMap( self ):
    return {
      'GoToCallers'       : ( lambda self, request_data, args:
                              self._CallHierarchy( request_data,
                                                   [ 'Incoming' ] ) ),
      'GoToCallees'  : ( lambda self, request_data, args:
                              self._CallHierarchy( request_data,
                                                   [ 'Outgoing' ] ) ),
      'RestartServer'     : ( lambda self, request_data, args:
                              self._RestartServer( request_data ) ),
      'StopServer'        : ( lambda self, request_data, args:
                              self._StopServer() ),
      'GoTo'              : ( lambda self, request_data, args:
                              self._GoToDefinition( request_data ) ),
      'GoToDefinition'    : ( lambda self, request_data, args:
                              self._GoToDefinition( request_data ) ),
      'GoToDeclaration'   : ( lambda self, request_data, args:
                              self._GoToDefinition( request_data ) ),
      'GoToImplementation': ( lambda self, request_data, args:
                              self._GoToImplementation( request_data ) ),
      'GoToReferences'    : ( lambda self, request_data, args:
                              self._GoToReferences( request_data ) ),
      'GoToType'          : ( lambda self, request_data, args:
                              self._GoToType( request_data ) ),
      'GoToSymbol'        : ( lambda self, request_data, args:
                              self._GoToSymbol( request_data, args ) ),
      'GetType'           : ( lambda self, request_data, args:
                              self._GetType( request_data ) ),
      'GetDoc'            : ( lambda self, request_data, args:
                              self._GetDoc( request_data ) ),
      'FixIt'             : ( lambda self, request_data, args:
                              self._FixIt( request_data, args ) ),
      'OrganizeImports'   : ( lambda self, request_data, args:
                              self._OrganizeImports( request_data ) ),
      'RefactorRename'    : ( lambda self, request_data, args:
                              self._RefactorRename( request_data, args ) ),
      'Format'            : ( lambda self, request_data, args:
                              self._Format( request_data ) ),
    }


  def OnBufferVisit( self, request_data ):
    filename = request_data[ 'filepath' ]
    self._SendCommand( 'open', { 'file': filename } )


  def OnBufferUnload( self, request_data ):
    filename = request_data[ 'filepath' ]
    self._SendCommand( 'close', { 'file': filename } )


  def ComputeInlayHints( self, request_data ):
    self._Reload( request_data )

    # Cache the offsets of all the newlines in the file. These are used to
    # calculate the line/column values from the offsets retuned by the diff
    # scanner
    contents = GetFileContents( request_data, request_data[ 'filepath' ] )
    lines = GetFileLines( request_data, request_data[ 'filepath' ] )
    newlines = [ -1 ] + [ i for i, c in enumerate( contents ) if c == '\n' ]
    newlines.append( len( contents ) )

    def LocationToOffset( location ):
      try:
        return (
          newlines[ location[ 'line_num' ] - 1 ]
          + utils.ByteOffsetToCodepointOffset( lines,
                                               location[ 'column_num' ] )
        )
      except IndexError:
        raise RuntimeError( "Invalid range" )

    r = request_data[ 'range' ]
    start = LocationToOffset( r[ 'start' ] )
    end = LocationToOffset( r[ 'end' ] )

    hints = self._SendRequest( 'provideInlayHints', {
      'file':   request_data[ 'filepath' ],
      'start':  start,
      'length': end - start,
    } )

    result = [ {
      'kind': h[ 'kind' ],
      'label': h[ 'text' ],
      'position': responses.BuildLocationData(
          _BuildLocation( lines,
                          request_data[ 'filepath' ],
                          h[ 'position' ][ 'line' ],
                          h[ 'position' ][ 'offset' ] ) ),
      'paddingLeft': h.get( 'whitespaceBefore', False ),
      'paddingRight': h.get( 'whitespaceAfter', False ),
    } for h in hints ]

    LOGGER.debug( "INLAY HINTS: %s", result )
    return result



  def OnFileReadyToParse( self, request_data ):
    # Only load the extra conf. We don't need it for anything but Format.
    extra_conf_store.ModuleFileForSourceFile( request_data[ 'filepath' ] )
    self._Reload( request_data )

    diagnostics = self.GetDiagnosticsForCurrentFile( request_data )
    filepath = request_data[ 'filepath' ]
    with self._latest_diagnostics_for_file_lock:
      self._latest_diagnostics_for_file[ filepath ] = diagnostics
    return responses.BuildDiagnosticResponse( diagnostics,
                                              filepath,
                                              self.max_diagnostics_to_display )


  def GetTsDiagnosticsForCurrentFile( self, request_data ):
    # This returns the data the TypeScript server responded with.
    # Note that its "offset" values represent codepoint offsets,
    # not byte offsets, which are required by the ycmd API.
    filepath = request_data[ 'filepath' ]

    ts_diagnostics = list( itertools.chain(
      self._GetSemanticDiagnostics( filepath ),
      self._GetSyntacticDiagnostics( filepath )
    ) )

    return ts_diagnostics


  def _TsDiagnosticToYcmdDiagnostic( self, request_data, ts_diagnostic ):
    filepath = request_data[ 'filepath' ]

    ts_fixes = self._SendRequest( 'getCodeFixes', {
      'file':        filepath,
      'startLine':   ts_diagnostic[ 'startLocation' ][ 'line' ],
      'startOffset': ts_diagnostic[ 'startLocation' ][ 'offset' ],
      'endLine':     ts_diagnostic[ 'endLocation' ][ 'line' ],
      'endOffset':   ts_diagnostic[ 'endLocation' ][ 'offset' ],
      'errorCodes':  [ ts_diagnostic[ 'code' ] ]
    } )
    location = responses.Location( request_data[ 'line_num' ],
                                   request_data[ 'column_num' ],
                                   filepath )

    fixits = []
    for fix in ts_fixes:
      description = fix[ 'description' ]
      # TSServer returns these fixits for every error in JavaScript files.
      # Ignore them since they are not useful.
      if description in [ 'Ignore this error message',
                          'Disable checking for this file' ]:
        continue

      fixit = responses.FixIt( location,
                               _BuildFixItForChanges( request_data,
                                                      fix[ 'changes' ] ),
                               description )
      fixits.append( fixit )

    contents = GetFileLines( request_data, filepath )

    ts_start_location = ts_diagnostic[ 'startLocation' ]
    ts_start_line = ts_start_location[ 'line' ]
    start_offset = utils.CodepointOffsetToByteOffset(
      contents[ ts_start_line - 1 ],
      ts_start_location[ 'offset' ] )

    ts_end_location = ts_diagnostic[ 'endLocation' ]
    ts_end_line = ts_end_location[ 'line' ]
    end_offset = utils.CodepointOffsetToByteOffset(
      contents[ ts_end_line - 1 ],
      ts_end_location[ 'offset' ] )

    location_start = responses.Location( ts_start_line, start_offset, filepath )
    location_end = responses.Location( ts_end_line, end_offset, filepath )

    location_extent = responses.Range( location_start, location_end )

    return responses.Diagnostic( [ location_extent ],
                                 location_start,
                                 location_extent,
                                 ts_diagnostic[ 'message' ],
                                 'ERROR',
                                 fixits = fixits )


  def GetDiagnosticsForCurrentFile( self, request_data ):
    ts_diagnostics = self.GetTsDiagnosticsForCurrentFile( request_data )

    return [ self._TsDiagnosticToYcmdDiagnostic( request_data, x )
             for x in ts_diagnostics ]


  def GetDetailedDiagnostic( self, request_data ):
    ts_diagnostics = self.GetTsDiagnosticsForCurrentFile( request_data )
    ts_diagnostics_on_line = list( filter(
      partial( IsLineInTsDiagnosticRange, request_data[ 'line_num' ] ),
      ts_diagnostics
    ) )

    if not ts_diagnostics_on_line:
      raise ValueError( NO_DIAGNOSTIC_MESSAGE )

    closest_ts_diagnostic = None
    distance_to_closest_ts_diagnostic = None

    line_value = request_data[ 'line_value' ]
    current_byte_offset = request_data[ 'column_num' ]

    for ts_diagnostic in ts_diagnostics_on_line:
      distance = GetByteOffsetDistanceFromTsDiagnosticRange(
        current_byte_offset,
        line_value,
        ts_diagnostic
      )
      if ( not closest_ts_diagnostic
            or distance < distance_to_closest_ts_diagnostic ):
        distance_to_closest_ts_diagnostic = distance
        closest_ts_diagnostic = ts_diagnostic

    closest_diagnostic = self._TsDiagnosticToYcmdDiagnostic(
      request_data,
      closest_ts_diagnostic )

    return responses.BuildDisplayMessageResponse( closest_diagnostic.text_ )


  def ComputeSignaturesInner( self, request_data ):
    self._Reload( request_data )
    try:
      items = self._SendRequest( 'signatureHelp', {
        'file': request_data[ 'filepath' ],
        'line': request_data[ 'line_num' ],
        'offset': request_data[ 'start_codepoint' ],
        # triggerReason - opitonal and tricky to populate
      } )
    except RuntimeError:
      # We get an exception when there are no results, so squash it
      if LOGGER.isEnabledFor( logging.DEBUG ):
        LOGGER.exception( "No signatures from tsserver" )
      return {}

    def MakeSignature( s ):
      def GetTSDocs( docs_list ):
        return '\n'.join( item[ 'text' ] for item in docs_list )

      label = _DisplayPartsToString( s[ 'prefixDisplayParts' ] )
      parameters = []
      sep = _DisplayPartsToString( s[ 'separatorDisplayParts' ] )
      for index, p in enumerate( s[ 'parameters' ] ):
        param = _DisplayPartsToString( p[ 'displayParts' ] )
        start = len( label )
        end = start + len( param )

        label += param
        if index < len( s[ 'parameters' ] ) - 1:
          label += sep

        parameters.append( {
          'documentation': GetTSDocs( p.get( 'documentation', [] ) ),
          'label': [ utils.CodepointOffsetToByteOffset( label, start ),
                     utils.CodepointOffsetToByteOffset( label, end ) ]
        } )

      label += _DisplayPartsToString( s[ 'suffixDisplayParts' ] )

      return {
        'documentation': GetTSDocs( s.get( 'documentation', [] ) ),
        'label': label,
        'parameters': parameters
      }

    return {
      'activeSignature': items[ 'selectedItemIndex' ],
      'activeParameter': items[ 'argumentIndex' ],
      'signatures': [
        MakeSignature( s ) for s in items[ 'items' ]
      ]
    }


  def _GetSemanticDiagnostics( self, filename ):
    return self._SendRequest( 'semanticDiagnosticsSync', {
      'file': filename,
      'includeLinePosition': True
    } )


  def _GetSyntacticDiagnostics( self, filename ):
    return self._SendRequest( 'syntacticDiagnosticsSync', {
      'file': filename,
      'includeLinePosition': True
    } )


  def _CallHierarchy( self, request_data, args ):
    self._Reload( request_data )

    response = self._SendRequest( f'provideCallHierarchy{ args[ 0 ] }Calls', {
      'file':   request_data[ 'filepath' ],
      'line':   request_data[ 'line_num' ],
      'offset': request_data[ 'column_codepoint' ]
    } )

    goto_response = []
    for hierarchy_item in response:
      description = hierarchy_item.get( 'from', hierarchy_item.get( 'to' ) )
      filepath = description[ 'file' ]
      start_position = hierarchy_item[ 'fromSpans' ][ 0 ][ 'start' ]
      goto_line = start_position[ 'line' ]
      try:
        line_value = GetFileLines( request_data, filepath )[ goto_line - 1 ]
      except IndexError:
        continue
      goto_column = utils.CodepointOffsetToByteOffset(
        line_value,
        start_position[ 'offset' ] )
      goto_response.append( responses.BuildGoToResponse(
        filepath,
        goto_line,
        goto_column,
        description[ 'name' ] ) )

    if goto_response:
      return goto_response
    raise RuntimeError( f'No { args[ 0 ].lower() } calls found.' )


  def _GoToDefinition( self, request_data ):
    self._Reload( request_data )
    filespans = self._SendRequest( 'definition', {
      'file':   request_data[ 'filepath' ],
      'line':   request_data[ 'line_num' ],
      'offset': request_data[ 'column_codepoint' ]
    } )

    if not filespans:
      raise RuntimeError( 'Could not find definition.' )

    span = filespans[ 0 ]
    return responses.BuildGoToResponseFromLocation(
      _BuildLocation( GetFileLines( request_data, span[ 'file' ] ),
                      span[ 'file' ],
                      span[ 'start' ][ 'line' ],
                      span[ 'start' ][ 'offset' ] ) )


  def _GoToImplementation( self, request_data ):
    self._Reload( request_data )
    try:
      filespans = self._SendRequest( 'implementation', {
        'file':   request_data[ 'filepath' ],
        'line':   request_data[ 'line_num' ],
        'offset': request_data[ 'column_codepoint' ]
      } )
    except RuntimeError:
      raise RuntimeError( 'No implementation found.' )

    results = []
    for span in filespans:
      filename = span[ 'file' ]
      start = span[ 'start' ]
      lines = GetFileLines( request_data, span[ 'file' ] )
      line_num = start[ 'line' ]
      results.append( responses.BuildGoToResponseFromLocation(
        _BuildLocation( lines, filename, line_num, start[ 'offset' ] ),
        lines[ line_num - 1 ] ) )
    return results


  def _GoToReferences( self, request_data ):
    self._Reload( request_data )
    response = self._SendRequest( 'references', {
      'file':   request_data[ 'filepath' ],
      'line':   request_data[ 'line_num' ],
      'offset': request_data[ 'column_codepoint' ]
    } )
    return [
      responses.BuildGoToResponseFromLocation(
        _BuildLocation( GetFileLines( request_data, ref[ 'file' ] ),
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
    except RuntimeError:
      raise RuntimeError( 'Could not find type definition.' )

    if not filespans:
      raise RuntimeError( 'Could not find type definition.' )

    span = filespans[ 0 ]
    return responses.BuildGoToResponse(
      filepath   = span[ 'file' ],
      line_num   = span[ 'start' ][ 'line' ],
      column_num = span[ 'start' ][ 'offset' ]
    )


  def _GoToSymbol( self, request_data, args ):
    if len( args ) < 1:
      raise RuntimeError( 'Must specify something to search for' )
    query = args[ 0 ]

    self._Reload( request_data )
    filespans = self._SendRequest( 'navto', {
      'searchValue': query,
      'file': request_data[ 'filepath' ]
    } )

    if not filespans:
      raise RuntimeError( 'Symbol not found' )

    results = [
      responses.BuildGoToResponseFromLocation(
        _BuildLocation( GetFileLines( request_data, fs[ 'file' ] ),
                        fs[ 'file' ],
                        fs[ 'start' ][ 'line' ],
                        fs[ 'start' ][ 'offset' ] ),
        fs[ 'name' ] )
      for fs in filespans
    ]

    if len( results ) == 1:
      return results[ 0 ]

    return results


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

    extra_info = _AggregateTagsFromDocstring( info )

    message = f'{ info[ "displayString" ] }\n\n{ info[ "documentation" ] }'
    if extra_info:
      message += f'\n\n{ extra_info }'

    return responses.BuildDetailedInfoResponse( message )


  def _FixIt( self, request_data, args ):
    self._Reload( request_data )

    filepath = request_data[ 'filepath' ]
    line_num = request_data[ 'line_num' ]

    fixits = []
    with self._latest_diagnostics_for_file_lock:
      for diagnostic in self._latest_diagnostics_for_file[ filepath ]:
        if diagnostic.location_.line_number_ != line_num:
          continue

        fixits.extend( diagnostic.fixits_ )

    return responses.BuildFixItResponse( fixits )


  def _OrganizeImports( self, request_data ):
    self._Reload( request_data )

    filepath = request_data[ 'filepath' ]
    changes = self._SendRequest( 'organizeImports', {
      'scope': {
        'type': 'file',
        'args': {
          'file': filepath
        }
      }
    } )

    location = responses.Location( request_data[ 'line_num' ],
                                   request_data[ 'column_num' ],
                                   filepath )
    return responses.BuildFixItResponse( [
      responses.FixIt( location,
                       _BuildFixItForChanges( request_data, changes ) )
    ] )


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
      raise RuntimeError( 'Value cannot be renamed: '
                          f'{ response[ "info" ][ "localizedErrorMessage" ] }' )

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


  def _Format( self, request_data ):
    filepath = request_data[ 'filepath' ]

    self._Reload( request_data )

    # TODO: support all formatting options. See
    # https://github.com/Microsoft/TypeScript/blob/72e92a055823f1ade97d03d7526dbab8be405dde/lib/protocol.d.ts#L2060-L2077
    # for the list of options. While not standard, a way to support these
    # options, which is already adopted by a number of clients, would be to read
    # the "formatOptions" field in the tsconfig.json file.
    options = dict( request_data[ 'options' ] )
    options[ 'tabSize' ] = options.pop( 'tab_size' )
    options[ 'indentSize' ] = options[ 'tabSize' ]
    options[ 'convertTabsToSpaces' ] = options.pop( 'insert_spaces' )
    options.update(
      self.AdditionalFormattingOptions( request_data ) )
    self._SendRequest( 'configure', {
      'file': filepath,
      'formatOptions': options
    } )

    response = self._SendRequest( 'format',
                                  _BuildTsFormatRange( request_data ) )

    contents = GetFileLines( request_data, filepath )
    chunks = [ _BuildFixItChunkForRange( text_edit[ 'newText' ],
                                         contents,
                                         filepath,
                                         text_edit ) for text_edit in response ]

    location = responses.Location( request_data[ 'line_num' ],
                                   request_data[ 'column_num' ],
                                   filepath )
    return responses.BuildFixItResponse( [
      responses.FixIt( location, chunks )
    ] )


  def _RestartServer( self, request_data ):
    with self._tsserver_lock:
      self._StopServerNoLock()
      self._StartServerNoLock()
      # This is needed because after we restart the TSServer it would lose all
      # the information about the files we were working on. This means that the
      # newly started TSServer will know nothing about the buffer we're working
      # on after restarting the server. So if we restart the server and right
      # after that ask for completion in the buffer, the server will timeout.
      # So we notify the server that we're working on the current buffer.
      self.OnBufferVisit( request_data )


  def _StopServer( self ):
    with self._tsserver_lock:
      self._StopServerNoLock()


  def _StopServerNoLock( self ):
    if self._ServerIsRunning():
      LOGGER.info( 'Stopping TSServer with PID %s',
                   self._tsserver_handle.pid )
      try:
        self._SendCommand( 'exit' )
        utils.WaitUntilProcessIsTerminated( self._tsserver_handle,
                                            timeout = 5 )
        LOGGER.info( 'TSServer stopped' )
      except Exception:
        LOGGER.exception( 'Error while stopping TSServer' )

    self._CleanUp()


  def _CleanUp( self ):
    utils.CloseStandardStreams( self._tsserver_handle )
    self._tsserver_handle = None
    self._latest_diagnostics_for_file = defaultdict( list )
    if not self.user_options[ 'server_keep_logfiles' ] and self._logfile:
      utils.RemoveIfExists( self._logfile )
      self._logfile = None


  def Shutdown( self ):
    self._StopServer()


  def DebugInfo( self, request_data ):
    with self._tsserver_lock:
      item_version = responses.DebugInfoItem( 'version',
                                              self._tsserver_version )
      tsserver = responses.DebugInfoServer(
          name = 'TSServer',
          handle = self._tsserver_handle,
          executable = self._tsserver_executable,
          logfiles = [ self._logfile ],
          extras = [ item_version ] )

      return responses.BuildDebugInfoResponse( name = 'TypeScript',
                                               servers = [ tsserver ] )


def _LogLevel():
  return 'verbose' if LOGGER.isEnabledFor( logging.DEBUG ) else 'normal'


def _AggregateTagsFromDocstring( info ):
  extra_info = []
  for tag in info.get( 'tags', [] ):
    tag_name = tag[ 'name' ]
    tag_text = tag.get( 'text' )
    formated_tag = tag_name + ( f': { tag_text }' if tag_text else '' )
    extra_info.append( formated_tag )
  return '\n'.join( extra_info )


def _BuildCompletionExtraMenuAndDetailedInfo( request_data, entry ):
  signature = _DisplayPartsToString( entry[ 'displayParts' ] )
  if entry[ 'name' ] == signature:
    extra_menu_info = None
    detailed_info = []
  else:
    # Strip new lines and indentation from the signature to display it on one
    # line.
    extra_menu_info = re.sub( '\\s+', ' ', signature )
    detailed_info = [ signature ]

  docs = entry.get( 'documentation', [] )
  detailed_info += [ doc[ 'text' ].strip() for doc in docs if doc ]

  extra_info = _AggregateTagsFromDocstring( entry )
  if extra_info:
    detailed_info.append( extra_info )

  detailed_info = '\n\n'.join( detailed_info )

  return extra_menu_info, detailed_info


def _BuildCompletionFixIts( request_data, entry ):
  if 'codeActions' in entry:
    location = responses.Location( request_data[ 'line_num' ],
                                   request_data[ 'column_num' ],
                                   request_data[ 'filepath' ] )
    return responses.BuildFixItResponse( [
      responses.FixIt( location,
                       _BuildFixItForChanges( request_data,
                                              action[ 'changes' ] ),
                       action[ 'description' ] )
      for action in entry[ 'codeActions' ]
    ] )
  return {}


def _BuildFixItChunkForRange( new_name,
                              file_contents,
                              file_name,
                              source_range ):
  """Returns list FixItChunk for a tsserver source range."""
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
  """Returns a list of FixItChunk for each replacement range for the supplied
  file."""
  # On Windows, TSServer annoyingly returns file path as C:/blah/blah,
  # whereas all other paths in Python are of the C:\\blah\\blah form. We use
  # normpath to have python do the conversion for us.
  file_path = os.path.normpath( file_replacement[ 'file' ] )
  file_contents = GetFileLines( request_data, file_path )
  return [ _BuildFixItChunkForRange( new_name, file_contents, file_path, r )
           for r in file_replacement[ 'locs' ] ]


def _BuildFixItForChanges( request_data, changes ):
  """Returns a list of FixItChunk given a list of TSServer changes."""
  chunks = []
  for change in changes:
    # On Windows, TSServer annoyingly returns file path as C:/blah/blah,
    # whereas all other paths in Python are of the C:\\blah\\blah form. We use
    # normpath to have python do the conversion for us.
    file_path = os.path.normpath( change[ 'fileName' ] )
    file_contents = GetFileLines( request_data, file_path )
    for text_change in change[ 'textChanges' ]:
      chunks.append( _BuildFixItChunkForRange(
        text_change[ 'newText' ],
        file_contents,
        file_path,
        text_change ) )
  return chunks


def _BuildLocation( file_contents, filename, line, offset ):
  return responses.Location(
    line = line,
    # TSServer returns codepoint offsets, but we need byte offsets, so we must
    # convert.
    column = utils.CodepointOffsetToByteOffset( file_contents[ line - 1 ],
                                                offset ),
    filename = filename )


def _BuildTsFormatRange( request_data ):
  filepath = request_data[ 'filepath' ]
  lines = GetFileLines( request_data, filepath )

  if 'range' not in request_data:
    return {
      'file': filepath,
      'line': 1,
      'offset': 1,
      'endLine': len( lines ),
      'endOffset': len( lines[ - 1 ] ) + 1
    }

  start = request_data[ 'range' ][ 'start' ]
  start_line_num = start[ 'line_num' ]
  start_line_value = lines[ start_line_num - 1 ]
  start_codepoint = utils.ByteOffsetToCodepointOffset( start_line_value,
                                                       start[ 'column_num' ] )

  end = request_data[ 'range' ][ 'end' ]
  end_line_num = end[ 'line_num' ]
  end_line_value = lines[ end_line_num - 1 ]
  end_codepoint = utils.ByteOffsetToCodepointOffset( end_line_value,
                                                     end[ 'column_num' ] )

  return {
    'file': filepath,
    'line': start_line_num,
    'offset': start_codepoint,
    'endLine': end_line_num,
    'endOffset': end_codepoint
  }


def _DisplayPartsToString( parts ):
  return ''.join( [ p[ 'text' ] for p in parts ] )
