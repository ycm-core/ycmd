# Copyright (C) 2016 ycmd contributors
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

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()
from builtins import *  # noqa

from hamcrest import assert_that, contains_string, matches_regexp

from ycmd.tests.clang import IsolatedYcmd, PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import BuildRequest


@SharedYcmd
def DebugInfo_ExtraConfLoaded_test( app ):
  app.post_json( '/load_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  request_data = BuildRequest( filepath = PathToTestFile( 'basic.cpp' ),
                               filetype = 'cpp' )
  assert_that(
    app.post_json( '/debug_info', request_data ).json,
    matches_regexp( 'C-family completer debug information:\n'
                    '  Configuration file found and loaded\n'
                    '  Configuration path: .+\n'
                    '  Flags: .+' ) )


@SharedYcmd
def DebugInfo_NoExtraConfFound_test( app ):
  request_data = BuildRequest( filetype = 'cpp' )
  # First time, an exception is raised when no .ycm_extra_conf.py file is found.
  assert_that(
    app.post_json( '/debug_info', request_data ).json,
    contains_string( 'C-family completer debug information:\n'
                     '  No configuration file found' ) )
  # Second time, None is returned as the .ycm_extra_conf.py path.
  assert_that(
    app.post_json( '/debug_info', request_data ).json,
    contains_string( 'C-family completer debug information:\n'
                     '  No configuration file found' ) )


@IsolatedYcmd
def DebugInfo_ExtraConfFoundButNotLoaded_test( app ):
  request_data = BuildRequest( filepath = PathToTestFile( 'basic.cpp' ),
                               filetype = 'cpp' )
  assert_that(
    app.post_json( '/debug_info', request_data ).json,
    matches_regexp(
      'C-family completer debug information:\n'
      '  Configuration file found but not loaded\n'
      '  Configuration path: .+' ) )
