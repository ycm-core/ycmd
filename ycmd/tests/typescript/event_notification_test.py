# Copyright (C) 2016-2018 ycmd contributors
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
# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa

from hamcrest import assert_that, contains, has_entries

from ycmd.tests.typescript import IsolatedYcmd, PathToTestFile
from ycmd.tests.test_utils import BuildRequest, CompletionEntryMatcher
from ycmd.utils import ReadFile


@IsolatedYcmd()
def EventNotification_OnBufferUnload_CloseFile_test( app ):
  # Open main.ts file in a buffer.
  main_filepath = PathToTestFile( 'buffer_unload', 'main.ts' )
  main_contents = ReadFile( main_filepath )

  event_data = BuildRequest( filepath = main_filepath,
                             filetype = 'typescript',
                             contents = main_contents,
                             event_name = 'BufferVisit' )
  app.post_json( '/event_notification', event_data )

  # Complete in main.ts buffer an object defined in imported.ts.
  completion_data = BuildRequest( filepath = main_filepath,
                                  filetype = 'typescript',
                                  contents = main_contents,
                                  line_num = 3,
                                  column_num = 10 )
  response = app.post_json( '/completions', completion_data )
  assert_that( response.json, has_entries( {
    'completions': contains( CompletionEntryMatcher( 'method' ) ) } ) )

  # Open imported.ts file in another buffer.
  imported_filepath = PathToTestFile( 'buffer_unload', 'imported.ts' )
  imported_contents = ReadFile( imported_filepath )

  event_data = BuildRequest( filepath = imported_filepath,
                             filetype = 'typescript',
                             contents = imported_contents,
                             event_name = 'BufferVisit' )
  app.post_json( '/event_notification', event_data )

  # Modify imported.ts buffer without writing the changes to disk.
  modified_imported_contents = imported_contents.replace( 'method',
                                                          'modified_method' )

  # FIXME: TypeScript completer should not rely on the FileReadyToParse events
  # to synchronize the contents of dirty buffers but use instead the file_data
  # field of the request.
  event_data = BuildRequest( filepath = imported_filepath,
                             filetype = 'typescript',
                             contents = modified_imported_contents,
                             event_name = 'FileReadyToParse' )
  app.post_json( '/event_notification', event_data )

  # Complete at same location in main.ts buffer.
  imported_data = {
    imported_filepath: {
      'filetypes': [ 'typescript' ],
      'contents': modified_imported_contents
    }
  }
  completion_data = BuildRequest( filepath = main_filepath,
                                  filetype = 'typescript',
                                  contents = main_contents,
                                  line_num = 3,
                                  column_num = 10,
                                  file_data = imported_data )
  response = app.post_json( '/completions', completion_data )
  assert_that( response.json, has_entries( {
    'completions': contains( CompletionEntryMatcher( 'modified_method' ) ) } )
  )

  # Unload imported.ts buffer.
  event_data = BuildRequest( filepath = imported_filepath,
                             filetype = 'typescript',
                             contents = imported_contents,
                             event_name = 'BufferUnload' )
  app.post_json( '/event_notification', event_data )

  # Complete at same location in main.ts buffer.
  completion_data = BuildRequest( filepath = main_filepath,
                                  filetype = 'typescript',
                                  contents = main_contents,
                                  line_num = 3,
                                  column_num = 10 )
  response = app.post_json( '/completions', completion_data )
  assert_that( response.json, has_entries( {
    'completions': contains( CompletionEntryMatcher( 'method' ) ) } ) )
