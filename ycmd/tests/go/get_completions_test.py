# encoding: utf-8
#
# Copyright (C) 2015-2018 ycmd contributors
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

from hamcrest import all_of, assert_that, has_items

from ycmd.tests.go import PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import BuildRequest, CompletionEntryMatcher
from ycmd.utils import ReadFile


@SharedYcmd
def GetCompletions_Basic_test( app ):
  filepath = PathToTestFile( 'td', 'test.go' )
  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'go',
                                  contents = ReadFile( filepath ),
                                  force_semantic = True,
                                  line_num = 9,
                                  column_num = 9 )

  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]
  assert_that( results,
               all_of(
                 has_items(
                   CompletionEntryMatcher(
                     'Llongfile',
                     'int',
                     {
                       'detailed_info': 'Llongfile = 8\n\n',
                       'menu_text': 'Llongfile = 8',
                       'kind': 'Constant',
                     }
                   ),
                   CompletionEntryMatcher(
                     'Logger',
                     'struct{...}',
                     {
                       'detailed_info': 'Logger\n\n',
                       'menu_text': 'Logger',
                       'kind': 'Struct',
                     }
                   ) ) ) )
