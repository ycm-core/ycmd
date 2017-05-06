# Copyright (C) 2011-2012 Jerry Marino <i@jerrymarino.com>
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
import os


HMAC_SECRET_LENGTH = 16
SSVIMHTTP_HMAC_HEADER = 'x-http-hmac'
LOGFILE_FORMAT = 'http_{port}_{std}_'
PATH_TO_SSVIMHTTP = os.path.abspath(
  os.path.join( os.path.dirname( __file__ ), '..', '..', '..',
                'third_party', 'swiftyswiftvim', 'build', 'http_server' ) )

class SwiftCompleter( Completer ):
  '''
  A Completer that uses the Swifty Swift Vim semantic engine for Swift.
  https://github.com/jerrymarino/swiftyswiftvim
  '''

  def __init__( self, user_options ):
    super( SwiftCompleter, self ).__init__( user_options )
    self._http_port = None
    self._http_phandle = None
    self._logger = logging.getLogger( __name__ )
    self._logfile_stdout = None
    self._logfile_stderr = None
    self._keep_logfiles = user_options[ 'server_keep_logfiles' ]
    self._hmac_secret = ''
    self._message = 'SSVIM'
    self._StartServer()

  def SupportedFiletypes( self ):
    return [ 'swift' ]

  def Shutdown( self ):
    self._StopServer()


  def ServerIsHealthy( self ):
    '''
    Check if the server is alive AND ready to serve requests.
    '''
    if not self._ServerIsRunning():
      self._logger.debug( 'JediHTTP not running.' )
      return False
      try:
        self._logger.error( 'Check Ready' )
        value = bool( self._GetResponse( '/status' ) )
        self._logger.error( 'ISReady:', value )
      except requests.exceptions.ConnectionError as e:
        self._logger.error( 'Failed Ready' )
        self._logger.exception( e )
    return False


  def _ServerIsRunning( self ):
    '''
    Check if the server is alive. That doesn't necessarily mean it's ready to
    serve requests; that's checked by ServerIsHealthy.
    '''
    return ( bool( self._http_port ) and
               ProcessIsRunning( self._http_phandle ) )


  def RestartServer( self, binary = None ):
    ''' Restart the the server. '''
    self._StopServer()
    self._StartServer()


  def _StopServer( self ):
    if self._ServerIsRunning():
      self._logger.info( 'Stopping SSVIM server with PID {0}'.format(
                               self._http_phandle.pid ) )
      self._GetResponse( '/shutdown' )
      try:
        utils.WaitUntilProcessIsTerminated( self._http_phandle,
                                            timeout = 5 )
        self._logger.info( 'SSVIM server stopped' )
      except RuntimeError:
        self._logger.exception( 'Error while stopping SSVIM server' )

      self._CleanUp()


  def _CleanUp( self ):
    self._http_phandle = None
    self._http_port = None
    if not self._keep_logfiles:
      utils.RemoveIfExists( self._logfile_stdout )
      self._logfile_stdout = None
      utils.RemoveIfExists( self._logfile_stderr )
      self._logfile_stderr = None


  def _StartServer( self ):
    self._logger.info( 'Starting SSVIM server' )
    self._http_port = utils.GetUnusedLocalhostPort()
    self._http_host = ToBytes( 'http://0.0.0.0:{0}'.format(
    self._http_port ) )
    self._logger.info( 'using port {0}'.format( self._http_port ) )
    self._hmac_secret = self._GenerateHmacSecret()

    # The server will delete the secret_file after it's done reading it
    with NamedTemporaryFile( delete = False, mode = 'w+' ) as hmac_file:
      json.dump( { 'hmac_secret': ToUnicode(
                    b64encode( self._hmac_secret ) ) },
                     hmac_file )
      command = [ PATH_TO_SSVIMHTTP,
                  '--port', str( self._http_port ),
                  '--log', self._GetLoggingLevel(),
                  '--hmac-file-secret', hmac_file.name ]

      self._logfile_stdout = utils.CreateLogfile(
        LOGFILE_FORMAT.format( port = self._http_port, std = 'stdout' ) )
      self._logfile_stderr = utils.CreateLogfile(
        LOGFILE_FORMAT.format( port = self._http_port, std = 'stderr' ) )

      with utils.OpenForStdHandle( self._logfile_stdout ) as logout:
        with utils.OpenForStdHandle( self._logfile_stderr ) as logerr:
          self._http_phandle = utils.SafePopen( command,
                                                  stdout = logout,
                                                  stderr = logerr )


  def _GenerateHmacSecret( self ):
    return os.urandom( HMAC_SECRET_LENGTH )


  def _GetLoggingLevel( self ):
    # Tests are run with the NOTSET logging level but JediHTTP only accepts the
    # predefined levels above (DEBUG, INFO, WARNING, etc.).
    log_level = max( self._logger.getEffectiveLevel(), logging.DEBUG )
    return logging.getLevelName( log_level ).lower()

  def _DebugDumpRequest(self, request_data):
    # This is debugging utility to extract all of
    # the fields from request data
    out = {}
    for key in request_data._computed_key:
      out[key] = request_data.get(key)
    self._logger.debug( 'SSVIM request: %s', out )
    return out


  def _GetResponse( self, handler, request_data = {} ):
    '''POST JSON requests and return JSON response.'''
    handler = ToBytes( handler )
    url = urljoin( self._http_host, handler )
    parameters = self._PrepareRequestBody( request_data )
    body = ToBytes( json.dumps( parameters ) ) if parameters else bytes()
    extra_headers = self._ExtraHeaders( handler, body )
    extra_headers = []

    self._logger.error( 'Making SSVIM request: %s %s %s %s', 'POST', url,
                        extra_headers, body )

    response = requests.request( native( bytes( b'POST' ) ),
                                 native( url ),
                                 data = body,
                                 headers = extra_headers )
    # Assume the entire protocol operations on JSON
    # use the headers to infer json
    response.raise_for_status()
    value = response.json()
    self._logger.error( 'Got SSVIM response: %s %s %s %s', 'POST', url,
                        value, value.keys())
    return value


  def _ExtraHeaders( self, handler, body ):
    hmac = hmac_utils.CreateRequestHmac( bytes( b'POST' ),
                                         handler,
                                         body,
                                         self._hmac_secret )

    extra_headers = { 'content-type': 'application/json' }
    extra_headers[ SSVIMHTTP_HMAC_HEADER ] = b64encode( hmac )
    return extra_headers


  def _PrepareRequestBody( self, request_data ):
    if not request_data:
      return {}

    path = request_data[ 'filepath' ]
    source = request_data[ 'file_data' ][ path ][ 'contents' ]
    line = request_data[ 'line_num' ]
    # The server expects columns to start at 0, not 1, and for
    # them to be unicode codepoint offsets.
    col = request_data[ 'start_codepoint' ] - 1

    # Bundle default flags for the latest OSX sdk.
    # TODO: Support this at the client level
    flags = []
    flags.append( '-sdk' )
    flags.append(
        '/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk' )
    flags.append( '-target' )
    flags.append( 'x86_64-apple-macosx10.12' )

    return {
      'contents': source,
      'line': line,
      'column': col,
      'file_name': path,
      'flags': flags
    }

  def _GetExtraData( self, completion ):
      location = {}
      if completion.module_path:
        location.filepath = completion.module_path
      if completion.line:
        location.line_num = completion.line
      if completion.column:
        location.column_num = completion.column + 1

      if location:
        extra_data = {}
        extra_data.location = location
        return extra_data
      else:
        return None

  def ShouldUseNowInner( self, request_data ):
    return True

  def ComputeCandidatesInner( self, request_data ):
    return [ responses.BuildCompletionData(
                completion.name,
                completion.description,
                completion.docstring(),
                extra_data = self._GetExtraData( completion ) )
             for completion in self._FetchCompletions( request_data ) ]

  def CompletionType( self, request_data ):
    # Classify query types 
    # Type 1 is the initial completion type. 
    # For many completions, this represents available operators
    initial_completion_type = 1
    if len(request_data[ 'query' ]) == 1: 
        return initial_completion_type

    # When the query's length is larger than 1, completions are static for that
    # character value. 
    # Offset character types to avoid collision with other types
    char_val = ord(request_data[ 'line_value' ][0])
    return char_val + 1000

  def _FetchCompletions( self, request_data ):
    logging.debug( 'Request SSVIM Completions' )
    response = self._GetResponse( '/completions',
                              request_data )
    
    # Build a completion Document with the completion portion of the response
    # TODO: we will likely want to insert more data into responses.
    # The API should likely package completions as a nested key
    # instead of the root object
    completion_doc = SwiftCompletionDocument( response, request_data )
    return completion_doc.completions()

  def GetSubcommandsMap( self ):
    return {
      'GetDiagnostics' : ( lambda self, request_data, args:
                           self._GetDiagnostics( request_data ) ),
      'StopServer'     : ( lambda self, request_data, args:
                           self.Shutdown() ),
      'RestartServer'  : ( lambda self, request_data, args:
                           self.RestartServer( *args ) )
    }

  def _GetDiagnostics( self, request_data ):
    logging.error( '_GetDiagnostics', request_data[ 'filepath' ])

  def _BuildDetailedInfoResponse( self, definition_list ):
    docs = [ definition[ 'docstring' ] for definition in definition_list ]
    return responses.BuildDetailedInfoResponse( '\n---\n'.join( docs ) )

  def DebugInfo( self, request_data ):
    http_server = responses.DebugInfoServer(
      name = 'SwiftySwiftVim',
      handle = self._http_phandle,
      executable = PATH_TO_SSVIMHTTP,
      address = '0.0.0.0',
      port = self._http_port,
      logfiles = [ self._logfile_stdout, self._logfile_stderr ] )

    return responses.BuildDebugInfoResponse(
        name = 'Swift',
        servers = [ http_server ],
        )


class SwiftCompletion():
  '''
  {
    'key.kind': 'source.lang.swift.decl.function.method.instance',
    'key.name': '`self`() -> Self',
    'key.sourcetext': '`self`() -> Self {\n<#code#>\n}',
    'key.description': '`self`() -> Self',
    'key.typename': '',
    'key.context': 'source.codecompletion.context.superclass',
    'key.num_bytes_to_erase': 0,
    'key.substructure': {
    'key.nameoffset': 0,
    'key.namelength': 16
    },
    'key.associated_usrs': 'c:objc(pl)NSObject(im)self',
    'key.modulename': 'ObjectiveC.NSObject'
  }
  '''

  def docstring(self):
    if self.docbrief:
      return self.description + '\n' + self.docbrief
    return self.description + '\n' + self.context

  def __init__(self, json_value, request_data):
    self.module_path = ''
    self.name = json_value.get( 'key.sourcetext' )
    self.description = json_value.get( 'key.description' )
    self.type = 'swift'
    self.line = 0
    self.column = 0

    self.modulename = json_value.get( 'key.modulename' )
    self.context = json_value.get( 'key.context' )
    self.docbrief = json_value.get( 'key.doc.brief' )

class SwiftCompletionDocument():
  def completions(self):
    completions = []
    for json_completion in self.json[ 'key.results' ]:
      completion = SwiftCompletion( json_completion, self.request_data )
      completions.append( completion )
    return completions

  def usages():
    return self.json_string

  def __init__(self, value, request_data):
    self.json = value
    self.request_data = request_data


