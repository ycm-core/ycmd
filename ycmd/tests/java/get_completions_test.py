# Copyright (C) 2017-2020 ycmd contributors
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

from hamcrest import ( assert_that,
                       contains_exactly,
                       contains_inanyorder,
                       empty,
                       equal_to,
                       matches_regexp,
                       has_entries,
                       has_item,
                       has_items,
                       has_key,
                       instance_of,
                       is_not )

from pprint import pformat
import requests
import os

from ycmd import handlers
from ycmd.tests.java import ( DEFAULT_PROJECT_DIR,
                              IsolatedYcmd,
                              PathToTestFile,
                              SharedYcmd )
from ycmd.tests.test_utils import ( ClearCompletionsCache,
                                    CombineRequest,
                                    ChunkMatcher,
                                    CompletionEntryMatcher,
                                    ErrorMatcher,
                                    LocationMatcher,
                                    WithRetry,
                                    UnixOnly )
from ycmd.utils import ReadFile
from unittest.mock import patch
from ycmd.completers.completer import CompletionsChanged


def ProjectPath( *args ):
  return PathToTestFile( DEFAULT_PROJECT_DIR,
                         'src',
                         'com',
                         'test',
                         *args )


def RunTest( app, test ):
  """
  Method to run a simple completion test and verify the result

  test is a dictionary containing:
    'request': kwargs for BuildRequest
    'expect': {
       'response': server response code (e.g. httplib.OK)
       'data': matcher for the server response json
    }
  """

  ClearCompletionsCache()

  contents = ReadFile( test[ 'request' ][ 'filepath' ] )

  app.post_json( '/event_notification',
                 CombineRequest( test[ 'request' ], {
                                   'event_name': 'FileReadyToParse',
                                   'contents': contents,
                                 } ),
                 expect_errors = True )

  # We ignore errors here and we check the response code ourself.
  # This is to allow testing of requests returning errors.
  request = CombineRequest( test[ 'request' ], { 'contents': contents } )
  response = app.post_json( '/completions', request, expect_errors = True )

  print( f'completer response: { pformat( response.json ) }' )

  assert_that( response.status_code,
               equal_to( test[ 'expect' ][ 'response' ] ) )

  assert_that( response.json, test[ 'expect' ][ 'data' ] )

  return request, response.json


PUBLIC_OBJECT_METHODS = [
  CompletionEntryMatcher( 'equals',
                          'Object.equals(Object arg0) : boolean',
                          { 'kind': 'Method' } ),
  CompletionEntryMatcher( 'getClass',
                          'Object.getClass() : Class<?>',
                          { 'kind': 'Method' } ),
  CompletionEntryMatcher( 'hashCode',
                          'Object.hashCode() : int',
                          { 'kind': 'Method' } ),
  CompletionEntryMatcher( 'notify',
                          'Object.notify() : void',
                          { 'kind': 'Method' } ),
  CompletionEntryMatcher( 'notifyAll',
                          'Object.notifyAll() : void',
                          { 'kind': 'Method' } ),
  CompletionEntryMatcher( 'toString',
                          'Object.toString() : String',
                          { 'kind': 'Method' } ),
  CompletionEntryMatcher( 'wait', 'Object.wait(long arg0, int arg1) : void', {
    'menu_text': matches_regexp( 'wait\\(long .*, int .*\\) : void' ),
    'kind': 'Method',
  } ),
  CompletionEntryMatcher( 'wait', 'Object.wait(long arg0) : void', {
    'menu_text': matches_regexp( 'wait\\(long .*\\) : void' ),
    'kind': 'Method',
  } ),
  CompletionEntryMatcher( 'wait', 'Object.wait() : void', {
    'menu_text': 'wait() : void',
    'kind': 'Method',
  } ),
]


# The zealots that designed java made everything inherit from Object (except,
# possibly Object, or Class, or whichever one they used to break the Smalltalk
# infinite recursion problem). Anyway, that means that we get a lot of noise
# suggestions from the Object Class interface. This allows us to write:
#
#   contains_inanyorder( *WithObjectMethods( CompletionEntryMatcher( ... ) ) )
#
# and focus on what we care about.
def WithObjectMethods( *args ):
  return list( PUBLIC_OBJECT_METHODS ) + list( args )


@WithRetry
@SharedYcmd
def GetCompletions_NoQuery_test( app ):
  RunTest( app, {
    'description': 'semantic completion works for builtin types (no query)',
    'request': {
      'filetype'  : 'java',
      'filepath'  : ProjectPath( 'TestFactory.java' ),
      'line_num'  : 27,
      'column_num': 12,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': has_items(
            CompletionEntryMatcher( 'test', 'TestFactory.Bar.test : int', {
              'kind': 'Field'
            } ),
            CompletionEntryMatcher( 'testString',
                                    'TestFactory.Bar.testString : String',
                                    {
                                      'kind': 'Field'
                                    } )
        ),
        'errors': empty(),
      } )
    },
  } )


@WithRetry
@SharedYcmd
def GetCompletions_WithQuery_test( app ):
  RunTest( app, {
    'description': 'semantic completion works for builtin types (with query)',
    'request': {
      'filetype'  : 'java',
      'filepath'  : ProjectPath( 'TestFactory.java' ),
      'line_num'  : 27,
      'column_num': 15,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': contains_inanyorder(
          CompletionEntryMatcher( 'test', 'TestFactory.Bar.test : int', {
              'kind': 'Field'
            } ),
            CompletionEntryMatcher( 'testString',
                                    'TestFactory.Bar.testString : String',
                                    {
                                      'kind': 'Field'
                                    } )
        ),
        'errors': empty(),
      } )
    },
  } )


@WithRetry
@SharedYcmd
def GetCompletions_DetailFromCache_test( app ):
  for i in range( 0, 2 ):
    RunTest( app, {
      'description': 'completion works when the elements come from the cache',
      'request': {
        'filetype'  : 'java',
        'filepath'  : ProjectPath( 'TestLauncher.java' ),
        'line_num'  : 32,
        'column_num': 15,
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'completion_start_column': 11,
          'completions': has_item(
            CompletionEntryMatcher(
              'doSomethingVaguelyUseful',
              'AbstractTestWidget.doSomethingVaguelyUseful() : void',
              {
                'kind': 'Method',
                'menu_text': 'doSomethingVaguelyUseful() : void',
              } )
          ),
          'errors': empty(),
        } )
      },
    } )


@WithRetry
@SharedYcmd
def GetCompletions_Package_test( app ):
  RunTest( app, {
    'description': 'completion works for package statements',
    'request': {
      'filetype'  : 'java',
      'filepath'  : ProjectPath( 'wobble', 'Wibble.java' ),
      'line_num'  : 1,
      'column_num': 18,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 9,
        'completions': contains_exactly(
          CompletionEntryMatcher( 'com.test.wobble', None, {
            'kind': 'Module'
          } ),
        ),
        'errors': empty(),
      } )
    },
  } )


@WithRetry
@SharedYcmd
def GetCompletions_Import_Class_test( app ):
  RunTest( app, {
    'description': 'completion works for import statements with a single class',
    'request': {
      'filetype'  : 'java',
      'filepath'  : ProjectPath( 'TestLauncher.java' ),
      'line_num'  : 3,
      'column_num': 34,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 34,
        'completions': contains_exactly(
          CompletionEntryMatcher( 'Tset', 'com.youcompleteme.testing.Tset', {
            'menu_text': 'Tset - com.youcompleteme.testing',
            'kind': 'Class',
          } )
        ),
        'errors': empty(),
      } )
    },
  } )


@WithRetry
@SharedYcmd
def GetCompletions_Import_Classes_test( app ):
  filepath = ProjectPath( 'TestLauncher.java' )
  RunTest( app, {
    'description': 'completion works for imports with multiple classes',
    'request': {
      'filetype'  : 'java',
      'filepath'  : filepath,
      'line_num'  : 4,
      'column_num': 52,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 52,
        'completions': contains_exactly(
          CompletionEntryMatcher( 'A;', None, {
            'menu_text': 'A - com.test.wobble',
            'kind': 'Class',
          } ),
          CompletionEntryMatcher( 'A_Very_Long_Class_Here;', None, {
            'menu_text': 'A_Very_Long_Class_Here - com.test.wobble',
            'kind': 'Class',
          } ),
          CompletionEntryMatcher( 'Waggle;', None, {
            'menu_text': 'Waggle - com.test.wobble',
            'kind': 'Interface',
          } ),
          CompletionEntryMatcher( 'Wibble;', None, {
            'menu_text': 'Wibble - com.test.wobble',
            'kind': 'Enum',
          } ),
        ),
        'errors': empty(),
      } )
    },
  } )


@WithRetry
@SharedYcmd
def GetCompletions_Import_ModuleAndClass_test( app ):
  filepath = ProjectPath( 'TestLauncher.java' )
  RunTest( app, {
    'description': 'completion works for imports of classes and modules',
    'request': {
      'filetype'  : 'java',
      'filepath'  : filepath,
      'line_num'  : 3,
      'column_num': 26,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 26,
        'completions': contains_exactly(
          CompletionEntryMatcher( 'testing.*;', None, {
            'menu_text': 'com.youcompleteme.testing',
            'kind': 'Module',
          } ),
          CompletionEntryMatcher( 'Test;', None, {
            'menu_text': 'Test - com.youcompleteme',
            'kind': 'Class',
          } ),
        ),
        'errors': empty(),
      } )
    },
  } )


@WithRetry
@SharedYcmd
def GetCompletions_WithFixIt_test( app ):
  filepath = ProjectPath( 'TestFactory.java' )
  RunTest( app, {
    'description': 'semantic completion with when additional textEdit',
    'request': {
      'filetype'  : 'java',
      'filepath'  : filepath,
      'line_num'  : 19,
      'column_num': 25,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 22,
        'completions': contains_inanyorder(
          CompletionEntryMatcher( 'CUTHBERT',
            'com.test.wobble.Wibble.CUTHBERT : Wibble',
            {
              'kind': 'EnumMember',
              'extra_data': has_entries( {
                'fixits': contains_exactly( has_entries( {
                  'chunks': contains_exactly(
                    ChunkMatcher( 'Wibble',
                                  LocationMatcher( filepath, 19, 15 ),
                                  LocationMatcher( filepath, 19, 21 ) ),
                    # OK, so it inserts the import
                    ChunkMatcher( '\n\nimport com.test.wobble.Wibble;\n\n',
                                  LocationMatcher( filepath, 1, 18 ),
                                  LocationMatcher( filepath, 3, 1 ) ),
                  ),
                } ) ),
              } ),
            } ),
        ),
        'errors': empty(),
      } )
    },
  } )


@WithRetry
@SharedYcmd
def GetCompletions_RejectMultiLineInsertion_test( app ):
  filepath = ProjectPath( 'TestLauncher.java' )
  RunTest( app, {
    'description': 'completion item discarded when not valid',
    'request': {
      'filetype'      : 'java',
      'filepath'      : filepath,
      'line_num'      : 28,
      'column_num'    : 16,
      'force_semantic': True
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 16,
        'completions': contains_exactly(
          CompletionEntryMatcher( 'TestLauncher',
            'com.test.TestLauncher.TestLauncher(int test)',
            {
              'kind': 'Constructor'
            } )
          # Note: There would be a suggestion here for the _real_ thing we want,
          # which is a TestLauncher.Launchable, but this would generate the code
          # for an anonymous inner class via a completion TextEdit (not
          # AdditionalTextEdit) which we don't support.
        ),
        'errors': empty(),
      } )
    },
  } )


@WithRetry
@SharedYcmd
def GetCompletions_UnicodeIdentifier_test( app ):
  filepath = PathToTestFile( DEFAULT_PROJECT_DIR,
                             'src',
                             'com',
                             'youcompleteme',
                             'Test.java' )
  RunTest( app, {
    'description': 'Completion works for unicode identifier',
    'request': {
      'filetype'      : 'java',
      'filepath'      : filepath,
      'line_num'      : 16,
      'column_num'    : 35,
      'force_semantic': True
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 35,
        'completions': has_items(
          CompletionEntryMatcher( 'a_test', 'Test.TéstClass.a_test : int', {
            'kind': 'Field',
            'detailed_info': 'a_test : int\n\n',
          } ),
          CompletionEntryMatcher( 'åtest', 'Test.TéstClass.åtest : boolean', {
            'kind': 'Field',
            'detailed_info': 'åtest : boolean\n\n',
          } ),
          CompletionEntryMatcher( 'testywesty',
                                  'Test.TéstClass.testywesty : String',
                                  {
                                    'kind': 'Field',
                                  } ),
        ),
        'errors': empty(),
      } )
    },
  } )


@WithRetry
@SharedYcmd
def GetCompletions_ResolveFailed_test( app ):
  filepath = PathToTestFile( DEFAULT_PROJECT_DIR,
                             'src',
                             'com',
                             'youcompleteme',
                             'Test.java' )

  from ycmd.completers.language_server import language_server_protocol as lsapi

  def BrokenResolveCompletion( request_id, completion ):
    return lsapi.BuildRequest( request_id, 'completionItem/FAIL', completion )

  with patch( 'ycmd.completers.language_server.language_server_protocol.'
              'ResolveCompletion',
              side_effect = BrokenResolveCompletion ):
    RunTest( app, {
      'description': 'Completion works for unicode identifier',
      'request': {
        'filetype'      : 'java',
        'filepath'      : filepath,
        'line_num'      : 16,
        'column_num'    : 35,
        'force_semantic': True
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'completion_start_column': 35,
          'completions': has_items(
            CompletionEntryMatcher( 'a_test', 'Test.TéstClass.a_test : int', {
              'kind': 'Field',
              'detailed_info': 'a_test : int\n\n',
            } ),
            CompletionEntryMatcher( 'åtest', 'Test.TéstClass.åtest : boolean', {
              'kind': 'Field',
              'detailed_info': 'åtest : boolean\n\n',
            } ),
            CompletionEntryMatcher( 'testywesty',
                                    'Test.TéstClass.testywesty : String',
                                    {
                                      'kind': 'Field',
                                    } ),
          ),
          'errors': empty(),
        } )
      },
    } )


@WithRetry
@IsolatedYcmd()
def GetCompletions_ServerNotInitialized_test( app ):
  filepath = PathToTestFile( 'simple_eclipse_project',
                             'src',
                             'com',
                             'test',
                             'AbstractTestWidget.java' )

  completer = handlers._server_state.GetFiletypeCompleter( [ 'java' ] )


  def MockHandleInitializeInPollThread( self, response ):
    pass


  with patch.object( completer,
                     '_HandleInitializeInPollThread',
                     MockHandleInitializeInPollThread ):
    RunTest( app, {
      'description': 'Completion works for unicode identifier',
      'request': {
        'filetype'      : 'java',
        'filepath'      : filepath,
        'line_num'      : 16,
        'column_num'    : 35,
        'force_semantic': True
      },
      'expect': {
        'response': requests.codes.ok,
        'data': has_entries( {
          'errors': empty(),
          'completions': empty(),
          'completion_start_column': 6
        } ),
      }
    } )


@WithRetry
@SharedYcmd
def GetCompletions_MoreThan10_NoResolve_ThenResolve_test( app ):
  ClearCompletionsCache()
  request, response = RunTest( app, {
    'description': "More than 10 candiates after filtering, don't resolve",
    'request': {
      'filetype'  : 'java',
      'filepath'  : ProjectPath( 'TestWithDocumentation.java' ),
      'line_num'  : 6,
      'column_num': 7,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': has_item(
          CompletionEntryMatcher(
            'useAString',
            'MethodsWithDocumentation.useAString(String s) : void',
            {
              'kind': 'Method',
              # This is the un-resolved info (no documentation)
              'detailed_info': 'useAString(String s) : void\n\n',
              'extra_data': has_entries( {
                'resolve': instance_of( int )
              } )
            }
          ),
        ),
        'completion_start_column': 7,
        'errors': empty(),
      } )
    },
  } )

  # We know the item we want is there, pull out the resolve ID
  resolve = None
  for item in response[ 'completions' ]:
    if item[ 'insertion_text' ] == 'useAString':
      resolve = item[ 'extra_data' ][ 'resolve' ]
      break

  assert resolve is not None

  request[ 'resolve' ] = resolve
  # Do this twice to prove that the request is idempotent
  for i in range( 2 ):
    response = app.post_json( '/resolve_completion', request ).json

    print( f"Resolve response: { pformat( response ) }" )

    nl = os.linesep
    assert_that( response, has_entries( {
      'completion': CompletionEntryMatcher(
          'useAString',
          'MethodsWithDocumentation.useAString(String s) : void',
          {
            'kind': 'Method',
            # This is the resolved info (no documentation)
            'detailed_info': 'useAString(String s) : void\n'
                             '\n'
                             f'Multiple lines of description here.{ nl }'
                             f'{ nl }'
                             f' *  **Parameters:**{ nl }'
                             f'    { nl }'
                             f'     *  **s** a string'
          }
        ),
      'errors': empty(),
    } ) )

    # The item is resoled
    assert_that( response[ 'completion' ], is_not( has_key( 'resolve' ) ) )
    assert_that( response[ 'completion' ], is_not( has_key( 'item' ) ) )



@WithRetry
@SharedYcmd
def GetCompletions_FewerThan10_Resolved_test( app ):
  ClearCompletionsCache()
  nl = os.linesep
  request, response = RunTest( app, {
    'description': "More than 10 candiates after filtering, don't resolve",
    'request': {
      'filetype'  : 'java',
      'filepath'  : ProjectPath( 'TestWithDocumentation.java' ),
      'line_num'  : 6,
      'column_num': 10,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': has_item(
          CompletionEntryMatcher(
            'useAString',
            'MethodsWithDocumentation.useAString(String s) : void',
            {
              'kind': 'Method',
              # This is the resolved info (no documentation)
              'detailed_info': 'useAString(String s) : void\n'
                               '\n'
                               f'Multiple lines of description here.{ nl }'
                               f'{ nl }'
                               f' *  **Parameters:**{ nl }'
                               f'    { nl }'
                               f'     *  **s** a string'
            }
          ),
        ),
        'completion_start_column': 7,
        'errors': empty(),
      } )
    },
  } )
  # All items are resolved
  assert_that( response[ 'completions' ][ 0 ], is_not( has_key( 'resolve' ) ) )
  assert_that( response[ 'completions' ][ 0 ], is_not( has_key( 'item' ) ) )
  assert_that( response[ 'completions' ][ -1 ], is_not( has_key( 'resolve' ) ) )
  assert_that( response[ 'completions' ][ -1 ], is_not( has_key( 'item' ) ) )



@WithRetry
@SharedYcmd
def GetCompletions_MoreThan10_NoResolve_ThenResolveCacheBad_test( app ):
  ClearCompletionsCache()
  request, response = RunTest( app, {
    'description': "More than 10 candiates after filtering, don't resolve",
    'request': {
      'filetype'  : 'java',
      'filepath'  : ProjectPath( 'TestWithDocumentation.java' ),
      'line_num'  : 6,
      'column_num': 7,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': has_item(
          CompletionEntryMatcher(
            'useAString',
            'MethodsWithDocumentation.useAString(String s) : void',
            {
              'kind': 'Method',
              # This is the un-resolved info (no documentation)
              'detailed_info': 'useAString(String s) : void\n\n',
              'extra_data': has_entries( {
                'resolve': instance_of( int )
              } )
            }
          ),
        ),
        'completion_start_column': 7,
        'errors': empty(),
      } )
    },
  } )

  # We know the item we want is there, pull out the resolve ID
  resolve = None
  for item in response[ 'completions' ]:
    if item[ 'insertion_text' ] == 'useAString':
      resolve = item[ 'extra_data' ][ 'resolve' ]
      break

  assert resolve is not None

  request[ 'resolve' ] = resolve
  # Use a different position - should mean the cache is not valid for request
  request[ 'column_num' ] = 20
  response = app.post_json( '/resolve_completion', request ).json

  print( f"Resolve response: { pformat( response ) }" )

  assert_that( response, has_entries( {
    'completion': None,
    'errors': contains_exactly( ErrorMatcher( CompletionsChanged ) )
  } ) )



@WithRetry
@UnixOnly
@SharedYcmd
def GetCompletions_MoreThan10ForceSemantic_test( app ):
  ClearCompletionsCache()
  RunTest( app, {
    'description': 'When forcing we pass the query, which reduces candidates',
    'request': {
      'filetype'  : 'java',
      'filepath'  : ProjectPath( 'TestLauncher.java' ),
      'line_num'  : 4,
      'column_num': 15,
      'force_semantic': True
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': contains_exactly(
          CompletionEntryMatcher( 'com.youcompleteme.*;', None, {
            'kind': 'Module',
            'detailed_info': 'com.youcompleteme\n\n',
          } ),
          CompletionEntryMatcher( 'com.youcompleteme.testing.*;', None, {
            'kind': 'Module',
            'detailed_info': 'com.youcompleteme.testing\n\n',
          } ),
        ),
        'completion_start_column': 8,
        'errors': empty(),
      } )
    },
  } )


@WithRetry
@SharedYcmd
def GetCompletions_ForceAtTopLevel_NoImport_test( app ):
  RunTest( app, {
    'description': 'When forcing semantic completion, pass the query to server',
    'request': {
      'filetype'  : 'java',
      'filepath'  : ProjectPath( 'TestWidgetImpl.java' ),
      'line_num'  : 30,
      'column_num': 20,
      'force_semantic': True,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': contains_exactly(
          CompletionEntryMatcher( 'TestFactory', None, {
            'kind': 'Class',
            'menu_text': 'TestFactory - com.test',
          } ),
        ),
        'completion_start_column': 12,
        'errors': empty(),
      } )
    },
  } )


@WithRetry
@SharedYcmd
def GetCompletions_NoForceAtTopLevel_NoImport_test( app ):
  RunTest( app, {
    'description': 'When not forcing semantic completion, use no context',
    'request': {
      'filetype'  : 'java',
      'filepath'  : ProjectPath( 'TestWidgetImpl.java' ),
      'line_num'  : 30,
      'column_num': 20,
      'force_semantic': False,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': contains_exactly(
          CompletionEntryMatcher( 'TestFactory', '[ID]', {} ),
        ),
        'completion_start_column': 12,
        'errors': empty(),
      } )
    },
  } )


@WithRetry
@SharedYcmd
def GetCompletions_ForceAtTopLevel_WithImport_test( app ):
  filepath = ProjectPath( 'TestWidgetImpl.java' )
  RunTest( app, {
    'description': 'Top level completions have import FixIts',
    'request': {
      'filetype'  : 'java',
      'filepath'  : filepath,
      'line_num'  : 34,
      'column_num': 16,
      'force_semantic': True,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completions': has_item(
          CompletionEntryMatcher( 'InputStreamReader', None, {
            'kind': 'Class',
            'menu_text': 'InputStreamReader - java.io',
            'extra_data': has_entries( {
              'fixits': contains_exactly( has_entries( {
                'chunks': contains_exactly(
                  ChunkMatcher( '\n\nimport java.io.InputStreamReader;\n\n',
                                LocationMatcher( filepath, 1, 18 ),
                                LocationMatcher( filepath, 3, 1 ) ),
                ),
              } ) ),
            } ),
          } ),
        ),
        'completion_start_column': 12,
        'errors': empty(),
      } )
    },
  } )


@WithRetry
@SharedYcmd
def GetCompletions_UseServerTriggers_test( app ):
  filepath = ProjectPath( 'TestWidgetImpl.java' )

  RunTest( app, {
    'description': 'We use the semantic triggers from the server (@ here)',
    'request': {
      'filetype'  : 'java',
      'filepath'  : filepath,
      'line_num'  : 24,
      'column_num': 7,
      'force_semantic': False,
    },
    'expect': {
      'response': requests.codes.ok,
      'data': has_entries( {
        'completion_start_column': 4,
        'completions': has_item(
          CompletionEntryMatcher( 'Override', None, {
            'kind': 'Interface',
            'menu_text': 'Override - java.lang',
          } )
        )
      } )
    }
  } )


def Dummy_test():
  # Workaround for https://github.com/pytest-dev/pytest-rerunfailures/issues/51
  assert True
