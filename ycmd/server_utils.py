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

import io
import logging
import os
import re
import sys

CORE_MISSING_ERROR_REGEX = re.compile( "No module named '?ycm_core'?" )
CORE_PYTHON2_ERROR_REGEX = re.compile(
  'dynamic module does not define (?:init|module export) '
  'function \(PyInit_ycm_core\)|'
  'Module use of python2[0-9].dll conflicts with this version of Python\.$' )
CORE_PYTHON3_ERROR_REGEX = re.compile(
  'dynamic module does not define init function \(initycm_core\)|'
  'Module use of python3[0-9].dll conflicts with this version of Python\.$' )

CORE_MISSING_MESSAGE = (
  'ycm_core library not detected; you need to compile it by running the '
  'build.py script. See the documentation for more details.' )
CORE_PYTHON2_MESSAGE = (
  'ycm_core library compiled for Python 2 but loaded in Python 3.' )
CORE_PYTHON3_MESSAGE = (
  'ycm_core library compiled for Python 3 but loaded in Python 2.' )
CORE_OUTDATED_MESSAGE = (
  'ycm_core library too old; PLEASE RECOMPILE by running the build.py script. '
  'See the documentation for more details.' )

# Exit statuses returned by the CompatibleWithCurrentCore function:
#  - CORE_COMPATIBLE_STATUS: ycm_core is compatible;
#  - CORE_UNEXPECTED_STATUS: unexpected error while loading ycm_core;
#  - CORE_MISSING_STATUS   : ycm_core is missing;
#  - CORE_PYTHON2_STATUS   : ycm_core is compiled with Python 2 but loaded with
#    Python 3;
#  - CORE_PYTHON3_STATUS   : ycm_core is compiled with Python 3 but loaded with
#    Python 2;
#  - CORE_OUTDATED_STATUS  : ycm_core version is outdated.
# Values 1 and 2 are not used because 1 is for general errors and 2 has often a
# special meaning for Unix programs. See
# https://docs.python.org/2/library/sys.html#sys.exit
CORE_COMPATIBLE_STATUS  = 0
CORE_UNEXPECTED_STATUS  = 3
CORE_MISSING_STATUS     = 4
CORE_PYTHON2_STATUS     = 5
CORE_PYTHON3_STATUS     = 6
CORE_OUTDATED_STATUS    = 7

VERSION_FILENAME = 'CORE_VERSION'

DIR_OF_CURRENT_SCRIPT = os.path.dirname( os.path.abspath( __file__ ) )
DIR_PACKAGES_REGEX = re.compile( '(site|dist)-packages$' )

_logger = logging.getLogger( __name__ )


def ExpectedCoreVersion():
  filepath = os.path.join( DIR_OF_CURRENT_SCRIPT, '..', VERSION_FILENAME )
  with io.open( filepath, encoding = 'utf8' ) as f:
    return int( f.read() )


def ImportCore():
  """Imports and returns the ycm_core module. This function exists for easily
  mocking this import in tests."""
  import ycm_core as ycm_core
  return ycm_core


def CompatibleWithCurrentCore():
  """Checks if ycm_core library is compatible and returns with an exit
  status."""
  try:
    ycm_core = ImportCore()
  except ImportError as error:
    message = str( error )
    if CORE_MISSING_ERROR_REGEX.match( message ):
      _logger.exception( CORE_MISSING_MESSAGE )
      return CORE_MISSING_STATUS
    if CORE_PYTHON2_ERROR_REGEX.match( message ):
      _logger.exception( CORE_PYTHON2_MESSAGE )
      return CORE_PYTHON2_STATUS
    if CORE_PYTHON3_ERROR_REGEX.match( message ):
      _logger.exception( CORE_PYTHON3_MESSAGE )
      return CORE_PYTHON3_STATUS
    _logger.exception( message )
    return CORE_UNEXPECTED_STATUS

  try:
    current_core_version = ycm_core.YcmCoreVersion()
  except AttributeError:
    _logger.exception( CORE_OUTDATED_MESSAGE )
    return CORE_OUTDATED_STATUS

  if ExpectedCoreVersion() != current_core_version:
    _logger.error( CORE_OUTDATED_MESSAGE )
    return CORE_OUTDATED_STATUS

  return CORE_COMPATIBLE_STATUS


def SetUpPythonPath():
  sys.path.insert( 0, os.path.join( DIR_OF_CURRENT_SCRIPT, '..' ) )

  AddNearestThirdPartyFoldersToSysPath( __file__ )


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


def GetStandardLibraryIndexInSysPath():
  for path in sys.path:
    if os.path.isfile( os.path.join( path, 'os.py' ) ):
      return sys.path.index( path )
  raise RuntimeError( 'Could not find standard library path in Python path.' )


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
    # library. Furthermore, we need to be sure that they are not overridden by
    # already installed packages (for example, the 'builtins' module from
    # 'pies2overrides' or a different version of 'python-future'). To work
    # around these issues, we place the python-future just after the Python
    # standard library so that its modules can be overridden by standard
    # modules but not by installed packages.
    if folder == 'python-future':
      folder = os.path.join( folder, 'src' )
      sys.path.insert( GetStandardLibraryIndexInSysPath() + 1,
                       os.path.realpath( os.path.join( path_to_third_party,
                                                       folder ) ) )
      continue
    sys.path.insert( 0, os.path.realpath( os.path.join( path_to_third_party,
                                                        folder ) ) )
