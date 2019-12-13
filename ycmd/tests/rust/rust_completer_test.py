# Copyright (C) 2020 ycmd contributors
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
from hamcrest import assert_that, equal_to

from ycmd import user_options_store
from ycmd.completers.rust.hook import GetCompleter


def GetCompleter_RlsFound_test():
  assert_that( GetCompleter( user_options_store.GetAll() ) )


@patch( 'ycmd.completers.rust.rust_completer.RLS_EXECUTABLE', None )
def GetCompleter_RlsNotFound_test( *args ):
  assert_that( not GetCompleter( user_options_store.GetAll() ) )


@patch( 'ycmd.utils.FindExecutableWithFallback',
        wraps = lambda x, fb: x if x == 'rls' or x == 'rustc' else fb )
@patch( 'os.path.isfile', return_value = True )
def GetCompleter_RlsFromUserOption_test( *args ):
  user_options = user_options_store.GetAll().copy( rls_binary_path = 'rls' )
  user_options = user_options.copy( rustc_binary_path = 'rustc' )
  assert_that( GetCompleter( user_options )._rls_path, equal_to( 'rls' ) )
  assert_that( GetCompleter( user_options )._rustc_path, equal_to( 'rustc' ) )


@patch( 'ycmd.completers.rust.rust_completer.RLS_EXECUTABLE', None )
def GetCompleter_RustcNotDefine_test( *args ):
  user_options = user_options_store.GetAll().copy( rls_binary_path = 'rls' )
  assert_that( not GetCompleter( user_options ) )
