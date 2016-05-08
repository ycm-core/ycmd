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
from hamcrest import assert_that, contains

from ycmd.tests import SharedYcmd
from ycmd.tests.test_utils import BuildRequest, DummyCompleter, PatchCompleter


@SharedYcmd
def MiscHandlers_SemanticCompletionAvailable_test( app ):
  with PatchCompleter( DummyCompleter, filetype = 'dummy_filetype' ):
    request_data = BuildRequest( filetype = 'dummy_filetype' )
    ok_( app.post_json( '/semantic_completion_available', request_data ).json )


@SharedYcmd
def MiscHandlers_EventNotification_AlwaysJsonResponse_test( app ):
  event_data = BuildRequest( contents = 'foo foogoo ba',
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data ).json


@SharedYcmd
def MiscHandlers_EventNotification_ReturnJsonOnBigFileError_test( app ):
  # We generate a content greater than Bottle.MEMFILE_MAX, which is set to 1Mb.
  contents = "foo " * 500000
  event_data = BuildRequest( contents = contents,
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data, expect_errors = True ).json


@SharedYcmd
def MiscHandlers_FilterAndSortCandidates_Basic_test( app ):
  candidate1 = { 'prop1': 'aoo', 'prop2': 'bar' }
  candidate2 = { 'prop1': 'bfo', 'prop2': 'zoo' }
  candidate3 = { 'prop1': 'cfo', 'prop2': 'moo' }

  data = {
    'candidates': [ candidate3, candidate1, candidate2 ],
    'sort_property': 'prop1',
    'query': 'fo'
  }

  response_data = app.post_json( '/filter_and_sort_candidates', data ).json

  assert_that( response_data, contains( candidate2, candidate3 ) )
