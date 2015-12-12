#!/usr/bin/env python
#
# Copyright (C) 2013 Google Inc.
#               2015 ycmd contributors
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

from webtest import TestApp
from nose.tools import eq_
from hamcrest import assert_that, has_items
from .. import handlers
from .handlers_test import Handlers_test


class GetCompletions_test( Handlers_test ):

  def RequestValidation_NoLineNumException_test( self ):
    response = self._app.post_json( '/semantic_completion_available', {
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


  def IdentifierCompleter_Works_test( self ):
    event_data = self._BuildRequest( contents = 'foo foogoo ba',
                                     event_name = 'FileReadyToParse' )

    self._app.post_json( '/event_notification', event_data )

    # query is 'oo'
    completion_data = self._BuildRequest( contents = 'oo foo foogoo ba',
                                          column_num = 3 )
    response_data = self._app.post_json( '/completions', completion_data ).json

    eq_( 1, response_data[ 'completion_start_column' ] )
    assert_that(
      response_data[ 'completions' ],
      has_items( self._CompletionEntryMatcher( 'foo', '[ID]' ),
                 self._CompletionEntryMatcher( 'foogoo', '[ID]' ) )
    )


  def IdentifierCompleter_StartColumn_AfterWord_test( self ):
    completion_data = self._BuildRequest( contents = 'oo foo foogoo ba',
                                          column_num = 11 )
    response_data = self._app.post_json( '/completions', completion_data ).json
    eq_( 8, response_data[ 'completion_start_column' ] )


  def IdentifierCompleter_WorksForSpecialIdentifierChars_test( self ):
    contents = """
      textarea {
        font-family: sans-serif;
        font-size: 12px;
      }"""
    event_data = self._BuildRequest( contents = contents,
                                     filetype = 'css',
                                     event_name = 'FileReadyToParse' )

    self._app.post_json( '/event_notification', event_data )

    # query is 'fo'
    completion_data = self._BuildRequest( contents = 'fo ' + contents,
                                          filetype = 'css',
                                          column_num = 3 )
    results = self._app.post_json( '/completions',
                                   completion_data ).json[ 'completions' ]

    assert_that(
      results,
      has_items( self._CompletionEntryMatcher( 'font-size', '[ID]' ),
                 self._CompletionEntryMatcher( 'font-family', '[ID]' ) )
    )


  def ForceSemantic_Works_test( self ):
    completion_data = self._BuildRequest( filetype = 'python',
                                          force_semantic = True )

    results = self._app.post_json( '/completions',
                                   completion_data ).json[ 'completions' ]
    assert_that( results, has_items( self._CompletionEntryMatcher( 'abs' ),
                                     self._CompletionEntryMatcher( 'open' ),
                                     self._CompletionEntryMatcher( 'bool' ) ) )


  def IdentifierCompleter_SyntaxKeywordsAdded_test( self ):
    event_data = self._BuildRequest( event_name = 'FileReadyToParse',
                                     syntax_keywords = ['foo', 'bar', 'zoo'] )

    self._app.post_json( '/event_notification', event_data )

    completion_data = self._BuildRequest( contents = 'oo ',
                                          column_num = 3 )

    results = self._app.post_json( '/completions',
                                   completion_data ).json[ 'completions' ]
    assert_that( results,
                 has_items( self._CompletionEntryMatcher( 'foo' ),
                            self._CompletionEntryMatcher( 'zoo' ) ) )


  def UltiSnipsCompleter_Works_test( self ):
    event_data = self._BuildRequest(
      event_name = 'BufferVisit',
      ultisnips_snippets = [
          {'trigger': 'foo', 'description': 'bar'},
          {'trigger': 'zoo', 'description': 'goo'},
      ] )

    self._app.post_json( '/event_notification', event_data )

    completion_data = self._BuildRequest( contents = 'oo ',
                                          column_num = 3 )

    results = self._app.post_json( '/completions',
                                   completion_data ).json[ 'completions' ]
    assert_that(
      results,
      has_items(
        self._CompletionEntryMatcher( 'foo', extra_menu_info='<snip> bar' ),
        self._CompletionEntryMatcher( 'zoo', extra_menu_info='<snip> goo' )
      )
    )


  def UltiSnipsCompleter_UnusedWhenOffWithOption_test( self ):
    self._ChangeSpecificOptions( { 'use_ultisnips_completer': False } )
    self._app = TestApp( handlers.app )

    event_data = self._BuildRequest(
      event_name = 'BufferVisit',
      ultisnips_snippets = [
          {'trigger': 'foo', 'description': 'bar'},
          {'trigger': 'zoo', 'description': 'goo'},
      ] )

    self._app.post_json( '/event_notification', event_data )

    completion_data = self._BuildRequest( contents = 'oo ',
                                          column_num = 3 )

    eq_( [],
         self._app.post_json( '/completions',
                              completion_data ).json[ 'completions' ] )
