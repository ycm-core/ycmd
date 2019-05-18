# Copyright (C) 2019 Jakub Kaszycki
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

import os.path as p


class ValaUnsupportedError( Exception ):
  pass


def n_dirname( n, f ):
  while n > 0:
    f = p.dirname( f )
    n -= 1
  return f


try:
  import gi
except ImportError as exc:
  raise ValaUnsupportedError( exc )

try:
  gi.require_version( 'GLib', '2.0' )
  gi.require_version( 'GObject', '2.0' )
  gi.require_version( 'GIRepository', '2.0' )
  # The proper version of Vala will be required by Ycmvala require
except ValueError as exc:
  raise ValaUnsupportedError( exc )

try:
  from gi.repository import GLib, GObject, GIRepository
except ImportError as exc:
  raise ValaUnsupportedError( exc )

GIRepository.Repository.prepend_library_path( n_dirname( 4, p.realpath( __file__ ) ) )
GIRepository.Repository.prepend_search_path( n_dirname( 4, p.realpath( __file__ ) ) )

try:
  gi.require_version( 'Ycmvala', '0' )
except ValueError as exc:
  raise ValaUnsupportedError( exc )

try:
  from gi.repository import Ycmvala
except ImportError as exc:
  raise ValaUnsupportedError( exc )
