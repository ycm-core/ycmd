# Copyright (C) 2013 Google Inc.
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

import json
import os
from frozendict import frozendict

from ycmd.utils import ReadFile

_USER_OPTIONS = {}


def SetAll( new_options ):
  global _USER_OPTIONS
  _USER_OPTIONS = frozendict( new_options )


def GetAll():
  return _USER_OPTIONS


def Value( key ):
  return _USER_OPTIONS[ key ]


def DefaultOptions():
  settings_path = os.path.join(
      os.path.dirname( os.path.abspath( __file__ ) ), 'default_settings.json' )
  options = json.loads( ReadFile( settings_path ) )
  options.pop( 'hmac_secret', None )
  return options
