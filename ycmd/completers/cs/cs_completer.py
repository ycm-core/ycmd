# Copyright (C) 2011-2020 ycmd contributors
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

from collections import defaultdict
import os
import errno
import time
import requests
import threading
from urllib.parse import urljoin

from ycmd.completers.completer import Completer
from ycmd.completers.completer_utils import GetFileLines
from ycmd.completers.cs import solutiondetection
from ycmd.utils import ( ByteOffsetToCodepointOffset,
                         CodepointOffsetToByteOffset,
                         FindExecutableWithFallback,
                         LOGGER )
from ycmd import responses
from ycmd import utils

SERVER_NOT_FOUND_MSG = ( 'OmniSharp server binary not found at {0}. ' +
                         'Did you compile it? You can do so by running ' +
                         '"./install.py --cs-completer".' )
INVALID_FILE_MESSAGE = 'File is invalid.'
NO_DIAGNOSTIC_MESSAGE = 'No diagnostic for current line!'
PATH_TO_ROSLYN_OMNISHARP = os.path.join(
  os.path.abspath( os.path.dirname( __file__ ) ),
  '..', '..', '..', 'third_party', 'omnisharp-roslyn'
)
PATH_TO_OMNISHARP_ROSLYN_BINARY = os.path.join(
  PATH_TO_ROSLYN_OMNISHARP, 'Omnisharp.exe' )
if ( not os.path.isfile( PATH_TO_OMNISHARP_ROSLYN_BINARY )
     and os.path.isfile( os.path.join( PATH_TO_ROSLYN_OMNISHARP, 'run' ) ) ):
  PATH_TO_OMNISHARP_ROSLYN_BINARY = (
    os.path.join( PATH_TO_ROSLYN_OMNISHARP, 'run' ) )
LOGFILE_FORMAT = 'omnisharp_{port}_{sln}_{std}_'


def ShouldEnableCsCompleter( user_options ):
  roslyn = FindExecutableWithFallback( user_options[ 'roslyn_binary_path' ],
                                       PATH_TO_OMNISHARP_ROSLYN_BINARY )
  if roslyn:
    return True
  LOGGER.info( 'No omnisharp-roslyn executable at %s', roslyn )
  return False


class CsharpCompleter( Completer ):
  """
  A Completer that uses the Omnisharp server as completion engine.
  """

  def __init__( self, user_options ):
    super().__init__( user_options )
    self._solution_for_file = {}
    self._completer_per_solution = {}
    self._diagnostic_store = None
    self._solution_state_lock = threading.Lock()
    self.SetSignatureHelpTriggers( [ '(', ',' ] )
    self._roslyn_path = FindExecutableWithFallback(
        user_options[ 'roslyn_binary_path' ],
        PATH_TO_OMNISHARP_ROSLYN_BINARY )


  def Shutdown( self ):
    if self.user_options[ 'auto_stop_csharp_server' ]:
      for solutioncompleter in self._completer_per_solution.values():
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
                                             desired_omnisharp_port,
                                             self._roslyn_path )
        self._completer_per_solution[ solution ] = completer

    return self._completer_per_solution[ solution ]


  def SignatureHelpAvailable( self ):
    if not self.ServerIsHealthy():
      return responses.SignatureHelpAvailalability.PENDING
    return responses.SignatureHelpAvailalability.AVAILABLE


  def ComputeSignaturesInner( self, request_data ):
    response = self._SolutionSubcommand( request_data, '_SignatureHelp' )

    if response is None:
      return {}

    signatures = response[ 'Signatures' ]

    def MakeSignature( s ):
      sig_label = s[ 'Label' ]
      end = 0
      parameters = []
      for arg in s[ 'Parameters' ]:
        arg_label = arg[ 'Label' ]
        begin = sig_label.find( arg_label, end )
        end = begin + len( arg_label )
        parameters.append( {
          'label': [ CodepointOffsetToByteOffset( sig_label, begin ),
                     CodepointOffsetToByteOffset( sig_label, end ) ]
        } )

      return {
        'label': sig_label,
        'parameters': parameters
      }

    return {
      'activeSignature': response[ 'ActiveSignature' ],
      'activeParameter': response[ 'ActiveParameter' ],
      'signatures': [ MakeSignature( s ) for s in signatures ]
    }


  def ResolveFixit( self, request_data ):
    return self._SolutionSubcommand( request_data, '_ResolveFixIt' )


  def ComputeCandidatesInner( self, request_data ):
    solutioncompleter = self._GetSolutionCompleter( request_data )
    return [ responses.BuildCompletionData(
                completion[ 'CompletionText' ],
                completion[ 'DisplayText' ],
                completion[ 'Description' ],
                None,
                completion[ 'Kind' ] )
             for completion
             in solutioncompleter._GetCompletions( request_data ) ]


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
      'GoToReferences'                   : ( lambda self, request_data, args:
         self._SolutionSubcommand( request_data,
                                   method = '_GoToReferences' ) ),
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
      'Format'                           : ( lambda self, request_data, args:
         self._SolutionSubcommand( request_data,
                                   method = '_Format' ) ),
      'FixIt'                            : ( lambda self, request_data, args:
         self._SolutionSubcommand( request_data,
                                   method = '_FixIt' ) ),
      'GetDoc'                           : ( lambda self, request_data, args:
         self._SolutionSubcommand( request_data,
                                   method = '_GetDoc' ) ),
      'RefactorRename'                   : ( lambda self, request_data, args:
         self._SolutionSubcommand( request_data,
                                   method = '_RefactorRename',
                                   args = args ) ),
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
        executable = self._roslyn_path )

      return responses.BuildDebugInfoResponse( name = 'C#',
                                               servers = [ omnisharp_server ] )

    with completer._server_state_lock:
      solution_item = responses.DebugInfoItem(
        key = 'solution',
        value = completer._solution_path )

      omnisharp_server = responses.DebugInfoServer(
        name = 'OmniSharp',
        handle = completer._omnisharp_phandle,
        executable = PATH_TO_ROSLYN_OMNISHARP,
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
    solutioncompleters = self._completer_per_solution.values()
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
  def __init__( self,
                solution_path,
                keep_logfiles,
                desired_omnisharp_port,
                roslyn_path ):
    self._solution_path = solution_path
    self._keep_logfiles = keep_logfiles
    self._filename_stderr = None
    self._filename_stdout = None
    self._omnisharp_port = None
    self._omnisharp_phandle = None
    self._desired_omnisharp_port = desired_omnisharp_port
    self._server_state_lock = threading.Lock()
    self._roslyn_path = roslyn_path


  def CodeCheck( self, request_data ):
    filename = request_data[ 'filepath' ]
    if not filename:
      raise ValueError( INVALID_FILE_MESSAGE )

    return self._GetResponse( '/codecheck',
                              self._DefaultParameters( request_data ) )


  def _StartServer( self ):
    with self._server_state_lock:
      return self._StartServerNoLock()


  def _StartServerNoLock( self ):
    """ Start the OmniSharp server if not already running. Use a lock to avoid
    starting the server multiple times for the same solution. """
    if self._ServerIsRunning():
      return

    LOGGER.info( 'Starting OmniSharp server' )
    LOGGER.info( 'Loading solution file %s', self._solution_path )

    self._ChooseOmnisharpPort()

    command = [ PATH_TO_OMNISHARP_ROSLYN_BINARY,
                '-p',
                str( self._omnisharp_port ),
                '-s',
                str( self._solution_path ) ]

    if ( not utils.OnWindows()
         and self._roslyn_path.endswith( '.exe' ) ):
      command.insert( 0, 'mono' )

    LOGGER.info( 'Starting OmniSharp server with: %s', command )

    solutionfile = os.path.basename( self._solution_path )
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

    LOGGER.info( 'Started OmniSharp server' )


  def _StopServer( self ):
    with self._server_state_lock:
      return self._StopServerNoLock()


  def _StopServerNoLock( self ):
    """ Stop the OmniSharp server using a lock. """
    if self._ServerIsRunning():
      LOGGER.info( 'Stopping OmniSharp server with PID %s',
                   self._omnisharp_phandle.pid )
      try:
        self._TryToStopServer()
        self._ForceStopServer()
        utils.WaitUntilProcessIsTerminated( self._omnisharp_phandle,
                                            timeout = 5 )
        LOGGER.info( 'OmniSharp server stopped' )
      except Exception:
        LOGGER.exception( 'Error while stopping OmniSharp server' )

    self._CleanUp()


  def _TryToStopServer( self ):
    for _ in range( 5 ):
      try:
        self._GetResponse( '/stopserver', timeout = .5 )
      except Exception:
        pass
      for _ in range( 10 ):
        if not self._ServerIsRunning():
          return
        time.sleep( .1 )


  def _ForceStopServer( self ):
    # Kill it if it's still up
    phandle = self._omnisharp_phandle
    if phandle is not None:
      LOGGER.info( 'Killing OmniSharp server' )
      for stream in [ phandle.stderr, phandle.stdout ]:
        if stream is not None:
          stream.close()
      try:
        phandle.kill()
      except OSError as e:
        if e.errno == errno.ESRCH: # No such process
          pass
        else:
          raise


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
      self._StopServerNoLock()
      return self._StartServerNoLock()


  def _GetCompletions( self, request_data ):
    """ Ask server for completions """
    parameters = self._DefaultParameters( request_data )
    parameters[ 'WantSnippet' ] = False
    parameters[ 'WantKind' ] = True
    parameters[ 'WantReturnType' ] = False
    parameters[ 'WantDocumentationForEveryCompletionResult' ] = True
    completions = self._GetResponse( '/autocomplete', parameters )
    return completions if completions is not None else []


  def _GoToDefinition( self, request_data ):
    """ Jump to definition of identifier under cursor """
    definition = self._GetResponse( '/gotodefinition',
                                    self._DefaultParameters( request_data ) )
    if definition[ 'FileName' ] is not None:
      filepath = definition[ 'FileName' ]
      return responses.BuildGoToResponseFromLocation(
        _BuildLocation( request_data,
                        filepath,
                        definition[ 'Line' ],
                        definition[ 'Column' ] ) )
    else:
      raise RuntimeError( 'Can\'t jump to definition' )


  def _GoToImplementation( self, request_data, fallback_to_declaration ):
    """ Jump to implementation of identifier under cursor """
    try:
      implementation = self._GetResponse(
          '/findimplementations',
          self._DefaultParameters( request_data ) )
    except ValueError:
      implementation = { 'QuickFixes': None }

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


  def _SignatureHelp( self, request_data ):
    request = self._DefaultParameters( request_data )
    return self._GetResponse( '/signatureHelp', request )


  def _RefactorRename( self, request_data, args ):
    request = self._DefaultParameters( request_data )
    if len( args ) != 1:
      raise ValueError( 'Please specify a new name to rename it to.\n'
                        'Usage: RefactorRename <new name>' )
    request[ 'RenameTo' ] = args[ 0 ]
    request[ 'WantsTextChanges' ] = True
    response = self._GetResponse( '/rename', request )
    fixit = _ModifiedFilesToFixIt( response[ 'Changes' ], request_data )
    return responses.BuildFixItResponse( [ fixit ] )


  def _GoToReferences( self, request_data ):
    """ Jump to references of identifier under cursor """
    # _GetResponse can throw. Original code by @mispencer
    # wrapped it in a try/except and set `reference` to `{ 'QuickFixes': None }`
    # After being unable to hit that case with tests,
    # that code path was thrown away.
    reference = self._GetResponse(
       '/findusages',
       self._DefaultParameters( request_data ) )

    if reference[ 'QuickFixes' ]:
      if len( reference[ 'QuickFixes' ] ) == 1:
        return responses.BuildGoToResponseFromLocation(
          _BuildLocation(
            request_data,
            reference[ 'QuickFixes' ][ 0 ][ 'FileName' ],
            reference[ 'QuickFixes' ][ 0 ][ 'Line' ],
            reference[ 'QuickFixes' ][ 0 ][ 'Column' ] ) )
      else:
        return [ responses.BuildGoToResponseFromLocation(
                   _BuildLocation( request_data,
                                   ref[ 'FileName' ],
                                   ref[ 'Line' ],
                                   ref[ 'Column' ] ) )
                 for ref in reference[ 'QuickFixes' ] ]
    else:
      raise RuntimeError( 'No references found' )


  def _GetType( self, request_data ):
    request = self._DefaultParameters( request_data )
    request[ "IncludeDocumentation" ] = False

    result = self._GetResponse( '/typelookup', request )
    message = result[ "Type" ]

    if not message:
      raise RuntimeError( 'No type info available.' )
    return responses.BuildDisplayMessageResponse( message )


  def _Format( self, request_data ):
    request = self._DefaultParameters( request_data )
    request[ 'WantsTextChanges' ] = True
    if 'range' in request_data:
      lines = request_data[ 'lines' ]
      start = request_data[ 'range' ][ 'start' ]
      start_line_num = start[ 'line_num' ]
      start_line_value = lines[ start_line_num ]

      start_codepoint = ByteOffsetToCodepointOffset( start_line_value,
                                                     start[ 'column_num' ] )

      end = request_data[ 'range' ][ 'end' ]
      end_line_num = end[ 'line_num' ]
      end_line_value = lines[ end_line_num ]
      end_codepoint = ByteOffsetToCodepointOffset( end_line_value,
                                                   end[ 'column_num' ] )
      request.update( {
        'line': start_line_num,
        'column': start_codepoint,
        'EndLine': end_line_num,
        'EndColumn': end_codepoint
      } )
      result = self._GetResponse( '/formatRange', request )
    else:
      result = self._GetResponse( '/codeformat', request )

    fixit = responses.FixIt(
      _BuildLocation(
        request_data,
        request_data[ 'filepath' ],
        request_data[ 'line_num' ],
        request_data[ 'column_codepoint' ] ),
      _LinePositionSpanTextChangeToFixItChunks(
        result[ 'Changes' ],
        request_data[ 'filepath' ],
        request_data ) )
    return responses.BuildFixItResponse( [ fixit ] )


  def _FixIt( self, request_data ):
    request = self._DefaultParameters( request_data )
    request[ 'WantsTextChanges' ] = True

    result = self._GetResponse( '/getcodeactions', request )

    fixits = []
    for i, code_action_name in enumerate( result[ 'CodeActions' ] ):
      fixit = responses.UnresolvedFixIt( { 'index': i }, code_action_name )
      fixits.append( fixit )

    if len( fixits ) == 1:
      fixit = fixits[ 0 ]
      fixit = { 'command': fixit.command, 'resolve': fixit.resolve }
      return self._ResolveFixIt( request_data, fixit )

    return responses.BuildFixItResponse( fixits )


  def _ResolveFixIt( self, request_data, unresolved_fixit = None ):
    fixit = unresolved_fixit if unresolved_fixit else request_data[ 'fixit' ]
    if not fixit[ 'resolve' ]:
      return { 'fixits': [ fixit ] }
    fixit = fixit[ 'command' ]
    code_action = fixit[ 'index' ]
    request = self._DefaultParameters( request_data )
    request.update( {
      'CodeAction': code_action,
      'WantsTextChanges': True,
    } )
    response = self._GetResponse( '/runcodeaction', request )
    fixit = responses.FixIt(
      _BuildLocation(
        request_data,
        request_data[ 'filepath' ],
        request_data[ 'line_num' ],
        request_data[ 'column_codepoint' ] ),
      _LinePositionSpanTextChangeToFixItChunks(
        response[ 'Changes' ],
        request_data[ 'filepath' ],
        request_data ),
      response[ 'Text' ] )
    # The sort is necessary to keep the tests stable.
    # Python's sort() is stable, so it won't mess up the order within a file.
    fixit.chunks.sort( key = lambda c: c.range.start_.filename_ )
    return responses.BuildFixItResponse( [ fixit ] )


  def _GetDoc( self, request_data ):
    request = self._DefaultParameters( request_data )
    request[ "IncludeDocumentation" ] = True

    result = self._GetResponse( '/typelookup', request )
    message = result.get( 'Type' ) or ''

    if ( result[ "Documentation" ] ):
      message += "\n" + result[ "Documentation" ]

    if not message:
      raise RuntimeError( 'No documentation available.' )
    return responses.BuildDetailedInfoResponse( message.strip() )


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
      return self._GetResponse( '/checkalivestatus', timeout = 3 )
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


  def _ServerLocation( self ):
    # We cannot use 127.0.0.1 like we do in other places because OmniSharp
    # server only listens on localhost.
    return 'http://localhost:' + str( self._omnisharp_port )


  def _GetResponse( self, handler, parameters = {}, timeout = None ):
    """ Handle communication with server """
    target = urljoin( self._ServerLocation(), handler )
    LOGGER.debug( 'TX (%s): %s', handler, parameters )
    response = requests.post( target, json = parameters, timeout = timeout )
    LOGGER.debug( 'RX: %s', response.json() )
    return response.json()


  def _ChooseOmnisharpPort( self ):
    if not self._omnisharp_port:
      if self._desired_omnisharp_port:
        self._omnisharp_port = int( self._desired_omnisharp_port )
      else:
        self._omnisharp_port = utils.GetUnusedLocalhostPort()
    LOGGER.info( 'using port %s', self._omnisharp_port )


def DiagnosticsToDiagStructure( diagnostics ):
  structure = defaultdict( lambda : defaultdict( list ) )
  for diagnostic in diagnostics:
    structure[ diagnostic.location_.filename_ ][
      diagnostic.location_.line_number_ ].append( diagnostic )
  return structure


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


def _LinePositionSpanTextChangeToFixItChunks( chunks, filename, request_data ):
  return [ responses.FixItChunk(
      chunk[ 'NewText' ],
      responses.Range(
        _BuildLocation(
          request_data,
          filename,
          chunk[ 'StartLine' ],
          chunk[ 'StartColumn' ] ),
        _BuildLocation(
          request_data,
          filename,
          chunk[ 'EndLine' ],
          chunk[ 'EndColumn' ] ) ) ) for chunk in chunks ]


def _ModifiedFilesToFixIt( changes, request_data ):
  chunks = []
  for change in changes:
    chunks.extend(
      _LinePositionSpanTextChangeToFixItChunks(
        change[ 'Changes' ],
        change[ 'FileName' ],
        request_data ) )
  # The sort is necessary to keep the tests stable.
  # Python's sort() is stable, so it won't mess up the order within a file.
  chunks.sort( key = lambda c: c.range.start_.filename_ )
  return responses.FixIt(
      _BuildLocation(
        request_data,
        request_data[ 'filepath' ],
        request_data[ 'line_num' ],
        request_data[ 'column_codepoint' ] ),
      chunks )
