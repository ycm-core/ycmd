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
# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa

from contextlib import contextmanager
import functools
import os
import sys
import time

from ycmd.tests.test_utils import ( BuildRequest,
                                    ClearCompletionsCache,
                                    IgnoreExtraConfOutsideTestsFolder,
                                    IsolatedApp,
                                    SetUpApp,
                                    # StartCompleterServer,
                                    StopCompleterServer,
                                    WaitUntilCompleterServerReady )

shared_app = None
shared_filepaths = []
shared_log_indexes = {}


def PathToTestFile( *args ):
  dir_of_current_script = os.path.dirname( os.path.abspath( __file__ ) )
  return os.path.join( dir_of_current_script, 'testdata', *args )


def setUpPackage():
  """Initializes the ycmd server as a WebTest application that will be shared
  by all tests using the SharedYcmd decorator in this package. Additional
  configuration that is common to these tests, like starting a semantic
  subserver, should be done here."""
  global shared_app

  shared_app = SetUpApp()


def tearDownPackage():
  """Cleans up the tests using the SharedYcmd decorator in this package. It is
  executed once after running all the tests in the package."""
  global shared_app, shared_filepaths

  for filepath in shared_filepaths:
    StopCompleterServer( shared_app, 'cs', filepath )


def GetDebugInfo( app, filepath ):
  """ TODO: refactor here and in clangd test to common util """
  request_data = BuildRequest( filetype = 'cs', filepath = filepath )
  return app.post_json( '/debug_info', request_data ).json


def GetDiagnostics( app, filepath ):
  contents, _ = ReadFile( filepath, 0 )

  event_data = BuildRequest( filepath = filepath,
                             event_name = 'FileReadyToParse',
                             filetype = 'cs',
                             contents = contents )

  return app.post_json( '/event_notification', event_data ).json


def ReadFile( filepath, fileposition ):
  with open( filepath, encoding = 'utf8' ) as f:
    if fileposition:
      f.seek( fileposition )
    return f.read(), f.tell()


def WaitUntilCsCompleterIsReady( app, filepath ):
  WaitUntilCompleterServerReady( app, 'cs' )
  # Omnisharp isn't ready when it says it is, so wait until Omnisharp returns
  # at least one diagnostic multiple times.
  success_count = 0
  for reraise_error in [ False ] * 39 + [ True ]:
    try:
      if len( GetDiagnostics( app, filepath ) ) == 0:
        raise RuntimeError( "No diagnostic" )
      success_count += 1
      if success_count > 2:
        break
    except Exception:
      success_count = 0
      if reraise_error:
        raise

    time.sleep( .5 )
  else:
    raise RuntimeError( "Never was ready" )


@contextmanager
def WrapOmniSharpServer( app, filepath ):
  global shared_filepaths
  global shared_log_indexes

  if filepath not in shared_filepaths:
    # StartCompleterServer( app, 'cs', filepath )
    GetDiagnostics( app, filepath )
    shared_filepaths.append( filepath )
    WaitUntilCsCompleterIsReady( app, filepath )

  logfiles = []
  response = GetDebugInfo( app, filepath )
  for server in response[ 'completer' ][ 'servers' ]:
    logfiles.extend( server[ 'logfiles' ] )

  try:
    yield
  finally:
    for logfile in logfiles:
      if os.path.isfile( logfile ):
        log_content, log_end_position = ReadFile(
            logfile, shared_log_indexes.get( logfile, 0 ) )
        shared_log_indexes[ logfile ] = log_end_position
        sys.stdout.write( 'Logfile {0}:\n\n'.format( logfile ) )
        sys.stdout.write( log_content )
        sys.stdout.write( '\n' )



def SharedYcmd( test ):
  """Defines a decorator to be attached to tests of this package. This decorator
  passes the shared ycmd application as a parameter.

  Do NOT attach it to test generators but directly to the yielded tests."""
  global shared_app

  @functools.wraps( test )
  def Wrapper( *args, **kwargs ):
    ClearCompletionsCache()
    with IgnoreExtraConfOutsideTestsFolder():
      return test( shared_app, *args, **kwargs )
  return Wrapper


def IsolatedYcmd( custom_options = {} ):
  """Defines a decorator to be attached to tests of this package. This decorator
  passes a unique ycmd application as a parameter. It should be used on tests
  that change the server state in a irreversible way (ex: a semantic subserver
  is stopped or restarted) or expect a clean state (ex: no semantic subserver
  started, no .ycm_extra_conf.py loaded, etc). Use the optional parameter
  |custom_options| to give additional options and/or override the default ones.

  Do NOT attach it to test generators but directly to the yielded tests.

  Example usage:

    from ycmd.tests.cs import IsolatedYcmd

    @IsolatedYcmd( { 'server_keep_logfiles': 1 } )
    def CustomServerKeepLogfiles_test( app ):
      ...
  """
  def Decorator( test ):
    @functools.wraps( test )
    def Wrapper( *args, **kwargs ):
      with IsolatedApp( custom_options ) as app:
        # We are not wrapping test() in a try/finally block and calling
        # StopCompleterServer() needs the correct filename to stop the
        # specific server corresponding to the solution file.
        #
        # Leaving the file unspecified in StopCompleterServer() starts
        # a new server only to shut it down right afterwards.
        # Instead, we leave the server running and let tearDownPackage()
        # stop all the running servers by running through all shared_filepaths.
        test( app, *args, **kwargs )
    return Wrapper
  return Decorator
