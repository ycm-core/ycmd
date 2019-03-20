# Copyright (C) 2013-2018 ycmd contributors
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

from future.utils import iteritems, PY2
from hamcrest import ( assert_that,
                       contains,
                       contains_string,
                       has_entries,
                       has_entry,
                       has_item )
from mock import patch
from webtest import TestApp
import bottle
import contextlib
import nose
import functools
import os
import tempfile
import time
import stat
import shutil
import json

from ycmd import extra_conf_store, handlers, user_options_store
from ycmd.completers.completer import Completer
from ycmd.responses import BuildCompletionData
from ycmd.utils import ( GetCurrentDirectory,
                         OnMac,
                         OnWindows,
                         ToUnicode,
                         WaitUntilProcessIsTerminated )
import ycm_core

try:
  from unittest import skipIf
except ImportError:
  from unittest2 import skipIf

TESTS_DIR = os.path.abspath( os.path.dirname( __file__ ) )

Py2Only = skipIf( not PY2, 'Python 2 only' )
Py3Only = skipIf( PY2, 'Python 3 only' )
WindowsOnly = skipIf( not OnWindows(), 'Windows only' )
ClangOnly = skipIf( not ycm_core.HasClangSupport(),
                    'Only when Clang support available' )
MacOnly = skipIf( not OnMac(), 'Mac only' )
UnixOnly = skipIf( OnWindows(), 'Unix only' )


def BuildRequest( **kwargs ):
  filepath = kwargs[ 'filepath' ] if 'filepath' in kwargs else '/foo'
  contents = kwargs[ 'contents' ] if 'contents' in kwargs else ''
  filetype = kwargs[ 'filetype' ] if 'filetype' in kwargs else 'foo'
  filetypes = kwargs[ 'filetypes' ] if 'filetypes' in kwargs else [ filetype ]

  request = {
    'line_num': 1,
    'column_num': 1,
    'filepath': filepath,
    'file_data': {
      filepath: {
        'contents': contents,
        'filetypes': filetypes
      }
    }
  }

  for key, value in iteritems( kwargs ):
    if key in [ 'contents', 'filetype', 'filepath' ]:
      continue

    if key in request and isinstance( request[ key ], dict ):
      # allow updating the 'file_data' entry
      request[ key ].update( value )
    else:
      request[ key ] = value

  return request


def CombineRequest( request, data ):
  kwargs = request.copy()
  kwargs.update( data )
  return BuildRequest( **kwargs )


def ErrorMatcher( cls, msg = None ):
  """ Returns a hamcrest matcher for a server exception response """
  entry = { 'exception': has_entry( 'TYPE', cls.__name__ ) }

  if msg:
    entry.update( { 'message': msg } )

  return has_entries( entry )


def CompletionEntryMatcher( insertion_text,
                            extra_menu_info = None,
                            extra_params = None ):
  match = { 'insertion_text': insertion_text }

  if extra_menu_info:
    match.update( { 'extra_menu_info': extra_menu_info } )

  if extra_params:
    match.update( extra_params )

  return has_entries( match )


def MessageMatcher( msg ):
  return has_entry( 'message', contains_string( msg ) )


def LocationMatcher( filepath, line_num, column_num ):
  return has_entries( {
    'line_num': line_num,
    'column_num': column_num,
    'filepath': filepath
  } )


def RangeMatcher( filepath, start, end ):
  return has_entries( {
    'start': LocationMatcher( filepath, *start ),
    'end': LocationMatcher( filepath, *end ),
  } )


def ChunkMatcher( replacement_text, start, end ):
  return has_entries( {
    'replacement_text': replacement_text,
    'range': has_entries( {
      'start': start,
      'end': end
    } )
  } )


def LineColMatcher( line, col ):
  return has_entries( {
    'line_num': line,
    'column_num': col
  } )


def CompleterProjectDirectoryMatcher( project_directory ):
  return has_entry(
    'completer',
    has_entry( 'servers', contains(
      has_entry( 'extras', has_item(
        has_entries( {
          'key': 'Project Directory',
          'value': project_directory,
        } )
      ) )
    ) )
  )


@contextlib.contextmanager
def PatchCompleter( completer, filetype ):
  user_options = handlers._server_state._user_options
  with patch.dict( 'ycmd.handlers._server_state._filetype_completers',
                   { filetype: completer( user_options ) } ):
    yield


@contextlib.contextmanager
def CurrentWorkingDirectory( path ):
  old_cwd = GetCurrentDirectory()
  os.chdir( path )
  try:
    yield old_cwd
  finally:
    os.chdir( old_cwd )


# The "exe" suffix is needed on Windows and not harmful on other platforms.
@contextlib.contextmanager
def TemporaryExecutable( extension = '.exe' ):
  with tempfile.NamedTemporaryFile( prefix = 'Temp',
                                    suffix = extension ) as executable:
    os.chmod( executable.name, stat.S_IXUSR )
    yield executable.name


@contextlib.contextmanager
def TemporarySymlink( source, link ):
  os.symlink( source, link )
  try:
    yield
  finally:
    os.remove( link )


def SetUpApp( custom_options = {} ):
  bottle.debug( True )
  options = user_options_store.DefaultOptions()
  options.update( custom_options )
  handlers.UpdateUserOptions( options )
  extra_conf_store.Reset()
  return TestApp( handlers.app )


@contextlib.contextmanager
def IgnoreExtraConfOutsideTestsFolder():
  with patch( 'ycmd.utils.IsRootDirectory',
              lambda path, parent: path in [ parent, TESTS_DIR ] ):
    yield


@contextlib.contextmanager
def IsolatedApp( custom_options = {} ):
  old_server_state = handlers._server_state
  old_extra_conf_store_state = extra_conf_store.Get()
  old_options = user_options_store.GetAll()
  try:
    with IgnoreExtraConfOutsideTestsFolder():
      yield SetUpApp( custom_options )
  finally:
    handlers._server_state = old_server_state
    extra_conf_store.Set( old_extra_conf_store_state )
    user_options_store.SetAll( old_options )


def StartCompleterServer( app, filetype, filepath = '/foo' ):
  app.post_json( '/run_completer_command',
                 BuildRequest( command_arguments = [ 'RestartServer' ],
                               filetype = filetype,
                               filepath = filepath ) )


def StopCompleterServer( app, filetype, filepath = '/foo' ):
  app.post_json( '/run_completer_command',
                 BuildRequest( command_arguments = [ 'StopServer' ],
                               filetype = filetype,
                               filepath = filepath ),
                 expect_errors = True )


def WaitUntilCompleterServerReady( app, filetype, timeout = 30 ):
  expiration = time.time() + timeout
  while True:
    if time.time() > expiration:
      raise RuntimeError( 'Waited for the {0} subserver to be ready for '
                          '{1} seconds, aborting.'.format( filetype, timeout ) )

    if app.get( '/ready', { 'subserver': filetype } ).json:
      return

    time.sleep( 0.1 )


def MockProcessTerminationTimingOut( handle, timeout = 5 ):
  WaitUntilProcessIsTerminated( handle, timeout )
  raise RuntimeError( 'Waited process to terminate for {0} seconds, '
                      'aborting.'.format( timeout ) )


def ClearCompletionsCache():
  """Invalidates cached completions for completers stored in the server state:
  filetype completers and general completers (identifier, filename, and
  ultisnips completers).

  This function is used when sharing the application between tests so that
  no completions are cached by previous tests."""
  server_state = handlers._server_state
  for completer in server_state.GetLoadedFiletypeCompleters():
    completer._completions_cache.Invalidate()
  general_completer = server_state.GetGeneralCompleter()
  for completer in general_completer._all_completers:
    completer._completions_cache.Invalidate()


class DummyCompleter( Completer ):
  def __init__( self, user_options ):
    super( DummyCompleter, self ).__init__( user_options )

  def SupportedFiletypes( self ):
    return []


  def ComputeCandidatesInner( self, request_data ):
    return [ BuildCompletionData( candidate )
             for candidate in self.CandidatesList() ]


  # This method is here for testing purpose, so it can be mocked during tests
  def CandidatesList( self ):
    return []


def ExpectedFailure( reason, *exception_matchers ):
  """Defines a decorator to be attached to tests. This decorator
  marks the test as being known to fail, e.g. where documenting or exercising
  known incorrect behaviour.

  The parameters are:
    - |reason| a textual description of the reason for the known issue. This
               is used for the skip reason
    - |exception_matchers| additional arguments are hamcrest matchers to apply
                 to the exception thrown. If the matchers don't match, then the
                 test is marked as error, with the original exception.

  If the test fails (for the correct reason), then it is marked as skipped.
  If it fails for any other reason, it is marked as failed.
  If the test passes, then it is also marked as failed."""
  def decorator( test ):
    @functools.wraps( test )
    def Wrapper( *args, **kwargs ):
      try:
        test( *args, **kwargs )
      except Exception as test_exception:
        # Ensure that we failed for the right reason
        test_exception_message = ToUnicode( test_exception )
        try:
          for matcher in exception_matchers:
            assert_that( test_exception_message, matcher )
        except AssertionError:
          # Failed for the wrong reason!
          import traceback
          print( 'Test failed for the wrong reason: ' + traceback.format_exc() )
          # Real failure reason is the *original* exception, we're only trapping
          # and ignoring the exception that is expected.
          raise test_exception

        # Failed for the right reason
        raise nose.SkipTest( reason )
      else:
        raise AssertionError( 'Test was expected to fail: {0}'.format(
          reason ) )
    return Wrapper

  return decorator


@contextlib.contextmanager
def TemporaryTestDir():
  """Context manager to execute a test with a temporary workspace area. The
  workspace is deleted upon completion of the test. This is useful particularly
  for testing project detection (e.g. compilation databases, etc.), by ensuring
  that the directory is empty and not affected by the user's filesystem."""
  tmp_dir = tempfile.mkdtemp()
  try:
    yield tmp_dir
  finally:
    shutil.rmtree( tmp_dir )


def WithRetry( test ):
  """Decorator to be applied to tests that retries the test over and over
  until it passes or |timeout| seconds have passed."""

  if 'YCM_TEST_NO_RETRY' in os.environ:
    return test

  @functools.wraps( test )
  def wrapper( *args, **kwargs ):
    expiry = time.time() + 30
    while True:
      try:
        test( *args, **kwargs )
        return
      except Exception as test_exception:
        if time.time() > expiry:
          raise
        print( 'Test failed, retrying: {0}'.format( str( test_exception ) ) )
        time.sleep( 0.25 )
  return wrapper


@contextlib.contextmanager
def TemporaryClangProject( tmp_dir, compile_commands ):
  """Context manager to create a compilation database in a directory and delete
  it when the test completes. |tmp_dir| is the directory in which to create the
  database file (typically used in conjunction with |TemporaryTestDir|) and
  |compile_commands| is a python object representing the compilation database.

  e.g.:
    with TemporaryTestDir() as tmp_dir:
      database = [
        {
          'directory': os.path.join( tmp_dir, dir ),
          'command': compiler_invocation,
          'file': os.path.join( tmp_dir, dir, filename )
        },
        ...
      ]
      with TemporaryClangProject( tmp_dir, database ):
        <test here>

  The context manager does not yield anything.
  """
  path = os.path.join( tmp_dir, 'compile_commands.json' )

  with open( path, 'w' ) as f:
    f.write( ToUnicode( json.dumps( compile_commands, indent=2 ) ) )

  try:
    yield
  finally:
    os.remove( path )
