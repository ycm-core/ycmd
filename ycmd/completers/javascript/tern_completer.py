# Copyright (C) 2015-2018 ycmd contributors
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

from future.utils import iterkeys
import logging
import os
import requests
import threading

from subprocess import PIPE
from ycmd import utils, responses
from ycmd.completers.completer import Completer
from ycmd.completers.completer_utils import GetFileLines
from ycmd.utils import LOGGER

PATH_TO_TERN_BINARY = os.path.abspath(
  os.path.join(
    os.path.dirname( __file__ ),
    '..',
    '..',
    '..',
    'third_party',
    'tern_runtime',
    'node_modules',
    'tern',
    'bin',
    'tern' ) )

PATH_TO_NODE = utils.FindExecutable( 'node' )

# host name/address on which the tern server should listen
# note: we use 127.0.0.1 rather than localhost because on some platforms
# localhost might not be correctly configured as an alias for the loopback
# address. (ahem: Windows)
SERVER_HOST = '127.0.0.1'

LOGFILE_FORMAT = 'tern_{port}_{std}_'


def ShouldEnableTernCompleter():
  """Returns whether or not the tern completer is 'installed'. That is whether
  or not the tern submodule has a 'node_modules' directory. This is pretty much
  the only way we can know if the user added '--js-completer' on
  install or manually ran 'npm install' in the tern submodule directory."""

  if not PATH_TO_NODE:
    LOGGER.warning( 'Not using Tern completer: unable to find node' )
    return False

  LOGGER.info( 'Using node binary from: %s', PATH_TO_NODE )

  installed = os.path.exists( PATH_TO_TERN_BINARY )

  if not installed:
    LOGGER.info( 'Not using Tern completer: not installed at %s',
                 PATH_TO_TERN_BINARY )
    return False

  return True


def GlobalConfigExists( tern_config ):
  """Returns whether or not the global config file with the supplied path
  exists. This method primarily exists to allow testability and simply returns
  whether the supplied file exists."""
  return os.path.exists( tern_config )


def FindTernProjectFile( starting_directory ):
  """Finds the path to either a Tern project file or the user's global Tern
  configuration file. If found, a tuple is returned containing the path and a
  boolean indicating if the path is to a .tern-project file. If not found,
  returns ( None, False )."""
  for folder in utils.PathsToAllParentFolders( starting_directory ):
    tern_project = os.path.join( folder, '.tern-project' )
    if os.path.exists( tern_project ):
      return tern_project, True

  # As described here: http://ternjs.net/doc/manual.html#server a global
  # .tern-config file is also supported for the Tern server. This can provide
  # meaningful defaults (for libs, and possibly also for require paths), so
  # don't warn if we find one. The point is that if the user has a .tern-config
  # set up, then she has deliberately done so and a ycmd warning is unlikely
  # to be anything other than annoying.
  tern_config = os.path.join( os.path.expanduser( '~' ), '.tern-config' )
  if GlobalConfigExists( tern_config ):
    return tern_config, False

  return None, False


class TernCompleter( Completer ):
  """Completer for JavaScript using tern.js: http://ternjs.net.

  The protocol is defined here: http://ternjs.net/doc/manual.html#protocol"""

  def __init__( self, user_options ):
    super( TernCompleter, self ).__init__( user_options )

    self._server_keep_logfiles = user_options[ 'server_keep_logfiles' ]

    # Used to ensure that starting/stopping of the server is synchronised
    self._server_state_mutex = threading.RLock()

    self._do_tern_project_check = False

    self._server_handle = None
    self._server_port = None
    self._server_stdout = None
    self._server_stderr = None

    self._server_started = False
    self._server_working_dir = None
    self._server_project_file = None


  def _WarnIfMissingTernProject( self, request_data ):
    # The Tern server will operate without a .tern-project file. However, it
    # does not operate optimally, and will likely lead to issues reported that
    # JavaScript completion is not working properly. So we raise a warning if we
    # aren't able to detect some semblance of manual Tern configuration.

    # We do this check after the server has started because the server does
    # have nonzero use without a project file, however limited. We only do this
    # check once, though because the server can only handle one project at a
    # time.
    if not self._ServerIsRunning() or not self._do_tern_project_check:
      return

    self._do_tern_project_check = False
    filepath = request_data[ 'filepath' ]
    project_file, _ = FindTernProjectFile( filepath )
    if not project_file:
      raise RuntimeError( 'Warning: Unable to detect a .tern-project file '
                          'in the hierarchy before ' + filepath +
                          ' and no global .tern-config file was found. '
                          'This is required for accurate JavaScript '
                          'completion. Please see the User Guide for '
                          'details.' )


  def _GetServerAddress( self ):
    return 'http://' + SERVER_HOST + ':' + str( self._server_port )


  def ComputeCandidatesInner( self, request_data ):
    query = {
      'type': 'completions',
      'types': True,
      'docs': True,
      'filter': False,
      'caseInsensitive': True,
      'guess': False,
      'sort': False,
      'includeKeywords': False,
      'expandWordForward': False,
      'omitObjectPrototype': False
    }

    response = self._GetResponse( query,
                                  request_data[ 'start_codepoint' ],
                                  request_data )

    completions = response.get( 'completions', [] )
    tern_start_codepoint = response[ 'start' ][ 'ch' ]

    # Tern returns the range of the word in the file which it is replacing. This
    # may not be the same range that our "completion start column" calculation
    # decided (i.e. it might not strictly be an identifier according to our
    # rules). For example, when completing:
    #
    # require( '|
    #
    # with the cursor on |, tern returns something like 'test' (i.e. including
    # the single-quotes). Single-quotes are not a JavaScript identifier, so
    # should not normally be considered an identifier character, but by using
    # our own start_codepoint calculation, the inserted string would be:
    #
    # require( ''test'
    #
    # which is clearly incorrect. It should be:
    #
    # require( 'test'
    #
    # So, we use the start position that tern tells us to use.
    # We add 1 because tern offsets are 0-based and ycmd offsets are 1-based
    request_data[ 'start_codepoint' ] = tern_start_codepoint + 1

    def BuildDoc( completion ):
      doc = completion.get( 'type', 'Unknown type' )
      if 'doc' in completion:
        doc = doc + '\n' + completion[ 'doc' ]

      return doc

    return [ responses.BuildCompletionData( completion[ 'name' ],
                                            completion.get( 'type', '?' ),
                                            BuildDoc( completion ) )
             for completion in completions ]


  def OnFileReadyToParse( self, request_data ):
    self._StartServer( request_data )

    self._WarnIfMissingTernProject( request_data )

    # Keep tern server up to date with the file data. We do this by sending an
    # empty request just containing the file data
    try:
      self._PostRequest( {}, request_data )
    except Exception:
      # The server might not be ready yet or the server might not be running.
      # in any case, just ignore this we'll hopefully get another parse request
      # soon.
      pass


  def GetSubcommandsMap( self ):
    return {
      'RestartServer':  ( lambda self, request_data, args:
                                         self._RestartServer( request_data ) ),
      'StopServer':     ( lambda self, request_data, args:
                                         self._StopServer() ),
      'GoToDefinition': ( lambda self, request_data, args:
                                         self._GoToDefinition( request_data ) ),
      'GoTo':           ( lambda self, request_data, args:
                                         self._GoToDefinition( request_data ) ),
      'GoToReferences': ( lambda self, request_data, args:
                                         self._GoToReferences( request_data ) ),
      'GetType':        ( lambda self, request_data, args:
                                         self._GetType( request_data ) ),
      'GetDoc':         ( lambda self, request_data, args:
                                         self._GetDoc( request_data ) ),
      'RefactorRename': ( lambda self, request_data, args:
                                         self._Rename( request_data, args ) ),
    }


  def SupportedFiletypes( self ):
    return [ 'javascript' ]


  def DebugInfo( self, request_data ):
    with self._server_state_mutex:
      extras = [
        responses.DebugInfoItem( key = 'configuration file',
                                 value = self._server_project_file ),
        responses.DebugInfoItem( key = 'working directory',
                                 value = self._server_working_dir )
      ]

      tern_server = responses.DebugInfoServer(
        name = 'Tern',
        handle = self._server_handle,
        executable = PATH_TO_TERN_BINARY,
        address = SERVER_HOST,
        port = self._server_port,
        logfiles = [ self._server_stdout, self._server_stderr ],
        extras = extras )

      return responses.BuildDebugInfoResponse( name = 'JavaScript',
                                               servers = [ tern_server ] )


  def Shutdown( self ):
    LOGGER.debug( 'Shutting down Tern server' )
    self._StopServer()


  def ServerIsHealthy( self ):
    if not self._ServerIsRunning():
      return False

    try:
      target = self._GetServerAddress() + '/ping'
      response = requests.get( target )
      return response.status_code == requests.codes.ok
    except requests.ConnectionError:
      return False


  def _PostRequest( self, request, request_data ):
    """Send a raw request with the supplied request block, and
    return the server's response. If the server is not running, it is started.

    This method is useful where the query block is not supplied, i.e. where just
    the files are being updated.

    The request block should contain the optional query block only. The file
    data are added automatically."""

    if not self._ServerIsRunning():
      raise ValueError( 'Not connected to server' )

    def MakeIncompleteFile( name, file_data ):
      return {
        'type': 'full',
        'name': name,
        'text': file_data[ 'contents' ],
      }

    file_data = request_data.get( 'file_data', {} )

    full_request = {
      'files': [ MakeIncompleteFile( x, file_data[ x ] )
                 for x in iterkeys( file_data )
                 if 'javascript' in file_data[ x ][ 'filetypes' ] ],
    }
    full_request.update( request )

    response = requests.post( self._GetServerAddress(),
                              json = full_request )

    if response.status_code != requests.codes.ok:
      raise RuntimeError( response.text )

    return response.json()


  def _GetResponse( self, query, codepoint, request_data ):
    """Send a standard file/line request with the supplied query block, and
    return the server's response. If the server is not running, it is started.

    This method should be used for almost all requests. The exception is when
    just updating file data in which case _PostRequest should be used directly.

    The query block should contain the type and any parameters. The files,
    position, etc. are added automatically.

    NOTE: the |codepoint| parameter is usually the current cursor position,
    though it should be the "completion start column" codepoint for completion
    requests."""

    def MakeTernLocation( request_data ):
      return {
        'line': request_data[ 'line_num' ] - 1,
        'ch':   codepoint - 1
      }

    full_query = {
      'file':              request_data[ 'filepath' ],
      'end':               MakeTernLocation( request_data ),
      'lineCharPositions': True,
    }
    full_query.update( query )

    return self._PostRequest( { 'query': full_query }, request_data )


  def _ServerPathToAbsolute( self, path ):
    """Given a path returned from the tern server, return it as an absolute
    path. In particular, if the path is a relative path, return an absolute path
    assuming that it is relative to the working directory of the Tern server
    (which is the location of the .tern-project file if there is one)."""
    if os.path.isabs( path ):
      return path

    return os.path.join( self._server_working_dir, path )


  def _SetServerProjectFileAndWorkingDirectory( self, request_data ):
    filepath = request_data[ 'filepath' ]
    self._server_project_file, is_project = FindTernProjectFile( filepath )
    working_dir = request_data.get( 'working_dir',
                                    utils.GetCurrentDirectory() )
    if not self._server_project_file:
      LOGGER.warning( 'No .tern-project file detected: %s', filepath )
      self._server_working_dir = working_dir
    else:
      LOGGER.info( 'Detected Tern configuration file at: %s',
                   self._server_project_file )
      self._server_working_dir = (
        os.path.dirname( self._server_project_file ) if is_project else
        working_dir )
    LOGGER.info( 'Tern paths are relative to: %s', self._server_working_dir )


  def _StartServer( self, request_data ):
    with self._server_state_mutex:
      if self._server_started:
        return

      self._server_started = True

      LOGGER.info( 'Starting Tern server...' )

      self._SetServerProjectFileAndWorkingDirectory( request_data )

      self._server_port = utils.GetUnusedLocalhostPort()

      command = [ PATH_TO_NODE,
                  PATH_TO_TERN_BINARY,
                  '--port',
                  str( self._server_port ),
                  '--host',
                  SERVER_HOST,
                  '--persistent',
                  '--no-port-file' ]

      if LOGGER.isEnabledFor( logging.DEBUG ):
        command.append( '--verbose' )

      LOGGER.debug( 'Starting tern with the following command: %s', command )

      self._server_stdout = utils.CreateLogfile(
          LOGFILE_FORMAT.format( port = self._server_port, std = 'stdout' ) )

      self._server_stderr = utils.CreateLogfile(
          LOGFILE_FORMAT.format( port = self._server_port, std = 'stderr' ) )

      # We need to open a pipe to stdin or the Tern server is killed.
      # See https://github.com/ternjs/tern/issues/740#issuecomment-203979749
      # For unknown reasons, this is only needed on Windows and for Python
      # 3.4+ on other platforms.
      with utils.OpenForStdHandle( self._server_stdout ) as stdout:
        with utils.OpenForStdHandle( self._server_stderr ) as stderr:
          self._server_handle = utils.SafePopen(
            command,
            stdin = PIPE,
            stdout = stdout,
            stderr = stderr,
            cwd = self._server_working_dir )

      if self._ServerIsRunning():
        LOGGER.info( 'Tern Server started with pid %d listening on port %d',
                     self._server_handle.pid, self._server_port )
        LOGGER.info( 'Tern Server log files are %s and %s',
                     self._server_stdout, self._server_stderr )

        self._do_tern_project_check = True
      else:
        LOGGER.warning( 'Tern server did not start successfully' )


  def _RestartServer( self, request_data ):
    with self._server_state_mutex:
      self._StopServer()
      self._StartServer( request_data )


  def _StopServer( self ):
    with self._server_state_mutex:
      if self._ServerIsRunning():
        LOGGER.info( 'Stopping Tern server with PID %s',
                     self._server_handle.pid )
        self._server_handle.terminate()
        try:
          utils.WaitUntilProcessIsTerminated( self._server_handle,
                                              timeout = 5 )
          LOGGER.info( 'Tern server stopped' )
        except RuntimeError:
          LOGGER.exception( 'Error while stopping Tern server' )

      self._CleanUp()


  def _CleanUp( self ):
    utils.CloseStandardStreams( self._server_handle )

    self._do_tern_project_check = False

    self._server_handle = None
    self._server_port = None
    if not self._server_keep_logfiles:
      if self._server_stdout:
        utils.RemoveIfExists( self._server_stdout )
        self._server_stdout = None
      if self._server_stderr:
        utils.RemoveIfExists( self._server_stderr )
        self._server_stderr = None

    self._server_started = False
    self._server_working_dir = None
    self._server_project_file = None


  def _ServerIsRunning( self ):
    return utils.ProcessIsRunning( self._server_handle )


  def _GetType( self, request_data ):
    query = {
      'type': 'type',
    }

    response = self._GetResponse( query,
                                  request_data[ 'column_codepoint' ],
                                  request_data )

    return responses.BuildDisplayMessageResponse( response[ 'type' ] )


  def _GetDoc( self, request_data ):
    # Note: we use the 'type' request because this is the best
    # way to get the name, type and doc string. The 'documentation' request
    # doesn't return the 'name' (strangely), wheras the 'type' request returns
    # the same docs with extra info.
    query = {
      'type':      'type',
      'docFormat': 'full',
      'types':      True
    }

    response = self._GetResponse( query,
                                  request_data[ 'column_codepoint' ],
                                  request_data )

    doc_string = 'Name: {name}\nType: {type}\n\n{doc}'.format(
        name = response.get( 'name', 'Unknown' ),
        type = response.get( 'type', 'Unknown' ),
        doc  = response.get( 'doc', 'No documentation available' ) )

    return responses.BuildDetailedInfoResponse( doc_string )


  def _GoToDefinition( self, request_data ):
    query = {
      'type': 'definition',
    }

    response = self._GetResponse( query,
                                  request_data[ 'column_codepoint' ],
                                  request_data )

    filepath = self._ServerPathToAbsolute( response[ 'file' ] )
    return responses.BuildGoToResponseFromLocation(
      _BuildLocation(
        GetFileLines( request_data, filepath ),
        filepath,
        response[ 'start' ][ 'line' ],
        response[ 'start' ][ 'ch' ] ) )


  def _GoToReferences( self, request_data ):
    query = {
      'type': 'refs',
    }

    response = self._GetResponse( query,
                                  request_data[ 'column_codepoint' ],
                                  request_data )

    def BuildRefResponse( ref ):
      filepath = self._ServerPathToAbsolute( ref[ 'file' ] )
      return responses.BuildGoToResponseFromLocation(
        _BuildLocation( GetFileLines( request_data, filepath ),
          filepath,
          ref[ 'start' ][ 'line' ],
          ref[ 'start' ][ 'ch' ] ) )

    return [ BuildRefResponse( ref ) for ref in response[ 'refs' ] ]


  def _Rename( self, request_data, args ):
    if len( args ) != 1:
      raise ValueError( 'Please specify a new name to rename it to.\n'
                        'Usage: RefactorRename <new name>' )

    query = {
      'type': 'rename',
      'newName': args[ 0 ],
    }

    response = self._GetResponse( query,
                                  request_data[ 'column_codepoint' ],
                                  request_data )

    # Tern response format:
    # 'changes': [
    #     {
    #         'file' (potentially relative path)
    #         'start' {
    #             'line'
    #             'ch' (codepoint offset)
    #         }
    #         'end' {
    #             'line'
    #             'ch' (codepoint offset)
    #         }
    #         'text'
    #     }
    # ]

    # ycmd response format:
    #
    # {
    #     'fixits': [
    #         'chunks': (list<Chunk>) [
    #             {
    #                  'replacement_text',
    #                  'range' (Range) {
    #                      'start_' (Location): {
    #                          'line_number_',
    #                          'column_number_', (byte offset)
    #                          'filename_' (note: absolute path!)
    #                      },
    #                      'end_' (Location): {
    #                          'line_number_',
    #                          'column_number_', (byte offset)
    #                          'filename_' (note: absolute path!)
    #                      }
    #                  }
    #              }
    #         ],
    #         'location' (Location) {
    #              'line_number_',
    #              'column_number_',
    #              'filename_' (note: absolute path!)
    #         }
    #
    #     ]
    # }


    def BuildRange( file_contents, filename, start, end ):
      return responses.Range(
        _BuildLocation( file_contents,
                        filename,
                        start[ 'line' ],
                        start[ 'ch' ] ),
        _BuildLocation( file_contents,
                        filename,
                        end[ 'line' ],
                        end[ 'ch' ] ) )


    def BuildFixItChunk( change ):
      filepath = self._ServerPathToAbsolute( change[ 'file' ] )
      file_contents = GetFileLines( request_data, filepath )
      return responses.FixItChunk(
        change[ 'text' ],
        BuildRange( file_contents,
                    filepath,
                    change[ 'start' ],
                    change[ 'end' ] ) )


    # From an API perspective, Refactor and FixIt are the same thing - it just
    # applies a set of changes to a set of files. So we re-use all of the
    # existing FixIt infrastructure.
    return responses.BuildFixItResponse( [
      responses.FixIt(
        responses.Location( request_data[ 'line_num' ],
                            request_data[ 'column_num' ],
                            request_data[ 'filepath' ] ),
        [ BuildFixItChunk( x ) for x in response[ 'changes' ] ] ) ] )


def _BuildLocation( file_contents, filename, line, ch ):
  # tern returns codepoint offsets, but we need byte offsets, so we must
  # convert
  return responses.Location(
    line = line + 1,
    column = utils.CodepointOffsetToByteOffset( file_contents[ line ],
                                                ch + 1 ),
    filename = os.path.realpath( filename ) )
