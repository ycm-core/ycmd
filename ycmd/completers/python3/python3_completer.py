import os
import time
import logging
import subprocess
from ycmd import utils
from ycmd.completers.completer import Completer
from ycmd import responses
import requests
import urlparse

DEFAULT_PYTHON3_PATH = "/usr/bin/python3"
JEDI_SERVER_PATH = os.path.join(
    # dirname of this script
    os.path.dirname(os.path.abspath(__file__)),
    "jedi_server.py"
    )

class Python3Completer( Completer ):
  subcommands = {
    'StartServer': ( lambda self, request_data: self._StartServer(
        request_data ) ),
    'StopServer': ( lambda self, request_data: self._StopServer() ),
    'RestartServer': ( lambda self, request_data: self._RestartServer(
        request_data ) ),
    'ServerTerminated': ( lambda self, request_data:
        self.ServerTerminated() ),
    'DebugInfo': ( lambda self, request_data: self.DebugInfo( 
        request_data ) ),
    'GoToDefinition': ( lambda self, request_data: self._GoToDefinition(
        request_data ) ),
    'GoToDeclaration': ( lambda self, request_data: self._GoToDefinition(
        request_data ) ),
    'GoTo': ( lambda self, request_data: self._GoToImplementation(
        request_data, True ) ),
  }

  def __init__( self, user_options ):
    super( Python3Completer, self ).__init__( user_options )
    self.python3_path = user_options.get( 'path_to_python_iterprteter' )
    if not self.python3_path:
      if os.path.exists(DEFAULT_PYTHON3_PATH):
        self.python3_path = DEFAULT_PYTHON3_PATH
      else:
        raise RuntimeError("Python3 interpreter wasn't found. You should "
            "set 'g:ycm_path_to_python_iterpreter' variable to use this completer")

    self._logger = logging.getLogger( __name__ )
    self._jedi_port = None
    self.user_options = user_options
    self._jedi_phandle = None

  def OnFileReadyToParse( self, request_data ):
    if not self._jedi_port:
      self._StartServer( request_data )
      return

  def Shutdown( self ):
    if not self.ServerTerminated():
      self._StopServer()

  def _ChooseJediServerPort( self ):
    self._jedi_port = int( self.user_options.get( 'jedi_server_port',
                                                       0 ) )
    if not self._jedi_port:
        self._jedi_port = utils.GetUnusedLocalhostPort()
    self._logger.info( u'using port {0}'.format( self._jedi_port ) )

  def _StartServer( self, request_data ):
    self._logger.info( 'startup' )
    self._ChooseJediServerPort()
    command = ' '.join( ( self.python3_path, 
                          JEDI_SERVER_PATH,
                          '-p',
                          str(self._jedi_port) ) )
    filename_format = os.path.join( utils.PathToTempDir(),
                                    u'jedi_server_{port}_{std}.log' )

    self._filename_stdout = filename_format.format(
        port = self._jedi_port, std = 'stdout' )
    self._filename_stderr = filename_format.format(
        port = self._jedi_port, std = 'stderr' )


    with open( self._filename_stderr, 'w' ) as fstderr:
      with open( self._filename_stdout, 'w' ) as fstdout:
        self._jedi_phandle = utils.SafePopen(
            command, stdout = fstdout, stderr = fstderr, shell = True )
    self._logger.info( 'Starting Python3Completer server' )

  def _StopServer( self ):
    self._jedi_phandle.kill()

    self._jedi_port = None
    self._jedi_phandle = None
    if ( not self.user_options[ 'server_keep_logfiles' ] ):
      os.unlink( self._filename_stdout );
      os.unlink( self._filename_stderr );
    self._logger.info( 'Stopping Python3Completer server' )

  def _RestartServer ( self, request_data ):
    if not self.ServerTerminated:
      self._StopServer()
    return self._StartServer( request_data )

  def ServerTerminated( self ):
    """ Check if the server process has already terminated. """
    return ( self._jedi_phandle is not None and
             self._jedi_phandle.poll() is not None )

  def DebugInfo( self, request_data ):
    if not self.ServerTerminated():
      return ( 'Python3Completer Server running at: {0}\n'
               'Python3Completer logfiles:\n{1}\n{2}' ).format(
                   self._ServerLocation(),
                   self._filename_stdout,
                   self._filename_stderr )
    else:
      return 'Python3Completer Server is not running'

  def SupportedFiletypes( self ):
    """ Just python """
    return [ 'python' ]


  def ComputeCandidatesInner( self, request_data ):
    completions = self._GetCompletions( request_data )
    return [ responses.BuildCompletionData(
                utils.ToUtf8IfNeeded( completion['name'] ),
                utils.ToUtf8IfNeeded( completion['description'] ),
                utils.ToUtf8IfNeeded( completion['docstring'] ) )
             for completion in completions ]

  def DefinedSubcommands( self ):
    return Python3Completer.subcommands.keys()

  def OnUserCommand( self, arguments, request_data ):
    if not arguments:
      raise ValueError( self.UserCommandsHelpMessage() )

    command = arguments[ 0 ]
    if command in Python3Completer.subcommands:
      command_lamba = Python3Completer.subcommands[ command ]
      return command_lamba( self, request_data )
    else:
      raise ValueError( self.UserCommandsHelpMessage() )

  def _GetCompletions( self, request_data ):
    parameters = self._DefaultParameters( request_data )
    completions = self._GetResponse( '/getcompletions', parameters )
    return completions if completions != None else []

  def _GoToDefinition( self, request_data ):
    parameters = self._DefaultParameters( request_data )
    definitions = self._GetResponse('/gotodefinition', parameters)
    if definitions:
      return self._BuildGoToResponse( definitions )
    else:
      raise RuntimeError( 'Can\'t jump to definition.' )


  def _GoToDeclaration( self, request_data ):
    parameters = self._DefaultParameters( request_data )
    definitions = self._GetResponse('/gotodeclaration', parameters)
    if definitions:
      return self._BuildGoToResponse( definitions )
    else:
      raise RuntimeError( 'Can\'t jump to declaration.' )


  def _GetResponse( self, handler, parameters = {}, silent = False ):
    """ Handle communication with server """
    target = urlparse.urljoin( self._ServerLocation(), handler )
    response = requests.post( target, data = parameters )
    return response.json()

  def _ServerLocation( self ):
      return "http://localhost:{port}".format( port = self._jedi_port )

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

  def _BuildGoToResponse( self, definition_list ):
    if len( definition_list ) == 1:
      definition = definition_list[ 0 ]
      if definition['in_builtin_module']:
        if definition['is_keyword']:
          raise RuntimeError(
                      'Cannot get the definition of Python keywords.' )
        else:
          raise RuntimeError( 'Builtin modules cannot be displayed.' )
      else:
        return responses.BuildGoToResponse( definition['module_path'],
                                            definition['line'],
                                            definition['column'] + 1 )
    else:
      # multiple definitions
      defs = []
      for definition in definition_list:
        if definition['in_builtin_module']:
          defs.append( responses.BuildDescriptionOnlyGoToResponse(
                       'Builtin ' + definition['description'] ) )
        else:
          defs.append(
            responses.BuildGoToResponse( definition['module_path'],
                                         definition['line'],
                                         definition['column'] + 1,
                                         definition['description'] ) )
      return defs
