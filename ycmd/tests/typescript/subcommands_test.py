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

from hamcrest import assert_that, has_items, has_entries

from ycmd.tests.typescript import PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import BuildRequest, ErrorMatcher, MessageMatcher
from ycmd.utils import ReadFile


@SharedYcmd
def Subcommands_GetType_Basic_test( app ):
  filepath = PathToTestFile( 'test.ts' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'typescript',
                             contents = contents,
                             event_name = 'BufferVisit' )

  app.post_json( '/event_notification', event_data )

  gettype_data = BuildRequest( completer_target = 'filetype_default',
                               command_arguments = [ 'GetType' ],
                               line_num = 17,
                               column_num = 1,
                               contents = contents,
                               filetype = 'typescript',
                               filepath = filepath )

  response = app.post_json( '/run_completer_command', gettype_data ).json
  assert_that( response, MessageMatcher( 'var foo: Foo' ) )


@SharedYcmd
def Subcommands_GetType_HasNoType_test( app ):
  filepath = PathToTestFile( 'test.ts' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'typescript',
                             contents = contents,
                             event_name = 'BufferVisit' )

  app.post_json( '/event_notification', event_data )

  gettype_data = BuildRequest( completer_target = 'filetype_default',
                               command_arguments = [ 'GetType' ],
                               line_num = 2,
                               column_num = 1,
                               contents = contents,
                               filetype = 'typescript',
                               filepath = filepath )

  response = app.post_json( '/run_completer_command',
                            gettype_data,
                            expect_errors = True ).json
  assert_that( response,
               ErrorMatcher( RuntimeError, 'No content available.' ) )


@SharedYcmd
def Subcommands_GetDoc_Method_test( app ):
  filepath = PathToTestFile( 'test.ts' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'typescript',
                             contents = contents,
                             event_name = 'BufferVisit' )

  app.post_json( '/event_notification', event_data )

  gettype_data = BuildRequest( completer_target = 'filetype_default',
                               command_arguments = [ 'GetDoc' ],
                               line_num = 34,
                               column_num = 9,
                               contents = contents,
                               filetype = 'typescript',
                               filepath = filepath )

  response = app.post_json( '/run_completer_command', gettype_data ).json
  assert_that( response,
               has_entries( {
                 'detailed_info': '(method) Bar.testMethod(): void\n\n'
                                  'Method documentation'
               } ) )


@SharedYcmd
def Subcommands_GetDoc_Class_test( app ):
  filepath = PathToTestFile( 'test.ts' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'typescript',
                             contents = contents,
                             event_name = 'BufferVisit' )

  app.post_json( '/event_notification', event_data )

  gettype_data = BuildRequest( completer_target = 'filetype_default',
                               command_arguments = [ 'GetDoc' ],
                               line_num = 37,
                               column_num = 2,
                               contents = contents,
                               filetype = 'typescript',
                               filepath = filepath )

  response = app.post_json( '/run_completer_command', gettype_data ).json
  assert_that( response,
               has_entries( {
                 'detailed_info': 'class Bar\n\n'
                                  'Class documentation\n\n'
                                  'Multi-line'
               } ) )


@SharedYcmd
def Subcommands_GoToReferences_test( app ):
  filepath = PathToTestFile( 'test.ts' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'typescript',
                             contents = contents,
                             event_name = 'BufferVisit' )

  app.post_json( '/event_notification', event_data )

  references_data = BuildRequest( completer_target = 'filetype_default',
                                  command_arguments = [ 'GoToReferences' ],
                                  line_num = 33,
                                  column_num = 6,
                                  contents = contents,
                                  filetype = 'typescript',
                                  filepath = filepath )

  expected = has_items(
    has_entries( { 'description': 'var bar = new Bar();',
                   'line_num'   : 33,
                   'column_num' : 5 } ),
    has_entries( { 'description': 'bar.testMethod();',
                   'line_num'   : 34,
                   'column_num' : 1 } ) )
  actual = app.post_json( '/run_completer_command', references_data ).json
  assert_that( actual, expected )


@SharedYcmd
def Subcommands_GoTo_test( app ):
  filepath = PathToTestFile( 'test.ts' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'typescript',
                             contents = contents,
                             event_name = 'BufferVisit' )

  app.post_json( '/event_notification', event_data )

  goto_data = BuildRequest( completer_target = 'filetype_default',
                            command_arguments = [ 'GoToDefinition' ],
                            line_num = 34,
                            column_num = 9,
                            contents = contents,
                            filetype = 'typescript',
                            filepath = filepath )

  response = app.post_json( '/run_completer_command', goto_data ).json
  assert_that( response,
               has_entries( {
                 'filepath': filepath,
                 'line_num': 30,
                 'column_num': 3,
               } ) )


@SharedYcmd
def Subcommands_GoTo_Fail_test( app ):
  filepath = PathToTestFile( 'test.ts' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'typescript',
                             contents = contents,
                             event_name = 'BufferVisit' )

  app.post_json( '/event_notification', event_data )

  goto_data = BuildRequest( completer_target = 'filetype_default',
                            command_arguments = [ 'GoToDefinition' ],
                            line_num = 35,
                            column_num = 6,
                            contents = contents,
                            filetype = 'typescript',
                            filepath = filepath )

  response = app.post_json( '/run_completer_command',
                            goto_data,
                            expect_errors = True ).json
  assert_that( response,
               ErrorMatcher( RuntimeError, 'Could not find definition' ) )
