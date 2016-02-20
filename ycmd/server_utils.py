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

DIR_OF_CURRENT_SCRIPT = os.path.dirname( os.path.abspath( __file__ ) )


def SetUpPythonPath():
  sys.path.insert( 0, os.path.join( DIR_OF_CURRENT_SCRIPT, '..' ) )

  AddNearestThirdPartyFoldersToSysPath( __file__ )


def ExpectedCoreVersion():
  filepath = os.path.join( DIR_OF_CURRENT_SCRIPT, '..', VERSION_FILENAME )
  with io.open( filepath, encoding = 'utf8' ) as f:
    return int( f.read() )


def CompatibleWithCurrentCoreVersion():
  import ycm_core
  try:
    current_core_version = ycm_core.YcmCoreVersion()
  except AttributeError:
    return False
  return ExpectedCoreVersion() == current_core_version


def AncestorFolders( path ):
  folder = os.path.normpath( path )
  while True:
    parent = os.path.dirname( folder )
    if parent == folder:
      break
    folder = parent
    yield folder


def PathToNearestThirdPartyFolder( path ):
  for folder in AncestorFolders( path ):
    path_to_third_party = os.path.join( folder, 'third_party' )
    if os.path.isdir( path_to_third_party ):
      return path_to_third_party
  return None


def AddNearestThirdPartyFoldersToSysPath( filepath ):
  path_to_third_party = PathToNearestThirdPartyFolder( filepath )
  if not path_to_third_party:
    raise RuntimeError(
        'No third_party folder found for: {0}'.format( filepath ) )

  # NOTE: Any hacks for loading modules that can't be imported without custom
  # logic need to be reproduced in run_tests.py as well.
  for folder in os.listdir( path_to_third_party ):
    # python-future needs special handling. Not only does it store the modules
    # under its 'src' folder, but SOME of its modules are only meant to be
    # accessible under py2, not py3. This is because these modules (like
    # `queue`) are implementations of modules present in the py3 standard
    # library. So to work around issues, we place the python-future last on
    # sys.path so that they can be overriden by the standard library.
    if folder == 'python-future':
      folder = os.path.join( folder, 'src' )
      sys.path.append( os.path.realpath( os.path.join( path_to_third_party,
                                                       folder ) ) )
      continue
    sys.path.insert( 0, os.path.realpath( os.path.join( path_to_third_party,
                                                        folder ) ) )
