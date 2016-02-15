# Copyright (C) 2013 Google Inc.
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
# No other imports from `future` because this module is loaded before we have
# put our submodules in sys.path

import sys
import os
import io

VERSION_FILENAME = 'CORE_VERSION'
CORE_NOT_COMPATIBLE_MESSAGE = (
  'ycmd can\'t run: ycm_core lib too old, PLEASE RECOMPILE'
)


def DirectoryOfThisScript():
  return os.path.dirname( os.path.abspath( __file__ ) )


def SetUpPythonPath():
  sys.path.insert( 0, os.path.join( DirectoryOfThisScript(), '..' ) )

  from ycmd import utils
  utils.AddNearestThirdPartyFoldersToSysPath( __file__ )


def ExpectedCoreVersion():
  filepath = os.path.join( DirectoryOfThisScript(), '..', VERSION_FILENAME )
  with io.open( filepath, encoding = 'utf8' ) as f:
    return int( f.read() )


def CompatibleWithCurrentCoreVersion():
  import ycm_core
  try:
    current_core_version = ycm_core.YcmCoreVersion()
  except AttributeError:
    return False
  return ExpectedCoreVersion() == current_core_version
