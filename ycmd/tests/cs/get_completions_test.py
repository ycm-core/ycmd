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

from ...server_utils import SetUpPythonPath
SetUpPythonPath()
from ..test_utils import BuildRequest, CompletionEntryMatcher, Setup
from .utils import ( PathToTestFile, StopOmniSharpServer,
                     WaitUntilOmniSharpServerReady )
from webtest import TestApp, AppError
from nose.tools import eq_, with_setup
from hamcrest import ( assert_that, has_item, has_items, has_entries, empty,
                       greater_than )
from ... import handlers
import bottle

bottle.debug( True )


@with_setup( Setup )
def GetCompletions_CsCompleter_Works_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy', 'Program.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app, filepath )

  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'cs',
                                  contents = contents,
                                  line_num = 10,
                                  column_num = 12 )
  response_data = app.post_json( '/completions', completion_data ).json
  assert_that( response_data[ 'completions' ],
               has_items( CompletionEntryMatcher( 'CursorLeft' ),
                          CompletionEntryMatcher( 'CursorSize' ) ) )
  eq_( 12, response_data[ 'completion_start_column' ] )

  StopOmniSharpServer( app, filepath )


@with_setup( Setup )
def GetCompletions_CsCompleter_MultipleSolution_Works_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepaths = [ PathToTestFile( 'testy', 'Program.cs' ),
                PathToTestFile( 'testy-multiple-solutions',
                                'solution-named-like-folder',
                                'testy',
                                'Program.cs' ) ]
  lines = [ 10, 9 ]
  for filepath, line in zip( filepaths, lines ):
    contents = open( filepath ).read()
    event_data = BuildRequest( filepath = filepath,
                               filetype = 'cs',
                               contents = contents,
                               event_name = 'FileReadyToParse' )

    app.post_json( '/event_notification', event_data )
    WaitUntilOmniSharpServerReady( app, filepath )

    completion_data = BuildRequest( filepath = filepath,
                                    filetype = 'cs',
                                    contents = contents,
                                    line_num = line,
                                    column_num = 12 )
    response_data = app.post_json( '/completions', completion_data ).json
    assert_that( response_data[ 'completions' ],
                 has_items( CompletionEntryMatcher( 'CursorLeft' ),
                            CompletionEntryMatcher( 'CursorSize' ) ) )
    eq_( 12, response_data[ 'completion_start_column' ] )

    StopOmniSharpServer( app, filepath )


@with_setup( Setup )
def GetCompletions_CsCompleter_PathWithSpace_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( u'неприличное слово', 'Program.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app, filepath )

  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'cs',
                                  contents = contents,
                                  line_num = 9,
                                  column_num = 12 )
  response_data = app.post_json( '/completions', completion_data ).json
  assert_that( response_data[ 'completions' ],
               has_items( CompletionEntryMatcher( 'CursorLeft' ),
                          CompletionEntryMatcher( 'CursorSize' ) ) )
  eq_( 12, response_data[ 'completion_start_column' ] )

  StopOmniSharpServer( app, filepath )


@with_setup( Setup )
def GetCompletions_CsCompleter_HasBothImportsAndNonImport_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy', 'ImportTest.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app, filepath )

  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'cs',
                                  contents = contents,
                                  line_num = 9,
                                  column_num = 12,
                                  force_semantic = True,
                                  query = 'Date' )
  response_data = app.post_json( '/completions', completion_data ).json

  assert_that( response_data[ 'completions' ],
               has_items( CompletionEntryMatcher( 'DateTime' ),
                          CompletionEntryMatcher( 'DateTimeStyles' ) ) )

  StopOmniSharpServer( app, filepath )


@with_setup( Setup )
def GetCompletions_CsCompleter_ImportsOrderedAfter_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy', 'ImportTest.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app, filepath )

  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'cs',
                                  contents = contents,
                                  line_num = 9,
                                  column_num = 12,
                                  force_semantic = True,
                                  query = 'Date' )
  response_data = app.post_json( '/completions', completion_data ).json

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
  StopOmniSharpServer( app, filepath )


@with_setup( Setup )
def GetCompletions_CsCompleter_ForcedReturnsResults_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy', 'ContinuousTest.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app, filepath )

  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'cs',
                                  contents = contents,
                                  line_num = 9,
                                  column_num = 21,
                                  force_semantic = True,
                                  query = 'Date' )
  response_data = app.post_json( '/completions', completion_data ).json

  assert_that( response_data[ 'completions' ],
               has_items( CompletionEntryMatcher( 'String' ),
                          CompletionEntryMatcher( 'StringBuilder' ) ) )
  StopOmniSharpServer( app, filepath )


@with_setup( Setup )
def GetCompletions_CsCompleter_NonForcedReturnsNoResults_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy', 'ContinuousTest.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app, filepath )

  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'cs',
                                  contents = contents,
                                  line_num = 9,
                                  column_num = 21,
                                  force_semantic = False,
                                  query = 'Date' )
  results = app.post_json( '/completions', completion_data ).json

  # There are no semantic completions. However, we fall back to identifier
  # completer in this case.
  assert_that( results, has_entries( {
    'completions': has_item( has_entries( {
      'insertion_text' : 'String',
      'extra_menu_info': '[ID]',
    } ) ),
    'errors': empty(),
  } ) )
  StopOmniSharpServer( app, filepath )


@with_setup( Setup )
def GetCompletions_CsCompleter_ForcedDividesCache_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy', 'ContinuousTest.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app, filepath )

  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'cs',
                                  contents = contents,
                                  line_num = 9,
                                  column_num = 21,
                                  force_semantic = True,
                                  query = 'Date' )
  results = app.post_json( '/completions', completion_data ).json

  assert_that( results[ 'completions' ], not( empty() ) )
  assert_that( results[ 'errors' ], empty() )

  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'cs',
                                  contents = contents,
                                  line_num = 9,
                                  column_num = 21,
                                  force_semantic = False,
                                  query = 'Date' )
  results = app.post_json( '/completions', completion_data ).json

  # There are no semantic completions. However, we fall back to identifier
  # completer in this case.
  assert_that( results, has_entries( {
    'completions': has_item( has_entries( {
      'insertion_text' : 'String',
      'extra_menu_info': '[ID]',
    } ) ),
    'errors': empty(),
  } ) )
  StopOmniSharpServer( app, filepath )


@with_setup( Setup )
def GetCompletions_CsCompleter_ReloadSolutionWorks_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy', 'Program.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data )
  WaitUntilOmniSharpServerReady( app, filepath )
  result = app.post_json(
    '/run_completer_command',
    BuildRequest( completer_target = 'filetype_default',
                  command_arguments = [ 'ReloadSolution' ],
                  filepath = filepath,
                  filetype = 'cs' ) ).json

  StopOmniSharpServer( app, filepath )
  eq_( result, True )


@with_setup( Setup )
def GetCompletions_CsCompleter_ReloadSolution_MultipleSolution_Works_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepaths = [ PathToTestFile( 'testy', 'Program.cs' ),
                PathToTestFile( 'testy-multiple-solutions',
                                'solution-named-like-folder',
                                'testy',
                                'Program.cs' ) ]
  for filepath in filepaths:
    contents = open( filepath ).read()
    event_data = BuildRequest( filepath = filepath,
                               filetype = 'cs',
                               contents = contents,
                               event_name = 'FileReadyToParse' )

    app.post_json( '/event_notification', event_data )
    WaitUntilOmniSharpServerReady( app, filepath )
    result = app.post_json(
      '/run_completer_command',
      BuildRequest( completer_target = 'filetype_default',
                    command_arguments = [ 'ReloadSolution' ],
                    filepath = filepath,
                    filetype = 'cs' ) ).json

    StopOmniSharpServer( app, filepath )
    eq_( result, True )


def _CsCompleter_SolutionSelectCheck( app, sourcefile, reference_solution,
                                      extra_conf_store = None ):
  # reusable test: verify that the correct solution (reference_solution) is
  #   detected for a given source file (and optionally a given extra_conf)
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  if extra_conf_store:
    app.post_json( '/load_extra_conf_file', { 'filepath': extra_conf_store } )

  result = app.post_json( '/run_completer_command',
                          BuildRequest( completer_target = 'filetype_default',
                                        command_arguments = [ 'SolutionFile' ],
                                        filepath = sourcefile,
                                        filetype = 'cs' ) ).json
  # Now that cleanup is done, verify solution file
  eq_( reference_solution, result)


@with_setup( Setup )
def GetCompletions_CsCompleter_UsesSubfolderHint_test():
  app = TestApp( handlers.app )
  _CsCompleter_SolutionSelectCheck( app,
                                    PathToTestFile(
                                      'testy-multiple-solutions',
                                      'solution-named-like-folder',
                                      'testy',
                                      'Program.cs' ),
                                    PathToTestFile(
                                      'testy-multiple-solutions',
                                      'solution-named-like-folder',
                                      'testy.sln' ) )


@with_setup( Setup )
def GetCompletions_CsCompleter_UsesSuperfolderHint_test():
  app = TestApp( handlers.app )
  _CsCompleter_SolutionSelectCheck( app,
                                    PathToTestFile(
                                      'testy-multiple-solutions',
                                      'solution-named-like-folder',
                                      'not-testy',
                                      'Program.cs' ),
                                    PathToTestFile(
                                      'testy-multiple-solutions',
                                      'solution-named-like-folder',
                                      'solution-named-like-folder.sln' ) )


@with_setup( Setup )
def GetCompletions_CsCompleter_ExtraConfStoreAbsolute_test():
  app = TestApp( handlers.app )
  _CsCompleter_SolutionSelectCheck( app,
                                    PathToTestFile(
                                      'testy-multiple-solutions',
                                      'solution-not-named-like-folder',
                                      'extra-conf-abs',
                                      'testy',
                                      'Program.cs' ),
                                    PathToTestFile(
                                      'testy-multiple-solutions',
                                      'solution-not-named-like-folder',
                                      'testy2.sln' ),
                                    PathToTestFile(
                                      'testy-multiple-solutions',
                                      'solution-not-named-like-folder',
                                      'extra-conf-abs',
                                      '.ycm_extra_conf.py' ) )


@with_setup( Setup )
def GetCompletions_CsCompleter_ExtraConfStoreRelative_test():
  app = TestApp( handlers.app )
  _CsCompleter_SolutionSelectCheck( app,
                                    PathToTestFile(
                                      'testy-multiple-solutions',
                                      'solution-not-named-like-folder',
                                      'extra-conf-rel',
                                      'testy',
                                      'Program.cs' ),
                                    PathToTestFile(
                                      'testy-multiple-solutions',
                                      'solution-not-named-like-folder',
                                      'extra-conf-rel',
                                      'testy2.sln' ),
                                    PathToTestFile(
                                      'testy-multiple-solutions',
                                      'solution-not-named-like-folder',
                                      'extra-conf-rel',
                                      '.ycm_extra_conf.py' ) )


@with_setup( Setup )
def GetCompletions_CsCompleter_ExtraConfStoreNonexisting_test():
  app = TestApp( handlers.app )
  _CsCompleter_SolutionSelectCheck( app,
                                    PathToTestFile(
                                      'testy-multiple-solutions',
                                      'solution-not-named-like-folder',
                                      'extra-conf-bad',
                                      'testy',
                                      'Program.cs' ),
                                    PathToTestFile(
                                      'testy-multiple-solutions',
                                      'solution-not-named-like-folder',
                                      'extra-conf-bad',
                                      'testy2.sln' ),
                                    PathToTestFile(
                                      'testy-multiple-solutions',
                                      'solution-not-named-like-folder',
                                      'extra-conf-bad',
                                      'testy',
                                      '.ycm_extra_conf.py' ) )


@with_setup( Setup )
def GetCompletions_CsCompleter_DoesntStartWithAmbiguousMultipleSolutions_test():
  app = TestApp( handlers.app )
  app.post_json( '/ignore_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  filepath = PathToTestFile( 'testy-multiple-solutions',
                             'solution-not-named-like-folder',
                             'testy', 'Program.cs' )
  contents = open( filepath ).read()
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'cs',
                             contents = contents,
                             event_name = 'FileReadyToParse' )

  exception_caught = False
  try:
    app.post_json( '/event_notification', event_data )
  except AppError as e:
    if 'Autodetection of solution file failed' in str( e ):
      exception_caught = True

  # The test passes if we caught an exception when trying to start it,
  # so raise one if it managed to start
  if not exception_caught:
    WaitUntilOmniSharpServerReady( app, filepath )
    StopOmniSharpServer( app, filepath )
    raise Exception( 'The Omnisharp server started, despite us not being able '
                     'to find a suitable solution file to feed it. Did you '
                     'fiddle with the solution finding code in '
                     'cs_completer.py? Hopefully you\'ve enhanced it: you need'
                     'to update this test then :)' )
