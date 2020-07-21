# Copyright (C) 2020 ycmd contributors
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

import os
import pytest
import sys
import time

from contextlib import contextmanager
from ycmd.tests.test_utils import ( BuildRequest,
                                    ClearCompletionsCache,
                                    IgnoreExtraConfOutsideTestsFolder,
                                    IsolatedApp,
                                    WaitUntilCompleterServerReady,
                                    StopCompleterServer,
                                    SetUpApp )

shared_app = None
# map of 'app' to filepaths
shared_filepaths = {}
shared_log_indexes = {}


@pytest.fixture( scope='package', autouse=True )
def set_up_shared_app():
  global shared_app, shared_filepaths
  shared_app = SetUpApp()
  yield
  for filepath in shared_filepaths.get( shared_app, [] ):
    StopCompleterServer( shared_app, 'cs', filepath )



@pytest.fixture
def app( request ):
  which = request.param[ 0 ]
  assert which == 'isolated' or which == 'shared'
  if which == 'isolated':
    custom_options = request.param[ 1 ]
    with IsolatedApp( custom_options ) as app:
      yield app
      # Shutdown the isolated app
      for filepath in shared_filepaths.get( app, [] ):
        StopCompleterServer( app, 'cs', filepath )

  else:
    global shared_app
    ClearCompletionsCache()
    with IgnoreExtraConfOutsideTestsFolder():
      yield shared_app


"""Defines a decorator to be attached to tests of this package. This decorator
passes the shared ycmd application as a parameter."""
SharedYcmd = pytest.mark.parametrize(
    # Name of the fixture/function argument
    'app',
    # Fixture parameters, passed to app() as request.param
    [ ( 'shared', ) ],
    # Non-empty ids makes fixture parameters visible in pytest verbose output
    ids = [ '' ],
    # Execute the fixture, instead of passing parameters directly to the
    # function argument
    indirect = True )


def IsolatedYcmd( custom_options = {} ):
  """Defines a decorator to be attached to tests of this package. This decorator
  passes a unique ycmd application as a parameter. It should be used on tests
  that change the server state in a irreversible way (ex: a semantic subserver
  is stopped or restarted) or expect a clean state (ex: no semantic subserver
  started, no .ycm_extra_conf.py loaded, etc). Use the optional parameter
  |custom_options| to give additional options and/or override the default ones.

  Example usage:

    from ycmd.tests.python import IsolatedYcmd

    @IsolatedYcmd( { 'python_binary_path': '/some/path' } )
    def CustomPythonBinaryPath_test( app ):
      ...
  """
  return pytest.mark.parametrize(
      # Name of the fixture/function argument
      'app',
      # Fixture parameters, passed to app() as request.param
      [ ( 'isolated', custom_options ) ],
      # Non-empty ids makes fixture parameters visible in pytest verbose output
      ids = [ '' ],
      # Execute the fixture, instead of passing parameters directly to the
      # function argument
      indirect = True )


def GetDebugInfo( app, filepath ):
  """ TODO: refactor here and in clangd test to common util """
  request_data = BuildRequest( filetype = 'cs', filepath = filepath )
  return app.post_json( '/debug_info', request_data ).json


def ReadFile( filepath, fileposition ):
  with open( filepath, encoding = 'utf8' ) as f:
    if fileposition:
      f.seek( fileposition )
    return f.read(), f.tell()


def GetDiagnostics( app, filepath ):
  contents, _ = ReadFile( filepath, 0 )

  event_data = BuildRequest( filepath = filepath,
                             event_name = 'FileReadyToParse',
                             filetype = 'cs',
                             contents = contents )

  return app.post_json( '/event_notification', event_data ).json


@contextmanager
def WrapOmniSharpServer( app, filepath ):
  global shared_filepaths
  global shared_log_indexes

  if filepath not in shared_filepaths.setdefault( app, [] ):
    # StartCompleterServer( app, 'cs', filepath )
    GetDiagnostics( app, filepath )
    shared_filepaths[ app ].append( filepath )
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
        sys.stdout.write( f'Logfile { logfile }:\n\n' )
        sys.stdout.write( log_content )
        sys.stdout.write( '\n' )


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
