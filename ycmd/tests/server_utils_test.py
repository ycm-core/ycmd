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
                       empty, equal_to, has_length, raises )
from mock import patch
from nose.tools import ok_
import os.path
import sys

from ycmd.server_utils import ( AddNearestThirdPartyFoldersToSysPath,
                                CompatibleWithCurrentCore,
                                PathToNearestThirdPartyFolder )
from ycmd.tests import PathToTestFile

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


@patch( 'ycmd.server_utils._logger', autospec = True )
def RunCompatibleWithCurrentCoreImportException( test, logger ):
  with patch( 'ycmd.server_utils.ImportCore',
              side_effect = ImportError( test[ 'exception_message' ] ) ):
    assert_that( CompatibleWithCurrentCore(),
                 equal_to( test[ 'exit_status' ] ) )

  assert_that( logger.method_calls, has_length( 1 ) )
  logger.exception.assert_called_with( test[ 'logged_message' ] )


@patch( 'ycmd.server_utils._logger', autospec = True )
def CompatibleWithCurrentCore_Compatible_test( logger ):
  assert_that( CompatibleWithCurrentCore(), equal_to( 0 ) )
  assert_that( logger.method_calls, empty() )


def CompatibleWithCurrentCore_Unexpected_test():
  RunCompatibleWithCurrentCoreImportException( {
    'exception_message': 'unexpected import exception',
    'exit_status': 3,
    'logged_message': 'unexpected import exception'
  } )


def CompatibleWithCurrentCore_Missing_test():
  import_errors = [
    # Raised by Python 2.
    'No module named ycm_core',
    # Raised by Python 3.
    "No module named 'ycm_core'"
  ]

  for error in import_errors:
    yield RunCompatibleWithCurrentCoreImportException, {
      'exception_message': error,
      'exit_status': 4,
      'logged_message': 'ycm_core library not detected; you need to compile it '
                        'by running the build.py script. See the documentation '
                        'for more details.'
    }


def CompatibleWithCurrentCore_Python2_test():
  import_exception_messages = [
    # Raised on Linux and OS X with Python 3.3 and 3.4.
    'dynamic module does not define init function (PyInit_ycm_core).',
    # Raised on Linux and OS X with Python 3.5.
    'dynamic module does not define module export function (PyInit_ycm_core).',
    # Raised on Windows.
    'Module use of python26.dll conflicts with this version of Python.',
    'Module use of python27.dll conflicts with this version of Python.'
  ]

  for message in import_exception_messages:
    yield RunCompatibleWithCurrentCoreImportException, {
      'exception_message': message,
      'exit_status': 5,
      'logged_message': 'ycm_core library compiled for Python 2 '
                        'but loaded in Python 3.'
    }


def CompatibleWithCurrentCore_Python3_test():
  import_exception_messages = [
    # Raised on Linux and OS X.
    'dynamic module does not define init function (initycm_core).',
    # Raised on Windows.
    'Module use of python34.dll conflicts with this version of Python.',
    'Module use of python35.dll conflicts with this version of Python.'
  ]

  for message in import_exception_messages:
    yield RunCompatibleWithCurrentCoreImportException, {
      'exception_message': message,
      'exit_status': 6,
      'logged_message': 'ycm_core library compiled for Python 3 '
                        'but loaded in Python 2.'
    }


@patch( 'ycm_core.YcmCoreVersion', side_effect = AttributeError() )
@patch( 'ycmd.server_utils._logger', autospec = True )
def CompatibleWithCurrentCore_Outdated_NoYcmCoreVersionMethod_test( logger,
                                                                    *args ):
  assert_that( CompatibleWithCurrentCore(), equal_to( 7 ) )
  assert_that( logger.method_calls, has_length( 1 ) )
  logger.exception.assert_called_with(
    'ycm_core library too old; PLEASE RECOMPILE by running the build.py '
    'script. See the documentation for more details.' )


@patch( 'ycm_core.YcmCoreVersion', return_value = 10 )
@patch( 'ycmd.server_utils.ExpectedCoreVersion', return_value = 11 )
@patch( 'ycmd.server_utils._logger', autospec = True )
def CompatibleWithCurrentCore_Outdated_NoVersionMatch_test( logger, *args ):
  assert_that( CompatibleWithCurrentCore(), equal_to( 7 ) )
  assert_that( logger.method_calls, has_length( 1 ) )
  logger.error.assert_called_with(
    'ycm_core library too old; PLEASE RECOMPILE by running the build.py '
    'script. See the documentation for more details.' )


def PathToNearestThirdPartyFolder_Success_test():
  ok_( PathToNearestThirdPartyFolder( os.path.abspath( __file__ ) ) )


def PathToNearestThirdPartyFolder_Failure_test():
  ok_( not PathToNearestThirdPartyFolder( os.path.expanduser( '~' ) ) )


def AddNearestThirdPartyFoldersToSysPath_Failure_test():
  assert_that(
    calling( AddNearestThirdPartyFoldersToSysPath ).with_args(
      os.path.expanduser( '~' ) ),
    raises( RuntimeError, '.*third_party folder.*' ) )


@patch( 'sys.path', [
  PathToTestFile( 'python-future', 'some', 'path' ),
  PathToTestFile( 'python-future', 'standard_library' ),
  PathToTestFile( 'python-future', 'standard_library', 'site-packages' ),
  PathToTestFile( 'python-future', 'another', 'path' ) ] )
def AddNearestThirdPartyFoldersToSysPath_FutureAfterStandardLibrary_test(
  *args ):
  AddNearestThirdPartyFoldersToSysPath( __file__ )
  assert_that( sys.path[ : len( THIRD_PARTY_FOLDERS ) ], contains_inanyorder(
    *THIRD_PARTY_FOLDERS
  ) )
  assert_that( sys.path[ len( THIRD_PARTY_FOLDERS ) : ], contains(
    PathToTestFile( 'python-future', 'some', 'path' ),
    PathToTestFile( 'python-future', 'standard_library' ),
    os.path.join( DIR_OF_THIRD_PARTY, 'python-future', 'src' ),
    PathToTestFile( 'python-future', 'standard_library', 'site-packages' ),
    PathToTestFile( 'python-future', 'another', 'path' )
  ) )


@patch( 'sys.path', [
  PathToTestFile( 'python_future', 'some', 'path' ),
  PathToTestFile( 'python_future', 'another', 'path' ) ] )
def AddNearestThirdPartyFoldersToSysPath_ErrorIfNoStandardLibrary_test( *args ):
  assert_that(
    calling( AddNearestThirdPartyFoldersToSysPath ).with_args( __file__ ),
    raises( RuntimeError,
            'Could not find standard library path in Python path.' ) )
