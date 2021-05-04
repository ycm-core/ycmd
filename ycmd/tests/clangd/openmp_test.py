# Copyright (C) 2020 ycmd contributors
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

from hamcrest import ( assert_that,
                       contains_exactly,
                       empty,
                       has_entries )
from pprint import pprint

from ycmd.tests.clangd import ( IsolatedYcmd,
                                PathToTestFile,
                                RunAfterInitialized )
from ycmd.utils import ReadFile


@IsolatedYcmd()
def OpenMp_HeaderFound_test( app ):
  filepath = PathToTestFile( 'openmp.cpp' )
  contents = ReadFile( filepath )
  request = { 'contents': contents,
              'filepath': filepath,
              'filetype': 'cpp' }

  test = { 'request': request, 'route': '/receive_messages' }
  response = RunAfterInitialized( app, test )
  pprint( response )
  assert_that( response, contains_exactly(
      has_entries( { 'diagnostics': empty() } ) ) )
