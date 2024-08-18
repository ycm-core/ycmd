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
from ycmd.completers.cs.hook import GetCompleter
from ycmd.completers.cs.cs_completer import PATH_TO_OMNISHARP_ROSLYN_BINARY
from ycmd.tests.cs import setUpModule, tearDownModule # noqa


class GoCompleterTest( TestCase ):
  def test_GetCompleter_OmniSharpFound( self ):
    assert_that( GetCompleter( user_options_store.GetAll() ) )


  @patch( 'ycmd.completers.cs.cs_completer.PATH_TO_OMNISHARP_ROSLYN_BINARY',
          None )
  def test_GetCompleter_OmniSharpNotFound( self, *args ):
    assert_that( not GetCompleter( user_options_store.GetAll() ) )


  @patch( 'ycmd.completers.cs.cs_completer.FindExecutableWithFallback',
          wraps = lambda x, fb: x if x == 'omnisharp' else None )
  @patch( 'os.path.isfile', return_value = False )
  def test_GetCompleter_CustomOmniSharpNotFound( self, *args ):
    user_options = user_options_store.GetAll().copy(
        roslyn_binary_path = 'omnisharp' )
    assert_that( not GetCompleter( user_options ) )


  @patch( 'ycmd.completers.cs.cs_completer.FindExecutableWithFallback',
          wraps = lambda x, fb: x if x == 'omnisharp' else None )
  @patch( 'os.path.isfile', return_value = True )
  def test_GetCompleter_CustomOmniSharpFound_MonoNotRequired( self, *args ):
    user_options = user_options_store.GetAll().copy(
        roslyn_binary_path = 'omnisharp' )
    assert_that( GetCompleter( user_options ) )


  @patch( 'ycmd.completers.cs.cs_completer.FindExecutableWithFallback',
          wraps = lambda x, fb: x if x in ( 'mono',
                                            'omnisharp.exe' ) else None )
  @patch( 'os.path.isfile', return_value = True )
  def test_GetCompleter_CustomOmniSharpFound_MonoRequiredAndFound( self,
                                                                   *args ):
    user_options = user_options_store.GetAll().copy(
        roslyn_binary_path = 'omnisharp.exe',
        mono_binary_path = 'mono' )
    assert_that( GetCompleter( user_options ) )


  @patch( 'ycmd.completers.cs.cs_completer.FindExecutableWithFallback',
          wraps = lambda x, fb: x if x == 'omnisharp.exe' else None )
  @patch( 'os.path.isfile', return_value = True )
  def test_GetCompleter_CustomOmniSharpFound_MonoRequiredAndMissing( self,
                                                                     *args ):
    user_options = user_options_store.GetAll().copy(
        roslyn_binary_path = 'omnisharp.exe' )
    assert_that( not GetCompleter( user_options ) )


  def test_GetCompleter_OmniSharpDefaultOptions( self, *args ):
    completer = GetCompleter( user_options_store.GetAll() )
    assert_that( completer._roslyn_path,
                 equal_to( PATH_TO_OMNISHARP_ROSLYN_BINARY ) )


  @patch( 'ycmd.completers.cs.cs_completer.FindExecutableWithFallback',
          wraps = lambda x, fb: x if x == 'omnisharp' else None )
  @patch( 'os.path.isfile', return_value = True )
  def test_GetCompleter_OmniSharpFromUserOption_NoMonoNeeded( self, *args ):
    user_options = user_options_store.GetAll().copy(
        roslyn_binary_path = 'omnisharp' )
    completer = GetCompleter( user_options )
    assert_that( completer._roslyn_path, equal_to( 'omnisharp' ) )
    assert_that( completer.GetCommandLine()[ 0 ], equal_to( 'omnisharp' ) )


  @patch( 'ycmd.completers.cs.cs_completer.FindExecutableWithFallback',
          wraps = lambda x, fb: x if x in ( 'omnisharp.exe',
                                            'mono' ) else None )
  @patch( 'os.path.isfile', return_value = True )
  def test_GetCompleter_OmniSharpFromUserOption_MonoNeeded( self, *args ):
    user_options = user_options_store.GetAll().copy(
        roslyn_binary_path = 'omnisharp.exe',
        mono_binary_path = 'mono' )
    completer = GetCompleter( user_options )
    assert_that( completer._roslyn_path, equal_to( 'omnisharp.exe' ) )
    assert_that( completer._mono, equal_to( 'mono' ) )
    assert_that( completer.GetCommandLine()[ 0 ], equal_to( 'mono' ) )
