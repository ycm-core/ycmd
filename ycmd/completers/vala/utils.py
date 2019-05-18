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


has_support = None
vala_version = None


def Check():
  global has_support
  global vala_version
  try:
    from ycmd.completers.vala.native import Ycmvala
    has_support = True
    vala_version = Ycmvala.vala_version()
  except Exception as exc:
    # We can't import ValaUnsupportedError, so we need to check type string
    if 'ValaUnsupportedError' in str( type( exc ) ):
      has_support = False
      vala_version = None
    else:
      raise exc


def HasValaSupport():
  global has_support
  if has_support is None:
    Check()
  return has_support


def ValaVersion():
  global has_support
  global vala_version
  if has_support is None:
    Check()
  return vala_version
