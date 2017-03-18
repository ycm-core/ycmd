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

from future.utils import listvalues
from waitress.server import TcpWSGIServer
import select


class StoppableWSGIServer( TcpWSGIServer ):
  """StoppableWSGIServer is a subclass of the TcpWSGIServer Waitress server
  with a shutdown method. It is based on StopableWSGIServer class from webtest:
  https://github.com/Pylons/webtest/blob/master/webtest/http.py"""

  shutdown_requested = False

  def Run( self ):
    """Wrapper of TcpWSGIServer run method. It prevents a traceback from
    asyncore."""

    # Message for compatibility with clients who expect the output from
    # waitress.serve here
    print( 'serving on http://{0}:{1}'.format(
      self.effective_host,
      self.effective_port ) )

    try:
      self.run()
    except select.error:
      if not self.shutdown_requested:
        raise


  def Shutdown( self ):
    """Properly shutdown the server."""
    self.shutdown_requested = True
    # Shutdown waitress threads.
    self.task_dispatcher.shutdown()
    # Close asyncore channels.
    # We don't use itervalues here because _map is modified while looping
    # through it.
    # NOTE: _map is an attribute from the asyncore.dispatcher class, which is a
    # base class of TcpWSGIServer. This may change in future versions of
    # waitress so extra care should be taken when updating waitress.
    for channel in listvalues( self._map ):
      channel.close()
