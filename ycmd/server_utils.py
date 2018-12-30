# Copyright (C) 2013-2018 ycmd contributors
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

import os.path as p
import re
import sys

ROOT_DIR = p.normpath( p.join( p.dirname( __file__ ), '..' ) )
DIR_OF_THIRD_PARTY = p.join( ROOT_DIR, 'third_party' )
PYTHON_STDLIB_ZIP_REGEX = re.compile( 'python[23][0-9]\\.zip' )


def IsStandardLibraryFolder( path ):
  return ( ( p.isfile( path )
             and PYTHON_STDLIB_ZIP_REGEX.match( p.basename( path ) ) )
           or p.isfile( p.join( path, 'os.py' ) ) )


def IsVirtualEnvLibraryFolder( path ):
  return p.isfile( p.join( path, 'orig-prefix.txt' ) )


def GetStandardLibraryIndexInSysPath():
  for index, path in enumerate( sys.path ):
    if ( IsStandardLibraryFolder( path ) and
         not IsVirtualEnvLibraryFolder( path ) ):
      return index
  raise RuntimeError( 'Could not find standard library path in Python path.' )


def SetUpPythonPath():
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
  sys.path.insert( GetStandardLibraryIndexInSysPath() + 1,
                   p.join( DIR_OF_THIRD_PARTY, 'python-future', 'src' ) )
  sys.path[ 0:0 ] = [ p.join( ROOT_DIR ),
                      p.join( DIR_OF_THIRD_PARTY, 'bottle' ),
                      p.join( DIR_OF_THIRD_PARTY, 'cregex',
                              'regex_{}'.format( sys.version_info[ 0 ] ) ),
                      p.join( DIR_OF_THIRD_PARTY, 'frozendict' ),
                      p.join( DIR_OF_THIRD_PARTY, 'jedi_deps', 'jedi' ),
                      p.join( DIR_OF_THIRD_PARTY, 'jedi_deps', 'parso' ),
                      p.join( DIR_OF_THIRD_PARTY, 'requests_deps', 'requests' ),
                      p.join( DIR_OF_THIRD_PARTY, 'requests_deps', 'chardet' ),
                      p.join( DIR_OF_THIRD_PARTY, 'requests_deps', 'certifi' ),
                      p.join( DIR_OF_THIRD_PARTY, 'requests_deps', 'idna' ),
                      p.join( DIR_OF_THIRD_PARTY,
                              'requests_deps',
                              'urllib3',
                              'src' ),
                      p.join( DIR_OF_THIRD_PARTY, 'waitress' ) ]
