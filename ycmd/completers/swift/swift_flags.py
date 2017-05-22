# Copyright (C) 2017 Jerry Marino <i@jerrymarino.com>
#               2017      ycmd contributors
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
import shlex
import os
import threading
import logging
from ycmd.utils import PathsToAllParentFolders


class CompilationDatabase( object ):
  def __init__( self ):
    self._raw_value = []
    self._db_hash = 0

  def Load( self, db_file_name ):
    with open( db_file_name ) as json_db:
      self._raw_value = json.load( json_db )
      logging.debug("Loaded JSON Raw Value: " + str(self._raw_value))
    self._db_hash =  CompilationDatabaseHash( db_file_name )

  def _RawCommandForFile( self, compilable_file ):
    logging.debug("Raw Command For File: " + compilable_file)
    for entry in self._raw_value:
      if entry[ 'file' ] == compilable_file:
        return entry[ 'command' ]
    return None

  def DBHash( self ):
    return self._db_hash


# Do a quick hash of the DB.
# We don't hash based on content to save reading in the file.
def CompilationDatabaseHash( path ):
  return os.path.getmtime(path)


# Flags wraps compilation databases and prepares flags for completion requests
# to a semantic server.
#
# Flags are based on the compilation command: a user can prepare these based on
# the output from build systems.
class Flags( object ):
  def __init__( self ):
    self._flag_lock = threading.RLock()
    self._db_lock = threading.RLock()
    self._flags_for_file = {}
    self._dbs_by_folder = {}

  def _SetFlags( self, flags, compilable_file ):
    with self._flag_lock:
      self._flags_for_file[ compilable_file ] = flags

  # Find the best DB for a file
  # Start by looking in the files folder, and loop up
  # the directory tree.
  # This is based on the CPP flag finding approach
  def _FindDBForFile( self, path ):
    file_dir = os.path.dirname( path )
    for folder in PathsToAllParentFolders( file_dir ):
      # Note: this name is not part of the standard, but CMake outputs the DB
      # and calls it this. Consider using other known filenames once they exist
      # for swift.
      db_file_name = 'compile_commands.json'
      absolute_db_path = folder + '/' + db_file_name
      if not os.path.isfile( absolute_db_path ):
        continue

      with self._db_lock:
        cached_db = self._dbs_by_folder.get( folder )
        # If there is a cached DB, and it's is still up to date then use it
        incoming_hash = CompilationDatabaseHash( absolute_db_path )
        if cached_db and incoming_hash == cached_db.DBHash():
          # DB CacheHit
          return cached_db

      db = CompilationDatabase()
      db.Load( absolute_db_path )
      with self._db_lock:
        self._dbs_by_folder[ folder ] = db
        return db
    logging.debug("No DB For File: " + path)
    return None

  def _RawCommandForFile( self, compilable_file ):
    db = self._FindDBForFile( compilable_file )
    if not db:
      return None
    with self._db_lock:
      return db._RawCommandForFile( compilable_file )

  # Return Completion flags for a file
  def FlagsForFile( self, compilable_file ):
    if not compilable_file:
      raise AssertionError('Missing a compilable file')
    # TODO: based on swifts compilation model, we may need to invalidate
    # these when the DB cache expires: when a user enters symbols that exist
    # in another file, the previous flags are invalided. Unlike clang
    # directory includes, we need to put all dependent *files* as part of the
    # 'primary-file'.

    with self._flag_lock:
      cached_flags = self._flags_for_file.get( compilable_file )
      if cached_flags:
        logging.debug("Cached Flags: " + str(cached_flags))
        return cached_flags
    command = self._RawCommandForFile( compilable_file )
    logging.debug("Raw Command: " + str(command))
    # The system will work without any flags specified by the client
    if not command:
      return []
    split = shlex.split( command )
    filtered = FlagsForCommandList( split )
    final_flags = filtered
    self._SetFlags( final_flags, compilable_file )
    return final_flags


# Command Preparation Logic

# Basic flag blacklist is a list of flags that cannot be included in a
# CompilerInvocation for completion.
#
# These flags are a pair in the form
# __FLAG__ Optional(__VALUE__)
#
# For example -c sometimes has a value after it.
#
# Only skip __VALUE__ when it doesn't start with -.

BASIC_FLAG_BLACKLIST = set( [
                              '-c',
                              '-MP',
                              '-MD',
                              '-MMD',
                              '--fcolor-diagnostics',
                              '-emit-reference-dependencies-path',
                              '-emit-dependencies-path',
                              '-emit-module-path',
                              '-serialize-diagnostics-path',
                              '-emit-module-doc-path',
                              '-frontend',
                              '-o',
                            ] )

# These flags may specified as pair of the form
# __FLAG__ __VALUE__
#
# Unconditionally exclude flags in this blacklist and the next value

PAIRED_FLAG_BLACKLIST = set( [ '-Xcc' ] )

FLAG_START_TOKEN = '-'


# Take a raw split command and output completion flags
def FlagsForCommandList( split_cmd ):
  flags = []

  # Skip the first flag.
  # This is the compiler being used.
  i = 1
  flags_len = len( split_cmd )
  while i < flags_len:
    flag = split_cmd[ i ]
    if flag in PAIRED_FLAG_BLACKLIST:
      i = i + 1

    elif flag in BASIC_FLAG_BLACKLIST:
      # Skip the flag
      next_idx = i + 1

      # Skip the pair (FLAG, VALUE) when the next value isn't
      # another flag.
      if next_idx < flags_len:
        if split_cmd[ next_idx ][ 0 ] != FLAG_START_TOKEN:
          i = i + 1

    else:
      flags.append( flag )
    i = i + 1
  return flags
