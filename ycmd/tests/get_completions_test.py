# encoding: utf-8
#
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

from hamcrest import ( assert_that,
                       contains,
                       contains_inanyorder,
                       empty,
                       equal_to,
                       has_entries,
                       has_items )
from mock import patch
from nose.tools import eq_

from ycmd.tests import IsolatedYcmd, SharedYcmd, PathToTestFile
from ycmd.tests.test_utils import ( BuildRequest, CompletionEntryMatcher,
                                    DummyCompleter, PatchCompleter )


@SharedYcmd
def GetCompletions_RequestValidation_NoLineNumException_test( app ):
  response = app.post_json( '/semantic_completion_available', {
    'column_num': 0,
    'filepath': '/foo',
    'file_data': {
      '/foo': {
        'filetypes': [ 'text' ],
        'contents': 'zoo'
      }
    }
  }, status = '5*', expect_errors = True )
  response.mustcontain( 'missing', 'line_num' )


@SharedYcmd
def GetCompletions_IdentifierCompleter_Works_test( app ):
  event_data = BuildRequest( contents = 'foo foogoo ba',
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )

  # query is 'oo'
  completion_data = BuildRequest( contents = 'oo foo foogoo ba',
                                  column_num = 3 )
  response_data = app.post_json( '/completions', completion_data ).json

  eq_( 1, response_data[ 'completion_start_column' ] )
  assert_that(
    response_data[ 'completions' ],
    has_items( CompletionEntryMatcher( 'foo', '[ID]' ),
               CompletionEntryMatcher( 'foogoo', '[ID]' ) )
  )


@IsolatedYcmd( { 'min_num_identifier_candidate_chars': 4 } )
def GetCompletions_IdentifierCompleter_FilterShortCandidates_test( app ):
  event_data = BuildRequest( contents = 'foo foogoo gooo',
                             event_name = 'FileReadyToParse' )
  app.post_json( '/event_notification', event_data )

  completion_data = BuildRequest( contents = 'oo', column_num = 3 )
  response = app.post_json( '/completions',
                            completion_data ).json[ 'completions' ]

  assert_that( response,
               contains_inanyorder( CompletionEntryMatcher( 'foogoo' ),
                                    CompletionEntryMatcher( 'gooo' ) ) )


@SharedYcmd
def GetCompletions_IdentifierCompleter_StartColumn_AfterWord_test( app ):
  completion_data = BuildRequest( contents = 'oo foo foogoo ba',
                                  column_num = 11 )
  response_data = app.post_json( '/completions', completion_data ).json
  eq_( 8, response_data[ 'completion_start_column' ] )


@SharedYcmd
def GetCompletions_IdentifierCompleter_WorksForSpecialIdentifierChars_test(
  app ):
  contents = """
    textarea {
      font-family: sans-serif;
      font-size: 12px;
    }"""
  event_data = BuildRequest( contents = contents,
                             filetype = 'css',
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )

  # query is 'fo'
  completion_data = BuildRequest( contents = 'fo ' + contents,
                                  filetype = 'css',
                                  column_num = 3 )
  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]

  assert_that(
    results,
    has_items( CompletionEntryMatcher( 'font-size', '[ID]' ),
               CompletionEntryMatcher( 'font-family', '[ID]' ) )
  )


@SharedYcmd
def GetCompletions_IdentifierCompleter_Unicode_InLine_test( app ):
  contents = """
    This is some text cøntaining unicøde
  """

  event_data = BuildRequest( contents = contents,
                             filetype = 'css',
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )

  # query is 'tx'
  completion_data = BuildRequest( contents = 'tx ' + contents,
                                  filetype = 'css',
                                  column_num = 3 )
  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]

  assert_that(
    results,
    has_items( CompletionEntryMatcher( 'text', '[ID]' ) )
  )


@SharedYcmd
def GetCompletions_IdentifierCompleter_UnicodeQuery_InLine_test( app ):
  contents = """
    This is some text cøntaining unicøde
  """

  event_data = BuildRequest( contents = contents,
                             filetype = 'css',
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )

  # query is 'cø'
  completion_data = BuildRequest( contents = 'cø ' + contents,
                                  filetype = 'css',
                                  column_num = 4 )
  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]

  assert_that(
    results,
    has_items( CompletionEntryMatcher( 'cøntaining', '[ID]' ),
               CompletionEntryMatcher( 'unicøde', '[ID]' ) )
  )


@IsolatedYcmd()
def GetCompletions_IdentifierCompleter_Unicode_MultipleCodePoints_test( app ):
  # The first ō is on one code point while the second is on two ("o" + combining
  # macron character).
  event_data = BuildRequest( contents = 'fōo\nfōo',
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )

  # query is 'fo'
  completion_data = BuildRequest( contents = 'fōo\nfōo\nfo',
                                  line_num = 3,
                                  column_num = 3 )
  response_data = app.post_json( '/completions', completion_data ).json

  eq_( 1, response_data[ 'completion_start_column' ] )
  assert_that(
    response_data[ 'completions' ],
    has_items( CompletionEntryMatcher( 'fōo', '[ID]' ),
               CompletionEntryMatcher( 'fōo', '[ID]' ) )
  )


@SharedYcmd
@patch( 'ycmd.tests.test_utils.DummyCompleter.CandidatesList',
        return_value = [ 'foo', 'bar', 'qux' ] )
def GetCompletions_ForceSemantic_Works_test( app, *args ):
  with PatchCompleter( DummyCompleter, 'dummy_filetype' ):
    completion_data = BuildRequest( filetype = 'dummy_filetype',
                                    force_semantic = True )

    results = app.post_json( '/completions',
                             completion_data ).json[ 'completions' ]
    assert_that( results, has_items( CompletionEntryMatcher( 'foo' ),
                                     CompletionEntryMatcher( 'bar' ),
                                     CompletionEntryMatcher( 'qux' ) ) )


@SharedYcmd
def GetCompletions_ForceSemantic_NoSemanticCompleter_test( app, *args ):
  event_data = BuildRequest( event_name = 'FileReadyToParse',
                             filetype = 'dummy_filetype',
                             contents = 'complete_this_word\ncom' )
  app.post_json( '/event_notification', event_data )

  completion_data = BuildRequest( filetype = 'dummy_filetype',
                                  force_semantic = True,
                                  contents = 'complete_this_word\ncom',
                                  line_number = 2,
                                  column_num = 4 )
  results = app.post_json( '/completions', completion_data ).json
  assert_that( results, has_entries( {
    'completions': empty(),
    'errors': empty(),
  } ) )

  # For proof, show that non-forced completion would return identifiers
  completion_data = BuildRequest( filetype = 'dummy_filetype',
                                  contents = 'complete_this_word\ncom',
                                  line_number = 2,
                                  column_num = 4 )
  results = app.post_json( '/completions', completion_data ).json
  assert_that( results, has_entries( {
    'completions': contains(
      CompletionEntryMatcher( 'com' ),
      CompletionEntryMatcher( 'complete_this_word' ) ),
    'errors': empty(),
  } ) )


@SharedYcmd
def GetCompletions_IdentifierCompleter_SyntaxKeywordsAdded_test( app ):
  event_data = BuildRequest( event_name = 'FileReadyToParse',
                             syntax_keywords = [ 'foo', 'bar', 'zoo' ] )

  app.post_json( '/event_notification', event_data )

  completion_data = BuildRequest( contents = 'oo ',
                                  column_num = 3 )

  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]
  assert_that( results,
               has_items( CompletionEntryMatcher( 'foo' ),
                          CompletionEntryMatcher( 'zoo' ) ) )


@SharedYcmd
def GetCompletions_IdentifierCompleter_TagsAdded_test( app ):
  event_data = BuildRequest( event_name = 'FileReadyToParse',
                             tag_files = [ PathToTestFile( 'basic.tags' ) ] )
  app.post_json( '/event_notification', event_data )

  completion_data = BuildRequest( contents = 'oo',
                                  column_num = 3,
                                  filetype = 'cpp' )
  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]
  assert_that( results,
               has_items( CompletionEntryMatcher( 'foosy' ),
                          CompletionEntryMatcher( 'fooaaa' ) ) )


@SharedYcmd
def GetCompletions_IdentifierCompleter_JustFinishedIdentifier_test( app ):
  event_data = BuildRequest( event_name = 'CurrentIdentifierFinished',
                             column_num = 4,
                             contents = 'foo' )
  app.post_json( '/event_notification', event_data )

  completion_data = BuildRequest( contents = 'oo', column_num = 3 )
  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]
  assert_that( results,
               has_items( CompletionEntryMatcher( 'foo' ) ) )


@IsolatedYcmd()
def GetCompletions_IdentifierCompleter_IgnoreFinishedIdentifierInString_test(
  app ):

  event_data = BuildRequest( event_name = 'CurrentIdentifierFinished',
                             column_num = 6,
                             contents = '"foo"' )

  app.post_json( '/event_notification', event_data )

  completion_data = BuildRequest( contents = 'oo', column_num = 3 )
  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]
  assert_that( results, empty() )


@SharedYcmd
def GetCompletions_IdentifierCompleter_IdentifierUnderCursor_test( app ):
  event_data = BuildRequest( event_name = 'InsertLeave',
                             column_num = 2,
                             contents = 'foo' )
  app.post_json( '/event_notification', event_data )

  completion_data = BuildRequest( contents = 'oo', column_num = 3 )
  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]
  assert_that( results,
               has_items( CompletionEntryMatcher( 'foo' ) ) )


@IsolatedYcmd()
def GetCompletions_IdentifierCompleter_IgnoreCursorIdentifierInString_test(
  app ):

  event_data = BuildRequest( event_name = 'InsertLeave',
                             column_num = 3,
                             contents = '"foo"' )
  app.post_json( '/event_notification', event_data )

  completion_data = BuildRequest( contents = 'oo', column_num = 3 )
  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]
  assert_that( results, empty() )


@SharedYcmd
def GetCompletions_FilenameCompleter_Works_test( app ):
  filepath = PathToTestFile( 'filename_completer', 'test.foo' )
  completion_data = BuildRequest( filepath = filepath,
                                  contents = './',
                                  column_num = 3 )
  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]
  assert_that( results,
               has_items( CompletionEntryMatcher( 'inner_dir', '[Dir]' ) ) )


@SharedYcmd
def GetCompletions_FilenameCompleter_FallBackToIdentifierCompleter_test( app ):
  filepath = PathToTestFile( 'filename_completer', 'test.foo' )
  event_data = BuildRequest( filepath = filepath,
                             contents = './nonexisting_dir',
                             filetype = 'foo',
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )

  completion_data = BuildRequest( filepath = filepath,
                                  contents = './nonexisting_dir nd',
                                  filetype = 'foo',
                                  column_num = 21 )

  assert_that(
    app.post_json( '/completions', completion_data ).json[ 'completions' ],
    has_items( CompletionEntryMatcher( 'nonexisting_dir', '[ID]' ) )
  )


@SharedYcmd
def GetCompletions_UltiSnipsCompleter_Works_test( app ):
  event_data = BuildRequest(
    event_name = 'BufferVisit',
    ultisnips_snippets = [
        { 'trigger': 'foo', 'description': 'bar' },
        { 'trigger': 'zoo', 'description': 'goo' },
    ] )

  app.post_json( '/event_notification', event_data )

  completion_data = BuildRequest( contents = 'oo ',
                                  column_num = 3 )

  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]
  assert_that(
    results,
    has_items(
      CompletionEntryMatcher( 'foo', extra_menu_info='<snip> bar' ),
      CompletionEntryMatcher( 'zoo', extra_menu_info='<snip> goo' )
    )
  )


@IsolatedYcmd( { 'use_ultisnips_completer': 0 } )
def GetCompletions_UltiSnipsCompleter_UnusedWhenOffWithOption_test( app ):
  event_data = BuildRequest(
    event_name = 'BufferVisit',
    ultisnips_snippets = [
        { 'trigger': 'foo', 'description': 'bar' },
        { 'trigger': 'zoo', 'description': 'goo' },
    ] )

  app.post_json( '/event_notification', event_data )

  completion_data = BuildRequest( contents = 'oo ', column_num = 3 )

  eq_( [],
       app.post_json( '/completions',
                      completion_data ).json[ 'completions' ] )


@IsolatedYcmd( { 'semantic_triggers': { 'dummy_filetype': [ '_' ] } } )
@patch( 'ycmd.tests.test_utils.DummyCompleter.CandidatesList',
        return_value = [ 'some_candidate' ] )
def GetCompletions_SemanticCompleter_WorksWhenTriggerIsIdentifier_test(
  app, *args ):
  with PatchCompleter( DummyCompleter, 'dummy_filetype' ):
    completion_data = BuildRequest( filetype = 'dummy_filetype',
                                    contents = 'some_can',
                                    column_num = 9 )

    results = app.post_json( '/completions',
                             completion_data ).json[ 'completions' ]
    assert_that(
      results,
      has_items( CompletionEntryMatcher( 'some_candidate' ) )
    )


@SharedYcmd
@patch( 'ycmd.tests.test_utils.DummyCompleter.ShouldUseNowInner',
        return_value = True )
@patch( 'ycmd.tests.test_utils.DummyCompleter.CandidatesList',
        return_value = [ 'attribute' ] )
def GetCompletions_CacheIsValid_test(
  app, candidates_list, *args ):
  with PatchCompleter( DummyCompleter, 'dummy_filetype' ):
    completion_data = BuildRequest( filetype = 'dummy_filetype',
                                    contents = 'object.attr',
                                    line_num = 1,
                                    column_num = 12 )

    results = app.post_json( '/completions',
                             completion_data ).json[ 'completions' ]
    assert_that(
      results,
      has_items( CompletionEntryMatcher( 'attribute' ) )
    )

    completion_data = BuildRequest( filetype = 'dummy_filetype',
                                    contents = 'object.attri',
                                    line_num = 1,
                                    column_num = 13 )

    results = app.post_json( '/completions',
                             completion_data ).json[ 'completions' ]
    assert_that(
      results,
      has_items( CompletionEntryMatcher( 'attribute' ) )
    )

    # We ask for candidates only once because of cache.
    assert_that( candidates_list.call_count, equal_to( 1 ) )


@SharedYcmd
@patch( 'ycmd.tests.test_utils.DummyCompleter.ShouldUseNowInner',
        return_value = True )
@patch( 'ycmd.tests.test_utils.DummyCompleter.CandidatesList',
        side_effect = [ [ 'attributeA' ], [ 'attributeB' ] ] )
def GetCompletions_CacheIsNotValid_DifferentLineNumber_test(
  app, candidates_list, *args ):
  with PatchCompleter( DummyCompleter, 'dummy_filetype' ):
    completion_data = BuildRequest( filetype = 'dummy_filetype',
                                    contents = 'objectA.attr\n'
                                               'objectB.attr',
                                    line_num = 1,
                                    column_num = 12 )

    results = app.post_json( '/completions',
                             completion_data ).json[ 'completions' ]
    assert_that(
      results,
      has_items( CompletionEntryMatcher( 'attributeA' ) )
    )

    completion_data = BuildRequest( filetype = 'dummy_filetype',
                                    contents = 'objectA.\n'
                                               'objectB.',
                                    line_num = 2,
                                    column_num = 12 )

    results = app.post_json( '/completions',
                             completion_data ).json[ 'completions' ]
    assert_that(
      results,
      has_items( CompletionEntryMatcher( 'attributeB' ) )
    )

    # We ask for candidates twice because of cache invalidation:
    # line numbers are different between requests.
    assert_that( candidates_list.call_count, equal_to( 2 ) )


@SharedYcmd
@patch( 'ycmd.tests.test_utils.DummyCompleter.ShouldUseNowInner',
        return_value = True )
@patch( 'ycmd.tests.test_utils.DummyCompleter.CandidatesList',
        side_effect = [ [ 'attributeA' ], [ 'attributeB' ] ] )
def GetCompletions_CacheIsNotValid_DifferentStartColumn_test(
  app, candidates_list, *args ):
  with PatchCompleter( DummyCompleter, 'dummy_filetype' ):
    # Start column is 9
    completion_data = BuildRequest( filetype = 'dummy_filetype',
                                    contents = 'objectA.attr',
                                    line_num = 1,
                                    column_num = 12 )

    results = app.post_json( '/completions',
                             completion_data ).json[ 'completions' ]
    assert_that(
      results,
      has_items( CompletionEntryMatcher( 'attributeA' ) )
    )

    # Start column is 8
    completion_data = BuildRequest( filetype = 'dummy_filetype',
                                    contents = 'object.attri',
                                    line_num = 1,
                                    column_num = 12 )

    results = app.post_json( '/completions',
                             completion_data ).json[ 'completions' ]
    assert_that(
      results,
      has_items( CompletionEntryMatcher( 'attributeB' ) )
    )

    # We ask for candidates twice because of cache invalidation:
    # start columns are different between requests.
    assert_that( candidates_list.call_count, equal_to( 2 ) )


@SharedYcmd
@patch( 'ycmd.tests.test_utils.DummyCompleter.ShouldUseNowInner',
        return_value = True )
@patch( 'ycmd.tests.test_utils.DummyCompleter.CandidatesList',
        side_effect = [ [ 'attributeA' ], [ 'attributeB' ] ] )
def GetCompletions_CacheIsNotValid_DifferentForceSemantic_test(
  app, candidates_list, *args ):
  with PatchCompleter( DummyCompleter, 'dummy_filetype' ):
    completion_data = BuildRequest( filetype = 'dummy_filetype',
                                    contents = 'objectA.attr',
                                    line_num = 1,
                                    column_num = 12,
                                    force_semantic = True )

    results = app.post_json( '/completions',
                             completion_data ).json[ 'completions' ]
    assert_that(
      results,
      has_items( CompletionEntryMatcher( 'attributeA' ) )
    )

    completion_data = BuildRequest( filetype = 'dummy_filetype',
                                    contents = 'objectA.attr',
                                    line_num = 1,
                                    column_num = 12 )

    results = app.post_json( '/completions',
                             completion_data ).json[ 'completions' ]
    assert_that(
      results,
      has_items( CompletionEntryMatcher( 'attributeB' ) )
    )

    # We ask for candidates twice because of cache invalidation:
    # semantic completion is forced for one of the request, not the other.
    assert_that( candidates_list.call_count, equal_to( 2 ) )


@SharedYcmd
@patch( 'ycmd.tests.test_utils.DummyCompleter.ShouldUseNowInner',
        return_value = True )
@patch( 'ycmd.tests.test_utils.DummyCompleter.CandidatesList',
        side_effect = [ [ 'attributeA' ], [ 'attributeB' ] ] )
def GetCompletions_CacheIsNotValid_DifferentContents_test(
  app, candidates_list, *args ):
  with PatchCompleter( DummyCompleter, 'dummy_filetype' ):
    completion_data = BuildRequest( filetype = 'dummy_filetype',
                                    contents = 'objectA = foo\n'
                                               'objectA.attr',
                                    line_num = 2,
                                    column_num = 12 )

    results = app.post_json( '/completions',
                             completion_data ).json[ 'completions' ]
    assert_that(
      results,
      has_items( CompletionEntryMatcher( 'attributeA' ) )
    )

    completion_data = BuildRequest( filetype = 'dummy_filetype',
                                    contents = 'objectA = bar\n'
                                               'objectA.attr',
                                    line_num = 2,
                                    column_num = 12 )

    results = app.post_json( '/completions',
                             completion_data ).json[ 'completions' ]
    assert_that(
      results,
      has_items( CompletionEntryMatcher( 'attributeB' ) )
    )

    # We ask for candidates twice because of cache invalidation:
    # both requests have the same cursor position and current line but file
    # contents are different.
    assert_that( candidates_list.call_count, equal_to( 2 ) )


@SharedYcmd
@patch( 'ycmd.tests.test_utils.DummyCompleter.ShouldUseNowInner',
        return_value = True )
@patch( 'ycmd.tests.test_utils.DummyCompleter.CandidatesList',
        side_effect = [ [ 'attributeA' ], [ 'attributeB' ] ] )
def GetCompletions_CacheIsNotValid_DifferentNumberOfLines_test(
  app, candidates_list, *args ):
  with PatchCompleter( DummyCompleter, 'dummy_filetype' ):
    completion_data = BuildRequest( filetype = 'dummy_filetype',
                                    contents = 'objectA.attr\n'
                                               'objectB.attr',
                                    line_num = 1,
                                    column_num = 12 )

    results = app.post_json( '/completions',
                             completion_data ).json[ 'completions' ]
    assert_that(
      results,
      has_items( CompletionEntryMatcher( 'attributeA' ) )
    )

    completion_data = BuildRequest( filetype = 'dummy_filetype',
                                    contents = 'objectA.attr',
                                    line_num = 1,
                                    column_num = 12 )

    results = app.post_json( '/completions',
                             completion_data ).json[ 'completions' ]
    assert_that(
      results,
      has_items( CompletionEntryMatcher( 'attributeB' ) )
    )

    # We ask for candidates twice because of cache invalidation:
    # both requests have the same cursor position and current line but the
    # number of lines in the current file is different.
    assert_that( candidates_list.call_count, equal_to( 2 ) )


@SharedYcmd
@patch( 'ycmd.tests.test_utils.DummyCompleter.ShouldUseNowInner',
        return_value = True )
@patch( 'ycmd.tests.test_utils.DummyCompleter.CandidatesList',
        side_effect = [ [ 'attributeA' ], [ 'attributeB' ] ] )
def GetCompletions_CacheIsNotValid_DifferentFileData_test(
  app, candidates_list, *args ):
  with PatchCompleter( DummyCompleter, 'dummy_filetype' ):
    completion_data = BuildRequest( filetype = 'dummy_filetype',
                                    contents = 'objectA.attr',
                                    line_num = 1,
                                    column_num = 12,
                                    file_data = {
                                      '/bar': {
                                        'contents': 'objectA = foo',
                                        'filetypes': [ 'dummy_filetype' ]
                                      }
                                    } )

    results = app.post_json( '/completions',
                             completion_data ).json[ 'completions' ]
    assert_that(
      results,
      has_items( CompletionEntryMatcher( 'attributeA' ) )
    )

    completion_data = BuildRequest( filetype = 'dummy_filetype',
                                    contents = 'objectA.attr',
                                    line_num = 1,
                                    column_num = 12,
                                    file_data = {
                                      '/bar': {
                                        'contents': 'objectA = bar',
                                        'filetypes': [ 'dummy_filetype' ]
                                      }
                                    } )

    results = app.post_json( '/completions',
                             completion_data ).json[ 'completions' ]
    assert_that(
      results,
      has_items( CompletionEntryMatcher( 'attributeB' ) )
    )

    # We ask for candidates twice because of cache invalidation:
    # both requests have the same cursor position and contents for the current
    # file but different contents for another file.
    assert_that( candidates_list.call_count, equal_to( 2 ) )


@SharedYcmd
@patch( 'ycmd.tests.test_utils.DummyCompleter.ShouldUseNowInner',
        return_value = True )
@patch( 'ycmd.tests.test_utils.DummyCompleter.CandidatesList',
        side_effect = [ [ 'attributeA' ], [ 'attributeB' ] ] )
def GetCompletions_CacheIsNotValid_DifferentExtraConfData_test(
  app, candidates_list, *args ):
  with PatchCompleter( DummyCompleter, 'dummy_filetype' ):
    completion_data = BuildRequest( filetype = 'dummy_filetype',
                                    contents = 'objectA.attr',
                                    line_num = 1,
                                    column_num = 12 )

    results = app.post_json( '/completions',
                             completion_data ).json[ 'completions' ]
    assert_that(
      results,
      has_items( CompletionEntryMatcher( 'attributeA' ) )
    )

    completion_data = BuildRequest( filetype = 'dummy_filetype',
                                    contents = 'objectA.attr',
                                    line_num = 1,
                                    column_num = 12,
                                    extra_conf_data = { 'key': 'value' } )

    results = app.post_json( '/completions',
                             completion_data ).json[ 'completions' ]
    assert_that(
      results,
      has_items( CompletionEntryMatcher( 'attributeB' ) )
    )

    # We ask for candidates twice because of cache invalidation:
    # both requests are identical except the extra conf data.
    assert_that( candidates_list.call_count, equal_to( 2 ) )


@SharedYcmd
@patch( 'ycmd.tests.test_utils.DummyCompleter.ShouldUseNowInner',
        return_value = True )
@patch( 'ycmd.tests.test_utils.DummyCompleter.CandidatesList',
        return_value = [ 'aba', 'cbc' ] )
def GetCompletions_FilterThenReturnFromCache_test( app,
                                                   candidates_list,
                                                   *args ):

  with PatchCompleter( DummyCompleter, 'dummy_filetype' ):
    # First, fill the cache with an empty query
    completion_data = BuildRequest( filetype = 'dummy_filetype',
                                    contents = 'objectA.',
                                    line_num = 1,
                                    column_num = 9 )

    results = app.post_json( '/completions',
                             completion_data ).json[ 'completions' ]
    assert_that( results,
                 has_items( CompletionEntryMatcher( 'aba' ),
                            CompletionEntryMatcher( 'cbc' ) ) )

    # Now, filter them. This causes them to be converted to bytes and back
    completion_data = BuildRequest( filetype = 'dummy_filetype',
                                    contents = 'objectA.c',
                                    line_num = 1,
                                    column_num = 10 )

    results = app.post_json( '/completions',
                             completion_data ).json[ 'completions' ]
    assert_that( results,
                 has_items( CompletionEntryMatcher( 'cbc' ) ) )

    # Finally, request the original (unfiltered) set again. Ensure that we get
    # proper results (not some bytes objects)
    completion_data = BuildRequest( filetype = 'dummy_filetype',
                                    contents = 'objectA.',
                                    line_num = 1,
                                    column_num = 9 )

    results = app.post_json( '/completions',
                             completion_data ).json[ 'completions' ]
    assert_that( results,
                 has_items( CompletionEntryMatcher( 'aba' ),
                            CompletionEntryMatcher( 'cbc' ) ) )

    assert_that( candidates_list.call_count, equal_to( 1 ) )
