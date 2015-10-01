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

from ...server_utils import SetUpPythonPath
SetUpPythonPath()
from ..test_utils import BuildRequest, CompletionEntryMatcher, Setup
from .utils import PathToTestFile, StopGoCodeServer
from webtest import TestApp
from nose.tools import with_setup
from hamcrest import assert_that, has_item
from ... import handlers
import bottle

bottle.debug( True )


@with_setup( Setup )
def GetCompletions_GoCodeCompleter_test():
  app = TestApp( handlers.app )
  filepath = PathToTestFile( 'test.go' )
  completion_data = BuildRequest( filepath = filepath,
                                  filetype = 'go',
                                  contents = open( filepath ).read(),
                                  force_semantic = True,
                                  line_num = 9,
                                  column_num = 11)

  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]
  assert_that( results, has_item( CompletionEntryMatcher( u'Logger' ) ) )

  StopGoCodeServer( app )
