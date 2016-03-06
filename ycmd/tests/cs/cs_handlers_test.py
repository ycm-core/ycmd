# Copyright (C) 2015 ycmd contributors
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
from future.utils import PY2

from ..handlers_test import Handlers_test
from ycmd.utils import OnTravis, OnWindows
import time
from contextlib import contextmanager

# If INSTANCE_PER_TEST is set, each test case will start up and shutdown an
# instance of Omnisharp server.  Otherwise - the default - it will reuse the
# Omnisharp instances between individual test cases. Non caching (false) is
# much faster, but test cases are not totally isolated from each other.
# For test case isolation, set to true.
# Reusing Omnisharp instances this way on Windows and Python 3 will randomly
# raise the error "OSError: [WinError 6] The handle is invalid" in tests so
# we set it to true in this case.
INSTANCE_PER_TEST = True if OnWindows() and not PY2 else False


class Cs_Handlers_test( Handlers_test ):

  omnisharp_file_solution = {}
  omnisharp_solution_port = {}
  omnisharp_solution_file = {}

  def __init__( self ):
    self._file = __file__


  def setUp( self ):
    super( Cs_Handlers_test, self ).setUp()
    self._app.post_json(
      '/ignore_extra_conf_file',
      { 'filepath': self._PathToTestFile( '.ycm_extra_conf.py' ) } )


  # See __init__.py for teardownPackage


  @contextmanager
  def _WrapOmniSharpServer( self, filepath ):
    self._SetupOmniSharpServer( filepath )
    yield
    self._TeardownOmniSharpServer( filepath )


  def _SetupOmniSharpServer( self, filepath ):
    solution_path = self._FindOmniSharpSolutionPath( filepath )
    if solution_path in Cs_Handlers_test.omnisharp_solution_port:
      port = Cs_Handlers_test.omnisharp_solution_port[ solution_path ]
      self._SetOmnisharpPort( filepath, port  )
      self._WaitUntilOmniSharpServerReady( filepath )
    else:
      self._StartOmniSharpServer( filepath )
      self._WaitUntilOmniSharpServerReady( filepath )
      port = self._GetOmnisharpPort( filepath )
      Cs_Handlers_test.omnisharp_solution_port[ solution_path ] = port


  def _TeardownOmniSharpServer( self, filepath ):
    if INSTANCE_PER_TEST:
      self._StopOmniSharpServer( filepath )
      try:
        solution = self._FindOmniSharpSolutionPath( filepath )
        del Cs_Handlers_test.omnisharp_solution_port[ solution ]
        del Cs_Handlers_test.omnisharp_solution_file[ solution ]
      except KeyError:
        pass


  def _StartOmniSharpServer( self, filepath ):
    self._app.post_json( '/run_completer_command',
                    self._BuildRequest( completer_target = 'filetype_default',
                                        command_arguments = [ "StartServer" ],
                                        filepath = filepath,
                                        filetype = 'cs' ) )


  def _FindOmniSharpSolutionPath( self, filepath ):
    if filepath in Cs_Handlers_test.omnisharp_file_solution:
      return Cs_Handlers_test.omnisharp_file_solution[ filepath ]

    solution_request = self._BuildRequest(
        completer_target = 'filetype_default',
        filepath = filepath,
        command_arguments = [ "SolutionFile" ],
        filetype = 'cs' )
    solution_path = self._app.post_json( '/run_completer_command',
                                         solution_request ).json
    Cs_Handlers_test.omnisharp_file_solution[ filepath ] = solution_path
    Cs_Handlers_test.omnisharp_solution_file[ solution_path ] = filepath

    return solution_path


  def _SetOmnisharpPort( self, filepath, port ):
    command_arguments = [ 'SetOmnisharpPort', port ]
    self._app.post_json( '/run_completer_command',
                    self._BuildRequest( completer_target = 'filetype_default',
                                        command_arguments = command_arguments,
                                        filepath = filepath,
                                        filetype = 'cs' ) )


  def _GetOmnisharpPort( self, filepath ):
    request = self._BuildRequest( completer_target = 'filetype_default',
                                  command_arguments = [ "GetOmnisharpPort" ],
                                  filepath = filepath,
                                  filetype = 'cs' )
    result = self._app.post_json( '/run_completer_command', request ).json

    return int( result[ "message" ] )


  def _StopOmniSharpServer( self, filepath ):
    self._app.post_json( '/run_completer_command',
                  self._BuildRequest( completer_target = 'filetype_default',
                                      command_arguments = [ 'StopServer' ],
                                      filepath = filepath,
                                      filetype = 'cs' ) )


  def _WaitUntilOmniSharpServerReady( self, filepath ):
    retries = 100
    success = False

    # If running on Travis CI, keep trying forever. Travis will kill the worker
    # after 10 mins if nothing happens.
    while retries > 0 or OnTravis():
      result = self._app.get( '/ready', { 'subserver': 'cs' } ).json
      if result:
        success = True
        break
      request = self._BuildRequest( completer_target = 'filetype_default',
                                    command_arguments = [ 'ServerIsRunning' ],
                                    filepath = filepath,
                                    filetype = 'cs' )
      result = self._app.post_json( '/run_completer_command', request ).json
      if not result:
        raise RuntimeError( "OmniSharp failed during startup." )
      time.sleep( 0.2 )
      retries = retries - 1

    if not success:
      raise RuntimeError( "Timeout waiting for OmniSharpServer" )


def StopAllOmniSharpServers():
  self = Cs_Handlers_test()
  with self.UserOption( 'auto_start_csharp_server', False ):
    with self.UserOption( 'confirm_extra_conf', False ):
      self.setUp()
      while Cs_Handlers_test.omnisharp_solution_port:
        ( solution, port ) = Cs_Handlers_test.omnisharp_solution_port.popitem()
        filepath = Cs_Handlers_test.omnisharp_solution_file[ solution ]
        self._SetOmnisharpPort( filepath, port )
        self._StopOmniSharpServer( filepath )
