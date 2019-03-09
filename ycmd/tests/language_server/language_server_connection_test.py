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

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa

from mock import patch, MagicMock
from ycmd.completers.language_server import language_server_completer as lsc
from hamcrest import assert_that, calling, equal_to, raises
from ycmd.tests.language_server import MockConnection

import queue


def LanguageServerConnection_ReadPartialMessage_test():
  connection = MockConnection()

  return_values = [
    bytes( b'Content-Length: 10\n\n{"abc":' ),
    bytes( b'""}' ),
    lsc.LanguageServerConnectionStopped
  ]

  with patch.object( connection, 'ReadData', side_effect = return_values ):
    with patch.object( connection, '_DispatchMessage' ) as dispatch_message:
      connection.run()
      dispatch_message.assert_called_with( { 'abc': '' } )


def LanguageServerConnection_MissingHeader_test():
  connection = MockConnection()

  return_values = [
    bytes( b'Content-NOTLENGTH: 10\n\n{"abc":' ),
    bytes( b'""}' ),
    lsc.LanguageServerConnectionStopped
  ]

  with patch.object( connection, 'ReadData', side_effect = return_values ):
    assert_that( calling( connection._ReadMessages ), raises( ValueError ) )


def LanguageServerConnection_RequestAbortCallback_test():
  connection = MockConnection()

  return_values = [
    lsc.LanguageServerConnectionStopped
  ]

  with patch.object( connection, 'ReadData', side_effect = return_values ):
    callback = MagicMock()
    response = connection.GetResponseAsync( 1,
                                            bytes( b'{"test":"test"}' ),
                                            response_callback = callback )
    connection.run()
    callback.assert_called_with( response, None )


def LanguageServerConnection_RequestAbortAwait_test():
  connection = MockConnection()

  return_values = [
    lsc.LanguageServerConnectionStopped
  ]

  with patch.object( connection, 'ReadData', side_effect = return_values ):
    response = connection.GetResponseAsync( 1,
                                            bytes( b'{"test":"test"}' ) )
    connection.run()
    assert_that( calling( response.AwaitResponse ).with_args( 10 ),
                 raises( lsc.ResponseAbortedException ) )


def LanguageServerConnection_ServerConnectionDies_test():
  connection = MockConnection()

  return_values = [
    IOError
  ]

  with patch.object( connection, 'ReadData', side_effect = return_values ):
    # No exception is thrown
    connection.run()


@patch( 'ycmd.completers.language_server.language_server_completer.'
        'CONNECTION_TIMEOUT',
        0.5 )
def LanguageServerConnection_ConnectionTimeout_test():
  connection = MockConnection()
  with patch.object( connection,
                     'TryServerConnectionBlocking',
                     side_effect=RuntimeError ):
    connection.Start()
    assert_that( calling( connection.AwaitServerConnection ),
                 raises( lsc.LanguageServerConnectionTimeout ) )

  assert_that( connection.isAlive(), equal_to( False ) )


def LanguageServerConnection_CloseTwice_test():
  connection = MockConnection()
  with patch.object( connection,
                     'TryServerConnectionBlocking',
                     side_effect=RuntimeError ):
    connection.Close()
    connection.Close()


@patch.object( lsc, 'MAX_QUEUED_MESSAGES', 2 )
def LanguageServerConnection_AddNotificationToQueue_RingBuffer_test():
  connection = MockConnection()
  notifications = connection._notifications

  # Queue empty

  assert_that( calling( notifications.get_nowait ), raises( queue.Empty ) )

  # Queue partially full, then drained

  connection._AddNotificationToQueue( 'one' )

  assert_that( notifications.get_nowait(), equal_to( 'one' ) )
  assert_that( calling( notifications.get_nowait ), raises( queue.Empty ) )

  # Queue full, then drained

  connection._AddNotificationToQueue( 'one' )
  connection._AddNotificationToQueue( 'two' )

  assert_that( notifications.get_nowait(), equal_to( 'one' ) )
  assert_that( notifications.get_nowait(), equal_to( 'two' ) )
  assert_that( calling( notifications.get_nowait ), raises( queue.Empty ) )

  # Queue full, then new notification, then drained

  connection._AddNotificationToQueue( 'one' )
  connection._AddNotificationToQueue( 'two' )
  connection._AddNotificationToQueue( 'three' )

  assert_that( notifications.get_nowait(), equal_to( 'two' ) )
  assert_that( notifications.get_nowait(), equal_to( 'three' ) )
  assert_that( calling( notifications.get_nowait ), raises( queue.Empty ) )


def LanguageServerConnection_RejectUnsupportedRequest_test():
  connection = MockConnection()

  return_values = [
    bytes( b'Content-Length: 26\r\n\r\n{"id":"1","method":"test"}' ),
    lsc.LanguageServerConnectionStopped
  ]

  expected_response = bytes( b'Content-Length: 104\r\n\r\n'
                             b'{"error": {'
                               b'"code": -32601, '
                               b'"reason": "Method not found"'
                             b'}, '
                             b'"id": "1", '
                             b'"jsonrpc": "2.0", '
                             b'"method": "test"}' )

  with patch.object( connection, 'ReadData', side_effect = return_values ):
    with patch.object( connection, 'WriteData' ) as write_data:
      connection.run()
      write_data.assert_called_with( expected_response )
