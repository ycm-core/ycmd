# Copyright (C) 2017-2021 ycmd contributors
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
from ycmd.completers.typescript.typescript_completer import (
    ShouldEnableTypeScriptCompleter,
    FindTSServer )
from ycmd.tests.typescript import setUpModule, tearDownModule # noqa


class TypescriptCompleterTest( TestCase ):
  def test_ShouldEnableTypeScriptCompleter_NodeAndTsserverFound( self ):
    user_options = user_options_store.GetAll()
    assert_that( ShouldEnableTypeScriptCompleter( user_options ) )


  @patch( 'ycmd.utils.FindExecutable', return_value = None )
  def test_ShouldEnableTypeScriptCompleter_TsserverNotFound( self, *args ):
    user_options = user_options_store.GetAll()
    assert_that( not ShouldEnableTypeScriptCompleter( user_options ) )


  @patch( 'ycmd.utils.FindExecutableWithFallback',
          wraps = lambda x, fb: x if x == 'tsserver' else None )
  @patch( 'os.path.isfile', return_value = True )
  def test_FindTSServer_CustomTsserverPath( self, *args ):
    assert_that( 'tsserver', equal_to( FindTSServer( 'tsserver' ) ) )
