#!/usr/bin/env python
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

from hamcrest import assert_that, has_items
from typescript_handlers_test import Typescript_Handlers_test


class TypeScript_GetCompletions_test( Typescript_Handlers_test ):

  def Basic_test( self ):
    filepath = self._PathToTestFile( 'test.ts' )
    contents = open( filepath ).read()

    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'typescript',
                                     contents = contents,
                                     event_name = 'BufferVisit' )

    self._app.post_json( '/event_notification', event_data )

    completion_data = self._BuildRequest( filepath = filepath,
                                          filetype = 'typescript',
                                          contents = contents,
                                          force_semantic = True,
                                          line_num = 12,
                                          column_num = 6 )

    results = self._app.post_json( '/completions',
                                   completion_data ).json[ 'completions' ]
    assert_that( results,
                 has_items( self._CompletionEntryMatcher( 'methodA' ),
                            self._CompletionEntryMatcher( 'methodB' ),
                            self._CompletionEntryMatcher( 'methodC' ) ) )
