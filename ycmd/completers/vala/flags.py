# Copyright (C) 2011, 2012 Google Inc.
#               2019 Jakub Kaszycki
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

import os
from ycmd import extra_conf_store
from ycmd.utils import ToUnicode


PATH_LONGFLAGS = [
  '--girdir',
  '--gresources',
  '--gresourcesdir',
  '--metadatadir',
  '--vapidir'
]

EMPTY_FLAGS = {
  'flags': [],
}


class NoCompilationDatabase( Exception ):
  pass


class Flags( object ):
  """Keeps track of the flags necessary to compile a file.
  The flags are loaded from user-created python files (hereafter referred to as
  'modules') that contain a method FlagsForFile( filename )."""

  def __init__( self ):
    # It's caches all the way down...
    self.flags_for_file = {}
    self.no_extra_conf_file_warning_posted = False


  def FlagsForFile( self,
                    filename,
                    client_data = None ):

    try:
      return self.flags_for_file[ filename ]
    except KeyError:
      pass

    module = extra_conf_store.ModuleForSourceFile( filename )
    results = self._GetFlagsFromExtraConf( module,
                                           filename,
                                           client_data )

    if not results:
      return []
    if not results.get( 'flags_ready', True ):
      return None

    flags = self._ExtractFlagsList( results )
    if not flags:
      return []

    if results.get( 'do_cache', True ):
      self.flags_for_file[ filename ] = flags
    return flags


  def _GetFlagsFromExtraConf( self, module, filename, client_data ):
    if module is None:
      return {
        'flags': []
      }

    results = module.Settings( language = 'vala',
                               filename = filename,
                               client_data = client_data )

    results[ 'flags' ] = self._MakeRelativePathsInFlagsAbsolute(
        results.get( 'flags', [] ),
        results.get( 'include_paths_relative_to_dir' ) )

    return results


  def Clear( self ):
    self.flags_for_file.clear()


  def _MakeRelativePathsInFlagsAbsolute( self, flags, working_directory ):
    if not working_directory:
      return flags
    new_flags = []
    make_next_absolute = False
    for flag in flags:
      new_flag = flag

      if make_next_absolute:
        make_next_absolute = False
        if not os.path.isabs( new_flag ):
          new_flag = os.path.join( working_directory, flag )
        new_flag = os.path.normpath( new_flag )
      else:
        for path_flag in PATH_LONGFLAGS:
          # Single dash argument alone, e.g. --vapidir /usr/share/vala/vapi
          if flag == path_flag:
            make_next_absolute = True
            break

          # Joined argument without path, e.g. --vapidir=

          if flag == path_flag + '=':
            raise ValueError( 'bad flag: ' + flag )

          # Joined argument, e.g. --vapidir=/usr/share/vala/vapi
          if flag.startswith( path_flag + '=' ):
            new_flag = self._MakeRelativeFlag( flag,
                                               working_directory,
                                               path_flag )
            break

      if new_flag:
        new_flags.append( new_flag )
    return new_flags


  def _MakeRelativeFlag( self, flag, working_directory, path_flag ):
    path = flag[ len( path_flag ) + 1: ]
    if not os.path.isabs( path ):
      path = os.path.join( working_directory, path )
    path = os.path.normpath( path )

    return '{0}={1}'.format( path_flag, path )

  def _ExtractFlagsList( self, flags_for_file_output ):
    if 'flags' in flags_for_file_output:
      return [ ToUnicode( x ) for x in flags_for_file_output[ 'flags' ] ]
    else:
      return []
