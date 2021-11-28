# Copyright (C) 2017-2021 ycmd contributors
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

from unittest.mock import patch
from unittest import TestCase
from hamcrest import ( all_of,
                       assert_that,
                       calling,
                       empty,
                       ends_with,
                       equal_to,
                       contains_exactly,
                       has_entries,
                       has_entry,
                       has_items,
                       has_key,
                       is_not,
                       raises )

from ycmd.completers import completer
from ycmd.completers.language_server import language_server_completer as lsc
from ycmd.completers.language_server.language_server_completer import (
    NoHoverInfoException,
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
    super().__init__( user_options )

    self._connection = MockConnection(
        lambda request: self.WorkspaceConfigurationResponse( request ) )
    self._started = False

  def Language( self ):
    return 'foo'


  def StartServer( self, request_data, **kwargs ):
    self._started = True
    self._project_directory = self.GetProjectDirectory( request_data )
    return True


  def GetConnection( self ):
    return self._connection


  def HandleServerCommand( self, request_data, command ):
    return super().HandleServerCommand( request_data, command )


  def ServerIsHealthy( self ):
    return self._started


  def GetCommandLine( self ):
    return [ 'server' ]


  def GetServerName( self ):
    return 'mock_completer'


def _TupleToLSPRange( tuple ):
  return { 'line': tuple[ 0 ], 'character': tuple[ 1 ] }


def _Check_Distance( point, start, end, expected ):
  point = _TupleToLSPRange( point )
  start = _TupleToLSPRange( start )
  end = _TupleToLSPRange( end )
  range = { 'start': start, 'end': end }
  result = lsc._DistanceOfPointToRange( point, range )
  assert_that( result, equal_to( expected ) )


class LanguageServerCompleterTest( TestCase ):
  @IsolatedYcmd( { 'global_ycm_extra_conf':
                   PathToTestFile( 'extra_confs', 'settings_extra_conf.py' ) } )
  def test_LanguageServerCompleter_ExtraConf_ServerReset( self, app ):
    filepath = PathToTestFile( 'extra_confs', 'foo' )
    app.post_json( '/event_notification',
                   BuildRequest( filepath = filepath,
                                 filetype = 'foo',
                                 contents = '',
                                 event_name = 'FileReadyToParse' ) )

    request_data = RequestWrap( BuildRequest() )

    completer = MockCompleter()

    assert_that( None, equal_to( completer._project_directory ) )

    completer.OnFileReadyToParse( request_data )
    assert_that( completer._project_directory, is_not( None ) )
    assert_that( completer._settings.get( 'ls', {} ), is_not( empty() ) )

    completer.ServerReset()
    assert_that( completer._settings.get( 'ls', {} ), empty() )
    assert_that( None, equal_to( completer._project_directory ) )


  @IsolatedYcmd( { 'global_ycm_extra_conf':
                   PathToTestFile( 'extra_confs', 'empty_extra_conf.py' ) } )
  def test_LanguageServerCompleter_ExtraConf_FileEmpty( self, app ):
    filepath = PathToTestFile( 'extra_confs', 'foo' )

    completer = MockCompleter()
    request_data = RequestWrap( BuildRequest( filepath = filepath,
                                              filetype = 'ycmtest',
                                              contents = '' ) )
    completer.OnFileReadyToParse( request_data )
    assert_that( {}, equal_to( completer._settings.get( 'ls', {} ) ) )

    # Simulate receipt of response and initialization complete
    initialize_response = {
      'result': {
        'capabilities': {}
      }
    }
    completer._HandleInitializeInPollThread( initialize_response )
    assert_that( {}, equal_to( completer._settings.get( 'ls', {} ) ) )
    # We shouldn't have used the extra_conf path for the project directory, but
    # that _also_ happens to be the path of the file we opened.
    assert_that( PathToTestFile( 'extra_confs' ),
                 equal_to( completer._project_directory ) )


  @IsolatedYcmd( { 'global_ycm_extra_conf':
                   PathToTestFile( 'extra_confs',
                                   'settings_none_extra_conf.py' ) } )
  def test_LanguageServerCompleter_ExtraConf_SettingsReturnsNone( self, app ):
    filepath = PathToTestFile( 'extra_confs', 'foo' )

    completer = MockCompleter()
    request_data = RequestWrap( BuildRequest( filepath = filepath,
                                              filetype = 'ycmtest',
                                              contents = '' ) )
    completer.OnFileReadyToParse( request_data )
    assert_that( {}, equal_to( completer._settings.get( 'ls', {} ) ) )
    # We shouldn't have used the extra_conf path for the project directory, but
    # that _also_ happens to be the path of the file we opened.
    assert_that( PathToTestFile( 'extra_confs' ),
                 equal_to( completer._project_directory ) )


  @IsolatedYcmd( { 'global_ycm_extra_conf':
                   PathToTestFile( 'extra_confs', 'settings_extra_conf.py' ) } )
  def test_LanguageServerCompleter_ExtraConf_SettingValid( self, app ):
    filepath = PathToTestFile( 'extra_confs', 'foo' )

    completer = MockCompleter()
    request_data = RequestWrap( BuildRequest( filepath = filepath,
                                              filetype = 'ycmtest',
                                              working_dir = PathToTestFile(),
                                              contents = '' ) )

    assert_that( {}, equal_to( completer._settings.get( 'ls', {} ) ) )
    completer.OnFileReadyToParse( request_data )
    assert_that( { 'java.rename.enabled' : False },
                 equal_to( completer._settings.get( 'ls', {} ) ) )
    # We use the working_dir not the path to the global extra conf (which is
    # ignored)
    assert_that( PathToTestFile(), equal_to( completer._project_directory ) )


  @IsolatedYcmd( { 'extra_conf_globlist': [ '!*' ] } )
  def test_LanguageServerCompleter_ExtraConf_NoExtraConf( self, app ):
    filepath = PathToTestFile( 'extra_confs', 'foo' )

    completer = MockCompleter()
    request_data = RequestWrap( BuildRequest( filepath = filepath,
                                              filetype = 'ycmtest',
                                              working_dir = PathToTestFile(),
                                              contents = '' ) )

    assert_that( {}, equal_to( completer._settings.get( 'ls', {} ) ) )
    completer.OnFileReadyToParse( request_data )
    assert_that( {}, equal_to( completer._settings.get( 'ls', {} ) ) )

    # Simulate receipt of response and initialization complete
    initialize_response = {
      'result': {
        'capabilities': {}
      }
    }
    completer._HandleInitializeInPollThread( initialize_response )
    assert_that( {}, equal_to( completer._settings.get( 'ls', {} ) ) )
    # We use the client working directory
    assert_that( PathToTestFile(), equal_to( completer._project_directory ) )


  @IsolatedYcmd( { 'extra_conf_globlist': [ '*' ] } )
  def test_LanguageServerCompleter_ExtraConf_NonGlobal( self, app ):
    filepath = PathToTestFile( 'project',
                               'settings_extra_conf',
                               'foo' )

    completer = MockCompleter()
    request_data = RequestWrap( BuildRequest( filepath = filepath,
                                              filetype = 'ycmtest',
                                              # ignored; ycm conf path used
                                              working_dir = 'ignore_this',
                                              contents = '' ) )

    assert_that( {}, equal_to( completer._settings.get( 'ls', {} ) ) )
    completer.OnFileReadyToParse( request_data )
    assert_that( { 'java.rename.enabled' : False },
                 equal_to( completer._settings.get( 'ls', {} ) ) )

    # Simulate receipt of response and initialization complete
    initialize_response = {
      'result': {
        'capabilities': {}
      }
    }
    completer._HandleInitializeInPollThread( initialize_response )
    assert_that( PathToTestFile( 'project', 'settings_extra_conf' ),
                 equal_to( completer._project_directory ) )


  @IsolatedYcmd()
  def test_LanguageServerCompleter_Initialise_Aborted( self, app ):
    completer = MockCompleter()
    request_data = RequestWrap( BuildRequest() )

    with patch.object( completer.GetConnection(),
                       'ReadData',
                       side_effect = RuntimeError ):

      assert_that( completer.ServerIsReady(), equal_to( False ) )

      completer.OnFileReadyToParse( request_data )

      with patch.object( completer,
                         '_HandleInitializeInPollThread' ) as handler:
        completer.GetConnection().run()
        handler.assert_not_called()

      assert_that( completer._initialize_event.is_set(), equal_to( False ) )
      assert_that( completer.ServerIsReady(), equal_to( False ) )


    with patch.object( completer, 'ServerIsHealthy', return_value = False ):
      assert_that( completer.ServerIsReady(), equal_to( False ) )


  @IsolatedYcmd()
  def test_LanguageServerCompleter_Initialise_Shutdown( self, app ):
    completer = MockCompleter()
    request_data = RequestWrap( BuildRequest() )

    with patch.object( completer.GetConnection(),
                       'ReadData',
                       side_effect = lsc.LanguageServerConnectionStopped ):

      assert_that( completer.ServerIsReady(), equal_to( False ) )

      completer.OnFileReadyToParse( request_data )

      with patch.object( completer,
                         '_HandleInitializeInPollThread' ) as handler:
        completer.GetConnection().run()
        handler.assert_not_called()

      assert_that( completer._initialize_event.is_set(), equal_to( False ) )
      assert_that( completer.ServerIsReady(), equal_to( False ) )


    with patch.object( completer, 'ServerIsHealthy', return_value = False ):
      assert_that( completer.ServerIsReady(), equal_to( False ) )


  @IsolatedYcmd()
  def test_LanguageServerCompleter_GoTo( self, app ):
    if utils.OnWindows():
      filepath = 'C:\\test.test'
      uri = 'file:///c:/test.test'
    else:
      filepath = '/test.test'
      uri = 'file:/test.test'

    contents = 'line1\nline2\nline3'

    completer = MockCompleter()
    # LSP server supports all code navigation features.
    completer._server_capabilities = {
      'definitionProvider':     True,
      'declarationProvider':    True,
      'typeDefinitionProvider': True,
      'implementationProvider': True,
      'referencesProvider':     True
    }
    request_data = RequestWrap( BuildRequest(
      filetype = 'ycmtest',
      filepath = filepath,
      contents = contents,
      line_num = 2,
      column_num = 3
    ) )

    @patch.object( completer, '_ServerIsInitialized', return_value = True )
    def Test( responses, command, exception, throws, *args ):
      with patch.object( completer.GetConnection(),
                         'GetResponse',
                         side_effect = responses ):
        if throws:
          assert_that(
            calling( completer.OnUserCommand ).with_args( [ command ],
                                                          request_data ),
            raises( exception )
          )
        else:
          result = completer.OnUserCommand( [ command ], request_data )
          print( f'Result: { result }' )
          assert_that( result, exception )


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
      ( [ { 'result': None } ], 'GoToDefinition', RuntimeError, True ),
      ( [ { 'result': location } ], 'GoToDeclaration', goto_response, False ),
      ( [ { 'result': {} } ], 'GoToType', RuntimeError, True ),
      ( [ { 'result': [] } ], 'GoToImplementation', RuntimeError, True ),
      ( [ { 'result': [ location ] } ],
        'GoToReferences', goto_response, False ),
      ( [ { 'result': [ location, location ] } ],
        'GoToReferences',
        contains_exactly( goto_response, goto_response ),
        False ),
    ]

    for response, goto_handlers, exception, throws in cases:
      Test( response, goto_handlers, exception, throws )


    # All requests return an invalid URI.
    with patch(
      'ycmd.completers.language_server.language_server_protocol.UriToFilePath',
      side_effect = lsp.InvalidUriException ):
      Test( [ {
        'result': {
          'uri': uri,
          'range': {
            'start': { 'line': 0, 'character': 0 },
            'end': { 'line': 0, 'character': 0 } }
        }
      } ], 'GoTo', LocationMatcher( '', 1, 1 ), False )

    with patch( 'ycmd.completers.completer_utils.GetFileContents',
                side_effect = IOError ):
      Test( [ {
        'result': {
          'uri': uri,
          'range': {
            'start': { 'line': 0, 'character': 0 },
            'end': { 'line': 0, 'character': 0 } }
        }
      } ], 'GoToDefinition', LocationMatcher( filepath, 1, 1 ), False )

    # Both requests return the location where the cursor is.
    Test( [ {
      'result': {
        'uri': uri,
        'range': {
          'start': { 'line': 1, 'character': 0 },
          'end': { 'line': 1, 'character': 4 } }
      }
    }, {
      'result': {
        'uri': uri,
        'range': {
          'start': { 'line': 1, 'character': 0 },
          'end': { 'line': 1, 'character': 4 },
        }
      }
    } ], 'GoTo', LocationMatcher( filepath, 2, 1 ), False )

    # First request returns two locations.
    Test( [ {
      'result': [ {
        'uri': uri,
        'range': {
          'start': { 'line': 0, 'character': 0 },
          'end': { 'line': 0, 'character': 4 } }
      }, {
        'uri': uri,
        'range': {
          'start': { 'line': 1, 'character': 0 },
          'end': { 'line': 1, 'character': 4 },
        }
      } ],
    } ], 'GoTo', contains_exactly(
      LocationMatcher( filepath, 1, 1 ),
      LocationMatcher( filepath, 2, 1 )
    ), False )

    # First request returns the location where the cursor is and second request
    # returns a different URI.
    if utils.OnWindows():
      other_filepath = 'C:\\another.test'
      other_uri = 'file:///c:/another.test'
    else:
      other_filepath = '/another.test'
      other_uri = 'file:/another.test'

    Test( [ {
      'result': {
        'uri': uri,
        'range': {
          'start': { 'line': 1, 'character': 0 },
          'end': { 'line': 1, 'character': 4 } }
      }
    }, {
      'result': {
        'uri': other_uri,
        'range': {
          'start': { 'line': 1, 'character': 0 },
          'end': { 'line': 1, 'character': 4 },
        }
      }
    } ], 'GoTo', LocationMatcher( other_filepath, 2, 1 ), False )

    # First request returns a location before the cursor.
    Test( [ {
      'result': {
        'uri': uri,
        'range': {
          'start': { 'line': 0, 'character': 1 },
          'end': { 'line': 1, 'character': 1 } }
      }
    } ], 'GoTo', LocationMatcher( filepath, 1, 2 ), False )

    # First request returns a location after the cursor.
    Test( [ {
      'result': {
        'uri': uri,
        'range': {
          'start': { 'line': 1, 'character': 3 },
          'end': { 'line': 2, 'character': 3 } }
      }
    } ], 'GoTo', LocationMatcher( filepath, 2, 4 ), False )


  def test_GetCompletions_RejectInvalid( self ):
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


  def test_WorkspaceEditToFixIt( self ):
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


    # Null response to textDocument/codeActions is valid
    assert_that( lsc.WorkspaceEditToFixIt( request_data, None ),
                 equal_to( None ) )
    # Empty WorkspaceEdit is not explicitly forbidden
    assert_that( lsc.WorkspaceEditToFixIt( request_data, {} ),
                 equal_to( None ) )
    # We don't support versioned documentChanges
    workspace_edit = {
      'documentChanges': [
        {
          'textDocument': {
            'version': 1,
            'uri': uri
          },
          'edits': [
            {
              'newText': 'blah',
              'range': {
                'start': { 'line': 0, 'character': 5 },
                'end': { 'line': 0, 'character': 5 },
              }
            }
          ]
        }
      ]
    }
    response = responses.BuildFixItResponse( [
      lsc.WorkspaceEditToFixIt( request_data, workspace_edit, 'test' )
    ] )

    print( f'Response: { response }' )
    assert_that(
      response,
      has_entries( {
        'fixits': contains_exactly( has_entries( {
          'text': 'test',
          'chunks': contains_exactly(
            ChunkMatcher( 'blah',
                          LocationMatcher( filepath, 1, 6 ),
                          LocationMatcher( filepath, 1, 6 ) ) )
        } ) )
      } )
    )

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

    print( f'Response: { response }' )
    print( f'Type Response: { type( response ) }' )

    assert_that(
      response,
      has_entries( {
        'fixits': contains_exactly( has_entries( {
          'text': 'test',
          'chunks': contains_exactly(
            ChunkMatcher( 'blah',
                          LocationMatcher( filepath, 1, 6 ),
                          LocationMatcher( filepath, 1, 6 ) ) )
        } ) )
      } )
    )


  @IsolatedYcmd( { 'extra_conf_globlist': [ '!*' ] } )
  def test_LanguageServerCompleter_DelayedInitialization( self, app ):
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


  @IsolatedYcmd()
  def test_LanguageServerCompleter_RejectWorkspaceConfigurationRequest(
      self, app ):
    completer = MockCompleter()
    notification = {
      'jsonrpc': '2.0',
      'method': 'workspace/configuration',
      'id': 1234,
      'params': {
        'items': [ { 'section': 'whatever' } ]
      }
    }
    with patch( 'ycmd.completers.language_server.'
                'language_server_protocol.Reject' ) as reject:
      completer.GetConnection()._DispatchMessage( notification )
      reject.assert_called_with( notification, lsp.Errors.MethodNotFound )


  @IsolatedYcmd()
  def test_LanguageServerCompleter_ShowMessage( self, app ):
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


  @IsolatedYcmd()
  def test_LanguageServerCompleter_GetCompletions_List( self, app ):
    completer = MockCompleter()
    request_data = RequestWrap( BuildRequest() )

    completion_response = { 'result': [ { 'label': 'test' } ] }

    resolve_responses = [
      { 'result': { 'label': 'test' } },
    ]

    with patch.object( completer, '_is_completion_provider', True ):
      with patch.object( completer.GetConnection(),
                         'GetResponse',
                         side_effect = [ completion_response ] +
                                       resolve_responses ):
        assert_that(
          completer.ComputeCandidatesInner( request_data, 1 ),
          contains_exactly(
            has_items( has_entries( { 'insertion_text': 'test' } ) ),
            False
          )
        )


  @IsolatedYcmd()
  def test_LanguageServerCompleter_GetCompletions_UnsupportedKinds( self, app ):
    completer = MockCompleter()
    request_data = RequestWrap( BuildRequest() )

    completion_response = { 'result': [ { 'label': 'test',
                                          'kind': len( lsp.ITEM_KIND ) + 1 } ] }

    resolve_responses = [
      { 'result': { 'label': 'test' } },
    ]

    with patch.object( completer, '_is_completion_provider', True ):
      with patch.object( completer.GetConnection(),
                         'GetResponse',
                         side_effect = [ completion_response ] +
                                       resolve_responses ):
        assert_that(
          completer.ComputeCandidatesInner( request_data, 1 ),
          contains_exactly(
            has_items( all_of( has_entry( 'insertion_text', 'test' ),
                               is_not( has_key( 'kind' ) ) ) ),
            False
          )
        )


  @IsolatedYcmd()
  def test_LanguageServerCompleter_GetCompletions_NullNoError( self, app ):
    completer = MockCompleter()
    request_data = RequestWrap( BuildRequest() )
    complete_response = { 'result': None }
    resolve_responses = []
    with patch.object( completer, '_ServerIsInitialized', return_value = True ):
      with patch.object( completer,
                         '_is_completion_provider',
                         return_value = True ):
        with patch.object( completer.GetConnection(),
                           'GetResponse',
                           side_effect = [ complete_response ] +
                                         resolve_responses ):
          assert_that(
            completer.ComputeCandidatesInner( request_data, 1 ),
            contains_exactly(
              empty(),
              False
            )
          )


  @IsolatedYcmd()
  def test_LanguageServerCompleter_GetCompletions_CompleteOnStartColumn(
      self, app ):
    completer = MockCompleter()
    completer._resolve_completion_items = False
    complete_response = {
      'result': {
        'items': [
          { 'label': 'aa' },
          { 'label': 'ac' },
          { 'label': 'ab' }
        ],
        'isIncomplete': False
      }
    }

    with patch.object( completer, '_is_completion_provider', True ):
      request_data = RequestWrap( BuildRequest(
        column_num = 2,
        contents = 'a',
        force_semantic = True
      ) )

      with patch.object( completer.GetConnection(),
                         'GetResponse',
                         return_value = complete_response ) as response:
        assert_that(
          completer.ComputeCandidates( request_data ),
          contains_exactly(
            has_entry( 'insertion_text', 'aa' ),
            has_entry( 'insertion_text', 'ab' ),
            has_entry( 'insertion_text', 'ac' )
          )
        )

        # Nothing cached yet.
        assert_that( response.call_count, equal_to( 1 ) )

      request_data = RequestWrap( BuildRequest(
        column_num = 3,
        contents = 'ab',
        force_semantic = True
      ) )

      with patch.object( completer.GetConnection(),
                         'GetResponse',
                         return_value = complete_response ) as response:
        assert_that(
          completer.ComputeCandidates( request_data ),
          contains_exactly(
            has_entry( 'insertion_text', 'ab' )
          )
        )

        # Since the server returned a complete list of completions on the
        # starting column, no request should be sent to the server and the
        # cache should be used instead.
        assert_that( response.call_count, equal_to( 0 ) )


  @IsolatedYcmd()
  def test_LanguageServerCompleter_GetCompletions_CompleteOnCurrentColumn(
      self, app ):
    completer = MockCompleter()
    completer._resolve_completion_items = False

    a_response = {
      'result': {
        'items': [
          { 'label': 'aba' },
          { 'label': 'aab' },
          { 'label': 'aaa' }
        ],
        'isIncomplete': True
      }
    }
    aa_response = {
      'result': {
        'items': [
          { 'label': 'aab' },
          { 'label': 'aaa' }
        ],
        'isIncomplete': False
      }
    }
    aaa_response = {
      'result': {
        'items': [
          { 'label': 'aaa' }
        ],
        'isIncomplete': False
      }
    }
    ab_response = {
      'result': {
        'items': [
          { 'label': 'abb' },
          { 'label': 'aba' }
        ],
        'isIncomplete': False
      }
    }

    with patch.object( completer, '_is_completion_provider', True ):
      # User starts by typing the character "a".
      request_data = RequestWrap( BuildRequest(
        column_num = 2,
        contents = 'a',
        force_semantic = True
      ) )

      with patch.object( completer.GetConnection(),
                         'GetResponse',
                         return_value = a_response ) as response:
        assert_that(
          completer.ComputeCandidates( request_data ),
          contains_exactly(
            has_entry( 'insertion_text', 'aaa' ),
            has_entry( 'insertion_text', 'aab' ),
            has_entry( 'insertion_text', 'aba' )
          )
        )

        # Nothing cached yet.
        assert_that( response.call_count, equal_to( 1 ) )

      # User types again the character "a".
      request_data = RequestWrap( BuildRequest(
        column_num = 3,
        contents = 'aa',
        force_semantic = True
      ) )

      with patch.object( completer.GetConnection(),
                         'GetResponse',
                         return_value = aa_response ) as response:
        assert_that(
          completer.ComputeCandidates( request_data ),
          contains_exactly(
            has_entry( 'insertion_text', 'aaa' ),
            has_entry( 'insertion_text', 'aab' )
          )
        )

        # The server returned an incomplete list of completions the first time
        # so a new completion request should have been sent.
        assert_that( response.call_count, equal_to( 1 ) )

      # User types the character "a" a third time.
      request_data = RequestWrap( BuildRequest(
        column_num = 4,
        contents = 'aaa',
        force_semantic = True
      ) )

      with patch.object( completer.GetConnection(),
                         'GetResponse',
                         return_value = aaa_response ) as response:

        assert_that(
          completer.ComputeCandidates( request_data ),
          contains_exactly(
            has_entry( 'insertion_text', 'aaa' )
          )
        )

        # The server returned a complete list of completions the second time
        # and the new query is a prefix of the cached one ("aa" is a prefix of
        # "aaa") so the cache should be used.
        assert_that( response.call_count, equal_to( 0 ) )

      # User deletes the third character.
      request_data = RequestWrap( BuildRequest(
        column_num = 3,
        contents = 'aa',
        force_semantic = True
      ) )

      with patch.object( completer.GetConnection(),
                         'GetResponse',
                         return_value = aa_response ) as response:

        assert_that(
          completer.ComputeCandidates( request_data ),
          contains_exactly(
            has_entry( 'insertion_text', 'aaa' ),
            has_entry( 'insertion_text', 'aab' )
          )
        )

        # The new query is still a prefix of the cached one ("aa" is a prefix of
        # "aa") so the cache should again be used.
        assert_that( response.call_count, equal_to( 0 ) )

      # User deletes the second character.
      request_data = RequestWrap( BuildRequest(
        column_num = 2,
        contents = 'a',
        force_semantic = True
      ) )

      with patch.object( completer.GetConnection(),
                         'GetResponse',
                         return_value = a_response ) as response:

        assert_that(
          completer.ComputeCandidates( request_data ),
          contains_exactly(
            has_entry( 'insertion_text', 'aaa' ),
            has_entry( 'insertion_text', 'aab' ),
            has_entry( 'insertion_text', 'aba' )
          )
        )

        # The new query is not anymore a prefix of the cached one ("aa" is not a
        # prefix of "a") so the cache is invalidated and a new request is sent.
        assert_that( response.call_count, equal_to( 1 ) )

      # Finally, user inserts the "b" character.
      request_data = RequestWrap( BuildRequest(
        column_num = 3,
        contents = 'ab',
        force_semantic = True
      ) )

      with patch.object( completer.GetConnection(),
                         'GetResponse',
                         return_value = ab_response ) as response:

        assert_that(
          completer.ComputeCandidates( request_data ),
          contains_exactly(
            has_entry( 'insertion_text', 'aba' ),
            has_entry( 'insertion_text', 'abb' )
          )
        )

        # Last response was incomplete so the cache should not be used.
        assert_that( response.call_count, equal_to( 1 ) )


  def test_FindOverlapLength( self ):
    for line, text, overlap in [
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
    ]:
      with self.subTest( line = line, text = text, overlap = overlap ):
        assert_that( lsc.FindOverlapLength( line, text ), equal_to( overlap ) )


  @IsolatedYcmd()
  def test_LanguageServerCompleter_GetCodeActions_CursorOnEmptyLine(
      self, app ):
    completer = MockCompleter()
    request_data = RequestWrap( BuildRequest( line_num = 1,
                                              column_num = 1,
                                              contents = '' ) )

    fixit_response = { 'result': [] }

    with patch.object( completer, '_ServerIsInitialized', return_value = True ):
      with patch.object( completer.GetConnection(),
                         'GetResponse',
                         side_effect = [ fixit_response ] ):
        with patch( 'ycmd.completers.language_server.language_server_protocol.'
                    'CodeAction' ) as code_action:
          assert_that( completer.GetCodeActions( request_data ),
                       has_entry( 'fixits', empty() ) )
          assert_that(
            # Range passed to lsp.CodeAction.
            # LSP requires to use the start of the next line as the end position
            # for a range that ends with a newline.
            code_action.call_args[ 0 ][ 2 ],
            has_entries( {
              'start': has_entries( {
                'line': 0,
                'character': 0
              } ),
              'end': has_entries( {
                'line': 1,
                'character': 0
              } )
            } )
          )


  @IsolatedYcmd()
  def test_LanguageServerCompleter_Diagnostics_MaxDiagnosticsNumberExceeded(
      self, app ):
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
          'message': 'Second error [8]'
        } ]
      }
    }
    completer.GetConnection()._notifications.put( notification )
    completer.HandleNotificationInPollThread( notification )

    with patch.object( completer, '_ServerIsInitialized', return_value = True ):
      completer.OnFileReadyToParse( request_data )
      # Simulate receipt of response and initialization complete
      initialize_response = {
        'result': {
          'capabilities': {}
        }
      }
      completer._HandleInitializeInPollThread( initialize_response )

      diagnostics = contains_exactly(
        has_entries( {
          'kind': equal_to( 'ERROR' ),
          'location': LocationMatcher( filepath, 4, 11 ),
          'location_extent': RangeMatcher( filepath, ( 4, 11 ), ( 4, 12 ) ),
          'ranges': contains_exactly(
             RangeMatcher( filepath, ( 4, 11 ), ( 4, 12 ) ) ),
          'text': equal_to( 'First error' ),
          'fixit_available': False
        } ),
        has_entries( {
          'kind': equal_to( 'ERROR' ),
          'location': LocationMatcher( filepath, 1, 1 ),
          'location_extent': RangeMatcher( filepath, ( 1, 1 ), ( 1, 1 ) ),
          'ranges': contains_exactly(
            RangeMatcher( filepath, ( 1, 1 ), ( 1, 1 ) ) ),
          'text': equal_to( 'Maximum number of diagnostics exceeded.' ),
          'fixit_available': False
        } )
      )

      assert_that( completer.OnFileReadyToParse( request_data ), diagnostics )

      assert_that(
        completer.PollForMessages( request_data ),
        contains_exactly( has_entries( {
          'diagnostics': diagnostics,
          'filepath': filepath
        } ) )
      )


  @IsolatedYcmd()
  def test_LanguageServerCompleter_Diagnostics_NoLimitToNumberOfDiagnostics(
      self, app ):
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

    with patch.object( completer, '_ServerIsInitialized', return_value = True ):
      completer.OnFileReadyToParse( request_data )
      # Simulate receipt of response and initialization complete
      initialize_response = {
        'result': {
          'capabilities': {}
        }
      }
      completer._HandleInitializeInPollThread( initialize_response )

      diagnostics = contains_exactly(
        has_entries( {
          'kind': equal_to( 'ERROR' ),
          'location': LocationMatcher( filepath, 4, 11 ),
          'location_extent': RangeMatcher( filepath, ( 4, 11 ), ( 4, 12 ) ),
          'ranges': contains_exactly(
             RangeMatcher( filepath, ( 4, 11 ), ( 4, 12 ) ) ),
          'text': equal_to( 'First error' ),
          'fixit_available': False
        } ),
        has_entries( {
          'kind': equal_to( 'ERROR' ),
          'location': LocationMatcher( filepath, 5, 8 ),
          'location_extent': RangeMatcher( filepath, ( 5, 8 ), ( 5, 14 ) ),
          'ranges': contains_exactly(
            RangeMatcher( filepath, ( 5, 8 ), ( 5, 14 ) ) ),
          'text': equal_to( 'Second error' ),
          'fixit_available': False
        } )
      )

      assert_that( completer.OnFileReadyToParse( request_data ), diagnostics )

      assert_that(
        completer.PollForMessages( request_data ),
        contains_exactly( has_entries( {
          'diagnostics': diagnostics,
          'filepath': filepath
        } ) )
      )


  @IsolatedYcmd()
  def test_LanguageServerCompleter_GetHoverResponse( self, app ):
    completer = MockCompleter()
    request_data = RequestWrap( BuildRequest( line_num = 1,
                                              column_num = 1,
                                              contents = '' ) )

    with patch.object( completer, '_ServerIsInitialized', return_value = True ):
      with patch.object( completer.GetConnection(),
                         'GetResponse',
                         side_effect = [ { 'result': None } ] ):
        assert_that(
          calling( completer.GetHoverResponse ).with_args( request_data ),
          raises( NoHoverInfoException, NO_HOVER_INFORMATION )
        )
      with patch.object(
          completer.GetConnection(),
          'GetResponse',
          side_effect = [ { 'result': { 'contents': 'test' } } ] ):
        assert_that( completer.GetHoverResponse( request_data ),
                     equal_to( 'test' ) )


  @IsolatedYcmd()
  def test_LanguageServerCompleter_Diagnostics_Code( self, app ):
    completer = MockCompleter()
    filepath = os.path.realpath( '/foo.cpp' )
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
          'message': 'First error',
          'code': 'random_error'
        }, {
          'range': {
            'start': { 'line': 3, 'character': 10 },
            'end': { 'line': 3, 'character': 11 }
          },
          'severity': 1,
          'message': 'Second error',
          'code': 8
        }, {
          'range': {
            'start': { 'line': 3, 'character': 10 },
            'end': { 'line': 3, 'character': 11 }
          },
          'severity': 1,
          'message': 'Third error',
          'code': '8'
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

      diagnostics = contains_exactly(
        has_entries( {
          'kind': equal_to( 'ERROR' ),
          'location': LocationMatcher( filepath, 4, 11 ),
          'location_extent': RangeMatcher( filepath, ( 4, 11 ), ( 4, 12 ) ),
          'ranges': contains_exactly(
             RangeMatcher( filepath, ( 4, 11 ), ( 4, 12 ) ) ),
          'text': equal_to( 'First error [random_error]' ),
          'fixit_available': False
        } ),
        has_entries( {
          'kind': equal_to( 'ERROR' ),
          'location': LocationMatcher( filepath, 4, 11 ),
          'location_extent': RangeMatcher( filepath, ( 4, 11 ), ( 4, 12 ) ),
          'ranges': contains_exactly(
             RangeMatcher( filepath, ( 4, 11 ), ( 4, 12 ) ) ),
          'text': equal_to( 'Second error [8]' ),
          'fixit_available': False
        } ),
        has_entries( {
          'kind': equal_to( 'ERROR' ),
          'location': LocationMatcher( filepath, 4, 11 ),
          'location_extent': RangeMatcher( filepath, ( 4, 11 ), ( 4, 12 ) ),
          'ranges': contains_exactly(
             RangeMatcher( filepath, ( 4, 11 ), ( 4, 12 ) ) ),
          'text': equal_to( 'Third error [8]' ),
          'fixit_available': False
        } )
      )

      assert_that( completer.OnFileReadyToParse( request_data ), diagnostics )

      assert_that(
        completer.PollForMessages( request_data ),
        contains_exactly( has_entries( {
          'diagnostics': diagnostics,
          'filepath': filepath
        } ) )
      )


  @IsolatedYcmd()
  def test_LanguageServerCompleter_Diagnostics_PercentEncodeCannonical(
      self, app ):
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

    with patch.object( completer, '_ServerIsInitialized', return_value = True ):
      completer.OnFileReadyToParse( request_data )
      # Simulate receipt of response and initialization complete
      initialize_response = {
        'result': {
          'capabilities': {}
        }
      }
      completer._HandleInitializeInPollThread( initialize_response )

      diagnostics = contains_exactly(
        has_entries( {
          'kind': equal_to( 'ERROR' ),
          'location': LocationMatcher( filepath, 4, 11 ),
          'location_extent': RangeMatcher( filepath, ( 4, 11 ), ( 4, 12 ) ),
          'ranges': contains_exactly(
             RangeMatcher( filepath, ( 4, 11 ), ( 4, 12 ) ) ),
          'text': equal_to( 'First error' ),
          'fixit_available': False
        } )
      )

      assert_that( completer.OnFileReadyToParse( request_data ), diagnostics )

      assert_that(
        completer.PollForMessages( request_data ),
        contains_exactly( has_entries( {
          'diagnostics': diagnostics,
          'filepath': filepath
        } ) )
      )


  @IsolatedYcmd()
  @patch.object( completer, 'MESSAGE_POLL_TIMEOUT', 0.01 )
  def test_LanguageServerCompleter_PollForMessages_ServerNotStarted(
      self, app ):
    server = MockCompleter()
    request_data = RequestWrap( BuildRequest() )
    assert_that( server.PollForMessages( request_data ), equal_to( True ) )


  @IsolatedYcmd()
  def test_LanguageServerCompleter_OnFileSave_BeforeServerReady( self, app ):
    completer = MockCompleter()
    request_data = RequestWrap( BuildRequest() )
    with patch.object( completer, 'ServerIsReady', return_value = False ):
      with patch.object( completer.GetConnection(),
                         'SendNotification' ) as send_notification:
        completer.OnFileSave( request_data )
        send_notification.assert_not_called()


  @IsolatedYcmd()
  def test_LanguageServerCompleter_OnFileReadyToParse_InvalidURI( self, app ):
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

    with patch.object( completer, '_ServerIsInitialized', return_value = True ):
      completer.OnFileReadyToParse( request_data )
      # Simulate receipt of response and initialization complete
      initialize_response = {
        'result': {
          'capabilities': {}
        }
      }
      completer._HandleInitializeInPollThread( initialize_response )

      diagnostics = contains_exactly(
        has_entries( {
          'kind': equal_to( 'ERROR' ),
          'location': LocationMatcher( '', 4, 11 ),
          'location_extent': RangeMatcher( '', ( 4, 11 ), ( 4, 12 ) ),
          'ranges': contains_exactly(
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


  def test_LanguageServerCompleter_DistanceOfPointToRange_SingleLineRange(
      self ):
    # Point to the left of range.
    _Check_Distance( ( 0, 0 ), ( 0, 2 ), ( 0, 5 ) , 2 )
    # Point inside range.
    _Check_Distance( ( 0, 4 ), ( 0, 2 ), ( 0, 5 ) , 0 )
    # Point to the right of range.
    _Check_Distance( ( 0, 8 ), ( 0, 2 ), ( 0, 5 ) , 3 )


  def test_LanguageServerCompleter_DistanceOfPointToRange_MultiLineRange(
      self ):
    # Point to the left of range.
    _Check_Distance( ( 0, 0 ), ( 0, 2 ), ( 3, 5 ) , 2 )
    # Point inside range.
    _Check_Distance( ( 1, 4 ), ( 0, 2 ), ( 3, 5 ) , 0 )
    # Point to the right of range.
    _Check_Distance( ( 3, 8 ), ( 0, 2 ), ( 3, 5 ) , 3 )
