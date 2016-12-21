# Copyright (C) 2016 ycmd contributors.
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

from future.utils import PY2
from ycmd.utils import ToCppStringCompatible, ToUnicode
import bottle


# Bottle.py is stupid when it comes to bytes vs unicode so we have to carefully
# conform to its stupidity when setting headers.
# Bottle docs state that the response.headers dict-like object stores keys and
# values as bytes on py2 and unicode on py3. What it _actually_ does is store
# keys in this variable state while values are always unicode (on both py2 and
# py3).
# Both the documented and actual behavior are dumb and cause needless problems.
# Bottle should just consistently store unicode objects on both Python versions,
# making life easier for codebases that work across versions, thus preventing
# tracebacks in the depths of WSGI server frameworks.
def SetResponseHeader( name, value ):
  name = ToCppStringCompatible( name ) if PY2 else ToUnicode( name )
  value = ToCppStringCompatible( value ) if PY2 else ToUnicode( value )
  bottle.response.set_header( name, value )
