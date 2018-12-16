# Copyright (C) 2016-2018 ycmd contributors
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
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa

from hamcrest import assert_that, calling, equal_to, raises
from mock import patch

from ycmd.server_utils import GetStandardLibraryIndexInSysPath
from ycmd.tests import PathToTestFile


@patch( 'sys.path', [
  PathToTestFile( 'python-future', 'some', 'path' ),
  PathToTestFile( 'python-future', 'another', 'path' ) ] )
def GetStandardLibraryIndexInSysPath_ErrorIfNoStandardLibrary_test( *args ):
  assert_that(
    calling( GetStandardLibraryIndexInSysPath ),
    raises( RuntimeError,
            'Could not find standard library path in Python path.' ) )


@patch( 'sys.path', [
  PathToTestFile( 'python-future', 'some', 'path' ),
  PathToTestFile( 'python-future', 'standard_library' ),
  PathToTestFile( 'python-future', 'another', 'path' ) ] )
def GetStandardLibraryIndexInSysPath_FindFullStandardLibrary_test( *args ):
  assert_that( GetStandardLibraryIndexInSysPath(), equal_to( 1 ) )


@patch( 'sys.path', [
  PathToTestFile( 'python-future', 'some', 'path' ),
  PathToTestFile( 'python-future', 'embedded_standard_library',
                                   'python35.zip' ),
  PathToTestFile( 'python-future', 'another', 'path' ) ] )
def GetStandardLibraryIndexInSysPath_FindEmbeddedStandardLibrary_test( *args ):
  assert_that( GetStandardLibraryIndexInSysPath(), equal_to( 1 ) )
