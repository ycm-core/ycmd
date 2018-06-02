# Copyright (C) 2014 Google Inc.
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

import threading

ALREADY_PARSING_MESSAGE = 'File already being parsed.'


# Holds a set of values in a python set. Trying to get an exclusive hold on a
# provided value results in a context manager that manages the lifetime of the
# value.
# For the context manager, trying to enter it if the value is already held by a
# different caller results in a RuntimeError. Otherwise an exclusive hold is
# provided until the context manager is exited.
#
# Example usage:
#    paths = EphemeralValuesSet()
#    ...
#    with path as paths.GetExclusive('/foo'):
#       ...
class EphemeralValuesSet( object ):
  def __init__( self ):
    self._values = set()
    self._values_lock = threading.Lock()

  def GetExclusive( self, value ):
    return EphemeralValue( value, self._values, self._values_lock )


# Implements the Python context manager API.
class EphemeralValue( object ):
  def __init__( self, value, parent_set, parent_lock ):
    self._value = value
    self._parent_set = parent_set
    self._parent_lock = parent_lock

  def __enter__( self ):
    with self._parent_lock:
      if self._value in self._parent_set:
        # This also prevents execution of __exit__
        raise RuntimeError( ALREADY_PARSING_MESSAGE )
      self._parent_set.add( self._value )
    return self._value


  def __exit__( self, *unused_args ):
    with self._parent_lock:
      self._parent_set.remove( self._value )
    return False
