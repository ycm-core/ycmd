# Copyright (C) 2017 Davit Samvelyan davitsamvelyan@gmail.com
#                    Synopsys.
#               2018 ycmd contributors
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
import threading

from collections import defaultdict, namedtuple
from ycmd import responses
from ycmd.completers.general.filename_completer import ( GetPathType,
                                                         GetPathTypeName )
from ycmd.utils import GetModificationTime, ListDirectory


""" Represents single include completion candidate.
name is the name/string of the completion candidate,
entry_type is an integer indicating whether the candidate is a
'File', 'Dir' or both (See EXTRA_INFO_MAP in filename_completer). """
IncludeEntry = namedtuple( 'IncludeEntry', [ 'name', 'entry_type' ] )


class IncludeList( object ):
  """
  Helper class for combining include completion candidates from
  several include paths.
  self._includes is a dictionary whose keys are
  IncludeEntry `name`s and values are IncludeEntry `entry_type`s.
  """

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
  """
  Holds a dictionary representing the include path cache.
  Dictionary keys are the include path directories.
  Dictionary values are tuples whose first object
  represents `mtime` of the dictionary key and the other
  object is an IncludeList.
  """

  def __init__( self ):
    self._cache = {}
    self._cache_lock = threading.Lock()


  def GetIncludes( self, path, is_framework = False ):
    includes = self._GetCached( path, is_framework )

    if includes is None:
      includes = self._ListIncludes( path, is_framework )
      self._AddToCache( path, includes )

    return includes


  def _AddToCache( self, path, includes, mtime = None ):
    if not mtime:
      mtime = GetModificationTime( path )
    # mtime of 0 is "a magic value" to represent inaccessible directory mtime.
    if mtime:
      with self._cache_lock:
        self._cache[ path ] = { 'mtime': mtime, 'includes': includes }


  def _GetCached( self, path, is_framework ):
    includes = None
    with self._cache_lock:
      cache_entry = self._cache.get( path )
    if cache_entry:
      mtime = GetModificationTime( path )
      if mtime > cache_entry[ 'mtime' ]:
        includes = self._ListIncludes( path, is_framework )
        self._AddToCache( path, includes, mtime )
      else:
        includes = cache_entry[ 'includes' ]

    return includes


  def _ListIncludes( self, path, is_framework ):
    includes = []
    for name in ListDirectory( path ):
      if is_framework:
        if not name.endswith( '.framework' ):
          continue
        name = name[ : -len( '.framework' ) ]

      inc_path = os.path.join( path, name )
      entry_type = GetPathType( inc_path, is_framework )
      includes.append( IncludeEntry( name, entry_type ) )

    return includes
