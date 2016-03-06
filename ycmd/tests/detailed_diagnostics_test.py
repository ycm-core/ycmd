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
from future import standard_library
standard_library.install_aliases()
from builtins import *  # noqa

from nose.tools import eq_
from hamcrest import assert_that
from ..responses import NoDiagnosticSupport, BuildDisplayMessageResponse
from .handlers_test import Handlers_test
from .test_utils import DummyCompleter
from mock import patch
import http.client


class Diagnostics_test( Handlers_test ):

  def DoesntWork_test( self ):
    with self.PatchCompleter( DummyCompleter, filetype = 'dummy_filetype' ):
      diag_data = self._BuildRequest( contents = "foo = 5",
                                      line_num = 2,
                                      filetype = 'dummy_filetype' )

      response = self._app.post_json( '/detailed_diagnostic',
                                      diag_data,
                                      expect_errors = True )

      eq_( response.status_code, http.client.INTERNAL_SERVER_ERROR )
      assert_that( response.json, self._ErrorMatcher( NoDiagnosticSupport ) )


  @patch( 'ycmd.tests.test_utils.DummyCompleter.GetDetailedDiagnostic',
          return_value = BuildDisplayMessageResponse( "detailed diagnostic" ) )
  def DoesWork_test( self, *args ):
    with self.PatchCompleter( DummyCompleter, filetype = 'dummy_filetype' ):
      diag_data = self._BuildRequest( contents = "foo = 5",
                                      filetype = 'dummy_filetype' )

      response = self._app.post_json( '/detailed_diagnostic', diag_data )
      assert_that( response.json,
                   self._MessageMatcher( "detailed diagnostic" ) )
