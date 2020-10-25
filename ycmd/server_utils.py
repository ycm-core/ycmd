# Copyright (C) 2013-2020 ycmd contributors
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
DIR_OF_WATCHDOG_DEPS = p.join( DIR_OF_THIRD_PARTY, 'watchdog_deps' )
PYTHON_STDLIB_ZIP_REGEX = re.compile( 'python3[0-9]\\.zip' )


def SetUpPythonPath():
  sys.path[ 0:0 ] = [ p.join( ROOT_DIR ),
                      p.join( DIR_OF_THIRD_PARTY, 'bottle' ),
                      p.join( DIR_OF_THIRD_PARTY, 'regex-build' ),
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
                      p.join( DIR_OF_WATCHDOG_DEPS,
                              'watchdog',
                              'build',
                              'lib3' ),
                      p.join( DIR_OF_WATCHDOG_DEPS, 'pathtools' ),
                      p.join( DIR_OF_THIRD_PARTY, 'waitress' ) ]
  sys.path.append( p.join( DIR_OF_THIRD_PARTY, 'jedi_deps', 'numpydoc' ) )
