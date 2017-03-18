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
# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa

from mock import patch
from nose.tools import eq_

from ycmd.tests import SharedYcmd
from ycmd.tests.test_utils import BuildRequest, DummyCompleter, PatchCompleter


@SharedYcmd
@patch( 'ycmd.tests.test_utils.DummyCompleter.GetSubcommandsMap',
        return_value = { 'A': lambda x: x,
                         'B': lambda x: x,
                         'C': lambda x: x } )
def Subcommands_Basic_test( app, *args ):
  with PatchCompleter( DummyCompleter, 'dummy_filetype' ):
    subcommands_data = BuildRequest( completer_target = 'dummy_filetype' )

    eq_( [ 'A', 'B', 'C' ],
         app.post_json( '/defined_subcommands', subcommands_data ).json )


@SharedYcmd
@patch( 'ycmd.tests.test_utils.DummyCompleter.GetSubcommandsMap',
        return_value = { 'A': lambda x: x,
                         'B': lambda x: x,
                         'C': lambda x: x } )
def Subcommands_NoExplicitCompleterTargetSpecified_test( app, *args ):
  with PatchCompleter( DummyCompleter, 'dummy_filetype' ):
    subcommands_data = BuildRequest( filetype = 'dummy_filetype' )

    eq_( [ 'A', 'B', 'C' ],
         app.post_json( '/defined_subcommands', subcommands_data ).json )
