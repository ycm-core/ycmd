# Copyright (C) 2017 ycmd contributors
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

from hamcrest import ( assert_that,
                       contains_string,
                       equal_to,
                       has_entry,
                       has_entries )

from ycmd.tests.typescript import PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import BuildRequest
from ycmd.utils import ReadFile


@SharedYcmd
def Diagnostics_FileReadyToParse_test( app ):
  main_filepath = PathToTestFile( 'test.ts' )
  main_contents = ReadFile( main_filepath )

  event_data = BuildRequest( filepath = main_filepath,
                             filetype = 'typescript',
                             contents = main_contents,
                             event_name = 'BufferVisit' )
  app.post_json( '/event_notification', event_data )

  event_data = BuildRequest( filepath = main_filepath,
                             filetype = 'typescript',
                             contents = main_contents,
                             event_name = 'FileReadyToParse' )
  results = app.post_json( '/event_notification', event_data ).json

  expected_text = ( 'Property \'nonExistingMethod\' '
                    'does not exist on type \'Bar\'.' )

  assert_that( results[1],
               has_entries( {
                 'kind': equal_to( 'ERROR' ),
                 'text': equal_to( expected_text ),
                 'location': has_entries( {
                   'column_num': 1,
                   'filepath': main_filepath,
                   'line_num': 35
                 } ),
                 'location_extent': has_entries( {
                   'start': has_entries( {
                     'column_num': 1,
                     'filepath': main_filepath,
                     'line_num': 35
                   } ),
                   'end': has_entries( {
                     'column_num': 1,
                     'line_num': 35,
                     'filepath': main_filepath
                   } ),
                 } )
               } ) )


@SharedYcmd
def Diagnostics_DetailedDiagnostics_test( app ):
  main_filepath = PathToTestFile( 'test.ts' )
  main_contents = ReadFile( main_filepath )

  event_data = BuildRequest( filepath = main_filepath,
                             filetype = 'typescript',
                             contents = main_contents,
                             event_name = 'BufferVisit' )
  app.post_json( '/event_notification', event_data )

  event_data = BuildRequest( filepath = main_filepath,
                             filetype = 'typescript',
                             contents = main_contents,
                             line_num = 35,
                             column_num = 6 )

  results = app.post_json( '/detailed_diagnostic', event_data ).json

  expected_message = ( 'Property \'nonExistingMethod\' '
                       'does not exist on type \'Bar\'.' )

  assert_that( results,
               has_entry(
                   'message',
                   contains_string( expected_message ) ) )
