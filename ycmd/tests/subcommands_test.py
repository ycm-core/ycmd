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

from hamcrest import assert_that, contains_exactly
from unittest.mock import patch
from unittest import TestCase

from ycmd.tests import SharedYcmd
from ycmd.tests.test_utils import BuildRequest, DummyCompleter, PatchCompleter


class SubcommandsTest( TestCase ):
  @SharedYcmd
  @patch( 'ycmd.tests.test_utils.DummyCompleter.GetSubcommandsMap',
          return_value = { 'A': lambda x: x,
                           'B': lambda x: x,
                           'C': lambda x: x } )
  def test_Subcommands_Basic( self, app, *args ):
    with PatchCompleter( DummyCompleter, 'dummy_filetype' ):
      subcommands_data = BuildRequest( completer_target = 'dummy_filetype' )
      assert_that( app.post_json( '/defined_subcommands',
                                  subcommands_data ).json,
                   contains_exactly( 'A', 'B', 'C' ) )


  @SharedYcmd
  @patch( 'ycmd.tests.test_utils.DummyCompleter.GetSubcommandsMap',
          return_value = { 'A': lambda x: x,
                           'B': lambda x: x,
                           'C': lambda x: x } )
  def test_Subcommands_NoExplicitCompleterTargetSpecified( self, app, *args ):
    with PatchCompleter( DummyCompleter, 'dummy_filetype' ):
      subcommands_data = BuildRequest( filetype = 'dummy_filetype' )
      assert_that( app.post_json( '/defined_subcommands',
                                  subcommands_data ).json,
                   contains_exactly( 'A', 'B', 'C' ) )
