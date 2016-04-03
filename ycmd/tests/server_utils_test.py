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

from hamcrest import ( assert_that, calling, contains, contains_inanyorder,
                       raises )
from mock import patch
from nose.tools import ok_
import os.path
import sys

from ycmd.server_utils import ( AddNearestThirdPartyFoldersToSysPath,
                                PathToNearestThirdPartyFolder )

DIR_OF_THIRD_PARTY = os.path.abspath(
  os.path.join( os.path.dirname( __file__ ), '..', '..', 'third_party' ) )
THIRD_PARTY_FOLDERS = (
  os.path.join( DIR_OF_THIRD_PARTY, 'argparse' ),
  os.path.join( DIR_OF_THIRD_PARTY, 'bottle' ),
  os.path.join( DIR_OF_THIRD_PARTY, 'frozendict' ),
  os.path.join( DIR_OF_THIRD_PARTY, 'godef' ),
  os.path.join( DIR_OF_THIRD_PARTY, 'gocode' ),
  os.path.join( DIR_OF_THIRD_PARTY, 'JediHTTP' ),
  os.path.join( DIR_OF_THIRD_PARTY, 'OmniSharpServer' ),
  os.path.join( DIR_OF_THIRD_PARTY, 'racerd' ),
  os.path.join( DIR_OF_THIRD_PARTY, 'requests' ),
  os.path.join( DIR_OF_THIRD_PARTY, 'tern_runtime' ),
  os.path.join( DIR_OF_THIRD_PARTY, 'waitress' )
)


def PathToNearestThirdPartyFolder_Success_test():
  ok_( PathToNearestThirdPartyFolder( os.path.abspath( __file__ ) ) )


def PathToNearestThirdPartyFolder_Failure_test():
  ok_( not PathToNearestThirdPartyFolder( os.path.expanduser( '~' ) ) )


def AddNearestThirdPartyFoldersToSysPath_Failure_test():
  assert_that(
    calling( AddNearestThirdPartyFoldersToSysPath ).with_args(
      os.path.expanduser( '~' ) ),
    raises( RuntimeError, '.*third_party folder.*' ) )


@patch( 'sys.path', [ '/some/path',
                      '/first/path/to/site-packages',
                      '/another/path',
                      '/second/path/to/site-packages' ] )
def AddNearestThirdPartyFoldersToSysPath_FutureBeforeSitePackages_test():
  AddNearestThirdPartyFoldersToSysPath( __file__ )
  assert_that( sys.path[ : len( THIRD_PARTY_FOLDERS ) ], contains_inanyorder(
    *THIRD_PARTY_FOLDERS
  ) )
  assert_that( sys.path[ len( THIRD_PARTY_FOLDERS ) : ], contains(
    '/some/path',
    os.path.join( DIR_OF_THIRD_PARTY, 'python-future', 'src' ),
    '/first/path/to/site-packages',
    '/another/path',
    '/second/path/to/site-packages',
  ) )


@patch( 'sys.path', [ '/some/path',
                      '/first/path/to/dist-packages',
                      '/another/path',
                      '/second/path/to/dist-packages' ] )
def AddNearestThirdPartyFoldersToSysPath_FutureBeforeDistPackages_test():
  AddNearestThirdPartyFoldersToSysPath( __file__ )
  assert_that( sys.path[ : len( THIRD_PARTY_FOLDERS ) ], contains_inanyorder(
    *THIRD_PARTY_FOLDERS
  ) )
  assert_that( sys.path[ len( THIRD_PARTY_FOLDERS ) : ], contains(
    '/some/path',
    os.path.join( DIR_OF_THIRD_PARTY, 'python-future', 'src' ),
    '/first/path/to/dist-packages',
    '/another/path',
    '/second/path/to/dist-packages',
  ) )


@patch( 'sys.path', [ '/some/path',
                      '/another/path' ] )
def AddNearestThirdPartyFoldersToSysPath_FutureLastIfNoPackages_test():
  AddNearestThirdPartyFoldersToSysPath( __file__ )
  assert_that( sys.path[ : len( THIRD_PARTY_FOLDERS ) ], contains_inanyorder(
    *THIRD_PARTY_FOLDERS
  ) )
  assert_that( sys.path[ len( THIRD_PARTY_FOLDERS ) : ], contains(
    '/some/path',
    '/another/path',
    os.path.join( DIR_OF_THIRD_PARTY, 'python-future', 'src' ),
  ) )
