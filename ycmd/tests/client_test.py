# Copyright (C) 2016 ycmd contributors
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
from future import standard_library
standard_library.install_aliases()
from builtins import *  # noqa
from future.utils import native

from base64 import b64decode, b64encode
from hamcrest import assert_that, equal_to, has_length, is_in
from tempfile import NamedTemporaryFile
import functools
import json
import os
import psutil
import re
import requests
import subprocess
import sys
import time
import urllib.parse

from ycmd.hmac_utils import CreateHmac, CreateRequestHmac, SecureBytesEqual
from ycmd.tests import PathToTestFile
from ycmd.tests.test_utils import BuildRequest
from ycmd.user_options_store import DefaultOptions
from ycmd.utils import ( GetUnusedLocalhostPort, OpenForStdHandle,
                         PathToCreatedTempDir, ReadFile, RemoveIfExists,
                         SafePopen, SetEnviron, ToBytes, ToUnicode )

HEADERS = { 'content-type': 'application/json' }
HMAC_HEADER = 'x-ycm-hmac'
HMAC_SECRET_LENGTH = 16
DIR_OF_THIS_SCRIPT = os.path.dirname( os.path.abspath( __file__ ) )
PATH_TO_YCMD = os.path.join( DIR_OF_THIS_SCRIPT, '..' )


class Client_test( object ):

  def __init__( self ):
    self._location = None
    self._port = None
    self._hmac_secret = None
    self._stdout = None
    self.server = None
    self.subservers = []
    self._options_dict = DefaultOptions()


  def setUp( self ):
    self._hmac_secret = os.urandom( HMAC_SECRET_LENGTH )
    self._options_dict[ 'hmac_secret' ] = ToUnicode(
      b64encode( self._hmac_secret ) )


  def tearDown( self ):
    if self.server.is_running():
      self.server.terminate()
    if self._stdout:
      RemoveIfExists( self._stdout )
    if self.subservers:
      for subserver in self.subservers:
        if subserver.is_running():
          subserver.terminate()


  def Start( self, idle_suicide_seconds = 60,
             check_interval_seconds = 60 * 10 ):
    # The temp options file is deleted by ycmd during startup
    with NamedTemporaryFile( mode = 'w+', delete = False ) as options_file:
      json.dump( self._options_dict, options_file )
      options_file.flush()
      self._port = GetUnusedLocalhostPort()
      self._location = 'http://127.0.0.1:' + str( self._port )

      # Define environment variable to enable subprocesses coverage. See:
      # http://coverage.readthedocs.org/en/coverage-4.0.3/subprocess.html
      env = os.environ.copy()
      SetEnviron( env, 'COVERAGE_PROCESS_START', '.coveragerc' )

      ycmd_args = [
        sys.executable,
        PATH_TO_YCMD,
        '--port={0}'.format( self._port ),
        '--options_file={0}'.format( options_file.name ),
        '--log=debug',
        '--idle_suicide_seconds={0}'.format( idle_suicide_seconds ),
        '--check_interval_seconds={0}'.format( check_interval_seconds ),
      ]

      self._stdout = os.path.join( PathToCreatedTempDir(), 'test.log' )
      with OpenForStdHandle( self._stdout ) as stdout:
        _popen_handle = SafePopen( ycmd_args,
                                   stdin_windows = subprocess.PIPE,
                                   stdout = stdout,
                                   stderr = subprocess.STDOUT,
                                   env = env )
        self.server = psutil.Process( _popen_handle.pid )

      self._WaitUntilReady()
      extra_conf = PathToTestFile( 'client', '.ycm_extra_conf.py' )
      self.PostRequest( 'load_extra_conf_file', { 'filepath': extra_conf } )


  def _IsReady( self, filetype = None ):
    params = { 'subserver': filetype } if filetype else None
    response = self.GetRequest( 'ready', params )
    response.raise_for_status()
    return response.json()


  def _WaitUntilReady( self, filetype = None, timeout = 5 ):
    total_slept = 0
    while True:
      try:
        if total_slept > timeout:
          server = ( 'the {0} subserver'.format( filetype ) if filetype else
                     'ycmd' )
          raise RuntimeError( 'Waited for {0} to be ready for {1} seconds, '
                              'aborting.'.format( server, timeout ) )

        if self._IsReady( filetype ):
          return
      except requests.exceptions.ConnectionError:
        pass
      finally:
        time.sleep( 0.1 )
        total_slept += 0.1


  def StartSubserverForFiletype( self, filetype ):
    filepath = PathToTestFile( 'client', 'some_file' )
    # Calling the BufferVisit event before the FileReadyToParse one is needed
    # for the TypeScript completer.
    self.PostRequest( 'event_notification',
                      BuildRequest( filepath = filepath,
                                    filetype = filetype,
                                    event_name = 'BufferVisit' ) )
    self.PostRequest( 'event_notification',
                      BuildRequest( filepath = filepath,
                                    filetype = filetype,
                                    event_name = 'FileReadyToParse' ) )

    self._WaitUntilReady( filetype )

    response = self.PostRequest(
      'debug_info',
      BuildRequest( filepath = filepath,
                    filetype = filetype )
    )
    pid_match = re.search( 'process ID: (\d+)', response.json() )
    if not pid_match:
      raise RuntimeError( 'Cannot find PID in debug informations for {0} '
                          'filetype.'.format( filetype ) )
    subserver_pid = int( pid_match.group( 1 ) )
    self.subservers.append( psutil.Process( subserver_pid ) )


  def AssertServerAndSubserversAreRunning( self ):
    for server in [ self.server ] + self.subservers:
      assert_that( server.is_running(), equal_to( True ) )


  def AssertServerAndSubserversShutDown( self, timeout = 5 ):
    _, alive = psutil.wait_procs( [ self.server ] + self.subservers,
                                  timeout = timeout )
    assert_that( alive, has_length( equal_to( 0 ) ) )


  def GetRequest( self, handler, params = None ):
    return self._Request( 'GET', handler, params = params )


  def PostRequest( self, handler, data = None ):
    return self._Request( 'POST', handler, data = data )


  def _ToUtf8Json( self, data ):
    return ToBytes( json.dumps( data ) if data else None )


  def _Request( self, method, handler, data = None, params = None ):
    request_uri = self._BuildUri( handler )
    data = self._ToUtf8Json( data )
    headers = self._ExtraHeaders( method,
                                  request_uri,
                                  data )
    response = requests.request( method,
                                 request_uri,
                                 headers = headers,
                                 data = data,
                                 params = params )
    return response


  def _BuildUri( self, handler ):
    return native( ToBytes( urllib.parse.urljoin( self._location, handler ) ) )


  def _ExtraHeaders( self, method, request_uri, request_body = None ):
    if not request_body:
      request_body = bytes( b'' )
    headers = dict( HEADERS )
    headers[ HMAC_HEADER ] = b64encode(
        CreateRequestHmac( ToBytes( method ),
                           ToBytes( urllib.parse.urlparse( request_uri ).path ),
                           request_body,
                           self._hmac_secret ) )
    return headers


  def AssertResponse( self, response ):
    assert_that( response.status_code, equal_to( requests.codes.ok ) )
    assert_that( HMAC_HEADER, is_in( response.headers ) )
    assert_that(
      self._ContentHmacValid( response ),
      equal_to( True )
    )


  def _ContentHmacValid( self, response ):
    our_hmac = CreateHmac( response.content, self._hmac_secret )
    their_hmac = ToBytes( b64decode( response.headers[ HMAC_HEADER ] ) )
    return SecureBytesEqual( our_hmac, their_hmac )


  @staticmethod
  def CaptureOutputFromServer( test ):
    @functools.wraps( test )
    def Wrapper( self, *args ):
      try:
        test( self, *args )
      finally:
        if self._stdout:
          sys.stdout.write( ReadFile( self._stdout ) )

    return Wrapper
