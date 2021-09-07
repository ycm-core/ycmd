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

from unittest.mock import patch
from unittest import TestCase
from hamcrest import assert_that, equal_to

from ycmd import user_options_store
from ycmd.completers.go.hook import GetCompleter
from ycmd.tests.go import setUpModule, tearDownModule # noqa


class GoCompleterTest( TestCase ):
  def test_GetCompleter_GoplsFound( self ):
    assert_that( GetCompleter( user_options_store.GetAll() ) )


  @patch( 'ycmd.completers.go.go_completer.PATH_TO_GOPLS', None )
  def test_GetCompleter_GoplsNotFound( self, *args ):
    assert_that( not GetCompleter( user_options_store.GetAll() ) )


  @patch( 'ycmd.utils.FindExecutableWithFallback',
          wraps = lambda x, fb: x if x == 'gopls' else None )
  @patch( 'os.path.isfile', return_value = True )
  def test_GetCompleter_GoplsFromUserOption( self, *args ):
    user_options = user_options_store.GetAll().copy(
        gopls_binary_path = 'gopls' )
    assert_that( GetCompleter( user_options )._gopls_path, equal_to( 'gopls' ) )
