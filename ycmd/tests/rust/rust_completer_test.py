# Copyright (C) 2021 ycmd contributors
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

import os
from unittest.mock import patch
from hamcrest import assert_that, equal_to
from unittest import TestCase

from ycmd import user_options_store
from ycmd.completers.rust.hook import GetCompleter
from ycmd.tests.rust import setUpModule, tearDownModule # noqa


class RustCompleterTest( TestCase ):
  def test_GetCompleter_RAFound( self ):
    assert_that( GetCompleter( user_options_store.GetAll() ) )


  @patch( 'ycmd.completers.rust.rust_completer.RA_EXECUTABLE', None )
  def test_GetCompleter_RANotFound( self, *args ):
    assert_that( not GetCompleter( user_options_store.GetAll() ) )


  @patch( 'ycmd.utils.FindExecutable',
          wraps = lambda x: x if 'rust-analyzer' in x else None )
  @patch( 'os.access', return_value = True )
  def test_GetCompleter_RAFromUserOption( self, *args ):
    user_options = user_options_store.GetAll().copy(
            rust_toolchain_root = 'rust-analyzer' )
    assert_that( GetCompleter( user_options )._rust_root,
                 equal_to( 'rust-analyzer' ) )
    expected = os.path.join( 'rust-analyzer', 'bin', 'rust-analyzer' )
    assert_that( GetCompleter( user_options )._ra_path,
                 equal_to( expected ) )


  def test_GetCompleter_InvalidRustRootFromUser( self, *args ):
    user_options = user_options_store.GetAll().copy(
            rust_toolchain_root = '/does/not/exist' )
    assert_that( not GetCompleter( user_options ) )


  @patch( 'ycmd.completers.rust.rust_completer.LOGGER', autospec = True )
  def test_GetCompleter_WarnsAboutOldConfig( self, logger ):
    user_options = user_options_store.GetAll().copy(
            rls_binary_path = '/does/not/exist' )
    GetCompleter( user_options )
    logger.warning.assert_called_with(
        'rls_binary_path detected. Did you mean rust_toolchain_root?' )
