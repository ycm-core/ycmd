# Copyright (C) 2011-2018 ycmd contributors
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

from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa

from collections import defaultdict
from future.utils import itervalues
import os
import requests
import threading

from ycmd.completers.completer import Completer
from ycmd.completers.completer_utils import GetFileLines
from ycmd.completers.cs import solutiondetection
from ycmd.utils import CodepointOffsetToByteOffset, LOGGER, re, urljoin
from ycmd import responses
from ycmd import utils

SERVER_NOT_FOUND_MSG = ( 'OmniSharp server binary not found at {0}. ' +
                         'Did you compile it? You can do so by running ' +
                         '"./install.py --cs-completer".' )
INVALID_FILE_MESSAGE = 'File is invalid.'
NO_DIAGNOSTIC_MESSAGE = 'No diagnostic for current line!'
PATH_TO_OMNISHARP_BINARY = os.path.abspath(
  os.path.join( os.path.dirname( __file__ ), '..', '..', '..',
                'third_party', 'OmniSharpServer', 'OmniSharp',
                'bin', 'Release', 'OmniSharp.exe' ) )
LOGFILE_FORMAT = 'omnisharp_{port}_{sln}_{std}_'


class CsharpCompleter( Completer ):
  """
  A Completer that uses the Omnisharp server as completion engine.
  """

  def __init__( self, user_options ):
    super( CsharpCompleter, self ).__init__( user_options )
    self._solution_for_file = {}
    self._completer_per_solution = {}
    self._diagnostic_store = None
    self._solution_state_lock = threading.Lock()

    if not os.path.isfile( PATH_TO_OMNISHARP_BINARY ):
      raise RuntimeError(
           SERVER_NOT_FOUND_MSG.format( PATH_TO_OMNISHARP_BINARY ) )


  def Shutdown( self ):
    if self.user_options[ 'auto_stop_csharp_server' ]:
      for solutioncompleter in itervalues( self._completer_per_solution ):
        solutioncompleter._StopServer()


  def SupportedFiletypes( self ):
    """ Just csharp """
    return [ 'cs' ]


  def _GetSolutionCompleter( self, request_data ):
    """ Get the solution completer or create a new one if it does not already
    exist. Use a lock to avoid creating the same solution completer multiple
    times."""
    solution = self._GetSolutionFile( request_data[ "filepath" ] )

    with self._solution_state_lock:
      if solution not in self._completer_per_solution:
        keep_logfiles = self.user_options[ 'server_keep_logfiles' ]
        desired_omnisharp_port = self.user_options.get( 'csharp_server_port' )
        completer = CsharpSolutionCompleter( solution,
                                             keep_logfiles,
                                             desired_omnisharp_port )
        self._completer_per_solution[ solution ] = completer

    return self._completer_per_solution[ solution ]


  def ShouldUseNowInner( self, request_data ):
    return True


  def ComputeCandidatesInner( self, request_data ):
    solutioncompleter = self._GetSolutionCompleter( request_data )
    return [ responses.BuildCompletionData(
                completion[ 'CompletionText' ],
                completion[ 'DisplayText' ],
                completion[ 'Description' ],
                None,
                None,
                { "required_namespace_import" :
                   completion[ 'RequiredNamespaceImport' ] } )
             for completion
             in solutioncompleter._GetCompletions( request_data ) ]


  def FilterAndSortCandidates( self, candidates, query ):
    result = super( CsharpCompleter, self ).FilterAndSortCandidates( candidates,
                                                                     query )
    result.sort( key = _CompleteIsFromImport )
    return result


  def GetSubcommandsMap( self ):
    return {
      'StopServer'                       : ( lambda self, request_data, args:
         self._SolutionSubcommand( request_data,
                                   method = '_StopServer',
                                   no_request_data = True ) ),
      'RestartServer'                    : ( lambda self, request_data, args:
         self._SolutionSubcommand( request_data,
                                   method = '_RestartServer',
                                   no_request_data = True ) ),
      'ReloadSolution'                   : ( lambda self, request_data, args:
         self._SolutionSubcommand( request_data,
                                   method = '_ReloadSolution',
                                   no_request_data = True ) ),
      'SolutionFile'                     : ( lambda self, request_data, args:
         self._SolutionSubcommand( request_data,
                                   method = '_SolutionFile',
                                   no_request_data = True ) ),
      'GoToDefinition'                   : ( lambda self, request_data, args:
         self._SolutionSubcommand( request_data,
                                   method = '_GoToDefinition' ) ),
      'GoToDeclaration'                  : ( lambda self, request_data, args:
         self._SolutionSubcommand( request_data,
                                   method = '_GoToDefinition' ) ),
      'GoTo'                             : ( lambda self, request_data, args:
         self._SolutionSubcommand( request_data,
                                   method = '_GoToImplementation',
                                   fallback_to_declaration = True ) ),
      'GoToDefinitionElseDeclaration'    : ( lambda self, request_data, args:
         self._SolutionSubcommand( request_data,
                                   method = '_GoToDefinition' ) ),
      'GoToImplementation'               : ( lambda self, request_data, args:
         self._SolutionSubcommand( request_data,
                                   method = '_GoToImplementation',
                                   fallback_to_declaration = False ) ),
      'GoToImplementationElseDeclaration': ( lambda self, request_data, args:
         self._SolutionSubcommand( request_data,
                                   method = '_GoToImplementation',
                                   fallback_to_declaration = True ) ),
      'GetType'                          : ( lambda self, request_data, args:
         self._SolutionSubcommand( request_data,
                                   method = '_GetType' ) ),
      'FixIt'                            : ( lambda self, request_data, args:
         self._SolutionSubcommand( request_data,
                                   method = '_FixIt' ) ),
      'GetDoc'                           : ( lambda self, request_data, args:
         self._SolutionSubcommand( request_data,
                                   method = '_GetDoc' ) )
    }


  def _SolutionSubcommand( self, request_data, method,
                           no_request_data = False, **kwargs ):
    solutioncompleter = self._GetSolutionCompleter( request_data )
    if not no_request_data:
      kwargs[ 'request_data' ] = request_data
    return getattr( solutioncompleter, method )( **kwargs )


  def OnFileReadyToParse( self, request_data ):
    solutioncompleter = self._GetSolutionCompleter( request_data )

    # Only start the server associated to this solution if the option to
    # automatically start one is set and no server process is already running.
    if ( self.user_options[ 'auto_start_csharp_server' ]
         and not solutioncompleter._ServerIsRunning() ):
      solutioncompleter._StartServer()
      return

    # Bail out if the server is unresponsive. We don't start or restart the
    # server in this case because current one may still be warming up.
    if not solutioncompleter.ServerIsHealthy():
      return

    errors = solutioncompleter.CodeCheck( request_data )

    diagnostics = [ self._QuickFixToDiagnostic( request_data, x ) for x in
                    errors[ "QuickFixes" ] ]

    self._diagnostic_store = DiagnosticsToDiagStructure( diagnostics )

    return responses.BuildDiagnosticResponse( diagnostics,
                                              request_data[ 'filepath' ],
                                              self.max_diagnostics_to_display )


  def _QuickFixToDiagnostic( self, request_data, quick_fix ):
    filename = quick_fix[ "FileName" ]
    # NOTE: end of diagnostic range returned by the OmniSharp server is not
    # included.
    location = _BuildLocation( request_data,
                               filename,
                               quick_fix[ 'Line' ],
                               quick_fix[ 'Column' ] )
    location_end = _BuildLocation( request_data,
                                   filename,
                                   quick_fix[ 'EndLine' ],
                                   quick_fix[ 'EndColumn' ] )
    if not location_end:
      location_end = location
    location_extent = responses.Range( location, location_end )
    return responses.Diagnostic( [],
                                 location,
                                 location_extent,
                                 quick_fix[ 'Text' ],
                                 quick_fix[ 'LogLevel' ].upper() )


  def GetDetailedDiagnostic( self, request_data ):
    current_line = request_data[ 'line_num' ]
    current_column = request_data[ 'column_num' ]
    current_file = request_data[ 'filepath' ]

    if not self._diagnostic_store:
      raise ValueError( NO_DIAGNOSTIC_MESSAGE )

    diagnostics = self._diagnostic_store[ current_file ][ current_line ]
    if not diagnostics:
      raise ValueError( NO_DIAGNOSTIC_MESSAGE )

    closest_diagnostic = None
    distance_to_closest_diagnostic = 999

    # FIXME: all of these calculations are currently working with byte
    # offsets, which are technically incorrect. We should be working with
    # codepoint offsets, as we want the nearest character-wise diagnostic
    for diagnostic in diagnostics:
      distance = abs( current_column - diagnostic.location_.column_number_ )
      if distance < distance_to_closest_diagnostic:
        distance_to_closest_diagnostic = distance
        closest_diagnostic = diagnostic

    return responses.BuildDisplayMessageResponse(
      closest_diagnostic.text_ )


  def DebugInfo( self, request_data ):
    try:
      completer = self._GetSolutionCompleter( request_data )
    except RuntimeError:
      omnisharp_server = responses.DebugInfoServer(
        name = 'OmniSharp',
        handle = None,
        executable = PATH_TO_OMNISHARP_BINARY )

      return responses.BuildDebugInfoResponse( name = 'C#',
                                               servers = [ omnisharp_server ] )

    with completer._server_state_lock:
      solution_item = responses.DebugInfoItem(
        key = 'solution',
        value = completer._solution_path )

      omnisharp_server = responses.DebugInfoServer(
        name = 'OmniSharp',
        handle = completer._omnisharp_phandle,
        executable = PATH_TO_OMNISHARP_BINARY,
        address = 'localhost',
        port = completer._omnisharp_port,
        logfiles = [ completer._filename_stdout, completer._filename_stderr ],
        extras = [ solution_item ] )

      return responses.BuildDebugInfoResponse( name = 'C#',
                                               servers = [ omnisharp_server ] )


  def ServerIsHealthy( self ):
    """ Check if our OmniSharp server is healthy (up and serving). """
    return self._CheckAllRunning( lambda i: i.ServerIsHealthy() )


  def ServerIsReady( self ):
    """ Check if our OmniSharp server is ready (loaded solution file)."""
    return self._CheckAllRunning( lambda i: i.ServerIsReady() )


  def _CheckAllRunning( self, action ):
    solutioncompleters = itervalues( self._completer_per_solution )
    return all( action( completer ) for completer in solutioncompleters
                if completer._ServerIsRunning() )


  def _GetSolutionFile( self, filepath ):
    if filepath not in self._solution_for_file:
      # NOTE: detection could throw an exception if an extra_conf_store needs
      # to be confirmed
      path_to_solutionfile = solutiondetection.FindSolutionPath( filepath )
      if not path_to_solutionfile:
        raise RuntimeError( 'Autodetection of solution file failed.' )
      self._solution_for_file[ filepath ] = path_to_solutionfile

    return self._solution_for_file[ filepath ]


class CsharpSolutionCompleter( object ):
  def __init__( self, solution_path, keep_logfiles, desired_omnisharp_port ):
    self._solution_path = solution_path
    self._keep_logfiles = keep_logfiles
    self._filename_stderr = None
    self._filename_stdout = None
    self._omnisharp_port = None
    self._omnisharp_phandle = None
    self._desired_omnisharp_port = desired_omnisharp_port
    self._server_state_lock = threading.RLock()


  def CodeCheck( self, request_data ):
    filename = request_data[ 'filepath' ]
    if not filename:
      raise ValueError( INVALID_FILE_MESSAGE )

    return self._GetResponse( '/codecheck',
                              self._DefaultParameters( request_data ) )


  def _StartServer( self ):
    """ Start the OmniSharp server if not already running. Use a lock to avoid
    starting the server multiple times for the same solution. """
    with self._server_state_lock:
      if self._ServerIsRunning():
        return

      LOGGER.info( 'Starting OmniSharp server' )

      path_to_solutionfile = self._solution_path
      LOGGER.info( 'Loading solution file %s', path_to_solutionfile )

      self._ChooseOmnisharpPort()

      command = [ PATH_TO_OMNISHARP_BINARY,
                  '-p',
                  str( self._omnisharp_port ),
                  '-s',
                  u'{0}'.format( path_to_solutionfile ) ]

      if not utils.OnWindows() and not utils.OnCygwin():
        command.insert( 0, 'mono' )

      if utils.OnCygwin():
        command.extend( [ '--client-path-mode', 'Cygwin' ] )

      solutionfile = os.path.basename( path_to_solutionfile )
      self._filename_stdout = utils.CreateLogfile(
          LOGFILE_FORMAT.format( port = self._omnisharp_port,
                                 sln = solutionfile,
                                 std = 'stdout' ) )
      self._filename_stderr = utils.CreateLogfile(
          LOGFILE_FORMAT.format( port = self._omnisharp_port,
                                 sln = solutionfile,
                                 std = 'stderr' ) )

      with utils.OpenForStdHandle( self._filename_stderr ) as fstderr:
        with utils.OpenForStdHandle( self._filename_stdout ) as fstdout:
          self._omnisharp_phandle = utils.SafePopen(
              command, stdout = fstdout, stderr = fstderr )

      self._solution_path = path_to_solutionfile


  def _StopServer( self ):
    """ Stop the OmniSharp server using a lock. """
    with self._server_state_lock:
      if self._ServerIsRunning():
        LOGGER.info( 'Stopping OmniSharp server with PID %s',
                     self._omnisharp_phandle.pid )
        try:
          self._GetResponse( '/stopserver' )
          utils.WaitUntilProcessIsTerminated( self._omnisharp_phandle,
                                              timeout = 5 )
          LOGGER.info( 'OmniSharp server stopped' )
        except Exception:
          LOGGER.exception( 'Error while stopping OmniSharp server' )

      self._CleanUp()


  def _CleanUp( self ):
    self._omnisharp_port = None
    self._omnisharp_phandle = None
    if not self._keep_logfiles:
      if self._filename_stdout:
        utils.RemoveIfExists( self._filename_stdout )
        self._filename_stdout = None
      if self._filename_stderr:
        utils.RemoveIfExists( self._filename_stderr )
        self._filename_stderr = None


  def _RestartServer( self ):
    """ Restarts the OmniSharp server using a lock. """
    with self._server_state_lock:
      self._StopServer()
      self._StartServer()


  def _ReloadSolution( self ):
    """ Reloads the solutions in the OmniSharp server """
    LOGGER.info( 'Reloading Solution in OmniSharp server' )
    return self._GetResponse( '/reloadsolution' )


  def _GetCompletions( self, request_data ):
    """ Ask server for completions """
    parameters = self._DefaultParameters( request_data )
    parameters[ 'WantImportableTypes' ] = request_data[ 'force_semantic' ]
    parameters[ 'ForceSemanticCompletion' ] = request_data[ 'force_semantic' ]
    parameters[ 'WantDocumentationForEveryCompletionResult' ] = True
    completions = self._GetResponse( '/autocomplete', parameters )
    return completions if completions is not None else []


  def _GoToDefinition( self, request_data ):
    """ Jump to definition of identifier under cursor """
    definition = self._GetResponse( '/gotodefinition',
                                    self._DefaultParameters( request_data ) )
    if definition[ 'FileName' ] is not None:
      return responses.BuildGoToResponseFromLocation(
        _BuildLocation( request_data,
                        definition[ 'FileName' ],
                        definition[ 'Line' ],
                        definition[ 'Column' ] ) )
    else:
      raise RuntimeError( 'Can\'t jump to definition' )


  def _GoToImplementation( self, request_data, fallback_to_declaration ):
    """ Jump to implementation of identifier under cursor """
    implementation = self._GetResponse(
        '/findimplementations',
        self._DefaultParameters( request_data ) )

    if implementation[ 'QuickFixes' ]:
      if len( implementation[ 'QuickFixes' ] ) == 1:
        return responses.BuildGoToResponseFromLocation(
          _BuildLocation(
            request_data,
            implementation[ 'QuickFixes' ][ 0 ][ 'FileName' ],
            implementation[ 'QuickFixes' ][ 0 ][ 'Line' ],
            implementation[ 'QuickFixes' ][ 0 ][ 'Column' ] ) )
      else:
        return [ responses.BuildGoToResponseFromLocation(
                   _BuildLocation( request_data,
                                   x[ 'FileName' ],
                                   x[ 'Line' ],
                                   x[ 'Column' ] ) )
                 for x in implementation[ 'QuickFixes' ] ]
    else:
      if ( fallback_to_declaration ):
        return self._GoToDefinition( request_data )
      elif implementation[ 'QuickFixes' ] is None:
        raise RuntimeError( 'Can\'t jump to implementation' )
      else:
        raise RuntimeError( 'No implementations found' )


  def _GetType( self, request_data ):
    request = self._DefaultParameters( request_data )
    request[ "IncludeDocumentation" ] = False

    result = self._GetResponse( '/typelookup', request )
    message = result[ "Type" ]

    return responses.BuildDisplayMessageResponse( message )


  def _FixIt( self, request_data ):
    request = self._DefaultParameters( request_data )

    result = self._GetResponse( '/fixcodeissue', request )
    replacement_text = result[ "Text" ]
    # Note: column_num is already a byte offset so we don't need to use
    # _BuildLocation.
    location = responses.Location( request_data[ 'line_num' ],
                                   request_data[ 'column_num' ],
                                   request_data[ 'filepath' ] )
    fixits = [ responses.FixIt( location,
                                _BuildChunks( request_data,
                                              replacement_text ) ) ]

    return responses.BuildFixItResponse( fixits )


  def _GetDoc( self, request_data ):
    request = self._DefaultParameters( request_data )
    request[ "IncludeDocumentation" ] = True

    result = self._GetResponse( '/typelookup', request )
    message = result[ "Type" ]
    if ( result[ "Documentation" ] ):
      message += "\n" + result[ "Documentation" ]

    return responses.BuildDetailedInfoResponse( message )


  def _DefaultParameters( self, request_data ):
    """ Some very common request parameters """
    parameters = {}
    parameters[ 'line' ] = request_data[ 'line_num' ]
    parameters[ 'column' ] = request_data[ 'column_codepoint' ]

    filepath = request_data[ 'filepath' ]
    parameters[ 'buffer' ] = (
      request_data[ 'file_data' ][ filepath ][ 'contents' ] )
    parameters[ 'filename' ] = filepath
    return parameters


  def _ServerIsRunning( self ):
    """ Check if our OmniSharp server is running (process is up)."""
    return utils.ProcessIsRunning( self._omnisharp_phandle )


  def ServerIsHealthy( self ):
    """ Check if our OmniSharp server is healthy (up and serving)."""
    if not self._ServerIsRunning():
      return False

    try:
      return self._GetResponse( '/checkalivestatus', timeout = .2 )
    except Exception:
      return False


  def ServerIsReady( self ):
    """ Check if our OmniSharp server is ready (loaded solution file)."""
    if not self._ServerIsRunning():
      return False

    try:
      return self._GetResponse( '/checkreadystatus', timeout = .2 )
    except Exception:
      return False


  def _SolutionFile( self ):
    """ Find out which solution file server was started with """
    return self._solution_path


  def _ServerLocation( self ):
    # We cannot use 127.0.0.1 like we do in other places because OmniSharp
    # server only listens on localhost.
    return 'http://localhost:' + str( self._omnisharp_port )


  def _GetResponse( self, handler, parameters = {}, timeout = None ):
    """ Handle communication with server """
    target = urljoin( self._ServerLocation(), handler )
    response = requests.post( target, data = parameters, timeout = timeout )
    return response.json()


  def _ChooseOmnisharpPort( self ):
    if not self._omnisharp_port:
      if self._desired_omnisharp_port:
        self._omnisharp_port = int( self._desired_omnisharp_port )
      else:
        self._omnisharp_port = utils.GetUnusedLocalhostPort()
    LOGGER.info( 'using port %s', self._omnisharp_port )


def _CompleteIsFromImport( candidate ):
  try:
    return candidate[ "extra_data" ][ "required_namespace_import" ] is not None
  except ( KeyError, TypeError ):
    return False


def DiagnosticsToDiagStructure( diagnostics ):
  structure = defaultdict( lambda : defaultdict( list ) )
  for diagnostic in diagnostics:
    structure[ diagnostic.location_.filename_ ][
      diagnostic.location_.line_number_ ].append( diagnostic )
  return structure


def _BuildChunks( request_data, new_buffer ):
  filepath = request_data[ 'filepath' ]
  old_buffer = request_data[ 'file_data' ][ filepath ][ 'contents' ]
  new_buffer = _FixLineEndings( old_buffer, new_buffer )

  new_length = len( new_buffer )
  old_length = len( old_buffer )
  if new_length == old_length and new_buffer == old_buffer:
    return []
  min_length = min( new_length, old_length )
  start_index = 0
  end_index = min_length
  for i in range( 0, min_length - 1 ):
    if new_buffer[ i ] != old_buffer[ i ]:
      start_index = i
      break
  for i in range( 1, min_length ):
    if new_buffer[ new_length - i ] != old_buffer[ old_length - i ]:
      end_index = i - 1
      break
  # To handle duplicates, i.e aba => a
  if ( start_index + end_index > min_length ):
    start_index -= start_index + end_index - min_length

  replacement_text = new_buffer[ start_index : new_length - end_index ]

  ( start_line, start_column ) = _IndexToLineColumn( old_buffer, start_index )
  ( end_line, end_column ) = _IndexToLineColumn( old_buffer,
                                                 old_length - end_index )

  # No need for _BuildLocation, because _IndexToLineColumn already converted
  # start_column and end_column to byte offsets for us.
  start = responses.Location( start_line, start_column, filepath )
  end = responses.Location( end_line, end_column, filepath )
  return [ responses.FixItChunk( replacement_text,
                                 responses.Range( start, end ) ) ]


def _FixLineEndings( old_buffer, new_buffer ):
  new_windows = "\r\n" in new_buffer
  old_windows = "\r\n" in old_buffer
  if new_windows != old_windows:
    if new_windows:
      new_buffer = new_buffer.replace( "\r\n", "\n" )
      new_buffer = new_buffer.replace( "\r", "\n" )
    else:
      new_buffer = re.sub( "\r(?!\n)|(?<!\r)\n", "\r\n", new_buffer )
  return new_buffer


# Adapted from http://stackoverflow.com/a/24495900
def _IndexToLineColumn( text, index ):
  """Get 1-based (line_number, col) of `index` in `string`, where string is a
  unicode string and col is a byte offset."""
  lines = text.splitlines( True )
  curr_pos = 0
  for linenum, line in enumerate( lines ):
    if curr_pos + len( line ) > index:
      return ( linenum + 1,
               CodepointOffsetToByteOffset( line, index - curr_pos + 1 ) )
    curr_pos += len( line )
  assert False


def _BuildLocation( request_data, filename, line_num, column_num ):
  if line_num <= 0:
    return None
  # OmniSharp sometimes incorrectly returns 0 for the column number. Assume the
  # column is 1 in that case.
  if column_num <= 0:
    column_num = 1
  contents = GetFileLines( request_data, filename )
  line_value = contents[ line_num - 1 ]
  return responses.Location(
      line_num,
      CodepointOffsetToByteOffset( line_value, column_num ),
      filename )
