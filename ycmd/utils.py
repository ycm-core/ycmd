# Copyright (C) 2011-2020 ycmd contributors
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

import copy
import json
import logging
import os
import socket
import subprocess
import sys
import tempfile
import time
import threading

LOGGER = logging.getLogger( 'ycmd' )
ROOT_DIR = os.path.normpath( os.path.join( os.path.dirname( __file__ ), '..' ) )
DIR_OF_THIRD_PARTY = os.path.join( ROOT_DIR, 'third_party' )
LIBCLANG_DIR = os.path.join( DIR_OF_THIRD_PARTY, 'clang', 'lib' )
if hasattr( os, 'add_dll_directory' ):
  os.add_dll_directory( LIBCLANG_DIR )


from collections.abc import Mapping
from urllib.parse import urljoin, urlparse, unquote, quote  # noqa
from urllib.request import pathname2url, url2pathname  # noqa


# We replace the re module with regex as it has better support for characters
# on multiple code points. However, this module has a compiled component so we
# can't import it in YCM if it is built for a different version of Python. We
# fall back to the re module in that case.
try:
  import regex as re
except ImportError: # pragma: no cover
  import re # noqa


# Creation flag to disable creating a console window on Windows. See
# https://msdn.microsoft.com/en-us/library/windows/desktop/ms684863.aspx
CREATE_NO_WINDOW = 0x08000000

EXECUTABLE_FILE_MASK = os.F_OK | os.X_OK

CORE_MISSING_ERROR_REGEX = re.compile( "No module named '?ycm_core'?" )

CORE_MISSING_MESSAGE = (
  'ycm_core library not detected; you need to compile it by running the '
  'build.py script. See the documentation for more details.' )
CORE_OUTDATED_MESSAGE = (
  'ycm_core library too old; PLEASE RECOMPILE by running the build.py script. '
  'See the documentation for more details.' )

# Exit statuses returned by the CompatibleWithCurrentCore function:
#  - CORE_COMPATIBLE_STATUS: ycm_core is compatible;
#  - CORE_UNEXPECTED_STATUS: unexpected error while loading ycm_core;
#  - CORE_MISSING_STATUS   : ycm_core is missing;
#  - CORE_OUTDATED_STATUS  : ycm_core version is outdated.
# Values 1 and 2 are not used because 1 is for general errors and 2 has often a
# special meaning for Unix programs. See
# https://docs.python.org/2/library/sys.html#sys.exit
CORE_COMPATIBLE_STATUS  = 0
CORE_UNEXPECTED_STATUS  = 3
CORE_MISSING_STATUS     = 4
CORE_OUTDATED_STATUS    = 7


# Python 3 complains on the common open(path).read() idiom because the file
# doesn't get closed. So, a helper func.
# Also, all files we read are UTF-8.
def ReadFile( filepath ):
  with open( filepath, encoding = 'utf8' ) as f:
    return f.read()


# Returns a file object that can be used to replace sys.stdout or sys.stderr
def OpenForStdHandle( filepath ):
  # Since this function is used for logging purposes, we don't want the output
  # to be delayed. This means line buffering for text mode.
  # See https://docs.python.org/2/library/io.html#io.open
  return open( filepath, mode = 'w', buffering = 1 )


def MakeSafeFileNameString( s ):
  """Return a representation of |s| that is safe for use in a file name.
  Explicitly, returns s converted to lowercase with all non alphanumeric
  characters replaced with '_'."""
  def is_ascii( c ):
    return ord( c ) < 128

  return "".join( c if c.isalnum() and is_ascii( c ) else '_'
                  for c in ToUnicode( s ).lower() )


def CreateLogfile( prefix = '' ):
  with tempfile.NamedTemporaryFile( prefix = prefix,
                                    suffix = '.log',
                                    delete = False ) as logfile:
    return logfile.name


def ToUnicode( value ):
  if not value:
    return ''
  if isinstance( value, str ):
    return value
  if isinstance( value, bytes ):
    # All incoming text should be utf8
    return str( value, 'utf8' )
  return str( value )


# When lines is an iterable of all strings or all bytes, equivalent to
#   '\n'.join( ToUnicode( lines ) )
# but faster on large inputs.
def JoinLinesAsUnicode( lines ):
  try:
    first = next( iter( lines ) )
  except StopIteration:
    return str()

  if isinstance( first, str ):
    return ToUnicode( '\n'.join( lines ) )
  if isinstance( first, bytes ):
    return ToUnicode( b'\n'.join( lines ) )
  raise ValueError( 'lines must contain either strings or bytes.' )


def ToBytes( value ):
  if not value:
    return b''

  if type( value ) == bytes:
    return value

  if isinstance( value, str ):
    return value.encode( 'utf-8' )

  # This is meant to catch `int` and similar non-string/bytes types.
  return str( value ).encode( 'utf-8' )


def ByteOffsetToCodepointOffset( line_value, byte_offset ):
  """The API calls for byte offsets into the UTF-8 encoded version of the
  buffer. However, ycmd internally uses unicode strings. This means that
  when we need to walk 'characters' within the buffer, such as when checking
  for semantic triggers and similar, we must use codepoint offsets, rather than
  byte offsets.

  This method converts the |byte_offset|, which is a 1-based utf-8 byte offset,
  into a 1-based codepoint offset in the unicode string |line_value|."""

  byte_line_value = ToBytes( line_value )
  return len( ToUnicode( byte_line_value[ : byte_offset - 1 ] ) ) + 1


def CodepointOffsetToByteOffset( unicode_line_value, codepoint_offset ):
  """The API calls for byte offsets into the UTF-8 encoded version of the
  buffer. However, ycmd internally uses unicode strings. This means that
  when we need to walk 'characters' within the buffer, such as when checking
  for semantic triggers and similar, we must use codepoint offsets, rather than
  byte offsets.

  This method converts the |codepoint_offset| which is a 1-based unicode
  codepoint offset into a 1-based byte offset into the utf-8 encoded bytes
  version of |unicode_line_value|."""

  # Should be a no-op, but in case someone passes a bytes instance.
  unicode_line_value = ToUnicode( unicode_line_value )
  return len( ToBytes( unicode_line_value[ : codepoint_offset - 1 ] ) ) + 1


def GetUnusedLocalhostPort():
  sock = socket.socket()
  # This tells the OS to give us any free port in the range [1024 - 65535]
  sock.bind( ( '', 0 ) )
  port = sock.getsockname()[ 1 ]
  sock.close()
  return port


def RemoveDirIfExists( dirname ):
  try:
    import shutil
    shutil.rmtree( dirname )
  except OSError:
    pass


def RemoveIfExists( filename ):
  try:
    os.remove( filename )
  except OSError:
    pass


def PathToFirstExistingExecutable( executable_name_list ):
  for executable_name in executable_name_list:
    path = FindExecutable( executable_name )
    if path:
      return path
  return None


def _GetWindowsExecutable( filename ):
  def _GetPossibleWindowsExecutable( filename ):
    pathext = [ ext.lower() for ext in
                os.environ.get( 'PATHEXT', '' ).split( os.pathsep ) ]
    base, extension = os.path.splitext( filename )
    if extension.lower() in pathext:
      return [ filename ]
    else:
      return [ base + ext for ext in pathext ]

  for exe in _GetPossibleWindowsExecutable( filename ):
    if os.path.isfile( exe ):
      return exe
  return None


# Check that a given file can be accessed as an executable file, so controlling
# the access mask on Unix and if has a valid extension on Windows. It returns
# the path to the executable or None if no executable was found.
def GetExecutable( filename ):
  if OnWindows():
    return _GetWindowsExecutable( filename )

  if ( os.path.isfile( filename )
       and os.access( filename, EXECUTABLE_FILE_MASK ) ):
    return filename
  return None


# Adapted from https://github.com/python/cpython/blob/v3.6.0/Lib/shutil.py#L1087
# to be backward compatible with Python2 and more consistent to our codebase.
def FindExecutable( executable ):
  # If we're given a path with a directory part, look it up directly rather
  # than referring to PATH directories. This includes checking relative to the
  # current directory, e.g. ./script
  if os.path.dirname( executable ):
    return GetExecutable( executable )

  paths = os.environ[ 'PATH' ].split( os.pathsep )

  if OnWindows():
    # The current directory takes precedence on Windows.
    curdir = os.path.abspath( os.curdir )
    if curdir not in paths:
      paths.insert( 0, curdir )

  for path in paths:
    exe = GetExecutable( os.path.join( path, executable ) )
    if exe:
      return exe
  return None


def FindExecutableWithFallback( executable_path, fallback ):
  if executable_path:
    executable_path = FindExecutable( ExpandVariablesInPath( executable_path ) )
    if not executable_path:
      # If the user told us to use a non-existing path, report an error.
      # Don't attempt to be too clever about the fallback.
      return None
    return executable_path
  else:
    return fallback


def ExecutableName( executable ):
  return executable + ( '.exe' if OnWindows() else '' )


def ExpandVariablesInPath( path ):
  # Replace '~' with the home directory and expand environment variables in
  # path.
  return os.path.expanduser( os.path.expandvars( path ) )


def OnWindows():
  return sys.platform == 'win32'


def OnMac():
  return sys.platform == 'darwin'


def ProcessIsRunning( handle ):
  return handle is not None and handle.poll() is None


def WaitUntilProcessIsTerminated( handle, timeout = 5 ):
  expiration = time.time() + timeout
  while True:
    if time.time() > expiration:
      raise RuntimeError( f'Waited process to terminate for { timeout } '
                          'seconds, aborting.' )
    if not ProcessIsRunning( handle ):
      return
    time.sleep( 0.1 )


def CloseStandardStreams( handle ):
  if not handle:
    return
  for stream in [ handle.stdin, handle.stdout, handle.stderr ]:
    if stream:
      stream.close()


def IsRootDirectory( path, parent ):
  return path == parent


def PathsToAllParentFolders( path ):
  folder = os.path.normpath( path )
  if os.path.isdir( folder ):
    yield folder
  while True:
    parent = os.path.dirname( folder )
    if IsRootDirectory( folder, parent ):
      break
    folder = parent
    yield folder


def PathLeftSplit( path ):
  """Split a path as (head, tail) where head is the part before the first path
  separator and tail is everything after. If the path is absolute, head is the
  root component, tail everything else. If there is no separator, head is the
  whole path and tail the empty string."""
  drive, path = os.path.splitdrive( path )
  separators = '/\\' if OnWindows() else '/'
  path_length = len( path )
  offset = 0
  while offset < path_length and path[ offset ] not in separators:
    offset += 1
  if offset == path_length:
    return drive + path, ''
  tail = path[ offset + 1 : ].rstrip( separators )
  if offset == 0:
    return drive + path[ 0 ], tail
  return drive + path[ : offset ], tail


# A wrapper for subprocess.Popen that fixes quirks on Windows.
def SafePopen( args, **kwargs ):
  if OnWindows():
    # We need this to start the server otherwise bad things happen.
    # See issue #637.
    if kwargs.get( 'stdin_windows' ) is subprocess.PIPE:
      kwargs[ 'stdin' ] = subprocess.PIPE
    # Do not create a console window
    kwargs[ 'creationflags' ] = CREATE_NO_WINDOW

  kwargs.pop( 'stdin_windows', None )
  return subprocess.Popen( args, **kwargs )


# Read the link and don't ask questions. Python likes to make importing hard.
# https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly
def LoadPythonSource( name, pathname ):
  import importlib.util
  spec = importlib.util.spec_from_file_location( name, pathname )
  module = importlib.util.module_from_spec( spec )
  sys.modules[ spec.name ] = module
  spec.loader.exec_module( module )
  return module


def SplitLines( contents ):
  """Return a list of each of the lines in the unicode string |contents|."""

  # We often want to get a list representation of a buffer such that we can
  # index all of the 'lines' within it. Python provides str.splitlines for this
  # purpose. However, this method not only splits on newline characters (\n,
  # \r\n, and \r) but also on line boundaries like \v and \f. Since old
  # Macintosh newlines (\r) are obsolete and Windows newlines (\r\n) end with a
  # \n character, we can ignore carriage return characters (\r) and only split
  # on \n.
  return contents.split( '\n' )


def GetCurrentDirectory():
  """Returns the current directory as an unicode object. If the current
  directory does not exist anymore, returns the temporary folder instead."""
  try:
    return os.getcwd()
  except FileNotFoundError:
    return tempfile.gettempdir()


def StartThread( func, *args ):
  thread = threading.Thread( target = func, args = args )
  thread.daemon = True
  thread.start()
  return thread


class HashableDict( Mapping ):
  """An immutable dictionary that can be used in dictionary's keys. The
  dictionary must be JSON-encodable; in particular, all keys must be strings."""

  def __init__( self, *args, **kwargs ):
    self._dict = dict( *args, **kwargs )


  def __getitem__( self, key ):
    return copy.deepcopy( self._dict[ key ] )


  def __iter__( self ):
    return iter( self._dict )


  def __len__( self ):
    return len( self._dict )


  def __repr__( self ):
    return '<HashableDict %s>' % repr( self._dict )


  def __hash__( self ):
    try:
      return self._hash
    except AttributeError:
      self._hash = json.dumps( self._dict,
                               separators = ( ',', ':' ),
                               sort_keys = True ).__hash__()
      return self._hash


  def __eq__( self, other ):
    return isinstance( other, HashableDict ) and self._dict == other._dict


  def __ne__( self, other ):
    return not self == other


  def copy( self, **add_or_replace ):
    return self.__class__( self, **add_or_replace )


def ListDirectory( path ):
  try:
    # Path must be a Unicode string to get Unicode strings out of listdir.
    return os.listdir( ToUnicode( path ) )
  except Exception:
    LOGGER.exception( 'Error while listing %s folder', path )
    return []


def GetModificationTime( path ):
  try:
    return os.path.getmtime( path )
  except OSError:
    LOGGER.exception( 'Cannot get modification time for path %s', path )
    return 0


def ExpectedCoreVersion():
  return int( ReadFile( os.path.join( ROOT_DIR, 'CORE_VERSION' ) ) )


def LoadYcmCoreDependencies():
  for name in ListDirectory( LIBCLANG_DIR ):
    if name.startswith( 'libclang' ):
      libclang_path = os.path.join( LIBCLANG_DIR, name )
      if os.path.isfile( libclang_path ):
        import ctypes
        ctypes.cdll.LoadLibrary( libclang_path )
        return


def ImportCore():
  """Imports and returns the ycm_core module. This function exists for easily
  mocking this import in tests."""
  import ycm_core as ycm_core
  return ycm_core


def ImportAndCheckCore():
  """Checks if ycm_core library is compatible and returns with an exit
  status."""
  try:
    try:
      ycm_core = ImportCore()
    except ImportError:
      LoadYcmCoreDependencies()
      ycm_core = ImportCore()
  except ImportError as error:
    message = str( error )
    if CORE_MISSING_ERROR_REGEX.match( message ):
      LOGGER.exception( CORE_MISSING_MESSAGE )
      return CORE_MISSING_STATUS
    LOGGER.exception( message )
    return CORE_UNEXPECTED_STATUS

  try:
    current_core_version = ycm_core.YcmCoreVersion()
  except AttributeError:
    LOGGER.exception( CORE_OUTDATED_MESSAGE )
    return CORE_OUTDATED_STATUS

  if ExpectedCoreVersion() != current_core_version:
    LOGGER.error( CORE_OUTDATED_MESSAGE )
    return CORE_OUTDATED_STATUS

  return CORE_COMPATIBLE_STATUS


def GetClangResourceDir():
  resource_dir = os.path.join( LIBCLANG_DIR, 'clang' )
  for version in ListDirectory( resource_dir ):
    return os.path.join( resource_dir, version )

  raise RuntimeError( 'Cannot find Clang resource directory.' )


CLANG_RESOURCE_DIR = GetClangResourceDir()


def AbsolutePath( path, relative_to ):
  """Returns a normalised, absolute path to |path|. If |path| is relative, it
  is resolved relative to |relative_to|."""
  if not os.path.isabs( path ):
    path = os.path.join( relative_to, path )

  return os.path.normpath( path )


def UpdateDict( target, override ):
  """Apply the updates in |override| to the dict |target|. This is like
  dict.update, but recursive. i.e. if the existing element is a dict, then
  override elements of the sub-dict rather than wholesale replacing.
  e.g.
  UpdateDict(
    {
      'outer': { 'inner': { 'key': 'oldValue', 'existingKey': True } }
    },
    {
      'outer': { 'inner': { 'key': 'newValue' } },
      'newKey': { 'newDict': True },
    }
  )
  yields:
    {
      'outer': {
        'inner': {
           'key': 'newValue',
           'existingKey': True
        }
      },
      'newKey': { newDict: True }
    }
  """

  for key, value in override.items():
    current_value = target.get( key )
    if not isinstance( current_value, Mapping ):
      target[ key ] = value
    elif isinstance( value, Mapping ):
      target[ key ] = UpdateDict( current_value, value )
    else:
      target[ key ] = value

  return target
