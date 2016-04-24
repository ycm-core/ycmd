# encoding: utf-8
#
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

import pprint

from hamcrest import ( assert_that,
                       contains,
                       contains_inanyorder,
                       has_entries )

from ycmd.tests.typescript import PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import ( BuildRequest,
                                    ChunkMatcher,
                                    ErrorMatcher,
                                    LocationMatcher,
                                    MessageMatcher )
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
def Subcommands_GetDoc_Class_Unicode_test( app ):
  filepath = PathToTestFile( 'unicode.ts' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'typescript',
                             contents = contents,
                             event_name = 'BufferVisit' )

  app.post_json( '/event_notification', event_data )

  gettype_data = BuildRequest( completer_target = 'filetype_default',
                               command_arguments = [ 'GetDoc' ],
                               line_num = 35,
                               column_num = 12,
                               contents = contents,
                               filetype = 'typescript',
                               filepath = filepath )

  response = app.post_json( '/run_completer_command', gettype_data ).json
  assert_that( response,
               has_entries( {
                 'detailed_info': 'class Båøz\n\n'
                                  'Test unicøde st††††',
               } ) )


@SharedYcmd
def Subcommands_GoToReferences_test( app ):
  filepath = PathToTestFile( 'test.ts' )
  file3 = PathToTestFile( 'file3.ts' )
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

  expected = contains_inanyorder(
    has_entries( { 'description': 'var bar = new Bar();',
                   'line_num'   : 33,
                   'column_num' : 5,
                   'filepath'   : filepath } ),
    has_entries( { 'description': 'bar.testMethod();',
                   'line_num'   : 34,
                   'column_num' : 1,
                   'filepath'   : filepath } ),
    has_entries( { 'description': 'bar.nonExistingMethod();',
                   'line_num'   : 35,
                   'column_num' : 1,
                   'filepath'   : filepath } ),
    has_entries( { 'description': 'var bar = new Bar();',
                   'line_num'   : 1,
                   'column_num' : 5,
                   'filepath'   : file3 } ),
    has_entries( { 'description': 'bar.testMethod();',
                   'line_num'   : 2,
                   'column_num' : 1,
                   'filepath'   : file3 } )
  )
  actual = app.post_json( '/run_completer_command', references_data ).json

  pprint.pprint( actual )

  assert_that( actual, expected )


@SharedYcmd
def Subcommands_GoToReferences_Unicode_test( app ):
  filepath = PathToTestFile( 'unicode.ts' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'typescript',
                             contents = contents,
                             event_name = 'BufferVisit' )

  app.post_json( '/event_notification', event_data )

  references_data = BuildRequest( completer_target = 'filetype_default',
                                  command_arguments = [ 'GoToReferences' ],
                                  line_num = 14,
                                  column_num = 3,
                                  contents = contents,
                                  filetype = 'typescript',
                                  filepath = filepath )

  expected = contains_inanyorder(
    has_entries( { 'description': '  å: number;',
                   'line_num'   : 14,
                   'column_num' : 3,
                   'filepath'   : filepath } ),
    has_entries( { 'description': 'var baz = new Bår(); baz.å;',
                   'line_num'   : 20,
                   'column_num' : 27,
                   'filepath'   : filepath } ),
    has_entries( { 'description': 'baz.å;',
                   'line_num'   : 23,
                   'column_num' : 5,
                   'filepath'   : filepath } ),
    has_entries( { 'description': 'føø_long_long.å;',
                   'line_num'   : 27,
                   'column_num' : 17,
                   'filepath'   : filepath } )
  )
  actual = app.post_json( '/run_completer_command', references_data ).json

  pprint.pprint( actual )

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
def Subcommands_GoTo_Unicode_test( app ):
  filepath = PathToTestFile( 'unicode.ts' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'typescript',
                             contents = contents,
                             event_name = 'BufferVisit' )

  app.post_json( '/event_notification', event_data )

  goto_data = BuildRequest( completer_target = 'filetype_default',
                            command_arguments = [ 'GoToDefinition' ],
                            line_num = 28,
                            column_num = 19,
                            contents = contents,
                            filetype = 'typescript',
                            filepath = filepath )

  response = app.post_json( '/run_completer_command', goto_data ).json
  assert_that( response,
               has_entries( {
                 'filepath': filepath,
                 'line_num': 15,
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


@SharedYcmd
def Subcommands_GoToType_test( app ):
  filepath = PathToTestFile( 'test.ts' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'typescript',
                             contents = contents,
                             event_name = 'BufferVisit' )

  app.post_json( '/event_notification', event_data )

  goto_data = BuildRequest( completer_target = 'filetype_default',
                            command_arguments = [ 'GoToType' ],
                            line_num = 14,
                            column_num = 6,
                            contents = contents,
                            filetype = 'typescript',
                            filepath = filepath )

  response = app.post_json( '/run_completer_command', goto_data ).json
  assert_that( response,
               has_entries( {
                 'filepath': filepath,
                 'line_num': 2,
                 'column_num': 1,
               } ) )


@SharedYcmd
def Subcommands_GoToType_fail_test( app ):
  filepath = PathToTestFile( 'test.ts' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'typescript',
                             contents = contents,
                             event_name = 'BufferVisit' )

  app.post_json( '/event_notification', event_data )

  goto_data = BuildRequest( completer_target = 'filetype_default',
                            command_arguments = [ 'GoToType' ],
                            line_num = 39,
                            column_num = 8,
                            contents = contents,
                            filetype = 'typescript',
                            filepath = filepath )

  response = app.post_json( '/run_completer_command',
                            goto_data,
                            expect_errors = True ).json
  assert_that( response,
               ErrorMatcher( RuntimeError, 'Could not find type definition' ) )


@SharedYcmd
def Subcommands_RefactorRename_Missing_test( app ):
  filepath = PathToTestFile( 'test.ts' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'typescript',
                             contents = contents,
                             event_name = 'BufferVisit' )

  app.post_json( '/event_notification', event_data )

  request = BuildRequest( completer_target = 'filetype_default',
                          command_arguments = [ 'RefactorRename' ],
                          line_num = 30,
                          column_num = 6,
                          contents = contents,
                          filetype = 'typescript',
                          filepath = filepath )

  response = app.post_json( '/run_completer_command',
                            request,
                            expect_errors = True ).json
  assert_that( response,
               ErrorMatcher( ValueError,
                             'Please specify a new name to rename it to.\n'
                             'Usage: RefactorRename <new name>' ) )


@SharedYcmd
def Subcommands_RefactorRename_NotPossible_test( app ):
  filepath = PathToTestFile( 'test.ts' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'typescript',
                             contents = contents,
                             event_name = 'BufferVisit' )

  app.post_json( '/event_notification', event_data )

  request = BuildRequest( completer_target = 'filetype_default',
                          command_arguments = [
                            'RefactorRename',
                            'whatever'
                          ],
                          line_num = 35,
                          column_num = 5,
                          contents = contents,
                          filetype = 'typescript',
                          filepath = filepath )

  response = app.post_json( '/run_completer_command',
                            request,
                            expect_errors = True ).json
  assert_that( response,
               ErrorMatcher( RuntimeError,
                             'Value cannot be renamed: '
                             'You cannot rename this element.' ) )


@SharedYcmd
def Subcommands_RefactorRename_Simple_test( app ):
  filepath = PathToTestFile( 'test.ts' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'typescript',
                             contents = contents,
                             event_name = 'BufferVisit' )

  app.post_json( '/event_notification', event_data )

  request = BuildRequest( completer_target = 'filetype_default',
                          command_arguments = [ 'RefactorRename', 'test' ],
                          line_num = 2,
                          column_num = 8,
                          contents = contents,
                          filetype = 'typescript',
                          filepath = filepath )

  response = app.post_json( '/run_completer_command',
                            request ).json

  pprint.pprint( response, indent = 2 )

  assert_that( response, has_entries ( {
    'fixits': contains( has_entries( {
      'chunks': contains_inanyorder(
        ChunkMatcher(
          'test',
          LocationMatcher( filepath, 14, 15 ),
          LocationMatcher( filepath, 14, 18 ) ),
        ChunkMatcher(
          'test',
          LocationMatcher( filepath, 2, 7 ),
          LocationMatcher( filepath, 2, 10 ) ),
      ),
      'location': LocationMatcher( filepath, 2, 8 )
    } ) )
  } ) )


@SharedYcmd
def Subcommands_RefactorRename_MultipleFiles_test( app ):
  filepath = PathToTestFile( 'test.ts' )
  file2 = PathToTestFile( 'file2.ts' )
  file3 = PathToTestFile( 'file3.ts' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'typescript',
                             contents = contents,
                             event_name = 'BufferVisit' )

  app.post_json( '/event_notification', event_data )

  request = BuildRequest( completer_target = 'filetype_default',
                          command_arguments = [
                            'RefactorRename',
                            'this-is-a-longer-string'
                          ],
                          line_num = 25,
                          column_num = 9,
                          contents = contents,
                          filetype = 'typescript',
                          filepath = filepath )

  response = app.post_json( '/run_completer_command',
                            request ).json

  pprint.pprint( response, indent = 2 )

  assert_that( response, has_entries ( {
    'fixits': contains( has_entries( {
      'chunks': contains_inanyorder(
        ChunkMatcher(
          'this-is-a-longer-string',
          LocationMatcher( filepath, 25, 7 ),
          LocationMatcher( filepath, 25, 10 ) ),
        ChunkMatcher(
          'this-is-a-longer-string',
          LocationMatcher( filepath, 33, 15 ),
          LocationMatcher( filepath, 33, 18 ) ),
        ChunkMatcher(
          'this-is-a-longer-string',
          LocationMatcher( filepath, 37, 1 ),
          LocationMatcher( filepath, 37, 4 ) ),
        ChunkMatcher(
          'this-is-a-longer-string',
          LocationMatcher( file2, 1, 5 ),
          LocationMatcher( file2, 1, 8 ) ),
        ChunkMatcher(
          'this-is-a-longer-string',
          LocationMatcher( file3, 1, 15 ),
          LocationMatcher( file3, 1, 18 ) ),
      ),
      'location': LocationMatcher( filepath, 25, 9 )
    } ) )
  } ) )


@SharedYcmd
def Subcommands_RefactorRename_SimpleUnicode_test( app ):
  filepath = PathToTestFile( 'unicode.ts' )
  contents = ReadFile( filepath )

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'typescript',
                             contents = contents,
                             event_name = 'BufferVisit' )

  app.post_json( '/event_notification', event_data )

  request = BuildRequest( completer_target = 'filetype_default',
                          command_arguments = [ 'RefactorRename', 'ø' ],
                          line_num = 14,
                          column_num = 3,
                          contents = contents,
                          filetype = 'typescript',
                          filepath = filepath )

  response = app.post_json( '/run_completer_command',
                            request ).json

  pprint.pprint( response, indent = 2 )

  assert_that( response, has_entries ( {
    'fixits': contains( has_entries( {
      'chunks': contains_inanyorder(
        ChunkMatcher(
          'ø',
          LocationMatcher( filepath, 14, 3 ),
          LocationMatcher( filepath, 14, 5 ) ),
        ChunkMatcher(
          'ø',
          LocationMatcher( filepath, 20, 27 ),
          LocationMatcher( filepath, 20, 29 ) ),
        ChunkMatcher(
          'ø',
          LocationMatcher( filepath, 23, 5 ),
          LocationMatcher( filepath, 23, 7 ) ),
        ChunkMatcher(
          'ø',
          LocationMatcher( filepath, 27, 17),
          LocationMatcher( filepath, 27, 19 ) ),
      ),
      'location': LocationMatcher( filepath, 14, 3 )
    } ) )
  } ) )
