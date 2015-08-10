#!/usr/bin/env python
#
# Copyright (C) 2013  Google Inc.
#
# This file is part of YouCompleteMe.
#
# YouCompleteMe is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# YouCompleteMe is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with YouCompleteMe.  If not, see <http://www.gnu.org/licenses/>.

import sys
import os

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
  return int( open( os.path.join( DirectoryOfThisScript(), '..',
                                  VERSION_FILENAME ) ).read() )


def CompatibleWithCurrentCoreVersion():
  import ycm_core
  try:
    current_core_version = ycm_core.YcmCoreVersion()
  except AttributeError:
    return False
  return ExpectedCoreVersion() == current_core_version
