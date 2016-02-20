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

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()
from builtins import *  # noqa

from hamcrest import raises, assert_that, calling
from nose.tools import ok_
from ycmd.server_utils import ( PathToNearestThirdPartyFolder,
                                AddNearestThirdPartyFoldersToSysPath )
import os.path


def PathToNearestThirdPartyFolder_Success_test():
  ok_( PathToNearestThirdPartyFolder( os.path.abspath( __file__ ) ) )


def PathToNearestThirdPartyFolder_Failure_test():
  ok_( not PathToNearestThirdPartyFolder( os.path.expanduser( '~' ) ) )


def AddNearestThirdPartyFoldersToSysPath_Failure_test():
  assert_that(
    calling( AddNearestThirdPartyFoldersToSysPath ).with_args(
      os.path.expanduser( '~' ) ),
    raises( RuntimeError, '.*third_party folder.*' ) )
