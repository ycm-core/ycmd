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
# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa

from hamcrest import ( assert_that, contains_string, equal_to,
                       has_entries )

from ycmd.tests.swift import PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import BuildRequest
from ycmd.utils import ReadFile


@SharedYcmd
def GetDiagnostics_Warning_test( app ):
  filepath = PathToTestFile( 'some_swift.swift' )
  contents = ReadFile( filepath )

  contents = ReadFile( filepath )
  event_data = BuildRequest( event_name = 'FileReadyToParse',
                             contents = contents,
                             filetype = 'swift' )

  results = app.post_json( '/event_notification', event_data ).json


  assert_that( results[ 0 ],
               has_entries( {
                 'kind': equal_to( 'WARNING' ),
                 'text': contains_string(
                    "string interpolation produces a debug description" ),
                 'location': has_entries( {
                    'line_num': equal_to( 16 ),
                    'column_num': equal_to( 40 ) } )
                  } ) )
