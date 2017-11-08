# Copyright (C) 2017 Davit Samvelyan davitsamvelyan@gmail.com
#                    Synopsys.
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

from future.utils import iteritems

import os

from collections import defaultdict
from ycmd import responses

EXTRA_INFO_MAP = { 1 : '[File]', 2 : '[Dir]', 3 : '[File&Dir]' }


class IncludeEntry( object ):

  def __init__( self, name, entry_type ):
    self.name = name
    self.entry_type = entry_type


class IncludeList( object ):

  def __init__( self ):
    self._includes = defaultdict( int )


  def AddIncludes( self, includes ):
    for include in includes:
      self._includes[ include.name ] |= include.entry_type


  def GetIncludes( self ):
    includes = []
    for name, include_type in iteritems( self._includes ):
      includes.append( responses.BuildCompletionData(
        name, EXTRA_INFO_MAP[ include_type ] ) )
    return includes


class IncludeCache( object ):

  def __init__( self ):
    self._cache = {}


  def GetIncludes( self, path, cache ):
    includes = None
    if cache:
      includes = self._cache.get( path )

    if includes is None:
      includes = self._GetIncludes( path )
      if cache:
        self._cache[ path ] = includes
    return includes


  def _GetIncludes( self, path ):
    try:
      names = os.listdir( path )
    except Exception:
      names = []

    includes = []
    for name in names:
      inc_path = os.path.join(path, name)
      entry_type = 2 if os.path.isdir( inc_path ) else 1
      includes.append( IncludeEntry( name, entry_type ) )

    return includes
