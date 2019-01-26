# Copyright (C) 2017 ycmd contributors
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

from mock import patch
from nose.tools import eq_
from hamcrest import ( all_of,
                       assert_that,
                       calling,
                       empty,
                       ends_with,
                       equal_to,
                       contains,
                       has_entries,
                       has_entry,
                       has_items,
                       has_key,
                       is_not,
                       raises )

from ycmd.completers.language_server import language_server_completer as lsc
from ycmd.completers.language_server.language_server_completer import (
    NO_HOVER_INFORMATION )
from ycmd.completers.language_server import language_server_protocol as lsp
from ycmd.tests.language_server import MockConnection
from ycmd.request_wrap import RequestWrap
from ycmd.tests.test_utils import ( BuildRequest,
                                    ChunkMatcher,
                                    DummyCompleter,
                                    LocationMatcher,
                                    RangeMatcher )
from ycmd.tests.language_server import IsolatedYcmd, PathToTestFile
from ycmd import handlers, utils, responses
import os


class MockCompleter( lsc.LanguageServerCompleter, DummyCompleter ):
  def __init__( self, custom_options = {} ):
    user_options = handlers._server_state._user_options.copy()
    user_options.update( custom_options )
    super( MockCompleter, self ).__init__( user_options )

    self._connection = MockConnection()
    self._started = False

  def Language( self ):
    return 'foo'


  def StartServer( self, request_data, **kwargs ):
    self._started = True
    return True


  def GetConnection( self ):
    return self._connection


  def HandleServerCommand( self, request_data, command ):
    return super( MockCompleter, self ).HandleServerCommand( request_data,
                                                             command )


  def ServerIsHealthy( self ):
    return self._started


@IsolatedYcmd( { 'global_ycm_extra_conf':
                 PathToTestFile( 'extra_confs', 'settings_extra_conf.py' ) } )
def LanguageServerCompleter_ExtraConf_ServerReset_test( app ):
  filepath = PathToTestFile( 'extra_confs', 'foo' )
  app.post_json( '/event_notification',
                 BuildRequest( filepath = filepath,
                               filetype = 'foo',
                               contents = '',
                               event_name = 'FileReadyToParse' ) )

  request_data = RequestWrap( BuildRequest() )

  completer = MockCompleter()

  eq_( None, completer._project_directory )

  completer.OnFileReadyToParse( request_data )
  assert_that( completer._project_directory, is_not( None ) )
  assert_that( completer._settings, is_not( empty() ) )

  completer.ServerReset()
  assert_that( completer._settings, empty() )
  eq_( None, completer._project_directory )


@IsolatedYcmd( { 'global_ycm_extra_conf':
                 PathToTestFile( 'extra_confs', 'empty_extra_conf.py' ) } )
def LanguageServerCompleter_ExtraConf_FileEmpty_test( app ):
  filepath = PathToTestFile( 'extra_confs', 'foo' )

  completer = MockCompleter()
  request_data = RequestWrap( BuildRequest( filepath = filepath,
                                            filetype = 'ycmtest',
                                            contents = '' ) )
  completer.OnFileReadyToParse( request_data )
  eq_( {}, completer._settings )

  # Simulate receipt of response and initialization complete
  initialize_response = {
    'result': {
      'capabilities': {}
    }
  }
  completer._HandleInitializeInPollThread( initialize_response )
  eq_( {}, completer._settings )
  # We shouldn't have used the extra_conf path for the project directory, but
  # that _also_ happens to be the path of the file we opened.
  eq_( PathToTestFile( 'extra_confs' ), completer._project_directory )


@IsolatedYcmd( { 'global_ycm_extra_conf':
                 PathToTestFile( 'extra_confs',
                                 'settings_none_extra_conf.py' ) } )
def LanguageServerCompleter_ExtraConf_SettingsReturnsNone_test( app ):
  filepath = PathToTestFile( 'extra_confs', 'foo' )

  completer = MockCompleter()
  request_data = RequestWrap( BuildRequest( filepath = filepath,
                                            filetype = 'ycmtest',
                                            contents = '' ) )
  completer.OnFileReadyToParse( request_data )
  eq_( {}, completer._settings )
  # We shouldn't have used the extra_conf path for the project directory, but
  # that _also_ happens to be the path of the file we opened.
  eq_( PathToTestFile( 'extra_confs' ), completer._project_directory )


@IsolatedYcmd( { 'global_ycm_extra_conf':
                 PathToTestFile( 'extra_confs', 'settings_extra_conf.py' ) } )
def LanguageServerCompleter_ExtraConf_SettingValid_test( app ):
  filepath = PathToTestFile( 'extra_confs', 'foo' )

  completer = MockCompleter()
  request_data = RequestWrap( BuildRequest( filepath = filepath,
                                            filetype = 'ycmtest',
                                            working_dir = PathToTestFile(),
                                            contents = '' ) )

  eq_( {}, completer._settings )
  completer.OnFileReadyToParse( request_data )
  eq_( { 'java.rename.enabled' : False }, completer._settings )
  # We use the working_dir not the path to the global extra conf (which is
  # ignored)
  eq_( PathToTestFile(), completer._project_directory )


@IsolatedYcmd( { 'extra_conf_globlist': [ '!*' ] } )
def LanguageServerCompleter_ExtraConf_NoExtraConf_test( app ):
  filepath = PathToTestFile( 'extra_confs', 'foo' )

  completer = MockCompleter()
  request_data = RequestWrap( BuildRequest( filepath = filepath,
                                            filetype = 'ycmtest',
                                            working_dir = PathToTestFile(),
                                            contents = '' ) )

  eq_( {}, completer._settings )
  completer.OnFileReadyToParse( request_data )
  eq_( {}, completer._settings )

  # Simulate receipt of response and initialization complete
  initialize_response = {
    'result': {
      'capabilities': {}
    }
  }
  completer._HandleInitializeInPollThread( initialize_response )
  eq_( {}, completer._settings )
  # We use the client working directory
  eq_( PathToTestFile(), completer._project_directory )


@IsolatedYcmd( { 'extra_conf_globlist': [ '*' ] } )
def LanguageServerCompleter_ExtraConf_NonGlobal_test( app ):
  filepath = PathToTestFile( 'project',
                             'settings_extra_conf',
                             'foo' )

  completer = MockCompleter()
  request_data = RequestWrap( BuildRequest( filepath = filepath,
                                            filetype = 'ycmtest',
                                            # ignored; ycm conf path used
                                            working_dir = 'ignore_this',
                                            contents = '' ) )

  eq_( {}, completer._settings )
  completer.OnFileReadyToParse( request_data )
  eq_( { 'java.rename.enabled' : False }, completer._settings )

  # Simulate receipt of response and initialization complete
  initialize_response = {
    'result': {
      'capabilities': {}
    }
  }
  completer._HandleInitializeInPollThread( initialize_response )
  eq_( PathToTestFile( 'project', 'settings_extra_conf' ),
       completer._project_directory )


def LanguageServerCompleter_Initialise_Aborted_test():
  completer = MockCompleter()
  request_data = RequestWrap( BuildRequest() )

  with patch.object( completer.GetConnection(),
                     'ReadData',
                     side_effect = RuntimeError ):

    assert_that( completer.ServerIsReady(), equal_to( False ) )

    completer.OnFileReadyToParse( request_data )

    with patch.object( completer, '_HandleInitializeInPollThread' ) as handler:
      completer.GetConnection().run()
      handler.assert_not_called()

    assert_that( completer._initialize_event.is_set(), equal_to( False ) )
    assert_that( completer.ServerIsReady(), equal_to( False ) )


  with patch.object( completer, 'ServerIsHealthy', return_value = False ):
    assert_that( completer.ServerIsReady(), equal_to( False ) )


def LanguageServerCompleter_Initialise_Shutdown_test():
  completer = MockCompleter()
  request_data = RequestWrap( BuildRequest() )

  with patch.object( completer.GetConnection(),
                     'ReadData',
                     side_effect = lsc.LanguageServerConnectionStopped ):

    assert_that( completer.ServerIsReady(), equal_to( False ) )

    completer.OnFileReadyToParse( request_data )

    with patch.object( completer, '_HandleInitializeInPollThread' ) as handler:
      completer.GetConnection().run()
      handler.assert_not_called()

    assert_that( completer._initialize_event.is_set(), equal_to( False ) )
    assert_that( completer.ServerIsReady(), equal_to( False ) )


  with patch.object( completer, 'ServerIsHealthy', return_value = False ):
    assert_that( completer.ServerIsReady(), equal_to( False ) )


def LanguageServerCompleter_GoToDeclaration_test():
  if utils.OnWindows():
    filepath = 'C:\\test.test'
    uri = 'file:///c:/test.test'
  else:
    filepath = '/test.test'
    uri = 'file:/test.test'

  contents = 'line1\nline2\nline3'

  completer = MockCompleter()
  request_data = RequestWrap( BuildRequest(
    filetype = 'ycmtest',
    filepath = filepath,
    contents = contents
  ) )

  @patch.object( completer, 'ServerIsReady', return_value = True )
  def Test( response, checker, throws, *args ):
    with patch.object( completer.GetConnection(),
                       'GetResponse',
                       return_value = response ):
      if throws:
        assert_that(
          calling( completer.GoToDeclaration ).with_args( request_data ),
          raises( checker )
        )
      else:
        result = completer.GoToDeclaration( request_data )
        print( 'Result: {0}'.format( result ) )
        assert_that( result, checker )


  location = {
    'uri': uri,
    'range': {
      'start': { 'line': 0, 'character': 0 },
      'end': { 'line': 0, 'character': 0 },
    }
  }

  goto_response = has_entries( {
    'filepath': filepath,
    'column_num': 1,
    'line_num': 1,
    'description': 'line1'
  } )

  cases = [
    ( { 'result': None }, RuntimeError, True ),
    ( { 'result': location }, goto_response, False ),
    ( { 'result': {} }, RuntimeError, True ),
    ( { 'result': [] }, RuntimeError, True ),
    ( { 'result': [ location ] }, goto_response, False ),
    ( { 'result': [ location, location ] },
      contains( goto_response, goto_response ),
      False ),
  ]

  for response, checker, throws in cases:
    yield Test, response, checker, throws


  with patch(
    'ycmd.completers.language_server.language_server_protocol.UriToFilePath',
    side_effect = lsp.InvalidUriException ):
    yield Test, {
      'result': {
        'uri': uri,
        'range': {
          'start': { 'line': 0, 'character': 0 },
          'end': { 'line': 0, 'character': 0 },
        }
      }
    }, has_entries( {
      'filepath': '',
      'column_num': 1,
      'line_num': 1,
    } ), False

  with patch( 'ycmd.completers.completer_utils.GetFileContents',
              side_effect = lsp.IOError ):
    yield Test, {
      'result': {
        'uri': uri,
        'range': {
          'start': { 'line': 0, 'character': 0 },
          'end': { 'line': 0, 'character': 0 },
        }
      }
    }, has_entries( {
      'filepath': filepath,
      'column_num': 1,
      'line_num': 1,
    } ), False


def GetCompletions_RejectInvalid_test():
  if utils.OnWindows():
    filepath = 'C:\\test.test'
  else:
    filepath = '/test.test'

  contents = 'line1.\nline2.\nline3.'

  request_data = RequestWrap( BuildRequest(
    filetype = 'ycmtest',
    filepath = filepath,
    contents = contents,
    line_num = 1,
    column_num = 7
  ) )

  text_edit = {
    'newText': 'blah',
    'range': {
      'start': { 'line': 0, 'character': 6 },
      'end': { 'line': 0, 'character': 6 },
    }
  }

  assert_that( lsc._GetCompletionItemStartCodepointOrReject( text_edit,
                                                             request_data ),
               equal_to( 7 ) )

  text_edit = {
    'newText': 'blah',
    'range': {
      'start': { 'line': 0, 'character': 6 },
      'end': { 'line': 1, 'character': 6 },
    }
  }

  assert_that(
    calling( lsc._GetCompletionItemStartCodepointOrReject ).with_args(
      text_edit, request_data ),
    raises( lsc.IncompatibleCompletionException ) )

  text_edit = {
    'newText': 'blah',
    'range': {
      'start': { 'line': 0, 'character': 20 },
      'end': { 'line': 0, 'character': 20 },
    }
  }

  assert_that(
    lsc._GetCompletionItemStartCodepointOrReject( text_edit, request_data ),
    equal_to( 7 ) )

  text_edit = {
    'newText': 'blah',
    'range': {
      'start': { 'line': 0, 'character': 6 },
      'end': { 'line': 0, 'character': 5 },
    }
  }

  assert_that(
    lsc._GetCompletionItemStartCodepointOrReject( text_edit, request_data ),
    equal_to( 7 ) )


def WorkspaceEditToFixIt_test():
  if utils.OnWindows():
    filepath = 'C:\\test.test'
    uri = 'file:///c:/test.test'
  else:
    filepath = '/test.test'
    uri = 'file:/test.test'

  contents = 'line1\nline2\nline3'

  request_data = RequestWrap( BuildRequest(
    filetype = 'ycmtest',
    filepath = filepath,
    contents = contents
  ) )


  # We don't support versioned documentChanges
  assert_that( lsc.WorkspaceEditToFixIt( request_data,
                                         { 'documentChanges': [] } ),
               equal_to( None ) )

  workspace_edit = {
    'changes': {
      uri: [
        {
          'newText': 'blah',
          'range': {
            'start': { 'line': 0, 'character': 5 },
            'end': { 'line': 0, 'character': 5 },
          }
        },
      ]
    }
  }

  response = responses.BuildFixItResponse( [
    lsc.WorkspaceEditToFixIt( request_data, workspace_edit, 'test' )
  ] )

  print( 'Response: {0}'.format( response ) )
  print( 'Type Response: {0}'.format( type( response ) ) )

  assert_that(
    response,
    has_entries( {
      'fixits': contains( has_entries( {
        'text': 'test',
        'chunks': contains( ChunkMatcher( 'blah',
                                          LocationMatcher( filepath, 1, 6 ),
                                          LocationMatcher( filepath, 1, 6 ) ) )
      } ) )
    } )
  )


@IsolatedYcmd( { 'extra_conf_globlist': [ '!*' ] } )
def LanguageServerCompleter_DelayedInitialization_test( app ):
  completer = MockCompleter()
  request_data = RequestWrap( BuildRequest( filepath = 'Test.ycmtest' ) )

  with patch.object( completer, '_UpdateServerWithFileContents' ) as update:
    with patch.object( completer, '_PurgeFileFromServer' ) as purge:
      completer.OnFileReadyToParse( request_data )
      completer.OnBufferUnload( request_data )
      update.assert_not_called()
      purge.assert_not_called()

      # Simulate receipt of response and initialization complete
      initialize_response = {
        'result': {
          'capabilities': {}
        }
      }
      completer._HandleInitializeInPollThread( initialize_response )

      update.assert_called_with( request_data )
      purge.assert_called_with( 'Test.ycmtest' )


def LanguageServerCompleter_ShowMessage_test():
  completer = MockCompleter()
  request_data = RequestWrap( BuildRequest() )
  notification = {
    'method': 'window/showMessage',
    'params': {
      'message': 'this is a test'
    }
  }
  assert_that( completer.ConvertNotificationToMessage( request_data,
                                                       notification ),
               has_entries( { 'message': 'this is a test' } ) )


def LanguageServerCompleter_GetCompletions_List_test():
  completer = MockCompleter()
  request_data = RequestWrap( BuildRequest() )

  completion_response = { 'result': [ { 'label': 'test' } ] }

  resolve_responses = [
    { 'result': { 'label': 'test' } },
  ]

  with patch.object( completer, 'ServerIsReady', return_value = True ):
    with patch.object( completer.GetConnection(),
                       'GetResponse',
                       side_effect = [ completion_response ] +
                                     resolve_responses ):
      assert_that( completer.ComputeCandidatesInner( request_data ),
                   has_items( has_entries( { 'insertion_text': 'test' } ) ) )


def LanguageServerCompleter_GetCompletions_UnsupportedKinds_test():
  completer = MockCompleter()
  request_data = RequestWrap( BuildRequest() )

  completion_response = { 'result': [ { 'label': 'test',
                                        'kind': len( lsp.ITEM_KIND ) + 1 } ] }

  resolve_responses = [
    { 'result': { 'label': 'test' } },
  ]

  with patch.object( completer, 'ServerIsReady', return_value = True ):
    with patch.object( completer.GetConnection(),
                       'GetResponse',
                       side_effect = [ completion_response ] +
                                     resolve_responses ):
      assert_that( completer.ComputeCandidatesInner( request_data ),
                   has_items( all_of( has_entry( 'insertion_text', 'test' ),
                                      is_not( has_key( 'kind' ) ) ) ) )


def FindOverlapLength_test():
  tests = [
    ( '', '', 0 ),
    ( 'a', 'a', 1 ),
    ( 'a', 'b', 0 ),
    ( 'abcdef', 'abcdefg', 6 ),
    ( 'abcdefg', 'abcdef', 0 ),
    ( 'aaab', 'aaab', 4 ),
    ( 'abab', 'ab', 2 ),
    ( 'aab', 'caab', 0 ),
    ( 'abab', 'abababab', 4 ),
    ( 'aaab', 'baaa', 1 ),
    ( 'test.', 'test.test', 5 ),
    ( 'test.', 'test', 0 ),
    ( 'test', 'testtest', 4 ),
    ( '', 'testtest', 0 ),
    ( 'test', '', 0 ),
    ( 'Some CoCo', 'CoCo Beans', 4 ),
    ( 'Have some CoCo and CoCo', 'CoCo and CoCo is here.', 13 ),
    ( 'TEST xyAzA', 'xyAzA test', 5 ),
  ]

  def Test( line, text, overlap ):
    assert_that( lsc.FindOverlapLength( line, text ), equal_to( overlap ) )

  for test in tests:
    yield Test, test[ 0 ], test[ 1 ], test[ 2 ]


def LanguageServerCompleter_GetCodeActions_CursorOnEmptyLine_test():
  completer = MockCompleter()
  request_data = RequestWrap( BuildRequest( line_num = 1,
                                            column_num = 1,
                                            contents = '' ) )

  fixit_response = { 'result': [] }

  with patch.object( completer, 'ServerIsReady', return_value = True ):
    with patch.object( completer.GetConnection(),
                       'GetResponse',
                       side_effect = [ fixit_response ] ):
      with patch( 'ycmd.completers.language_server.language_server_protocol.'
                  'CodeAction' ) as code_action:
        assert_that( completer.GetCodeActions( request_data, [] ),
                     has_entry( 'fixits', empty() ) )
        assert_that(
          # Range passed to lsp.CodeAction.
          code_action.call_args[ 0 ][ 2 ],
          has_entries( {
            'start': has_entries( {
              'line': 0,
              'character': 0
            } ),
            'end': has_entries( {
              'line': 0,
              'character': 0
            } )
          } )
        )


def LanguageServerCompleter_Diagnostics_MaxDiagnosticsNumberExceeded_test():
  completer = MockCompleter( { 'max_diagnostics_to_display': 1 } )
  filepath = os.path.realpath( '/foo' )
  uri = lsp.FilePathToUri( filepath )
  request_data = RequestWrap( BuildRequest( line_num = 1,
                                            column_num = 1,
                                            filepath = filepath,
                                            contents = '' ) )
  notification = {
    'jsonrpc': '2.0',
    'method': 'textDocument/publishDiagnostics',
    'params': {
      'uri': uri,
      'diagnostics': [ {
        'range': {
          'start': { 'line': 3, 'character': 10 },
          'end': { 'line': 3, 'character': 11 }
        },
        'severity': 1,
        'message': 'First error'
      }, {
        'range': {
          'start': { 'line': 4, 'character': 7 },
          'end': { 'line': 4, 'character': 13 }
        },
        'severity': 1,
        'message': 'Second error'
      } ]
    }
  }
  completer.GetConnection()._notifications.put( notification )
  completer.HandleNotificationInPollThread( notification )

  with patch.object( completer, 'ServerIsReady', return_value = True ):
    completer.OnFileReadyToParse( request_data )
    # Simulate receipt of response and initialization complete
    initialize_response = {
      'result': {
        'capabilities': {}
      }
    }
    completer._HandleInitializeInPollThread( initialize_response )

    diagnostics = contains(
      has_entries( {
        'kind': equal_to( 'ERROR' ),
        'location': LocationMatcher( filepath, 4, 11 ),
        'location_extent': RangeMatcher( filepath, ( 4, 11 ), ( 4, 12 ) ),
        'ranges': contains(
           RangeMatcher( filepath, ( 4, 11 ), ( 4, 12 ) ) ),
        'text': equal_to( 'First error' ),
        'fixit_available': False
      } ),
      has_entries( {
        'kind': equal_to( 'ERROR' ),
        'location': LocationMatcher( filepath, 1, 1 ),
        'location_extent': RangeMatcher( filepath, ( 1, 1 ), ( 1, 1 ) ),
        'ranges': contains( RangeMatcher( filepath, ( 1, 1 ), ( 1, 1 ) ) ),
        'text': equal_to( 'Maximum number of diagnostics exceeded.' ),
        'fixit_available': False
      } )
    )

    assert_that( completer.OnFileReadyToParse( request_data ), diagnostics )

    assert_that(
      completer.PollForMessages( request_data ),
      contains( has_entries( {
        'diagnostics': diagnostics,
        'filepath': filepath
      } ) )
    )


def LanguageServerCompleter_Diagnostics_NoLimitToNumberOfDiagnostics_test():
  completer = MockCompleter( { 'max_diagnostics_to_display': 0 } )
  filepath = os.path.realpath( '/foo' )
  uri = lsp.FilePathToUri( filepath )
  request_data = RequestWrap( BuildRequest( line_num = 1,
                                            column_num = 1,
                                            filepath = filepath,
                                            contents = '' ) )
  notification = {
    'jsonrpc': '2.0',
    'method': 'textDocument/publishDiagnostics',
    'params': {
      'uri': uri,
      'diagnostics': [ {
        'range': {
          'start': { 'line': 3, 'character': 10 },
          'end': { 'line': 3, 'character': 11 }
        },
        'severity': 1,
        'message': 'First error'
      }, {
        'range': {
          'start': { 'line': 4, 'character': 7 },
          'end': { 'line': 4, 'character': 13 }
        },
        'severity': 1,
        'message': 'Second error'
      } ]
    }
  }
  completer.GetConnection()._notifications.put( notification )
  completer.HandleNotificationInPollThread( notification )

  with patch.object( completer, 'ServerIsReady', return_value = True ):
    completer.OnFileReadyToParse( request_data )
    # Simulate receipt of response and initialization complete
    initialize_response = {
      'result': {
        'capabilities': {}
      }
    }
    completer._HandleInitializeInPollThread( initialize_response )

    diagnostics = contains(
      has_entries( {
        'kind': equal_to( 'ERROR' ),
        'location': LocationMatcher( filepath, 4, 11 ),
        'location_extent': RangeMatcher( filepath, ( 4, 11 ), ( 4, 12 ) ),
        'ranges': contains(
           RangeMatcher( filepath, ( 4, 11 ), ( 4, 12 ) ) ),
        'text': equal_to( 'First error' ),
        'fixit_available': False
      } ),
      has_entries( {
        'kind': equal_to( 'ERROR' ),
        'location': LocationMatcher( filepath, 5, 8 ),
        'location_extent': RangeMatcher( filepath, ( 5, 8 ), ( 5, 14 ) ),
        'ranges': contains( RangeMatcher( filepath, ( 5, 8 ), ( 5, 14 ) ) ),
        'text': equal_to( 'Second error' ),
        'fixit_available': False
      } )
    )

    assert_that( completer.OnFileReadyToParse( request_data ), diagnostics )

    assert_that(
      completer.PollForMessages( request_data ),
      contains( has_entries( {
        'diagnostics': diagnostics,
        'filepath': filepath
      } ) )
    )


def LanguageServerCompleter_GetHoverResponse_test():
  completer = MockCompleter()
  request_data = RequestWrap( BuildRequest( line_num = 1,
                                            column_num = 1,
                                            contents = '' ) )

  with patch.object( completer, 'ServerIsReady', return_value = True ):
    with patch.object( completer.GetConnection(),
                       'GetResponse',
                       side_effect = [ { 'result': None } ] ):
      assert_that(
        calling( completer.GetHoverResponse ).with_args( request_data ),
        raises( RuntimeError, NO_HOVER_INFORMATION )
      )
    with patch.object( completer.GetConnection(),
                       'GetResponse',
                       side_effect = [ { 'result': { 'contents': 'test' } } ] ):
      eq_( completer.GetHoverResponse( request_data ), 'test' )


def LanguageServerCompleter_Diagnostics_PercentEncodeCannonical_test():
  completer = MockCompleter()
  filepath = os.path.realpath( '/foo?' )
  uri = lsp.FilePathToUri( filepath )
  assert_that( uri, ends_with( '%3F' ) )
  request_data = RequestWrap( BuildRequest( line_num = 1,
                                            column_num = 1,
                                            filepath = filepath,
                                            contents = '' ) )
  notification = {
    'jsonrpc': '2.0',
    'method': 'textDocument/publishDiagnostics',
    'params': {
      'uri': uri.replace( '%3F', '%3f' ),
      'diagnostics': [ {
        'range': {
          'start': { 'line': 3, 'character': 10 },
          'end': { 'line': 3, 'character': 11 }
        },
        'severity': 1,
        'message': 'First error'
      } ]
    }
  }
  completer.GetConnection()._notifications.put( notification )
  completer.HandleNotificationInPollThread( notification )

  with patch.object( completer, 'ServerIsReady', return_value = True ):
    completer.OnFileReadyToParse( request_data )
    # Simulate receipt of response and initialization complete
    initialize_response = {
      'result': {
        'capabilities': {}
      }
    }
    completer._HandleInitializeInPollThread( initialize_response )

    diagnostics = contains(
      has_entries( {
        'kind': equal_to( 'ERROR' ),
        'location': LocationMatcher( filepath, 4, 11 ),
        'location_extent': RangeMatcher( filepath, ( 4, 11 ), ( 4, 12 ) ),
        'ranges': contains(
           RangeMatcher( filepath, ( 4, 11 ), ( 4, 12 ) ) ),
        'text': equal_to( 'First error' ),
        'fixit_available': False
      } )
    )

    assert_that( completer.OnFileReadyToParse( request_data ), diagnostics )

    assert_that(
      completer.PollForMessages( request_data ),
      contains( has_entries( {
        'diagnostics': diagnostics,
        'filepath': filepath
      } ) )
    )


def LanguageServerCompleter_OnFileReadyToParse_InvalidURI_test():
  completer = MockCompleter()
  filepath = os.path.realpath( '/foo?' )
  uri = lsp.FilePathToUri( filepath )
  request_data = RequestWrap( BuildRequest( line_num = 1,
                                            column_num = 1,
                                            filepath = filepath,
                                            contents = '' ) )
  notification = {
    'jsonrpc': '2.0',
    'method': 'textDocument/publishDiagnostics',
    'params': {
      'uri': uri,
      'diagnostics': [ {
        'range': {
          'start': { 'line': 3, 'character': 10 },
          'end': { 'line': 3, 'character': 11 }
        },
        'severity': 1,
        'message': 'First error'
      } ]
    }
  }
  completer.GetConnection()._notifications.put( notification )
  completer.HandleNotificationInPollThread( notification )

  with patch.object( completer, 'ServerIsReady', return_value = True ):
    completer.OnFileReadyToParse( request_data )
    # Simulate receipt of response and initialization complete
    initialize_response = {
      'result': {
        'capabilities': {}
      }
    }
    completer._HandleInitializeInPollThread( initialize_response )

    diagnostics = contains(
      has_entries( {
        'kind': equal_to( 'ERROR' ),
        'location': LocationMatcher( '', 4, 11 ),
        'location_extent': RangeMatcher( '', ( 4, 11 ), ( 4, 12 ) ),
        'ranges': contains(
           RangeMatcher( '', ( 4, 11 ), ( 4, 12 ) ) ),
        'text': equal_to( 'First error' ),
        'fixit_available': False
      } )
    )

    with patch( 'ycmd.completers.language_server.language_server_protocol.'
                'UriToFilePath', side_effect = lsp.InvalidUriException ) as \
                    uri_to_filepath:
      assert_that( completer.OnFileReadyToParse( request_data ), diagnostics )
      uri_to_filepath.assert_called()
