#!/usr/bin/env python
#
# Copyright (C) 2011, 2012  Chiel ten Brinke <ctenbrinke@gmail.com>
#                           Google Inc.
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

from collections import defaultdict
import os
import time
from ycmd.completers.completer import Completer
from ycmd.utils import ForceSemanticCompletion
from ycmd import responses
from ycmd import utils
import requests
import urlparse
import logging
import solutiondetection

SERVER_NOT_FOUND_MSG = ( 'OmniSharp server binary not found at {0}. ' +
                         'Did you compile it? You can do so by running ' +
                         '"./install.py --omnisharp-completer".' )
INVALID_FILE_MESSAGE = 'File is invalid.'
NO_DIAGNOSTIC_MESSAGE = 'No diagnostic for current line!'
PATH_TO_OMNISHARP_BINARY = os.path.join(
  os.path.abspath( os.path.dirname( __file__ ) ),
  '..', '..', '..', 'third_party', 'OmniSharpServer',
  'OmniSharp', 'bin', 'Release', 'OmniSharp.exe' )


# TODO: Handle this better than dummy classes
class CsharpDiagnostic:
  def __init__ ( self, ranges, location, location_extent, text, kind ):
    self.ranges_ = ranges
    self.location_ = location
    self.location_extent_ = location_extent
    self.text_ = text
    self.kind_ = kind


class CsharpFixIt:
  def __init__ ( self, location, chunks ):
    self.location = location
    self.chunks = chunks


class CsharpFixItChunk:
  def __init__ ( self, replacement_text, range ):
    self.replacement_text = replacement_text
    self.range = range


class CsharpDiagnosticRange:
  def __init__ ( self, start, end ):
    self.start_ = start
    self.end_ = end


class CsharpDiagnosticLocation:
  def __init__ ( self, line, column, filename ):
    self.line_number_ = line
    self.column_number_ = column
    self.filename_ = filename


class CsharpCompleter( Completer ):
  """
  A Completer that uses the Omnisharp server as completion engine.
  """

  def __init__( self, user_options ):
    super( CsharpCompleter, self ).__init__( user_options )
    self._logger = logging.getLogger( __name__ )
    self._solution_for_file = {}
    self._completer_per_solution = {}
    self._diagnostic_store = None
    self._max_diagnostics_to_display = user_options[
      'max_diagnostics_to_display' ]

    if not os.path.isfile( PATH_TO_OMNISHARP_BINARY ):
      raise RuntimeError(
           SERVER_NOT_FOUND_MSG.format( PATH_TO_OMNISHARP_BINARY ) )


  def Shutdown( self ):
    if ( self.user_options[ 'auto_stop_csharp_server' ] ):
      for solutioncompleter in self._completer_per_solution.values():
        if solutioncompleter.ServerIsRunning():
          solutioncompleter._StopServer()


  def SupportedFiletypes( self ):
    """ Just csharp """
    return [ 'cs' ]


  def _GetSolutionCompleter( self, request_data ):
    solution = self._GetSolutionFile( request_data[ "filepath" ] )
    if not solution in self._completer_per_solution:
      keep_logfiles = self.user_options[ 'server_keep_logfiles' ]
      desired_omnisharp_port = self.user_options.get( 'csharp_server_port' )
      completer = CsharpSolutionCompleter( solution, keep_logfiles, desired_omnisharp_port )
      self._completer_per_solution[ solution ] = completer

    return self._completer_per_solution[ solution ]


  def ShouldUseNowInner( self, request_data ):
    return True


  def CompletionType( self, request_data ):
    return ForceSemanticCompletion( request_data )


  def ComputeCandidatesInner( self, request_data ):
    solutioncompleter = self._GetSolutionCompleter( request_data )
    completion_type = self.CompletionType( request_data )
    return [ responses.BuildCompletionData(
                completion[ 'CompletionText' ],
                completion[ 'DisplayText' ],
                completion[ 'Description' ],
                None,
                None,
                { "required_namespace_import" :
                   completion[ 'RequiredNamespaceImport' ] } )
             for completion
             in solutioncompleter._GetCompletions( request_data,
                                                   completion_type ) ]


  def FilterAndSortCandidates( self, candidates, query ):
    result = super(CsharpCompleter, self).FilterAndSortCandidates( candidates,
                                                                   query )
    result.sort( _CompleteSorterByImport );
    return result


  def DefinedSubcommands( self ):
    return CsharpSolutionCompleter.subcommands.keys()


  def OnFileReadyToParse( self, request_data ):
    solutioncompleter = self._GetSolutionCompleter( request_data )

    if ( not solutioncompleter.ServerIsRunning() and
         self.user_options[ 'auto_start_csharp_server' ] ):
      solutioncompleter._StartServer()
      return

    errors = solutioncompleter.CodeCheck( request_data )

    diagnostics = [ self._QuickFixToDiagnostic( x ) for x in
                    errors[ "QuickFixes" ] ]

    self._diagnostic_store = DiagnosticsToDiagStructure( diagnostics )

    return [ responses.BuildDiagnosticData( x ) for x in
             diagnostics[ : self._max_diagnostics_to_display ] ]


  def _QuickFixToDiagnostic( self, quick_fix ):
    filename = quick_fix[ "FileName" ]

    location = CsharpDiagnosticLocation( quick_fix[ "Line" ],
                                         quick_fix[ "Column" ], filename )
    location_range = CsharpDiagnosticRange( location, location )
    return CsharpDiagnostic( list(),
                             location,
                             location_range,
                             quick_fix[ "Text" ],
                             quick_fix[ "LogLevel" ].upper() )


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

    for diagnostic in diagnostics:
      distance = abs( current_column - diagnostic.location_.column_number_ )
      if distance < distance_to_closest_diagnostic:
        distance_to_closest_diagnostic = distance
        closest_diagnostic = diagnostic

    return responses.BuildDisplayMessageResponse(
      closest_diagnostic.text_ )


  def OnUserCommand( self, arguments, request_data ):
    if not arguments:
      raise ValueError( self.UserCommandsHelpMessage() )

    command = arguments[ 0 ]
    if command in CsharpSolutionCompleter.subcommands:
      solutioncompleter = self._GetSolutionCompleter( request_data )
      return solutioncompleter.Subcommand( command, arguments, request_data )
    else:
      raise ValueError( self.UserCommandsHelpMessage() )


  def DebugInfo( self, request_data ):
    solutioncompleter = self._GetSolutionCompleter( request_data )
    if solutioncompleter.ServerIsRunning():
      return ( 'OmniSharp Server running at: {0}\n'
               'OmniSharp logfiles:\n{1}\n{2}' ).format(
                   solutioncompleter._ServerLocation(),
                   solutioncompleter._filename_stdout,
                   solutioncompleter._filename_stderr )
    else:
      return 'OmniSharp Server is not running'


  def ServerIsRunning( self, request_data = None ):
    """ Check if our OmniSharp server is running. """
    return self._CheckSingleOrAllActive( request_data,
                                         lambda i: i.ServerIsRunning() )


  def ServerIsReady( self, request_data = None ):
    """ Check if our OmniSharp server is ready (loaded solution file)."""
    return self._CheckSingleOrAllActive( request_data,
                                         lambda i: i.ServerIsReady() )


  def ServerTerminated( self, request_data = None ):
    """ Check if the server process has already terminated. """
    return self._CheckSingleOrAllActive( request_data,
                                         lambda i: i.ServerTerminated() )


  def _CheckSingleOrAllActive( self, request_data, action ):
    if request_data is not None:
      solutioncompleter = self._GetSolutionCompleter( request_data )
      return action( solutioncompleter )
    else:
      solutioncompleters = self._completer_per_solution.values()
      return all( action( completer )
        for completer in solutioncompleters if completer.ServerIsActive() )


  def _GetSolutionFile( self, filepath ):
    if not filepath in self._solution_for_file:
      # NOTE: detection could throw an exception if an extra_conf_store needs
      # to be confirmed
      path_to_solutionfile = solutiondetection.FindSolutionPath( filepath )
      if not path_to_solutionfile:
          raise RuntimeError( 'Autodetection of solution file failed. \n' )
      self._solution_for_file[ filepath ] = path_to_solutionfile

    return self._solution_for_file[ filepath ]


class CsharpSolutionCompleter:
  subcommands = {
    'StartServer': ( lambda self, request_data: self._StartServer() ),
    'StopServer': ( lambda self, request_data: self._StopServer() ),
    'RestartServer': ( lambda self, request_data: self._RestartServer() ),
    'ReloadSolution': ( lambda self, request_data: self._ReloadSolution() ),
    'SolutionFile': ( lambda self, request_data: self._SolutionFile() ),
    'GoToDefinition': ( lambda self, request_data: self._GoToDefinition(
        request_data ) ),
    'GoToDeclaration': ( lambda self, request_data: self._GoToDefinition(
        request_data ) ),
    'GoTo': ( lambda self, request_data: self._GoToImplementation(
        request_data, True ) ),
    'GoToDefinitionElseDeclaration': ( lambda self, request_data:
        self._GoToDefinition( request_data ) ),
    'GoToImplementation': ( lambda self, request_data:
        self._GoToImplementation( request_data, False ) ),
    'GoToImplementationElseDeclaration': ( lambda self, request_data:
        self._GoToImplementation( request_data, True ) ),
    'GetType': ( lambda self, request_data: self._GetType(
        request_data ) ),
    'FixIt': ( lambda self, request_data: self._FixIt( request_data ) ),
    'GetDoc': ( lambda self, request_data: self._GetDoc( request_data ) ),
    'ServerRunning': ( lambda self, request_data: self.ServerIsRunning() ),
    'ServerReady': ( lambda self, request_data: self.ServerIsReady() ),
    'ServerTerminated': ( lambda self, request_data: self.ServerTerminated() ),
  }


  def __init__( self, solution_path, keep_logfiles, desired_omnisharp_port ):
    self._logger = logging.getLogger( __name__ )
    self._solution_path = solution_path
    self._keep_logfiles = keep_logfiles
    self._filename_stderr = None
    self._filename_stdout = None
    self._omnisharp_port = None
    self._omnisharp_phandle = None
    self._desired_omnisharp_port = desired_omnisharp_port;


  def Subcommand( self, command, arguments, request_data ):
    command_lamba = CsharpSolutionCompleter.subcommands[ command ]
    return command_lamba( self, request_data )


  def DefinedSubcommands( self ):
    return CsharpSolutionCompleter.subcommands.keys()


  def CodeCheck( self, request_data ):
    filename = request_data[ 'filepath' ]
    if not filename:
      raise ValueError( INVALID_FILE_MESSAGE )

    return self._GetResponse( '/codecheck',
                              self._DefaultParameters( request_data ) )


  def _StartServer( self ):
    """ Start the OmniSharp server """
    self._logger.info( 'startup' )

    path_to_solutionfile = self._solution_path
    self._logger.info(
        u'Loading solution file {0}'.format( path_to_solutionfile ) )

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

    filename_format = os.path.join( utils.PathToTempDir(),
                                    u'omnisharp_{port}_{sln}_{std}.log' )

    solutionfile = os.path.basename( path_to_solutionfile )
    self._filename_stdout = filename_format.format(
        port = self._omnisharp_port, sln = solutionfile, std = 'stdout' )
    self._filename_stderr = filename_format.format(
        port = self._omnisharp_port, sln = solutionfile, std = 'stderr' )

    with open( self._filename_stderr, 'w' ) as fstderr:
      with open( self._filename_stdout, 'w' ) as fstdout:
        self._omnisharp_phandle = utils.SafePopen(
            command, stdout = fstdout, stderr = fstderr )

    self._solution_path = path_to_solutionfile

    self._logger.info( 'Starting OmniSharp server' )


  def _StopServer( self ):
    """ Stop the OmniSharp server """
    self._logger.info( 'Stopping OmniSharp server' )

    self._TryToStopServer()

    # Kill it if it's still up
    if not self.ServerTerminated() and self._omnisharp_phandle is not None:
      self._logger.info( 'Killing OmniSharp server' )
      self._omnisharp_phandle.kill()

    self._CleanupAfterServerStop()

    self._logger.info( 'Stopped OmniSharp server' )


  def _TryToStopServer( self ):
    for _ in range( 5 ):
      try:
        self._GetResponse( '/stopserver', timeout = .1 )
      except:
        pass
      for _ in range( 10 ):
        if self.ServerTerminated():
          return
        time.sleep( .1 )


  def _CleanupAfterServerStop( self ):
    self._omnisharp_port = None
    self._omnisharp_phandle = None
    if ( not self._keep_logfiles ):
      if self._filename_stdout:
        os.unlink( self._filename_stdout );
      if self._filename_stderr:
        os.unlink( self._filename_stderr );


  def _RestartServer ( self ):
    """ Restarts the OmniSharp server """
    if self.ServerIsRunning():
      self._StopServer()
    return self._StartServer()


  def _ReloadSolution( self ):
    """ Reloads the solutions in the OmniSharp server """
    self._logger.info( 'Reloading Solution in OmniSharp server' )
    return self._GetResponse( '/reloadsolution' )


  def CompletionType( self, request_data ):
    return ForceSemanticCompletion( request_data )


  def _GetCompletions( self, request_data, completion_type ):
    """ Ask server for completions """
    parameters = self._DefaultParameters( request_data )
    parameters[ 'WantImportableTypes' ] = completion_type
    parameters[ 'ForceSemanticCompletion' ] = completion_type
    parameters[ 'WantDocumentationForEveryCompletionResult' ] = True
    completions = self._GetResponse( '/autocomplete', parameters )
    return completions if completions != None else []


  def _GoToDefinition( self, request_data ):
    """ Jump to definition of identifier under cursor """
    definition = self._GetResponse( '/gotodefinition',
                                    self._DefaultParameters( request_data ) )
    if definition[ 'FileName' ] != None:
      return responses.BuildGoToResponse( definition[ 'FileName' ],
                                          definition[ 'Line' ],
                                          definition[ 'Column' ] )
    else:
      raise RuntimeError( 'Can\'t jump to definition' )


  def _GoToImplementation( self, request_data, fallback_to_declaration ):
    """ Jump to implementation of identifier under cursor """
    implementation = self._GetResponse(
        '/findimplementations',
        self._DefaultParameters( request_data ) )

    if implementation[ 'QuickFixes' ]:
      if len( implementation[ 'QuickFixes' ] ) == 1:
        return responses.BuildGoToResponse(
            implementation[ 'QuickFixes' ][ 0 ][ 'FileName' ],
            implementation[ 'QuickFixes' ][ 0 ][ 'Line' ],
            implementation[ 'QuickFixes' ][ 0 ][ 'Column' ] )
      else:
        return [ responses.BuildGoToResponse( x[ 'FileName' ],
                                              x[ 'Line' ],
                                              x[ 'Column' ] )
                 for x in implementation[ 'QuickFixes' ] ]
    else:
      if ( fallback_to_declaration ):
        return self._GoToDefinition( request_data )
      elif implementation[ 'QuickFixes' ] == None:
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
    location = CsharpDiagnosticLocation( request_data['line_num'],
                                         request_data['column_num'],
                                         request_data['filepath'] )
    fixits = [ CsharpFixIt( location,
                            _BuildChunks( request_data, replacement_text ) ) ]

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
    parameters[ 'column' ] = request_data[ 'column_num' ]
    filepath = request_data[ 'filepath' ]
    parameters[ 'buffer' ] = (
      request_data[ 'file_data' ][ filepath ][ 'contents' ] )
    parameters[ 'filename' ] = filepath
    return parameters


  def ServerIsActive( self ):
    """ Check if our OmniSharp server is active (started, not yet stopped)."""
    try:
      return bool( self._omnisharp_port )
    except:
      return False


  def ServerIsRunning( self ):
    """ Check if our OmniSharp server is running (up and serving)."""
    try:
      return bool( self._omnisharp_port and
                   self._GetResponse( '/checkalivestatus', timeout = .2 ) )
    except:
      return False


  def ServerIsReady( self ):
    """ Check if our OmniSharp server is ready (loaded solution file)."""
    try:
      return bool( self._omnisharp_port and
                   self._GetResponse( '/checkreadystatus', timeout = .2 ) )
    except:
      return False


  def ServerTerminated( self ):
    """ Check if the server process has already terminated. """
    return ( self._omnisharp_phandle is not None and
             self._omnisharp_phandle.poll() is not None )


  def _SolutionFile( self ):
    """ Find out which solution file server was started with """
    return self._solution_path


  def _ServerLocation( self ):
    return 'http://localhost:' + str( self._omnisharp_port )


  def _GetResponse( self, handler, parameters = {}, timeout = None ):
    """ Handle communication with server """
    target = urlparse.urljoin( self._ServerLocation(), handler )
    response = requests.post( target, data = parameters, timeout = timeout )
    return response.json()


  def _ChooseOmnisharpPort( self ):
    if not self._omnisharp_port:
        if self._desired_omnisharp_port:
            self._omnisharp_port = int( self._desired_omnisharp_port )
        else:
            self._omnisharp_port = utils.GetUnusedLocalhostPort()
    self._logger.info( u'using port {0}'.format( self._omnisharp_port ) )



def _CompleteSorterByImport( a, b ):
  return cmp( _CompleteIsFromImport( a ), _CompleteIsFromImport( b ) )


def _CompleteIsFromImport( candidate ):
  try:
    return candidate[ "extra_data" ][ "required_namespace_import" ] != None
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
  start = CsharpDiagnosticLocation( start_line, start_column, filepath )
  end = CsharpDiagnosticLocation( end_line, end_column, filepath )
  return [ CsharpFixItChunk( replacement_text,
                             CsharpDiagnosticRange( start, end ) ) ]


def _FixLineEndings( old_buffer, new_buffer ):
  new_windows = "\r\n" in new_buffer
  old_windows = "\r\n" in old_buffer
  if new_windows != old_windows:
    if new_windows:
      new_buffer = new_buffer.replace( "\r\n", "\n" )
      new_buffer = new_buffer.replace( "\r", "\n" )
    else:
      import re
      new_buffer = re.sub( "\r(?!\n)|(?<!\r)\n", "\r\n", new_buffer )
  return new_buffer


# Adapted from http://stackoverflow.com/a/24495900
def _IndexToLineColumn( text, index ):
  """Get (line_number, col) of `index` in `string`."""
  lines = text.splitlines( True )
  curr_pos = 0
  for linenum, line in enumerate( lines ):
    if curr_pos + len( line ) > index:
      return linenum + 1, index - curr_pos + 1
    curr_pos += len( line )
  assert False
