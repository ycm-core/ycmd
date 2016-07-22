# Copyright (C) 2015 ycmd contributors
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

from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from future import standard_library
standard_library.install_aliases()
from builtins import *  # noqa

from hamcrest import ( all_of, any_of, assert_that, calling,
                       contains_inanyorder, has_entries, has_item, is_not,
                       raises )
from mock import patch
from webtest import AppError

from ycmd.tests.typescript import IsolatedYcmd, PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import ( BuildRequest, CompletionEntryMatcher,
                                    StopCompleterServer )
from ycmd.utils import ReadFile


def RunTest( app, test ):
  filepath = PathToTestFile( 'test.ts' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'typescript',
                             contents = contents,
                             event_name = 'BufferVisit' )

  app.post_json( '/event_notification', event_data )

  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'typescript',
                                  contents = contents,
                                  force_semantic = True,
                                  line_num = 17,
                                  column_num = 6 )

  response = app.post_json( '/completions', completion_data )

  assert_that( response.json, test[ 'expect' ][ 'data' ] )


@SharedYcmd
def GetCompletions_Basic_test( app ):
  RunTest( app, {
    'expect': {
      'data': has_entries( {
        'completions': contains_inanyorder(
          CompletionEntryMatcher( 'methodA', extra_params = {
            'menu_text': 'methodA (method) Foo.methodA(): void' } ),
          CompletionEntryMatcher( 'methodB', extra_params = {
            'menu_text': 'methodB (method) Foo.methodB(): void' } ),
          CompletionEntryMatcher( 'methodC', extra_params = {
            'menu_text': ( 'methodC (method) Foo.methodC(a: '
                           '{ foo: string; bar: number; }): void' ) } ),
        )
      } )
    }
  } )


@SharedYcmd
@patch( 'ycmd.completers.typescript.'
          'typescript_completer.MAX_DETAILED_COMPLETIONS',
        2 )
def GetCompletions_MaxDetailedCompletion_test( app ):
  RunTest( app, {
    'expect': {
      'data': has_entries( {
        'completions': all_of(
          contains_inanyorder(
            CompletionEntryMatcher( 'methodA' ),
            CompletionEntryMatcher( 'methodB' ),
            CompletionEntryMatcher( 'methodC' ),
          ),
          is_not( any_of(
            has_item(
              CompletionEntryMatcher( 'methodA', extra_params = {
                'menu_text': 'methodA (method) Foo.methodA(): void' } ) ),
            has_item(
              CompletionEntryMatcher( 'methodB', extra_params = {
                'menu_text': 'methodB (method) Foo.methodB(): void' } ) ),
            has_item(
              CompletionEntryMatcher( 'methodC', extra_params = {
                'menu_text': ( 'methodC (method) Foo.methodC(a: '
                               '{ foo: string; bar: number; }): void' ) } ) )
          ) )
        )
      } )
    }
  } )


@SharedYcmd
def GetCompletions_AfterRestart_test( app ):
  filepath = PathToTestFile( 'test.ts' )

  app.post_json( '/run_completer_command',
                BuildRequest( completer_target = 'filetype_default',
                              command_arguments = [ 'RestartServer' ],
                              filetype = 'typescript',
                              filepath = filepath ) )

  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'typescript',
                                  contents = ReadFile( filepath ),
                                  force_semantic = True,
                                  line_num = 17,
                                  column_num = 6 )

  response = app.post_json( '/completions', completion_data )
  assert_that( response.json, has_entries( {
        'completions': contains_inanyorder(
          CompletionEntryMatcher( 'methodA', extra_params = {
            'menu_text': 'methodA (method) Foo.methodA(): void' } ),
          CompletionEntryMatcher( 'methodB', extra_params = {
            'menu_text': 'methodB (method) Foo.methodB(): void' } ),
          CompletionEntryMatcher( 'methodC', extra_params = {
            'menu_text': ( 'methodC (method) Foo.methodC(a: '
                           '{ foo: string; bar: number; }): void' ) } ),
        )
      } ) )


@IsolatedYcmd
def GetCompletions_ServerIsNotRunning_test( app ):
  StopCompleterServer( app, filetype = 'typescript' )

  filepath = PathToTestFile( 'test.ts' )
  contents = ReadFile( filepath )

  # Check that sending a request to TSServer (the response is ignored) raises
  # the proper exception.
  event_data = BuildRequest( filepath = filepath,
                             filetype = 'typescript',
                             contents = contents,
                             event_name = 'BufferVisit' )

  assert_that(
    calling( app.post_json ).with_args( '/event_notification', event_data ),
    raises( AppError, 'TSServer is not running.' ) )

  # Check that sending a command to TSServer (the response is processed) raises
  # the proper exception.
  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'typescript',
                                  contents = contents,
                                  force_semantic = True,
                                  line_num = 17,
                                  column_num = 6 )

  assert_that(
    calling( app.post_json ).with_args( '/completions', completion_data ),
    raises( AppError, 'TSServer is not running.' ) )
