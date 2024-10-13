# Copyright (C) 2021 ycmd contributors
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

from hamcrest import assert_that, has_entry
from unittest import TestCase

from ycmd.tests.cs import setUpModule, tearDownModule # noqa
from ycmd.tests.cs import PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import ( BuildRequest,
                                    WaitForDiagnosticsToBeReady,
                                    WithRetry )
from ycmd.utils import ReadFile


class DiagnosticsTest( TestCase ):
  @WithRetry()
  @SharedYcmd
  def test_Diagnostics_DetailedDiags( self, app ):
    filepath = PathToTestFile( 'testy', 'Program.cs' )
    contents = ReadFile( filepath )
    WaitForDiagnosticsToBeReady( app, filepath, contents, 'cs' )
    request_data = BuildRequest( contents = contents,
                                 filepath = filepath,
                                 filetype = 'cs',
                                 line_num = 11,
                                 column_num = 1 )

    results = app.post_json( '/detailed_diagnostic', request_data ).json
    assert_that( results,
                 has_entry( 'message',
                            "'Console' does not contain "
                            "a definition for '' [CS0117]" ) )
