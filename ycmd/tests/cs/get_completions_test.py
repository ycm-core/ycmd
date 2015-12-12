#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 ycmd contributors.
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

from webtest import AppError
from nose.tools import eq_
from hamcrest import ( assert_that, empty, greater_than, has_item, has_items,
                       has_entries )
from cs_handlers_test import Cs_Handlers_test


class Cs_GetCompletions_test( Cs_Handlers_test ):

  def Basic_test( self ):
    filepath = self._PathToTestFile( 'testy', 'Program.cs' )
    contents = open( filepath ).read()
    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'cs',
                                     contents = contents,
                                     event_name = 'FileReadyToParse' )

    self._app.post_json( '/event_notification', event_data )
    self._WaitUntilOmniSharpServerReady( filepath )

    completion_data = self._BuildRequest( filepath = filepath,
                                          filetype = 'cs',
                                          contents = contents,
                                          line_num = 10,
                                          column_num = 12 )
    response_data = self._app.post_json( '/completions', completion_data ).json
    assert_that( response_data[ 'completions' ],
                 has_items( self._CompletionEntryMatcher( 'CursorLeft' ),
                            self._CompletionEntryMatcher( 'CursorSize' ) ) )
    eq_( 12, response_data[ 'completion_start_column' ] )

    self._StopOmniSharpServer( filepath )


  def MultipleSolution_test( self ):
    filepaths = [ self._PathToTestFile( 'testy', 'Program.cs' ),
                  self._PathToTestFile( 'testy-multiple-solutions',
                                        'solution-named-like-folder',
                                        'testy',
                                        'Program.cs' ) ]
    lines = [ 10, 9 ]
    for filepath, line in zip( filepaths, lines ):
      contents = open( filepath ).read()
      event_data = self._BuildRequest( filepath = filepath,
                                       filetype = 'cs',
                                       contents = contents,
                                       event_name = 'FileReadyToParse' )

      self._app.post_json( '/event_notification', event_data )
      self._WaitUntilOmniSharpServerReady( filepath )

      completion_data = self._BuildRequest( filepath = filepath,
                                            filetype = 'cs',
                                            contents = contents,
                                            line_num = line,
                                            column_num = 12 )
      response_data = self._app.post_json( '/completions',
                                           completion_data ).json
      assert_that( response_data[ 'completions' ],
                   has_items( self._CompletionEntryMatcher( 'CursorLeft' ),
                              self._CompletionEntryMatcher( 'CursorSize' ) ) )
      eq_( 12, response_data[ 'completion_start_column' ] )

      self._StopOmniSharpServer( filepath )


  def PathWithSpace_test( self ):
    filepath = self._PathToTestFile( u'неприличное слово', 'Program.cs' )
    contents = open( filepath ).read()
    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'cs',
                                     contents = contents,
                                     event_name = 'FileReadyToParse' )

    self._app.post_json( '/event_notification', event_data )
    self._WaitUntilOmniSharpServerReady( filepath )

    completion_data = self._BuildRequest( filepath = filepath,
                                          filetype = 'cs',
                                          contents = contents,
                                          line_num = 9,
                                          column_num = 12 )
    response_data = self._app.post_json( '/completions', completion_data ).json
    assert_that( response_data[ 'completions' ],
                 has_items( self._CompletionEntryMatcher( 'CursorLeft' ),
                            self._CompletionEntryMatcher( 'CursorSize' ) ) )
    eq_( 12, response_data[ 'completion_start_column' ] )

    self._StopOmniSharpServer( filepath )


  def HasBothImportsAndNonImport_test( self ):
    filepath = self._PathToTestFile( 'testy', 'ImportTest.cs' )
    contents = open( filepath ).read()
    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'cs',
                                     contents = contents,
                                     event_name = 'FileReadyToParse' )

    self._app.post_json( '/event_notification', event_data )
    self._WaitUntilOmniSharpServerReady( filepath )

    completion_data = self._BuildRequest( filepath = filepath,
                                          filetype = 'cs',
                                          contents = contents,
                                          line_num = 9,
                                          column_num = 12,
                                          force_semantic = True,
                                          query = 'Date' )
    response_data = self._app.post_json( '/completions', completion_data ).json

    assert_that(
      response_data[ 'completions' ],
      has_items( self._CompletionEntryMatcher( 'DateTime' ),
                 self._CompletionEntryMatcher( 'DateTimeStyles' ) )
    )

    self._StopOmniSharpServer( filepath )


  def ImportsOrderedAfter_test( self ):
    filepath = self._PathToTestFile( 'testy', 'ImportTest.cs' )
    contents = open( filepath ).read()
    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'cs',
                                     contents = contents,
                                     event_name = 'FileReadyToParse' )

    self._app.post_json( '/event_notification', event_data )
    self._WaitUntilOmniSharpServerReady( filepath )

    completion_data = self._BuildRequest( filepath = filepath,
                                          filetype = 'cs',
                                          contents = contents,
                                          line_num = 9,
                                          column_num = 12,
                                          force_semantic = True,
                                          query = 'Date' )
    response_data = self._app.post_json( '/completions', completion_data ).json

    min_import_index = min(
      loc for loc, val
      in enumerate( response_data[ 'completions' ] )
      if val[ 'extra_data' ][ 'required_namespace_import' ]
    )

    max_nonimport_index = max(
      loc for loc, val
      in enumerate( response_data[ 'completions' ] )
      if not val[ 'extra_data' ][ 'required_namespace_import' ]
    )

    assert_that( min_import_index, greater_than( max_nonimport_index ) ),
    self._StopOmniSharpServer( filepath )


  def ForcedReturnsResults_test( self ):
    filepath = self._PathToTestFile( 'testy', 'ContinuousTest.cs' )
    contents = open( filepath ).read()
    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'cs',
                                     contents = contents,
                                     event_name = 'FileReadyToParse' )

    self._app.post_json( '/event_notification', event_data )
    self._WaitUntilOmniSharpServerReady( filepath )

    completion_data = self._BuildRequest( filepath = filepath,
                                          filetype = 'cs',
                                          contents = contents,
                                          line_num = 9,
                                          column_num = 21,
                                          force_semantic = True,
                                          query = 'Date' )
    response_data = self._app.post_json( '/completions', completion_data ).json

    assert_that( response_data[ 'completions' ],
                 has_items( self._CompletionEntryMatcher( 'String' ),
                            self._CompletionEntryMatcher( 'StringBuilder' ) ) )
    self._StopOmniSharpServer( filepath )


  def NonForcedReturnsNoResults_test( self ):
    filepath = self._PathToTestFile( 'testy', 'ContinuousTest.cs' )
    contents = open( filepath ).read()
    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'cs',
                                     contents = contents,
                                     event_name = 'FileReadyToParse' )

    self._app.post_json( '/event_notification', event_data )
    self._WaitUntilOmniSharpServerReady( filepath )

    completion_data = self._BuildRequest( filepath = filepath,
                                          filetype = 'cs',
                                          contents = contents,
                                          line_num = 9,
                                          column_num = 21,
                                          force_semantic = False,
                                          query = 'Date' )
    results = self._app.post_json( '/completions', completion_data ).json

    # There are no semantic completions. However, we fall back to identifier
    # completer in this case.
    assert_that( results, has_entries( {
      'completions': has_item( has_entries( {
        'insertion_text' : 'String',
        'extra_menu_info': '[ID]',
      } ) ),
      'errors': empty(),
    } ) )
    self._StopOmniSharpServer( filepath )


  def ForcedDividesCache_test( self ):
    filepath = self._PathToTestFile( 'testy', 'ContinuousTest.cs' )
    contents = open( filepath ).read()
    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'cs',
                                     contents = contents,
                                     event_name = 'FileReadyToParse' )

    self._app.post_json( '/event_notification', event_data )
    self._WaitUntilOmniSharpServerReady( filepath )

    completion_data = self._BuildRequest( filepath = filepath,
                                          filetype = 'cs',
                                          contents = contents,
                                          line_num = 9,
                                          column_num = 21,
                                          force_semantic = True,
                                          query = 'Date' )
    results = self._app.post_json( '/completions', completion_data ).json

    assert_that( results[ 'completions' ], not( empty() ) )
    assert_that( results[ 'errors' ], empty() )

    completion_data = self._BuildRequest( filepath = filepath,
                                          filetype = 'cs',
                                          contents = contents,
                                          line_num = 9,
                                          column_num = 21,
                                          force_semantic = False,
                                          query = 'Date' )
    results = self._app.post_json( '/completions', completion_data ).json

    # There are no semantic completions. However, we fall back to identifier
    # completer in this case.
    assert_that( results, has_entries( {
      'completions': has_item( has_entries( {
        'insertion_text' : 'String',
        'extra_menu_info': '[ID]',
      } ) ),
      'errors': empty(),
    } ) )
    self._StopOmniSharpServer( filepath )


  def ReloadSolution_Basic_test( self ):
    filepath = self._PathToTestFile( 'testy', 'Program.cs' )
    contents = open( filepath ).read()
    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'cs',
                                     contents = contents,
                                     event_name = 'FileReadyToParse' )

    self._app.post_json( '/event_notification', event_data )
    self._WaitUntilOmniSharpServerReady( filepath )
    result = self._app.post_json(
      '/run_completer_command',
      self._BuildRequest( completer_target = 'filetype_default',
                          command_arguments = [ 'ReloadSolution' ],
                          filepath = filepath,
                          filetype = 'cs' ) ).json

    self._StopOmniSharpServer( filepath )
    eq_( result, True )


  def ReloadSolution_MultipleSolution_test( self ):
    filepaths = [ self._PathToTestFile( 'testy', 'Program.cs' ),
                  self._PathToTestFile( 'testy-multiple-solutions',
                                        'solution-named-like-folder',
                                        'testy',
                                        'Program.cs' ) ]
    for filepath in filepaths:
      contents = open( filepath ).read()
      event_data = self._BuildRequest( filepath = filepath,
                                       filetype = 'cs',
                                       contents = contents,
                                       event_name = 'FileReadyToParse' )

      self._app.post_json( '/event_notification', event_data )
      self._WaitUntilOmniSharpServerReady( filepath )
      result = self._app.post_json(
        '/run_completer_command',
        self._BuildRequest( completer_target = 'filetype_default',
                            command_arguments = [ 'ReloadSolution' ],
                            filepath = filepath,
                            filetype = 'cs' ) ).json

      self._StopOmniSharpServer( filepath )
      eq_( result, True )


  def _SolutionSelectCheck( self, sourcefile, reference_solution,
                            extra_conf_store = None ):
    # reusable test: verify that the correct solution (reference_solution) is
    #   detected for a given source file (and optionally a given extra_conf)
    if extra_conf_store:
      self._app.post_json( '/load_extra_conf_file',
                           { 'filepath': extra_conf_store } )

    result = self._app.post_json(
      '/run_completer_command',
      self._BuildRequest( completer_target = 'filetype_default',
                          command_arguments = [ 'SolutionFile' ],
                          filepath = sourcefile,
                          filetype = 'cs' ) ).json

    # Now that cleanup is done, verify solution file
    eq_( reference_solution, result)


  def UsesSubfolderHint_test( self ):
    self._SolutionSelectCheck(
      self._PathToTestFile( 'testy-multiple-solutions',
                            'solution-named-like-folder',
                            'testy', 'Program.cs' ),
      self._PathToTestFile( 'testy-multiple-solutions',
                            'solution-named-like-folder',
                            'testy.sln' ) )


  def UsesSuperfolderHint_test( self ):
    self._SolutionSelectCheck(
      self._PathToTestFile( 'testy-multiple-solutions',
                            'solution-named-like-folder',
                            'not-testy', 'Program.cs' ),
      self._PathToTestFile( 'testy-multiple-solutions',
                            'solution-named-like-folder',
                            'solution-named-like-folder.sln' ) )


  def ExtraConfStoreAbsolute_test( self ):
    self._SolutionSelectCheck(
      self._PathToTestFile( 'testy-multiple-solutions',
                            'solution-not-named-like-folder', 'extra-conf-abs',
                            'testy', 'Program.cs' ),
      self._PathToTestFile( 'testy-multiple-solutions',
                            'solution-not-named-like-folder', 'testy2.sln' ),
      self._PathToTestFile( 'testy-multiple-solutions',
                            'solution-not-named-like-folder', 'extra-conf-abs',
                            '.ycm_extra_conf.py' ) )


  def ExtraConfStoreRelative_test( self ):
    self._SolutionSelectCheck(
      self._PathToTestFile( 'testy-multiple-solutions',
                            'solution-not-named-like-folder', 'extra-conf-rel',
                            'testy', 'Program.cs' ),
      self._PathToTestFile( 'testy-multiple-solutions',
                            'solution-not-named-like-folder', 'extra-conf-rel',
                            'testy2.sln' ),
      self._PathToTestFile( 'testy-multiple-solutions',
                            'solution-not-named-like-folder', 'extra-conf-rel',
                            '.ycm_extra_conf.py' ) )


  def ExtraConfStoreNonexisting_test( self ):
    self._SolutionSelectCheck(
      self._PathToTestFile( 'testy-multiple-solutions',
                            'solution-not-named-like-folder', 'extra-conf-bad',
                            'testy', 'Program.cs' ),
      self._PathToTestFile( 'testy-multiple-solutions',
                            'solution-not-named-like-folder', 'extra-conf-bad',
                            'testy2.sln' ),
      self._PathToTestFile( 'testy-multiple-solutions',
                            'solution-not-named-like-folder', 'extra-conf-bad',
                            'testy', '.ycm_extra_conf.py' ) )


  def DoesntStartWithAmbiguousMultipleSolutions_test( self ):
    filepath = self._PathToTestFile( 'testy-multiple-solutions',
                                     'solution-not-named-like-folder',
                                     'testy', 'Program.cs' )
    contents = open( filepath ).read()
    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'cs',
                                     contents = contents,
                                     event_name = 'FileReadyToParse' )

    exception_caught = False
    try:
      self._app.post_json( '/event_notification', event_data )
    except AppError as e:
      if 'Autodetection of solution file failed' in str( e ):
        exception_caught = True

    # The test passes if we caught an exception when trying to start it,
    # so raise one if it managed to start
    if not exception_caught:
      self._WaitUntilOmniSharpServerReady( filepath )
      self._StopOmniSharpServer( filepath )
      raise Exception( 'The Omnisharp server started, despite us not being '
                       'able to find a suitable solution file to feed it. Did '
                       'you fiddle with the solution finding code in '
                       'cs_completer.py? Hopefully you\'ve enhanced it: you '
                       'need to update this test then :)' )
