# Copyright (C) 2017-2018 ycmd contributors
# encoding: utf-8
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

from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import division
# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa

import time
import json
from future.utils import iterkeys
from hamcrest import ( assert_that,
                       contains,
                       contains_inanyorder,
                       empty,
                       equal_to,
                       has_entries,
                       has_item )
from nose.tools import eq_

from ycmd.tests.java import ( DEFAULT_PROJECT_DIR,
                              IsolatedYcmd,
                              PathToTestFile,
                              PollForMessages,
                              PollForMessagesTimeoutException,
                              SharedYcmd,
                              StartJavaCompleterServerInDirectory )

from ycmd.tests.test_utils import ( BuildRequest, LocationMatcher, RangeMatcher,
                                    WithRetry )
from ycmd.utils import ReadFile, StartThread
from ycmd.completers import completer

from pprint import pformat
from mock import patch
from ycmd.completers.language_server import language_server_protocol as lsp
from ycmd import handlers



def ProjectPath( *args ):
  return PathToTestFile( DEFAULT_PROJECT_DIR,
                         'src',
                         'com',
                         'test',
                         *args )


ProjectRoot = PathToTestFile( DEFAULT_PROJECT_DIR )
InternalNonProjectFile = PathToTestFile( DEFAULT_PROJECT_DIR, 'test.java' )
TestFactory = ProjectPath( 'TestFactory.java' )
TestLauncher = ProjectPath( 'TestLauncher.java' )
TestWidgetImpl = ProjectPath( 'TestWidgetImpl.java' )
youcompleteme_Test = PathToTestFile( DEFAULT_PROJECT_DIR,
                                     'src',
                                     'com',
                                     'youcompleteme',
                                     'Test.java' )

DIAG_MATCHERS_PER_FILE = {
  ProjectRoot: [],
  InternalNonProjectFile: [],
  TestFactory: contains_inanyorder(
    has_entries( {
      'kind': 'WARNING',
      'text': 'The value of the field TestFactory.Bar.testString is not used',
      'location': LocationMatcher( TestFactory, 15, 19 ),
      'location_extent': RangeMatcher( TestFactory, ( 15, 19 ), ( 15, 29 ) ),
      'ranges': contains( RangeMatcher( TestFactory, ( 15, 19 ), ( 15, 29 ) ) ),
      'fixit_available': False
    } ),
    has_entries( {
      'kind': 'ERROR',
      'text': 'Wibble cannot be resolved to a type',
      'location': LocationMatcher( TestFactory, 18, 24 ),
      'location_extent': RangeMatcher( TestFactory, ( 18, 24 ), ( 18, 30 ) ),
      'ranges': contains( RangeMatcher( TestFactory, ( 18, 24 ), ( 18, 30 ) ) ),
      'fixit_available': False
    } ),
    has_entries( {
      'kind': 'ERROR',
      'text': 'Wibble cannot be resolved to a variable',
      'location': LocationMatcher( TestFactory, 19, 15 ),
      'location_extent': RangeMatcher( TestFactory, ( 19, 15 ), ( 19, 21 ) ),
      'ranges': contains( RangeMatcher( TestFactory, ( 19, 15 ), ( 19, 21 ) ) ),
      'fixit_available': False
    } ),
    has_entries( {
      'kind': 'ERROR',
      'text': 'Type mismatch: cannot convert from int to boolean',
      'location': LocationMatcher( TestFactory, 27, 10 ),
      'location_extent': RangeMatcher( TestFactory, ( 27, 10 ), ( 27, 16 ) ),
      'ranges': contains( RangeMatcher( TestFactory, ( 27, 10 ), ( 27, 16 ) ) ),
      'fixit_available': False
    } ),
    has_entries( {
      'kind': 'ERROR',
      'text': 'Type mismatch: cannot convert from int to boolean',
      'location': LocationMatcher( TestFactory, 30, 10 ),
      'location_extent': RangeMatcher( TestFactory, ( 30, 10 ), ( 30, 16 ) ),
      'ranges': contains( RangeMatcher( TestFactory, ( 30, 10 ), ( 30, 16 ) ) ),
      'fixit_available': False
    } ),
    has_entries( {
      'kind': 'ERROR',
      'text': 'The method doSomethingVaguelyUseful() in the type '
              'AbstractTestWidget is not applicable for the arguments '
              '(TestFactory.Bar)',
      'location': LocationMatcher( TestFactory, 30, 23 ),
      'location_extent': RangeMatcher( TestFactory, ( 30, 23 ), ( 30, 47 ) ),
      'ranges': contains( RangeMatcher( TestFactory, ( 30, 23 ), ( 30, 47 ) ) ),
      'fixit_available': False
    } ),
  ),
  TestWidgetImpl: contains_inanyorder(
    has_entries( {
      'kind': 'WARNING',
      'text': 'The value of the local variable a is not used',
      'location': LocationMatcher( TestWidgetImpl, 15, 9 ),
      'location_extent': RangeMatcher( TestWidgetImpl, ( 15, 9 ), ( 15, 10 ) ),
      'ranges': contains( RangeMatcher( TestWidgetImpl,
                                        ( 15, 9 ),
                                        ( 15, 10 ) ) ),
      'fixit_available': False
    } ),
    has_entries( {
      'kind': 'ERROR',
      'text': 'ISR cannot be resolved to a variable',
      'location': LocationMatcher( TestWidgetImpl, 34, 12 ),
      'location_extent': RangeMatcher( TestWidgetImpl, ( 34, 12 ), ( 34, 15 ) ),
      'ranges': contains( RangeMatcher( TestWidgetImpl,
                                        ( 34, 12 ),
                                        ( 34, 15 ) ) ),
      'fixit_available': False
    } ),
    has_entries( {
      'kind': 'ERROR',
      'text': 'Syntax error, insert ";" to complete BlockStatements',
      'location': LocationMatcher( TestWidgetImpl, 34, 12 ),
      'location_extent': RangeMatcher( TestWidgetImpl, ( 34, 12 ), ( 34, 15 ) ),
      'ranges': contains( RangeMatcher( TestWidgetImpl,
                                        ( 34, 12 ),
                                        ( 34, 15 ) ) ),
      'fixit_available': False
    } ),
  ),
  TestLauncher: contains_inanyorder(
    has_entries( {
      'kind': 'ERROR',
      'text': 'The type new TestLauncher.Launchable(){} must implement the '
              'inherited abstract method TestLauncher.Launchable.launch('
              'TestFactory)',
      'location': LocationMatcher( TestLauncher, 28, 16 ),
      'location_extent': RangeMatcher( TestLauncher, ( 28, 16 ), ( 28, 28 ) ),
      'ranges': contains( RangeMatcher( TestLauncher,
                                        ( 28, 16 ),
                                        ( 28, 28 ) ) ),
      'fixit_available': False
    } ),
    has_entries( {
      'kind': 'ERROR',
      'text': 'The method launch() of type new TestLauncher.Launchable(){} '
              'must override or implement a supertype method',
      'location': LocationMatcher( TestLauncher, 30, 19 ),
      'location_extent': RangeMatcher( TestLauncher, ( 30, 19 ), ( 30, 27 ) ),
      'ranges': contains( RangeMatcher( TestLauncher,
                                        ( 30, 19 ),
                                        ( 30, 27 ) ) ),
      'fixit_available': False
    } ),
    has_entries( {
      'kind': 'ERROR',
      'text': 'Cannot make a static reference to the non-static field factory',
      'location': LocationMatcher( TestLauncher, 31, 32 ),
      'location_extent': RangeMatcher( TestLauncher, ( 31, 32 ), ( 31, 39 ) ),
      'ranges': contains( RangeMatcher( TestLauncher,
                                        ( 31, 32 ),
                                        ( 31, 39 ) ) ),
      'fixit_available': False
    } ),
  ),
  youcompleteme_Test: contains(
    has_entries( {
      'kind': 'ERROR',
      'text': 'The method doUnicødeTes() in the type Test is not applicable '
              'for the arguments (String)',
      'location': LocationMatcher( youcompleteme_Test, 13, 10 ),
      'location_extent': RangeMatcher( youcompleteme_Test,
                                       ( 13, 10 ),
                                       ( 13, 23 ) ),
      'ranges': contains( RangeMatcher( youcompleteme_Test,
                                        ( 13, 10 ),
                                        ( 13, 23 ) ) ),
      'fixit_available': False
    } ),
  ),
}


def _WaitForDiagnosticsForFile( app,
                                filepath,
                                contents,
                                diags_filepath,
                                diags_are_ready = lambda d: True,
                                **kwargs ):
  diags = None
  try:
    for message in PollForMessages( app,
                                    { 'filepath': filepath,
                                      'contents': contents },
                                    **kwargs ):
      if ( 'diagnostics' in message and
           message[ 'filepath' ] == diags_filepath ):
        print( 'Message {0}'.format( pformat( message ) ) )
        diags = message[ 'diagnostics' ]
        if diags_are_ready( diags ):
          return diags

      # Eventually PollForMessages will throw a timeout exception and we'll fail
      # if we don't see the diagnostics go empty
  except PollForMessagesTimeoutException as e:
    raise AssertionError(
      '{0}. Timed out waiting for diagnostics for file {1}. '.format(
        e,
        diags_filepath )
    )

  return diags


def _WaitForDiagnosticsToBeReady( app, filepath, contents, **kwargs ):
  results = None
  for tries in range( 0, 60 ):
    event_data = BuildRequest( event_name = 'FileReadyToParse',
                               contents = contents,
                               filepath = filepath,
                               filetype = 'java',
                               **kwargs )

    results = app.post_json( '/event_notification', event_data ).json

    if results:
      break

    time.sleep( 0.5 )

  return results


@WithRetry
@SharedYcmd
def FileReadyToParse_Diagnostics_Simple_test( app ):
  filepath = ProjectPath( 'TestFactory.java' )
  contents = ReadFile( filepath )

  # It can take a while for the diagnostics to be ready
  results = _WaitForDiagnosticsToBeReady( app, filepath, contents )
  print( 'completer response: {0}'.format( pformat( results ) ) )

  assert_that( results, DIAG_MATCHERS_PER_FILE[ filepath ] )


@IsolatedYcmd()
def FileReadyToParse_Diagnostics_FileNotOnDisk_test( app ):
  StartJavaCompleterServerInDirectory( app,
                                       PathToTestFile( DEFAULT_PROJECT_DIR ) )

  contents = '''
    package com.test;
    class Test {
      public String test
    }
  '''
  filepath = ProjectPath( 'Test.java' )

  event_data = BuildRequest( event_name = 'FileReadyToParse',
                             contents = contents,
                             filepath = filepath,
                             filetype = 'java' )

  results = app.post_json( '/event_notification', event_data ).json

  # This is a new file, so the diagnostics can't possibly be available when the
  # initial parse request is sent. We receive these asynchronously.
  eq_( results, {} )

  diag_matcher = contains( has_entries( {
    'kind': 'ERROR',
    'text': 'Syntax error, insert ";" to complete ClassBodyDeclarations',
    'location': LocationMatcher( filepath, 4, 21 ),
    'location_extent': RangeMatcher( filepath, ( 4, 21 ), ( 4, 25 ) ),
    'ranges': contains( RangeMatcher( filepath, ( 4, 21 ), ( 4, 25 ) ) ),
    'fixit_available': False
  } ) )

  # Poll until we receive the diags
  for message in PollForMessages( app,
                                  { 'filepath': filepath,
                                    'contents': contents } ):
    if 'diagnostics' in message and message[ 'filepath' ] == filepath:
      print( 'Message {0}'.format( pformat( message ) ) )
      assert_that( message, has_entries( {
        'diagnostics': diag_matcher,
        'filepath': filepath
      } ) )
      break

  # Now confirm that we _also_ get these from the FileReadyToParse request
  for tries in range( 0, 60 ):
    results = app.post_json( '/event_notification', event_data ).json
    if results:
      break
    time.sleep( 0.5 )

  print( 'completer response: {0}'.format( pformat( results ) ) )

  assert_that( results, diag_matcher )


@WithRetry
@SharedYcmd
def Poll_Diagnostics_ProjectWide_Eclipse_test( app ):
  filepath = TestLauncher
  contents = ReadFile( filepath )

  # Poll until we receive _all_ the diags asynchronously
  to_see = sorted( iterkeys( DIAG_MATCHERS_PER_FILE ) )
  seen = {}

  try:
    for message in PollForMessages( app,
                                    { 'filepath': filepath,
                                      'contents': contents } ):
      print( 'Message {0}'.format( pformat( message ) ) )
      if 'diagnostics' in message:
        seen[ message[ 'filepath' ] ] = True
        if message[ 'filepath' ] not in DIAG_MATCHERS_PER_FILE:
          raise AssertionError(
            'Received diagnostics for unexpected file {0}. '
            'Only expected {1}'.format( message[ 'filepath' ], to_see ) )
        assert_that( message, has_entries( {
          'diagnostics': DIAG_MATCHERS_PER_FILE[ message[ 'filepath' ] ],
          'filepath': message[ 'filepath' ]
        } ) )

      if sorted( iterkeys( seen ) ) == to_see:
        break
      else:
        print( 'Seen diagnostics for {0}, still waiting for {1}'.format(
          json.dumps( sorted( iterkeys( seen ) ), indent=2 ),
          json.dumps( [ x for x in to_see if x not in seen ], indent=2 ) ) )

      # Eventually PollForMessages will throw a timeout exception and we'll fail
      # if we don't see all of the expected diags
  except PollForMessagesTimeoutException as e:
    raise AssertionError(
      str( e ) +
      'Timed out waiting for full set of diagnostics. '
      'Expected to see diags for {0}, but only saw {1}.'.format(
        json.dumps( to_see, indent=2 ),
        json.dumps( sorted( iterkeys( seen ) ), indent=2 ) ) )


@IsolatedYcmd()
def Poll_Diagnostics_ChangeFileContents_test( app ):
  StartJavaCompleterServerInDirectory( app,
                                       PathToTestFile( DEFAULT_PROJECT_DIR ) )

  filepath = youcompleteme_Test
  old_contents = """package com.youcompleteme;

public class Test {
  public String test;
}"""

  messages_for_filepath = []

  def PollForMessagesInAnotherThread( filepath, contents ):
    try:
      for message in PollForMessages( app,
                                      { 'filepath': filepath,
                                        'contents': contents } ):
        if 'filepath' in message and message[ 'filepath' ] == filepath:
          messages_for_filepath.append( message )
    except PollForMessagesTimeoutException:
      pass

  StartThread( PollForMessagesInAnotherThread, filepath, old_contents )

  new_contents = """package com.youcompleteme;

public class Test {
  public String test;
  public String test;
}"""

  event_data = BuildRequest( event_name = 'FileReadyToParse',
                             contents = new_contents,
                             filepath = filepath,
                             filetype = 'java' )
  app.post_json( '/event_notification', event_data ).json

  expiration = time.time() + 10
  while True:
    try:
      assert_that(
        messages_for_filepath,
        has_item( has_entries( {
          'filepath': filepath,
          'diagnostics': contains(
            has_entries( {
              'kind': 'ERROR',
              'text': 'Duplicate field Test.test',
              'location': LocationMatcher( youcompleteme_Test, 4, 17 ),
              'location_extent': RangeMatcher( youcompleteme_Test,
                                               ( 4, 17 ),
                                               ( 4, 21 ) ),
              'ranges': contains( RangeMatcher( youcompleteme_Test,
                                                ( 4, 17 ),
                                                ( 4, 21 ) ) ),
              'fixit_available': False
            } ),
            has_entries( {
              'kind': 'ERROR',
              'text': 'Duplicate field Test.test',
              'location': LocationMatcher( youcompleteme_Test, 5, 17 ),
              'location_extent': RangeMatcher( youcompleteme_Test,
                                               ( 5, 17 ),
                                               ( 5, 21 ) ),
              'ranges': contains( RangeMatcher( youcompleteme_Test,
                                                ( 5, 17 ),
                                                ( 5, 21 ) ) ),
              'fixit_available': False
            } )
          )
        } ) )
      )
      break
    except AssertionError:
      if time.time() > expiration:
        raise

      time.sleep( 0.25 )


@IsolatedYcmd()
def FileReadyToParse_ServerNotReady_test( app ):
  filepath = TestFactory
  contents = ReadFile( filepath )

  StartJavaCompleterServerInDirectory( app, ProjectPath() )

  completer = handlers._server_state.GetFiletypeCompleter( [ 'java' ] )

  # It can take a while for the diagnostics to be ready
  for tries in range( 0, 60 ):
    event_data = BuildRequest( event_name = 'FileReadyToParse',
                               contents = contents,
                               filepath = filepath,
                               filetype = 'java' )

    results = app.post_json( '/event_notification', event_data ).json

    if results:
      break

    time.sleep( 0.5 )

  # To make the test fair, we make sure there are some results prior to the
  # 'server not running' call
  assert results

  # Call the FileReadyToParse handler but pretend that the server isn't running
  with patch.object( completer, 'ServerIsHealthy', return_value = False ):
    event_data = BuildRequest( event_name = 'FileReadyToParse',
                               contents = contents,
                               filepath = filepath,
                               filetype = 'java' )
    results = app.post_json( '/event_notification', event_data ).json
    assert_that( results, empty() )


@IsolatedYcmd()
def FileReadyToParse_ChangeFileContents_test( app ):
  filepath = TestFactory
  contents = ReadFile( filepath )

  StartJavaCompleterServerInDirectory( app, ProjectPath() )

  # It can take a while for the diagnostics to be ready
  for tries in range( 0, 60 ):
    event_data = BuildRequest( event_name = 'FileReadyToParse',
                               contents = contents,
                               filepath = filepath,
                               filetype = 'java' )

    results = app.post_json( '/event_notification', event_data ).json

    if results:
      break

    time.sleep( 0.5 )

  # To make the test fair, we make sure there are some results prior to the
  # 'server not running' call
  assert results

  # Call the FileReadyToParse handler but pretend that the server isn't running
  contents = 'package com.test; class TestFactory {}'
  # It can take a while for the diagnostics to be ready
  event_data = BuildRequest( event_name = 'FileReadyToParse',
                             contents = contents,
                             filepath = filepath,
                             filetype = 'java' )

  app.post_json( '/event_notification', event_data )

  diags = None
  try:
    for message in PollForMessages( app,
                                    { 'filepath': filepath,
                                      'contents': contents } ):
      print( 'Message {0}'.format( pformat( message ) ) )
      if 'diagnostics' in message and message[ 'filepath' ]  == filepath:
        diags = message[ 'diagnostics' ]
        if not diags:
          break

      # Eventually PollForMessages will throw a timeout exception and we'll fail
      # if we don't see the diagnostics go empty
  except PollForMessagesTimeoutException as e:
    raise AssertionError(
      '{0}. Timed out waiting for diagnostics to clear for updated file. '
      'Expected to see none, but diags were: {1}'.format( e, diags ) )

  assert_that( diags, empty() )

  # Close the file (ensuring no exception)
  event_data = BuildRequest( event_name = 'BufferUnload',
                             contents = contents,
                             filepath = filepath,
                             filetype = 'java' )
  result = app.post_json( '/event_notification', event_data ).json
  assert_that( result, equal_to( {} ) )

  # Close the file again, someone erroneously (ensuring no exception)
  event_data = BuildRequest( event_name = 'BufferUnload',
                             contents = contents,
                             filepath = filepath,
                             filetype = 'java' )
  result = app.post_json( '/event_notification', event_data ).json
  assert_that( result, equal_to( {} ) )


@IsolatedYcmd()
def FileReadyToParse_ChangeFileContentsFileData_test( app ):
  filepath = TestFactory
  contents = ReadFile( filepath )
  unsaved_buffer_path = TestLauncher
  file_data = {
    unsaved_buffer_path: {
      'contents': 'package com.test; public class TestLauncher {}',
      'filetypes': [ 'java' ],
    }
  }

  StartJavaCompleterServerInDirectory( app, ProjectPath() )

  # It can take a while for the diagnostics to be ready
  results = _WaitForDiagnosticsToBeReady( app,
                                          filepath,
                                          contents )
  assert results

  # Check that we have diagnostics for the saved file
  diags = _WaitForDiagnosticsForFile( app,
                                      filepath,
                                      contents,
                                      unsaved_buffer_path,
                                      lambda d: d )
  assert_that( diags, DIAG_MATCHERS_PER_FILE[ unsaved_buffer_path ] )

  # Now update the unsaved file with new contents
  event_data = BuildRequest( event_name = 'FileReadyToParse',
                             contents = contents,
                             filepath = filepath,
                             filetype = 'java',
                             file_data = file_data )
  app.post_json( '/event_notification', event_data )

  # Check that we have no diagnostics for the dirty file
  diags = _WaitForDiagnosticsForFile( app,
                                      filepath,
                                      contents,
                                      unsaved_buffer_path,
                                      lambda d: not d )
  assert_that( diags, empty() )

  # Now send the request again, but don't include the unsaved file. It should be
  # read from disk, casuing the diagnostics for that file to appear.
  event_data = BuildRequest( event_name = 'FileReadyToParse',
                             contents = contents,
                             filepath = filepath,
                             filetype = 'java' )
  app.post_json( '/event_notification', event_data )

  # Check that we now have diagnostics for the previously-dirty file
  diags = _WaitForDiagnosticsForFile( app,
                                      filepath,
                                      contents,
                                      unsaved_buffer_path,
                                      lambda d: d )

  assert_that( diags, DIAG_MATCHERS_PER_FILE[ unsaved_buffer_path ] )


@WithRetry
@SharedYcmd
def OnBufferUnload_ServerNotRunning_test( app ):
  filepath = TestFactory
  contents = ReadFile( filepath )
  completer = handlers._server_state.GetFiletypeCompleter( [ 'java' ] )

  with patch.object( completer, 'ServerIsHealthy', return_value = False ):
    event_data = BuildRequest( event_name = 'BufferUnload',
                               contents = contents,
                               filepath = filepath,
                               filetype = 'java' )
    result = app.post_json( '/event_notification', event_data ).json
    assert_that( result, equal_to( {} ) )


@IsolatedYcmd()
def PollForMessages_InvalidUri_test( app, *args ):
  StartJavaCompleterServerInDirectory(
    app,
    PathToTestFile( 'simple_eclipse_project' ) )

  filepath = TestFactory
  contents = ReadFile( filepath )

  with patch(
    'ycmd.completers.language_server.language_server_protocol.UriToFilePath',
    side_effect = lsp.InvalidUriException ):

    for tries in range( 0, 5 ):
      response = app.post_json( '/receive_messages',
                                BuildRequest(
                                  filetype = 'java',
                                  filepath = filepath,
                                  contents = contents ) ).json
      if response is True:
        break
      elif response is False:
        raise AssertionError( 'Message poll was aborted unexpectedly' )
      elif 'diagnostics' in response:
        raise AssertionError( 'Did not expect diagnostics when file paths '
                              'are invalid' )

      time.sleep( 0.5 )

  assert_that( response, equal_to( True ) )


@IsolatedYcmd()
@patch.object( completer, 'MESSAGE_POLL_TIMEOUT', 2 )
def PollForMessages_ServerNotRunning_test( app ):
  StartJavaCompleterServerInDirectory(
    app,
    PathToTestFile( 'simple_eclipse_project' ) )

  filepath = TestFactory
  contents = ReadFile( filepath )
  app.post_json(
    '/run_completer_command',
    BuildRequest(
      filetype = 'java',
      command_arguments = [ 'StopServer' ],
    ),
  )

  response = app.post_json( '/receive_messages',
                            BuildRequest(
                              filetype = 'java',
                              filepath = filepath,
                              contents = contents ) ).json

  assert_that( response, equal_to( False ) )


@IsolatedYcmd()
def PollForMessages_AbortedWhenServerDies_test( app ):
  StartJavaCompleterServerInDirectory(
    app,
    PathToTestFile( 'simple_eclipse_project' ) )

  filepath = TestFactory
  contents = ReadFile( filepath )

  state = {
    'aborted': False
  }

  def AwaitMessages():
    max_tries = 20
    for tries in range( 0, max_tries ):
      response = app.post_json( '/receive_messages',
                                BuildRequest(
                                  filetype = 'java',
                                  filepath = filepath,
                                  contents = contents ) ).json
      if response is False:
        state[ 'aborted' ] = True
        return

    raise AssertionError( 'The poll request was not aborted in {} tries'.format(
      max_tries ) )

  message_poll_task = StartThread( AwaitMessages )

  app.post_json(
    '/run_completer_command',
    BuildRequest(
      filetype = 'java',
      command_arguments = [ 'StopServer' ],
    ),
  )

  message_poll_task.join()
  eq_( state[ 'aborted' ], True )
