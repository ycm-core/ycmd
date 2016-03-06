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

from hamcrest import assert_that, contains_inanyorder, has_entries
from .typescript_handlers_test import Typescript_Handlers_test
from ycmd.utils import ReadFile
from mock import patch


class TypeScript_GetCompletions_test( Typescript_Handlers_test ):

  def _RunTest( self, test ):
    filepath = self._PathToTestFile( 'test.ts' )
    contents = ReadFile( filepath )

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

    response = self._app.post_json( '/completions', completion_data )
    assert_that( response.json, test[ 'expect' ][ 'data' ] )


  def Basic_test( self ):
    self._RunTest( {
      'expect': {
        'data': has_entries( {
          'completions': contains_inanyorder(
            self.CompletionEntryMatcher(
              'methodA',
              'methodA (method) Foo.methodA(): void' ),
            self.CompletionEntryMatcher(
              'methodB',
              'methodB (method) Foo.methodB(): void' ),
            self.CompletionEntryMatcher(
              'methodC',
              'methodC (method) Foo.methodC(): void' ),
          )
        } )
      }
    } )


  @patch( 'ycmd.completers.typescript.'
            'typescript_completer.MAX_DETAILED_COMPLETIONS',
          2 )
  def MaxDetailedCompletion_test( self ):
    self._RunTest( {
      'expect': {
        'data': has_entries( {
          'completions': contains_inanyorder(
            self.CompletionEntryMatcher( 'methodA' ),
            self.CompletionEntryMatcher( 'methodB' ),
            self.CompletionEntryMatcher( 'methodC' )
          )
        } )
      }
    } )
