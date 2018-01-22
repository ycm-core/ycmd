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
from ycmd.completers.general.filename_completer import ( GetPathType,
                                                         GetPathTypeName )


class IncludeEntry( object ):
  """ Represents single include completion candidate.
  name is the name/string of the completion candidate,
  entry_type is an integer indicating whether the candidate is a
  'File', 'Dir' or both (See EXTRA_INFO_MAP in filename_completer). """

  def __init__( self, name, entry_type ):
    self.name = name
    self.entry_type = entry_type


class IncludeList( object ):
  """ Helper class fo combining include completion candidates from
  several include paths. """

  def __init__( self ):
    self._includes = defaultdict( int )


  def AddIncludes( self, includes ):
    for include in includes:
      self._includes[ include.name ] |= include.entry_type


  def GetIncludes( self ):
    includes = []
    for name, include_type in iteritems( self._includes ):
      includes.append( responses.BuildCompletionData(
        name, GetPathTypeName( include_type ) ) )
    return includes


class IncludeCache( object ):

  def __init__( self ):
    self._cache = {}


  def Clear( self ):
    self._cache = {}


  def GetIncludes( self, path, cache ):
    includes = None
    if cache:
      includes = self._GetCached( path )

    if includes is None:
      includes = self._ListIncludes( path )
      if cache:
        self._AddToCache( path, includes )

    return includes


  def _AddToCache( self, path, includes ):
    mtime = _GetModificationTime( path )
    self._cache[ path ] = ( mtime, includes )


  def _GetCached( self, path ):
    includes = None
    cache_entry = self._cache.get( path )
    if cache_entry:
      mtime = _GetModificationTime( path )
      if mtime > cache_entry[ 0 ]:
        del self._cache[ path ]
      else:
        includes = cache_entry[ 1 ]

    return includes


  def _ListIncludes( self, path ):
    try:
      names = os.listdir( path )
    except Exception:
      return []

    includes = []
    for name in names:
      inc_path = os.path.join(path, name)
      try:
        entry_type = GetPathType( inc_path )
        includes.append( IncludeEntry( name, entry_type ) )
      except Exception:
        pass

    return includes


def _GetModificationTime( path ):
  try:
    return os.path.getmtime( path )
  except Exception:
    return 0
