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

from nose.tools import eq_

from ycmd.tests.rust import PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import BuildRequest
from ycmd.utils import ReadFile


@SharedYcmd
def RunGoToTest( app, params ):
  filepath = PathToTestFile( 'test.rs' )
  contents = ReadFile( filepath )

  command = params[ 'command' ]
  goto_data = BuildRequest( completer_target = 'filetype_default',
                            command_arguments = [ command ],
                            line_num = 7,
                            column_num = 12,
                            contents = contents,
                            filetype = 'rust',
                            filepath = filepath )

  results = app.post_json( '/run_completer_command',
                           goto_data )

  eq_( {
    'line_num': 1, 'column_num': 8, 'filepath': filepath
  }, results.json )


def Subcommands_GoTo_all_test():
  tests = [
    { 'command': 'GoTo' },
    { 'command': 'GoToDefinition' },
    { 'command': 'GoToDeclaration' }
  ]

  for test in tests:
    yield RunGoToTest, test
