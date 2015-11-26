#
# Copyright (C) 2015 ycmd contrubutors.
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

import sys, logging, os, requests
from ycmd import utils, responses
from ycmd.completers.completer import Completer

_logger = logging.getLogger( __name__ )

PATH_TO_TERNJS_BINARY = os.path.join(
    os.path.abspath( os.path.dirname( __file__ ) ),
    '..',
    '..',
    '..',
    'third_party',
    'tern',
    'bin',
    'tern' )

class TernCompleter( Completer ):
  subcommands = {
    'StartServer':     ( lambda self, request_data:
                                        self._StartServer() ),
    'StopServer':      ( lambda self, request_data:
                                        self._StopServer() ),
    'GoToDefinition':  ( lambda self, request_data:
                                        self._GoToDefinition( request_data) ),
    'GoTo':            ( lambda self, request_data:
                                        self._GoToDefinition( request_data) ),
    'GetType':         ( lambda self, request_data:
                                        self._GetType( request_data) ),
    'GetDoc':          ( lambda self, request_data:
                                        self._GetDoc( request_data) ),
  }

  def __init__( self, user_options ):
    super( TernCompleter, self ).__init__( user_options )

    self._user_options = user_options
    self._Reset()


  def ComputeCandidatesInner( self, request_data ):
    query = {
      'type': 'completions',
      'types': True,
      'docs': True,
      'filter': False,
      'caseInsensitive': True,
      'guess': True,
      'sort': False,
      'includeKeywords': False
    }

    return [ responses.BuildCompletionData(
      completion[ 'name' ],
      completion.get( 'type', '?' ),
      completion.get( 'doc', None ),
    ) for completion in self._GetResponse( query, request_data )[ 'completions' ] ]


  def DefinedSubcommands( self ):
    return self.subcommands.keys()


  def OnFileReadyToParse( self, request_data ):
    self._StartServer()


  def OnUserCommand( self, arguments, request_data ):
    if not arguments or arguments[ 0 ] not in TernCompleter.subcommands:
      raise ValueError( self.UserCommandsHelpMessage() )

    return TernCompleter.subcommands[ arguments[ 0 ] ]( self, request_data )


  def SupportedFiletypes( self ):
    return [ 'javascript' ]


  def Shutdown( self ):
    self._StopServer()


  def _Reset( self ):
    self._server_handle   = None
    self._server_port     = 0


  def _GetResponse( self, query, request_data ):
    # start the server on demand (if not already started)
    self._StartServer()

    target = 'http://localhost:' + str( self._server_port )

    def MakeIncompleteFile( name, file_data ):
      return {
        'type': 'full',
        'name': name,
        'text': file_data[ 'contents' ],
      }

    def MakeTernLocation( request_data ):
      return {
        'line': request_data[ 'line_num' ] - 1,
        'ch': request_data[ 'start_column' ] - 1
      }

    full_query = {
      'file':              request_data[ 'filepath' ],
      'end':               MakeTernLocation( request_data ),
      'lineCharPositions': True,
    }
    full_query.update( query )

    response = requests.post( target, data = utils.ToUtf8Json( {
      'query': full_query,
      'files': [
        MakeIncompleteFile( x, request_data[ 'file_data' ][ x ] )
          for x in request_data[ 'file_data' ].keys()
      ],
      'timeout': 500,
    } ) )

    return response.json()


  def _StartServer( self ):
    if self._server_handle is None:
      _logger.info( 'Starting ternjs server...' )

      self._server_port = utils.GetUnusedLocalhostPort()

      if _logger.isEnabledFor( logging.debug ):
        extra_args = [ '--verbose' ]
      else:
        extra_args = []

      command = [ PATH_TO_TERNJS_BINARY,
                  '--port',
                  str( self._server_port ),
                  '--host',
                  'localhost',
                  '--persistent',
                  '--no-port-file' ] + extra_args

      _logger.debug( ' - command: ' + ' '.join( command ) )

      self._server_handle = utils.SafePopen( command,
                                             stdout = sys.stdout,
                                             stderr = sys.stderr )

      _logger.info( 'Server started.' )


  def _StopServer( self ):
    self._logger.info( 'Stopping ternjs server...' )

    if self._server_handle is not None:
      self._server_handle.kill()

    self._Reset()

    self._logger.info( 'ternjs server killed.' )


  def _GetType( self, request_data ):
    query = {
      'type': 'type',
    }

    response = self._GetResponse( query, request_data )

    return responses.BuildDisplayMessageResponse( response[ 'type' ] )


  def _GetDoc( self, request_data ):
    query = {
      'type':      'documentation',
      'docFormat': 'full',
    }

    response = self._GetResponse( query, request_data )

    return responses.BuildDetailedInfoResponse( response[ 'doc' ] )


  def _GoToDefinition( self, request_data ):
    query = {
      'type': 'definition',
    }

    response = self._GetResponse( query, request_data )

    return responses.BuildGoToResponse(
      response[ 'file' ],
      response[ 'start' ][ 'line' ] + 1,
      response[ 'start' ][ 'ch' ] + 1
    )


