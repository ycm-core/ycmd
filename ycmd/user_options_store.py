# Copyright (C) 2020 ycmd contributors
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

import json
import os

from ycmd.utils import HashableDict, ReadFile

_USER_OPTIONS = {}


def SetAll( new_options ):
  global _USER_OPTIONS
  _USER_OPTIONS = HashableDict( new_options )


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
