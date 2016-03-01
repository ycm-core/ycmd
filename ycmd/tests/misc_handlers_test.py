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

from nose.tools import ok_
from .handlers_test import Handlers_test
from ycmd.tests.test_utils import DummyCompleter
from hamcrest import assert_that, contains


class MiscHandlers_test( Handlers_test ):

  def SemanticCompletionAvailable_test( self ):
    with self.PatchCompleter( DummyCompleter, filetype = 'dummy_filetype' ):
      request_data = self._BuildRequest( filetype = 'dummy_filetype' )
      ok_( self._app.post_json( '/semantic_completion_available',
                                request_data ).json )


  def EventNotification_AlwaysJsonResponse_test( self ):
    event_data = self._BuildRequest( contents = 'foo foogoo ba',
                                     event_name = 'FileReadyToParse' )

    self._app.post_json( '/event_notification', event_data ).json


  def FilterAndSortCandidates_Basic_test( self ):
    candidate1 = { 'prop1': 'aoo', 'prop2': 'bar' }
    candidate2 = { 'prop1': 'bfo', 'prop2': 'zoo' }
    candidate3 = { 'prop1': 'cfo', 'prop2': 'moo' }

    data = {
      'candidates': [ candidate3, candidate1, candidate2 ],
      'sort_property': 'prop1',
      'query': 'fo'
    }

    response_data = self._app.post_json(
      '/filter_and_sort_candidates', data ).json

    assert_that( response_data, contains( candidate2, candidate3 ) )
