# Copyright (C) 2011-2012 Stephen Sugden <me@stephensugden.com>
#                         Google Inc.
#                         Stanislav Golovanov <stgolovanov@gmail.com>
#               2017      ycmd contributors
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

from ycmd.utils import ToBytes, ToUnicode, ProcessIsRunning, urljoin
from ycmd.completers.completer import Completer
from ycmd import responses, utils, hmac_utils
from tempfile import NamedTemporaryFile

from base64 import b64encode
from future.utils import native
import json
import logging
import requests
import threading
import sys
import os


HMAC_SECRET_LENGTH = 16
JEDIHTTP_HMAC_HEADER = 'x-jedihttp-hmac'
BINARY_NOT_FOUND_MESSAGE = ( 'The specified python interpreter {0} ' +
                             'was not found. Did you specify it correctly?' )
LOGFILE_FORMAT = 'jedihttp_{port}_{std}_'
PATH_TO_JEDIHTTP = os.path.abspath(
  os.path.join( os.path.dirname( __file__ ), '..', '..', '..',
                'third_party', 'JediHTTP', 'jedihttp.py' ) )


class JediCompleter( Completer ):
  """
  A Completer that uses the Jedi engine HTTP wrapper JediHTTP.
  https://jedi.readthedocs.org/en/latest/
  https://github.com/vheon/JediHTTP
  """

  def __init__( self, user_options ):
    super( JediCompleter, self ).__init__( user_options )
    self._server_lock = threading.RLock()
    self._jedihttp_port = None
    self._jedihttp_phandle = None
    self._logger = logging.getLogger( __name__ )
    self._logfile_stdout = None
    self._logfile_stderr = None
    self._keep_logfiles = user_options[ 'server_keep_logfiles' ]
    self._hmac_secret = ''
    self._python_binary_path = sys.executable

    self._UpdatePythonBinary( user_options.get( 'python_binary_path' ) )
    self._StartServer()


  def _UpdatePythonBinary( self, binary ):
    if binary:
      resolved_binary = utils.FindExecutable( binary )
      if not resolved_binary:
        msg = BINARY_NOT_FOUND_MESSAGE.format( binary )
        self._logger.error( msg )
        raise RuntimeError( msg )
      self._python_binary_path = resolved_binary


  def SupportedFiletypes( self ):
    """ Just python """
    return [ 'python' ]


  def Shutdown( self ):
    self._StopServer()


  def ServerIsHealthy( self ):
    """
    Check if JediHTTP is alive AND ready to serve requests.
    """
    if not self._ServerIsRunning():
      self._logger.debug( 'JediHTTP not running.' )
      return False
    try:
      return bool( self._GetResponse( '/ready' ) )
    except requests.exceptions.ConnectionError as e:
      self._logger.exception( e )
      return False


  def _ServerIsRunning( self ):
    """
    Check if JediHTTP is alive. That doesn't necessarily mean it's ready to
    serve requests; that's checked by ServerIsHealthy.
    """
    with self._server_lock:
      return ( bool( self._jedihttp_port ) and
               ProcessIsRunning( self._jedihttp_phandle ) )


  def RestartServer( self, binary = None ):
    """ Restart the JediHTTP Server. """
    with self._server_lock:
      if binary:
        self._UpdatePythonBinary( binary )
      self._StopServer()
      self._StartServer()


  def _StopServer( self ):
    with self._server_lock:
      if self._ServerIsRunning():
        self._logger.info( 'Stopping JediHTTP server with PID {0}'.format(
                               self._jedihttp_phandle.pid ) )
        self._jedihttp_phandle.terminate()
        try:
          utils.WaitUntilProcessIsTerminated( self._jedihttp_phandle,
                                              timeout = 5 )
          self._logger.info( 'JediHTTP server stopped' )
        except RuntimeError:
          self._logger.exception( 'Error while stopping JediHTTP server' )

      self._CleanUp()


  def _CleanUp( self ):
    self._jedihttp_phandle = None
    self._jedihttp_port = None
    if not self._keep_logfiles:
      utils.RemoveIfExists( self._logfile_stdout )
      self._logfile_stdout = None
      utils.RemoveIfExists( self._logfile_stderr )
      self._logfile_stderr = None


  def _StartServer( self ):
    with self._server_lock:
      self._logger.info( 'Starting JediHTTP server' )
      self._jedihttp_port = utils.GetUnusedLocalhostPort()
      self._jedihttp_host = ToBytes( 'http://127.0.0.1:{0}'.format(
        self._jedihttp_port ) )
      self._logger.info( 'using port {0}'.format( self._jedihttp_port ) )
      self._hmac_secret = self._GenerateHmacSecret()

      # JediHTTP will delete the secret_file after it's done reading it
      with NamedTemporaryFile( delete = False, mode = 'w+' ) as hmac_file:
        json.dump( { 'hmac_secret': ToUnicode(
                        b64encode( self._hmac_secret ) ) },
                   hmac_file )
        command = [ self._python_binary_path,
                    PATH_TO_JEDIHTTP,
                    '--port', str( self._jedihttp_port ),
                    '--log', self._GetLoggingLevel(),
                    '--hmac-file-secret', hmac_file.name ]

      self._logfile_stdout = utils.CreateLogfile(
          LOGFILE_FORMAT.format( port = self._jedihttp_port, std = 'stdout' ) )
      self._logfile_stderr = utils.CreateLogfile(
          LOGFILE_FORMAT.format( port = self._jedihttp_port, std = 'stderr' ) )

      with utils.OpenForStdHandle( self._logfile_stdout ) as logout:
        with utils.OpenForStdHandle( self._logfile_stderr ) as logerr:
          self._jedihttp_phandle = utils.SafePopen( command,
                                                    stdout = logout,
                                                    stderr = logerr )


  def _GenerateHmacSecret( self ):
    return os.urandom( HMAC_SECRET_LENGTH )


  def _GetLoggingLevel( self ):
    # Tests are run with the NOTSET logging level but JediHTTP only accepts the
    # predefined levels above (DEBUG, INFO, WARNING, etc.).
    log_level = max( self._logger.getEffectiveLevel(), logging.DEBUG )
    return logging.getLevelName( log_level ).lower()


  def _GetResponse( self, handler, request_data = {} ):
    """POST JSON data to JediHTTP server and return JSON response."""
    handler = ToBytes( handler )
    url = urljoin( self._jedihttp_host, handler )
    parameters = self._TranslateRequestForJediHTTP( request_data )
    body = ToBytes( json.dumps( parameters ) ) if parameters else bytes()
    extra_headers = self._ExtraHeaders( handler, body )

    self._logger.debug( 'Making JediHTTP request: %s %s %s %s', 'POST', url,
                        extra_headers, body )

    response = requests.request( native( bytes( b'POST' ) ),
                                 native( url ),
                                 data = body,
                                 headers = extra_headers )

    response.raise_for_status()
    return response.json()


  def _ExtraHeaders( self, handler, body ):
    hmac = hmac_utils.CreateRequestHmac( bytes( b'POST' ),
                                         handler,
                                         body,
                                         self._hmac_secret )

    extra_headers = { 'content-type': 'application/json' }
    extra_headers[ JEDIHTTP_HMAC_HEADER ] = b64encode( hmac )
    return extra_headers


  def _TranslateRequestForJediHTTP( self, request_data ):
    if not request_data:
      return {}

    path = request_data[ 'filepath' ]
    source = request_data[ 'file_data' ][ path ][ 'contents' ]
    line = request_data[ 'line_num' ]
    # JediHTTP (as Jedi itself) expects columns to start at 0, not 1, and for
    # them to be unicode codepoint offsets.
    col = request_data[ 'start_codepoint' ] - 1

    return {
      'source': source,
      'line': line,
      'col': col,
      'source_path': path
    }


  def _GetExtraData( self, completion ):
      location = {}
      if completion[ 'module_path' ]:
        location[ 'filepath' ] = completion[ 'module_path' ]
      if completion[ 'line' ]:
        location[ 'line_num' ] = completion[ 'line' ]
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
                completion[ 'name' ],
                completion[ 'description' ],
                completion[ 'docstring' ],
                extra_data = self._GetExtraData( completion ) )
             for completion in self._JediCompletions( request_data ) ]


  def _JediCompletions( self, request_data ):
    return self._GetResponse( '/completions',
                              request_data )[ 'completions' ]


  def GetSubcommandsMap( self ):
    return {
      'GoToDefinition' : ( lambda self, request_data, args:
                           self._GoToDefinition( request_data ) ),
      'GoToDeclaration': ( lambda self, request_data, args:
                           self._GoToDeclaration( request_data ) ),
      'GoTo'           : ( lambda self, request_data, args:
                           self._GoTo( request_data ) ),
      'GetDoc'         : ( lambda self, request_data, args:
                           self._GetDoc( request_data ) ),
      'GoToReferences' : ( lambda self, request_data, args:
                           self._GoToReferences( request_data ) ),
      'StopServer'     : ( lambda self, request_data, args:
                           self.Shutdown() ),
      'RestartServer'  : ( lambda self, request_data, args:
                           self.RestartServer( *args ) )
    }


  def _GoToDefinition( self, request_data ):
    definitions = self._GetDefinitionsList( '/gotodefinition',
                                            request_data )
    if not definitions:
      raise RuntimeError( 'Can\'t jump to definition.' )
    return self._BuildGoToResponse( definitions )


  def _GoToDeclaration( self, request_data ):
    definitions = self._GetDefinitionsList( '/gotoassignment',
                                            request_data )
    if not definitions:
      raise RuntimeError( 'Can\'t jump to declaration.' )
    return self._BuildGoToResponse( definitions )


  def _GoTo( self, request_data ):
    try:
      return self._GoToDefinition( request_data )
    except Exception as e:
      self._logger.exception( e )
      pass

    try:
      return self._GoToDeclaration( request_data )
    except Exception as e:
      self._logger.exception( e )
      raise RuntimeError( 'Can\'t jump to definition or declaration.' )


  def _GetDoc( self, request_data ):
    try:
      definitions = self._GetDefinitionsList( '/gotodefinition',
                                              request_data )
      return self._BuildDetailedInfoResponse( definitions )
    except Exception as e:
      self._logger.exception( e )
      raise RuntimeError( 'Can\'t find a definition.' )


  def _GoToReferences( self, request_data ):
    definitions = self._GetDefinitionsList( '/usages', request_data )
    if not definitions:
      raise RuntimeError( 'Can\'t find references.' )
    return self._BuildGoToResponse( definitions )


  def _GetDefinitionsList( self, handler, request_data ):
    try:
      response = self._GetResponse( handler, request_data )
      return response[ 'definitions' ]
    except Exception as e:
      self._logger.exception( e )
      raise RuntimeError( 'Cannot follow nothing. '
                          'Put your cursor on a valid name.' )


  def _BuildGoToResponse( self, definition_list ):
    if len( definition_list ) == 1:
      definition = definition_list[ 0 ]
      if definition[ 'in_builtin_module' ]:
        if definition[ 'is_keyword' ]:
          raise RuntimeError( 'Cannot get the definition of Python keywords.' )
        else:
          raise RuntimeError( 'Builtin modules cannot be displayed.' )
      else:
        return responses.BuildGoToResponse( definition[ 'module_path' ],
                                            definition[ 'line' ],
                                            definition[ 'column' ] + 1 )
    else:
      # multiple definitions
      defs = []
      for definition in definition_list:
        if definition[ 'in_builtin_module' ]:
          defs.append( responses.BuildDescriptionOnlyGoToResponse(
                       'Builtin ' + definition[ 'description' ] ) )
        else:
          defs.append(
            responses.BuildGoToResponse( definition[ 'module_path' ],
                                         definition[ 'line' ],
                                         definition[ 'column' ] + 1,
                                         definition[ 'description' ] ) )
      return defs


  def _BuildDetailedInfoResponse( self, definition_list ):
    docs = [ definition[ 'docstring' ] for definition in definition_list ]
    return responses.BuildDetailedInfoResponse( '\n---\n'.join( docs ) )


  def DebugInfo( self, request_data ):
    with self._server_lock:
      jedihttp_server = responses.DebugInfoServer(
        name = 'JediHTTP',
        handle = self._jedihttp_phandle,
        executable = PATH_TO_JEDIHTTP,
        address = '127.0.0.1',
        port = self._jedihttp_port,
        logfiles = [ self._logfile_stdout, self._logfile_stderr ] )

      python_interpreter_item = responses.DebugInfoItem(
        key = 'Python interpreter',
        value = self._python_binary_path )

      return responses.BuildDebugInfoResponse(
        name = 'Python',
        servers = [ jedihttp_server ],
        items = [ python_interpreter_item ] )
