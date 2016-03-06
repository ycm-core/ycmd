# Copyright (C) 2013 Google Inc.
#               2015 ycmd contributors
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
from future import standard_library
standard_library.install_aliases()
from builtins import *  # noqa

from nose.tools import eq_
from .handlers_test import Handlers_test
from ycmd.tests.test_utils import DummyCompleter
from mock import patch


class Subcommands_test( Handlers_test ):

  @patch( 'ycmd.tests.test_utils.DummyCompleter.GetSubcommandsMap',
          return_value = { 'A': lambda x: x,
                           'B': lambda x: x,
                           'C': lambda x: x } )
  def Basic_test( self, *args ):
    with self.PatchCompleter( DummyCompleter, 'dummy_filetype' ):
      subcommands_data = self._BuildRequest(
          completer_target = 'dummy_filetype' )

      eq_( [ 'A', 'B', 'C' ],
           self._app.post_json( '/defined_subcommands',
                                subcommands_data ).json )


  @patch( 'ycmd.tests.test_utils.DummyCompleter.GetSubcommandsMap',
          return_value = { 'A': lambda x: x,
                           'B': lambda x: x,
                           'C': lambda x: x } )
  def NoExplicitCompleterTargetSpecified_test( self, *args ):
    with self.PatchCompleter( DummyCompleter, 'dummy_filetype' ):
      subcommands_data = self._BuildRequest( filetype = 'dummy_filetype' )

      eq_( [ 'A', 'B', 'C' ],
           self._app.post_json( '/defined_subcommands',
                                subcommands_data ).json )
