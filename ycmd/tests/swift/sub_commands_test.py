# Copyright (C) 2017 ycmd contributors
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

from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa

from hamcrest import assert_that, equal_to

from ycmd.tests.swift import SharedYcmd
from ycmd.tests.test_utils import BuildRequest
from os import system


def _KillServer( app ):
  completion_data = BuildRequest( filetype = 'swift' )
  debug_info = app.post_json( '/debug_info', completion_data ).json
  server_info = debug_info[ 'completer' ][ 'servers' ][ 0 ]
  pid = server_info[ 'pid' ]
  system( 'kill -9 ' + str( pid ) )


@SharedYcmd
def Shutdown_test( app ):
  completion_data = BuildRequest( filetype = 'swift' )

  response = app.post_json( '/shutdown',
                           completion_data )

  # Expect a 200. If we've made a shutdown request, rely on the server to shut
  # it's self off. The completer will rasie an exception after 5 seconds
  # otherwise.
  assert_that( response.status_code, equal_to( 200 ) )

  # Don't wait for the process to exit.
  _KillServer( app )

  # Make sure that shutdown will work.
  is_healty = app.get( '/healthy',
                       { 'subserver' : 'swift' } ).json
  assert_that( is_healty, equal_to( False ) )


@SharedYcmd
def UnHealthy_test( app ):
  # Kill the process. We should be not returning true if the server
  # fails goes down for external reasons
  _KillServer( app )

  is_healty = app.get( '/healthy',
                       { 'subserver' : 'swift' } ).json
  assert_that( is_healty, equal_to( False ) )
