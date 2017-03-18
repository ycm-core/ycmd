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

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa

from hamcrest import assert_that
from mock import patch
from nose.tools import eq_
import requests

from ycmd.responses import NoDiagnosticSupport, BuildDisplayMessageResponse
from ycmd.tests import SharedYcmd
from ycmd.tests.test_utils import ( BuildRequest, DummyCompleter, ErrorMatcher,
                                    MessageMatcher, PatchCompleter )


@SharedYcmd
def Diagnostics_DoesntWork_test( app ):
  with PatchCompleter( DummyCompleter, filetype = 'dummy_filetype' ):
    diag_data = BuildRequest( contents = "foo = 5",
                              line_num = 2,
                              filetype = 'dummy_filetype' )

    response = app.post_json( '/detailed_diagnostic',
                              diag_data,
                              expect_errors = True )

    eq_( response.status_code, requests.codes.internal_server_error )
    assert_that( response.json, ErrorMatcher( NoDiagnosticSupport ) )


@SharedYcmd
@patch( 'ycmd.tests.test_utils.DummyCompleter.GetDetailedDiagnostic',
        return_value = BuildDisplayMessageResponse( 'detailed diagnostic' ) )
def Diagnostics_DoesWork_test( app, *args ):
  with PatchCompleter( DummyCompleter, filetype = 'dummy_filetype' ):
    diag_data = BuildRequest( contents = 'foo = 5',
                              filetype = 'dummy_filetype' )

    response = app.post_json( '/detailed_diagnostic', diag_data )
    assert_that( response.json, MessageMatcher( 'detailed diagnostic' ) )
