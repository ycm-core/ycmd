# Copyright (C) 2017 Jerry Marino <i@jerrymarino.com>
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
from ycmd.completers.swift.swift_flags import Flags

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
LOGFILE_FORMAT = 'swiftyswift_http_{port}_{std}_'
PATH_TO_SSVIMHTTP = os.path.abspath(
  os.path.join( os.path.dirname( __file__ ), '..', '..', '..',
                'third_party', 'swiftyswiftvim', 'build', 'http_server' ) )
SSVIM_IP = "127.0.0.1"


def ShouldEnableSwiftCompleter():
  return os.path.isfile( PATH_TO_SSVIMHTTP )


class SwiftCompleter( Completer ):
  '''
  A Completer that uses the Swifty Swift Vim semantic engine for Swift.
  https://github.com/jerrymarino/swiftyswiftvim
  '''

  def __init__( self, user_options ):
    super( SwiftCompleter, self ).__init__( user_options )
    self._server_lock = threading.RLock()
    self._http_port = None
    self._http_phandle = None
    self._logger = logging.getLogger( __name__ )
    self._logfile_stdout = None
    self._logfile_stderr = None
    self._keep_logfiles = user_options[ 'server_keep_logfiles' ]
    self._hmac_secret = ''
    self._flags = Flags()
    self._StartServer()


  def SupportedFiletypes( self ):
    return [ 'swift' ]


  def Shutdown( self ):
    self._StopServer()


  def ServerIsHealthy( self ):
    '''
    Check if the server is alive AND ready to serve requests.
    '''
    self._logger.info( 'Got SSVIM Healthy Request' )
    if not self._ServerIsRunning():
      self._logger.info( 'SSVIM not running.' )
      try:
        return bool( self._GetResponse( '/status' ) )
      except requests.exceptions.ConnectionError as e:
        self._logger.error( 'Failed Ready' )
        self._logger.exception( e )
        return False
    return True


  def _ServerIsRunning( self ):
    '''
    Check if the server is alive. That doesn't necessarily mean it's ready to
    serve requests; that's checked by ServerIsHealthy.
    '''
    with self._server_lock:
      status = ( bool( self._http_port ) and
                 ProcessIsRunning( self._http_phandle ) )
      self._logger.debug( 'Healthy Status ' + str( status ) )
      return status


  def RestartServer( self, binary = None ):
    ''' Restart the the server. '''
    self._StopServer()
    self._StartServer()


  def _StopServer( self ):
    with self._server_lock:
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
    with self._server_lock:
      self._logger.info( 'Starting SSVIM server' )
      self._http_port = utils.GetUnusedLocalhostPort()
      self._http_host = ToBytes( 'http://{0}:{1}'.format(
        SSVIM_IP, self._http_port ) )
      self._logger.info( 'using port {0}'.format( self._http_port ) )
      self._hmac_secret = self._GenerateHmacSecret()

      # The server will delete the secret_file after it's done reading it
      with NamedTemporaryFile( delete = False, mode = 'w+' ) as hmac_file:
        json.dump( { 'hmac_secret': ToUnicode(
                      b64encode( self._hmac_secret ) ) },
                       hmac_file )
        command = [ PATH_TO_SSVIMHTTP,
                    '--ip', SSVIM_IP,
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

      self._logger.info( 'Started SSVIM server' )


  def _GenerateHmacSecret( self ):
    return os.urandom( HMAC_SECRET_LENGTH )


  def _GetLoggingLevel( self ):
    # Tests are run with the NOTSET logging level and the server accepts the
    # predefined levels (DEBUG, INFO, WARNING, etc.).
    log_level = max( self._logger.getEffectiveLevel(), logging.DEBUG )
    return logging.getLevelName( log_level ).lower()


  def _GetResponse( self, handler, request_data = {} ):
    '''POST JSON requests and return JSON response.'''
    handler = ToBytes( handler )
    url = urljoin( self._http_host, handler )
    parameters = self._PrepareRequestBody( request_data )
    body = ToBytes( json.dumps( parameters ) ) if parameters else bytes()
    extra_headers = self._ExtraHeaders( handler, body )

    self._logger.debug( 'Making SSVIM request: %s %s %s %s', 'POST', url,
                        extra_headers, body )

    response = requests.request( native( bytes( b'POST' ) ),
                                 native( url ),
                                 data = body,
                                 headers = extra_headers )
    response.raise_for_status()
    value = response.json()
    self._logger.debug( 'Got SSVIM response: %s %s %s %s', 'POST', url,
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
    col = request_data[ 'start_codepoint' ]

    filename = request_data[ 'filepath' ]
    flags = self._flags.FlagsForFile( filename )

    return {
      'contents': source,
      'line': line,
      'column': col,
      'file_name': path,
      'flags': flags
    }


  def ShouldUseNowInner( self, request_data ):
    return True


  def ComputeCandidatesInner( self, request_data ):
    logging.debug( 'Request SSVIM Completions' )
    response = self._GetResponse( '/completions', request_data )
    # Build a completion Document with the completion portion of the response
    completion_doc = SwiftCompletionDocument( response, request_data )
    return [ responses.BuildCompletionData(
                completion.name,
                completion.description,
                completion.docbrief )
             for completion in completion_doc.GetCompletions() ]


  def GetSubcommandsMap( self ):
    return {
      'StopServer'     : ( lambda self, request_data, args:
                           self.Shutdown() ),
      'RestartServer'  : ( lambda self, request_data, args:
                           self.RestartServer( *args ) )
    }


  def DebugInfo( self, request_data ):
    http_server = responses.DebugInfoServer(
      name = 'SwiftySwiftVim',
      handle = self._http_phandle,
      executable = PATH_TO_SSVIMHTTP,
      address = SSVIM_IP,
      port = self._http_port,
      logfiles = [ self._logfile_stdout, self._logfile_stderr ] )

    return responses.BuildDebugInfoResponse(
        name = 'Swift',
        servers = [ http_server ],
    )


class SwiftCompletion():
  '''
  Represent a Swift Completion
  '''

  def __init__( self, json_value, request_data ):
    self.module_path = ''
    # TODO: Give the user the option to use for placeholders for quick typing:
    # insertion_text is conditionally ( key.sourcetext ).
    self.name = json_value.get( 'key.name' )
    self.description = json_value.get( 'key.description' )
    self.type = 'swift'

    self.modulename = json_value.get( 'key.modulename' )
    self.context = json_value.get( 'key.context' )
    json_docbrief = json_value.get( 'key.doc.brief' )

    if json_docbrief:
      self.docbrief = self.description + '\n' + json_docbrief
    else:
      # If we don't have a docbrief, format some information to
      # help the user comprehend where this came from.
      if self.modulename:
        topline = self.modulename + ' - ' + self.description
      else:
        topline = self.description
      self.docbrief = topline + '\n' + self.context


class SwiftCompletionDocument():
  def __init__( self, value, request_data ):
    self.json = value
    self.request_data = request_data


  def GetCompletions( self ):
    # TODO: we will likely want to insert more data into responses.
    # The API should likely package completions as a nested key
    # instead of the root object
    completions = []
    for json_completion in self.json[ 'key.results' ]:
      completion = SwiftCompletion( json_completion, self.request_data )
      completions.append( completion )
    return completions
