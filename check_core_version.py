#!/usr/bin/env python
#
# Copyright (C) 2015  Google Inc.
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

import sys
import os
import ycm_client_support

VERSION_FILENAME = 'EXPECTED_CORE_VERSION'

def DirectoryOfThisScript():
  return os.path.dirname( os.path.abspath( __file__ ) )


def ExpectedCoreVersion():
  return int( open( os.path.join( DirectoryOfThisScript(),
                                  VERSION_FILENAME ) ).read() )


def CompatibleWithCurrentCoreVersion():
  try:
    current_core_version = ycm_client_support.YcmCoreVersion()
  except AttributeError:
    return False
  return ExpectedCoreVersion() == current_core_version


if not CompatibleWithCurrentCoreVersion():
  sys.exit( 2 )
sys.exit( 0 )
