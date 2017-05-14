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


# FIXME: Use the YCMD version of this
def PathsToAllParentFolders( path ):
  folder = os.path.normpath( path )
  if os.path.isdir( folder ):
    yield folder
  while True:
    parent = os.path.dirname( folder )
    if parent == folder:
      break
    folder = parent
    yield folder


class CompilationDatabase( object ):
  def __init__( self ):
    self._raw_value = []
    self._db_hash = 0

  def Load( self, db_file_name ):
    json_db = open( db_file_name )
    self._raw_value = json.load( json_db )
    self._db_hash =  CompilationDatabaseHash( db_file_name )

  def _RawCommandForFile( self, compileable_file ):
    for entry in self._raw_value:
      if entry[ 'file' ] == compileable_file:
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

  def _SetFlags( self, flags, compileable_file ):
    with self._flag_lock:
      self._flags_for_file[ compileable_file ] = flags

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
    return None

  def _RawCommandForFile( self, compileable_file ):
    db = self._FindDBForFile( compileable_file )
    if not db:
      return None
    with self._db_lock:
      return db._RawCommandForFile( compileable_file )

  # Return Completion flags for a file
  def FlagsForFile( self, compileable_file ):
    # TODO: based on swifts compilation model, we may need to invalidate
    # these when the DB cache expires: when a user enters symbols that exist
    # in another file the previous flags are invalided. Unlike clang
    # directory includes, we need to put all dependent *files* as part of the
    # 'primary-file'.

    with self._flag_lock:
      cached_flags = self._flags_for_file.get( compileable_file )
      if cached_flags:
        return cached_flags

    command = self._RawCommandForFile( compileable_file )
    # The system will work without any flags specified by the client
    if not command:
      return []
    split = shlex.split( command )
    filtered = FlagsForCommandList( split )
    final_flags = filtered
    self._SetFlags( final_flags, compileable_file )
    return final_flags


# Command Preparation Logic

# Basic flag blacklist is a list of flags where
# that cannot be included in a ComplierInvocation for
# completion.
#
# These flags are specified as pair of the form
# __FLAG__ Value
BASIC_FLAG_BLACKLIST = set( [ '-o',
                              '-MP',
                              '-MD',
                              '-MMD',
                              '--fcolor-diagnostics',
                              '-Xcc',
                              '-emit-reference-dependencies-path',
                              '-emit-dependencies-path',
                              '-emit-module-path',
                              '-serialize-diagnostics-path',
                              '-emit-module-doc-path',
                              ] )

FLAG_START_TOKEN = '-'


# Take a raw split command and output completion flags
def FlagsForCommandList( split_cmd ):
  flags = []

  # Skip the first 3 flags
  # ( which is compiler, -frontend, -c )
  i = 3
  flags_len = len( split_cmd )
  while i < flags_len:
    flag = split_cmd[ i ]
    # Primary file includes the deps in a given file
    # Special case it: it is specified as -primary-file [FILES]
    if flag == '-primary-file':
      flags.append( flag )
      while i < flags_len - 1:
        i = i + 1
        flag = split_cmd[ i ]
        # Collect until we hit another flag
        if flag[ 0 ] == FLAG_START_TOKEN:
          break
        flags.append( flag )

    if flag in BASIC_FLAG_BLACKLIST:
      # Skip the pair (FLAG, VALUE)
      i = i + 1
    else:
      flags.append( flag )
    i = i + 1
  return flags


# TODO: Enable these tests on the CI
# there is some work to get the paths resolving correctly
# since the search algorithm hits the FS
def BasicExampleNamed( file_name ):
  example_dir = '/Users/jerrymarino/swiftyswiftvim/'
  + 'Examples/Basic/Basic/'
  return example_dir + file_name


def test_primary_basic_flags():
  testf = BasicExampleNamed( 'AppDelegate.swift' )
  cmds = Flags().FlagsForFile( testf )
  assert cmds[0] == '-primary-file'
  assert cmds[1] == testf


def test_primary_dependency_flags():
  testf = BasicExampleNamed( 'ViewController.swift' )
  cmds = Flags().FlagsForFile( testf )
  assert cmds[0] == '-primary-file'
  assert cmds[1] == testf
  # This file is a 'primary-file' of ViewController
  assert cmds[2] == BasicExampleNamed( 'AppDelegate.swift' )


def test_primary_dependency_flags_caching():
  depf = BasicExampleNamed( 'AppDelegate.swift' )
  testf = BasicExampleNamed( 'ViewController.swift' )
  flags = Flags()
  cmds = flags.FlagsForFile( testf )
  cmds = flags.FlagsForFile( depf )
  assert cmds[0] == '-primary-file'
  assert cmds[1] == testf
  assert cmds[2] == depf
