#!/usr/bin/env python
#
# Copyright (C) 2013  Google Inc.
#
# This file is part of YouCompleteMe.
#
# YouCompleteMe is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# YouCompleteMe is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with YouCompleteMe.  If not, see <http://www.gnu.org/licenses/>.

from ..server_utils import SetUpPythonPath
SetUpPythonPath()
from webtest import TestApp
from .. import handlers
from nose.tools import ok_, with_setup
from .test_utils import Setup, BuildRequest
import bottle

bottle.debug( True )


@with_setup( Setup )
def SemanticCompletionAvailable_Works_test():
  app = TestApp( handlers.app )
  request_data = BuildRequest( filetype = 'python' )
  ok_( app.post_json( '/semantic_completion_available',
                      request_data ).json )


@with_setup( Setup )
def EventNotification_AlwaysJsonResponse_test():
  app = TestApp( handlers.app )
  event_data = BuildRequest( contents = 'foo foogoo ba',
                             event_name = 'FileReadyToParse' )

  app.post_json( '/event_notification', event_data ).json
