#!/usr/bin/env python
#
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

from nose.tools import ok_
from .handlers_test import Handlers_test


class MiscHandlers_test( Handlers_test ):

  def SemanticCompletionAvailable_test( self ):
    request_data = self._BuildRequest( filetype = 'python' )
    ok_( self._app.post_json( '/semantic_completion_available',
                              request_data ).json )


  def EventNotification_AlwaysJsonResponse_test( self ):
    event_data = self._BuildRequest( contents = 'foo foogoo ba',
                                     event_name = 'FileReadyToParse' )

    self._app.post_json( '/event_notification', event_data ).json
