#!/usr/bin/env python
#
# Copyright (C) 2011, 2012  Stephen Sugden <me@stephensugden.com>
#                           Google Inc.
#                           Stanislav Golovanov <stgolovanov@gmail.com>
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

from ycmd.utils import ToUtf8IfNeeded
from ycmd.completers.completer import Completer
from ycmd import responses
from ycmd import utils

import urlparse
import requests
import logging

import os
import sys


PATH_TO_PYTHON = sys.executable
PATH_TO_JEDIHTTP = os.path.join(
  os.path.abspath( os.path.dirname( __file__ ) ),
  '..', '..', '..', 'third_party', 'JediHTTP', 'jedihttp' )

FILENAME_FORMAT = os.path.join( utils.PathToTempDir(),
                                u'jedihttp_{port}_{std}.log' )



class JediCompleter( Completer ):
  """
  A Completer that uses the Jedi engine HTTP Wrapper JediHTTP.
  https://jedi.readthedocs.org/en/latest/
  https://github.com/vheon/JediHTTP
  """

  def __init__( self, user_options ):
    super( JediCompleter, self ).__init__( user_options )
    self._jedihttp_port = None
    self._jedihttp_phandle = None
    self._logger = logging.getLogger( __name__ )
    self._filename_stderr = None
    self._filename_stdout = None


  def Shutdown( self ):
    if ( self.ServerIsRunning() ):
      self._StopServer()


  def _StopServer( self ):
    # TODO(vheon)
    pass


  def ServerIsRunning( self ):
    """ Check if JediHTTP server is running (up and serving)."""
    try:
      return bool( self._GetResponse( '/healthy' ) )
    except:
      return False

  def _StartServer( self, request_data ):
    self._ChoosePort()

    command = [ PATH_TO_PYTHON,
                PATH_TO_JEDIHTTP,
                '--port',
                str( self._jedihttp_port ) ]

    self._filename_stdout = FILENAME_FORMAT.format(
        port = self._jedihttp_port, std = 'stdout' )
    self._filename_stderr = FILENAME_FORMAT.format(
        port = self._jedihttp_port, std = 'stderr' )

    with open( self._filename_stderr, 'w' ) as fstderr:
      with open( self._filename_stdout, 'w' ) as fstdout:
        self._jedihttp_phandle = utils.SafePopen(
            command, stdout = fstdout, stderr = fstderr )

    self._logger.info( 'starting JediHTTP server' )


  def _ChoosePort( self ):
    if not self._jedihttp_port:
      self._jedihttp_port = utils.GetUnusedLocalhostPort()
    self._logger.info( u'using port {0}'.format( self._jedihttp_port ) )


  def _GetResponse( self, handler, parameters = {} ):
    """ Handle communication with server """
    target = urlparse.urljoin( self._ServerLocation(), handler )
    response = requests.post( target, json = parameters )
    return response.json()


  def _ServerLocation( self ):
    return 'http://localhost:' + str( self._jedihttp_port )


  def SupportedFiletypes( self ):
    """ Just python """
    return [ 'python' ]


  def _GetExtraData( self, completion ):
      location = {}
      if completion[ 'module_path' ]:
        location[ 'filepath' ] = ToUtf8IfNeeded( completion[ 'module_path' ] )
      if completion[ 'line' ]:
        location[ 'line_num' ] = completion['line']
      if completion[ 'column' ]:
        location[ 'column_num' ] = completion[ 'column' ] + 1

      if location:
        extra_data = {}
        extra_data[ 'location' ] = location
        return extra_data
      else:
        return None


  def ComputeCandidatesInner( self, request_data ):
    return [ responses.BuildCompletionData(
                ToUtf8IfNeeded( completion['name'] ),
                ToUtf8IfNeeded( completion['description'] ),
                ToUtf8IfNeeded( completion['docstring'] ),
                extra_data = self._GetExtraData( completion ) )
             for completion in self._JediCompletions( request_data ) ]


  def _JediCompletions( self, request_data ):
    path = request_data[ 'filepath' ]
    source = request_data[ 'file_data' ][ path ][ 'contents' ]
    line = request_data[ 'line_num' ]
    # JediHTTP as Jedi itself expects columns to start at 0, not 1
    col = request_data[ 'column_num' ] - 1

    request = {
      'source': source,
      'line': line,
      'col': col,
      'path': path
    }

    resp = self._GetResponse( '/completions', request )[ 'completions' ]
    return resp


  def OnFileReadyToParse( self, request_data ):
    if( not self.ServerIsRunning() ):
      self._StartServer( request_data )
      return


  def DefinedSubcommands( self ):
    pass
    # return [ 'GoToDefinition',
    #          'GoToDeclaration',
    #          'GoTo' ]


  def OnUserCommand( self, arguments, request_data ):
    pass
    # if not arguments:
    #   raise ValueError( self.UserCommandsHelpMessage() )

    # command = arguments[ 0 ]
    # if command == 'GoToDefinition':
    #   return self._GoToDefinition( request_data )
    # elif command == 'GoToDeclaration':
    #   return self._GoToDeclaration( request_data )
    # elif command == 'GoTo':
    #   return self._GoTo( request_data )
    # raise ValueError( self.UserCommandsHelpMessage() )


  # def _GoToDefinition( self, request_data ):
    # definitions = self._GetDefinitionsList( request_data )
    # if definitions:
    #   return self._BuildGoToResponse( definitions )
    # else:
    #   raise RuntimeError( 'Can\'t jump to definition.' )


  # def _GoToDeclaration( self, request_data ):
    # definitions = self._GetDefinitionsList( request_data, declaration = True )
    # if definitions:
    #   return self._BuildGoToResponse( definitions )
    # else:
    #   raise RuntimeError( 'Can\'t jump to declaration.' )


  # def _GoTo( self, request_data ):
    # definitions = ( self._GetDefinitionsList( request_data ) or
    #     self._GetDefinitionsList( request_data, declaration = True ) )
    # if definitions:
    #   return self._BuildGoToResponse( definitions )
    # else:
    #   raise RuntimeError( 'Can\'t jump to definition or declaration.' )


  # def _GetDefinitionsList( self, request_data, declaration = False ):
  #   definitions = []
  #   script = self._GetJediScript( request_data )
  #   try:
  #     if declaration:
  #       definitions = script.goto_assignments()
  #     else:
  #       definitions = script.goto_definitions()
  #   except jedi.NotFoundError:
  #     raise RuntimeError(
  #                 'Cannot follow nothing. Put your cursor on a valid name.' )

  #   return definitions


  # def _BuildGoToResponse( self, definition_list ):
  #   if len( definition_list ) == 1:
  #     definition = definition_list[ 0 ]
  #     if definition.in_builtin_module():
  #       if definition.is_keyword:
  #         raise RuntimeError(
  #                 'Cannot get the definition of Python keywords.' )
  #       else:
  #         raise RuntimeError( 'Builtin modules cannot be displayed.' )
  #     else:
  #       return responses.BuildGoToResponse( definition.module_path,
  #                                           definition.line,
  #                                           definition.column + 1 )
  #   else:
  #     # multiple definitions
  #     defs = []
  #     for definition in definition_list:
  #       if definition.in_builtin_module():
  #         defs.append( responses.BuildDescriptionOnlyGoToResponse(
  #                      'Builtin ' + definition.description ) )
  #       else:
  #         defs.append(
  #           responses.BuildGoToResponse( definition.module_path,
  #                                        definition.line,
  #                                        definition.column + 1,
  #                                        definition.description ) )
  #     return defs

