# encoding: utf-8
#
# Copyright (C) 2011-2019 ycmd contributors
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

from future.utils import PY2, native
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


# Idiom to import pathname2url, url2pathname, urljoin, and urlparse on Python 2
# and 3. By exposing these functions here, we can import them directly from this
# module:
#
#   from ycmd.utils import pathname2url, url2pathname, urljoin, urlparse
#
if PY2:
  from collections import Mapping
  from urlparse import urljoin, urlparse, unquote
  from urllib import pathname2url, url2pathname, quote
else:
  from collections.abc import Mapping  # noqa
  from urllib.parse import urljoin, urlparse, unquote, quote  # noqa
  from urllib.request import pathname2url, url2pathname  # noqa


# We replace the re module with regex as it has better support for characters on
# multiple code points. However, this module has a compiled component so we
# can't import it in YCM if it is built for a different version of Python (e.g.
# if YCM is running on Python 2 while ycmd on Python 3). We fall back to the re
# module in that case.
try:
  import regex as re
except ImportError: # pragma: no cover
  import re # noqa


# Creation flag to disable creating a console window on Windows. See
# https://msdn.microsoft.com/en-us/library/windows/desktop/ms684863.aspx
CREATE_NO_WINDOW = 0x08000000

EXECUTABLE_FILE_MASK = os.F_OK | os.X_OK

CORE_MISSING_ERROR_REGEX = re.compile( "No module named '?ycm_core'?" )
CORE_PYTHON2_ERROR_REGEX = re.compile(
  'dynamic module does not define (?:init|module export) '
  'function \\(PyInit_ycm_core\\)|'
  'Module use of python2[0-9]\\.dll conflicts with this version of Python\\.$' )
CORE_PYTHON3_ERROR_REGEX = re.compile(
  'dynamic module does not define init function \\(initycm_core\\)|'
  'Module use of python3[0-9]\\.dll conflicts with this version of Python\\.$' )

CORE_MISSING_MESSAGE = (
  'ycm_core library not detected; you need to compile it by running the '
  'build.py script. See the documentation for more details.' )
CORE_PYTHON2_MESSAGE = (
  'ycm_core library compiled for Python 2 but loaded in Python 3.' )
CORE_PYTHON3_MESSAGE = (
  'ycm_core library compiled for Python 3 but loaded in Python 2.' )
CORE_OUTDATED_MESSAGE = (
  'ycm_core library too old; PLEASE RECOMPILE by running the build.py script. '
  'See the documentation for more details.' )

# Exit statuses returned by the CompatibleWithCurrentCore function:
#  - CORE_COMPATIBLE_STATUS: ycm_core is compatible;
#  - CORE_UNEXPECTED_STATUS: unexpected error while loading ycm_core;
#  - CORE_MISSING_STATUS   : ycm_core is missing;
#  - CORE_PYTHON2_STATUS   : ycm_core is compiled with Python 2 but loaded with
#    Python 3;
#  - CORE_PYTHON3_STATUS   : ycm_core is compiled with Python 3 but loaded with
#    Python 2;
#  - CORE_OUTDATED_STATUS  : ycm_core version is outdated.
# Values 1 and 2 are not used because 1 is for general errors and 2 has often a
# special meaning for Unix programs. See
# https://docs.python.org/2/library/sys.html#sys.exit
CORE_COMPATIBLE_STATUS  = 0
CORE_UNEXPECTED_STATUS  = 3
CORE_MISSING_STATUS     = 4
CORE_PYTHON2_STATUS     = 5
CORE_PYTHON3_STATUS     = 6
CORE_OUTDATED_STATUS    = 7


# Python 3 complains on the common open(path).read() idiom because the file
# doesn't get closed. So, a helper func.
# Also, all files we read are UTF-8.
def ReadFile( filepath ):
  with open( filepath, encoding = 'utf8' ) as f:
    return f.read()


# Returns a file object that can be used to replace sys.stdout or sys.stderr
def OpenForStdHandle( filepath ):
  # Need to open the file in binary mode on py2 because of bytes vs unicode.
  # If we open in text mode (default), then third-party code that uses `print`
  # (we're replacing sys.stdout!) with an `str` object on py2 will cause
  # tracebacks because text mode insists on unicode objects. (Don't forget,
  # `open` is actually `io.open` because of future builtins.)
  # Since this function is used for logging purposes, we don't want the output
  # to be delayed. This means no buffering for binary mode and line buffering
  # for text mode. See https://docs.python.org/2/library/io.html#io.open
  if PY2:
    return open( filepath, mode = 'wb', buffering = 0 )
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


# Given an object, returns a str object that's utf-8 encoded. This is meant to
# be used exclusively when producing strings to be passed to the C++ Python
# plugins. For other code, you likely want to use ToBytes below.
def ToCppStringCompatible( value ):
  if isinstance( value, str ):
    return native( value.encode( 'utf8' ) )
  if isinstance( value, bytes ):
    return native( value )
  return native( str( value ).encode( 'utf8' ) )


# Returns a unicode type; either the new python-future str type or the real
# unicode type. The difference shouldn't matter.
def ToUnicode( value ):
  if not value:
    return str()
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


# Consistently returns the new bytes() type from python-future. Assumes incoming
# strings are either UTF-8 or unicode (which is converted to UTF-8).
def ToBytes( value ):
  if not value:
    return bytes()

  # This is tricky. On py2, the bytes type from builtins (from python-future) is
  # a subclass of str. So all of the following are true:
  #   isinstance(str(), bytes)
  #   isinstance(bytes(), str)
  # But they don't behave the same in one important aspect: iterating over a
  # bytes instance yields ints, while iterating over a (raw, py2) str yields
  # chars. We want consistent behavior so we force the use of bytes().
  if type( value ) == bytes:
    return value

  # This is meant to catch Python 2's native str type.
  if isinstance( value, bytes ):
    return bytes( value, encoding = 'utf8' )

  if isinstance( value, str ):
    # On py2, with `from builtins import *` imported, the following is true:
    #
    #   bytes(str(u'abc'), 'utf8') == b"b'abc'"
    #
    # Obviously this is a bug in python-future. So we work around it. Also filed
    # upstream at: https://github.com/PythonCharmers/python-future/issues/193
    # We can't just return value.encode( 'utf8' ) on both py2 & py3 because on
    # py2 that *sometimes* returns the built-in str type instead of the newbytes
    # type from python-future.
    if PY2:
      return bytes( value.encode( 'utf8' ), encoding = 'utf8' )
    else:
      return bytes( value, encoding = 'utf8' )

  # This is meant to catch `int` and similar non-string/bytes types.
  return ToBytes( str( value ) )


def ByteOffsetToCodepointOffset( line_value, byte_offset ):
  """The API calls for byte offsets into the UTF-8 encoded version of the
  buffer. However, ycmd internally uses unicode strings. This means that
  when we need to walk 'characters' within the buffer, such as when checking
  for semantic triggers and similar, we must use codepoint offets, rather than
  byte offsets.

  This method converts the |byte_offset|, which is a utf-8 byte offset, into
  a codepoint offset in the unicode string |line_value|."""

  byte_line_value = ToBytes( line_value )
  return len( ToUnicode( byte_line_value[ : byte_offset - 1 ] ) ) + 1


def CodepointOffsetToByteOffset( unicode_line_value, codepoint_offset ):
  """The API calls for byte offsets into the UTF-8 encoded version of the
  buffer. However, ycmd internally uses unicode strings. This means that
  when we need to walk 'characters' within the buffer, such as when checking
  for semantic triggers and similar, we must use codepoint offets, rather than
  byte offsets.

  This method converts the |codepoint_offset| which is a unicode codepoint
  offset into an byte offset into the utf-8 encoded bytes version of
  |unicode_line_value|."""

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


# Adapted from https://hg.python.org/cpython/file/3.5/Lib/shutil.py#l1081
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


def ExecutableName( executable ):
  return executable + ( '.exe' if OnWindows() else '' )


def ExpandVariablesInPath( path ):
  # Replace '~' with the home directory and expand environment variables in
  # path.
  return os.path.expanduser( os.path.expandvars( path ) )


def OnWindows():
  return sys.platform == 'win32'


def OnCygwin():
  return sys.platform == 'cygwin'


def OnMac():
  return sys.platform == 'darwin'


def ProcessIsRunning( handle ):
  return handle is not None and handle.poll() is None


def WaitUntilProcessIsTerminated( handle, timeout = 5 ):
  expiration = time.time() + timeout
  while True:
    if time.time() > expiration:
      raise RuntimeError( 'Waited process to terminate for {0} seconds, '
                          'aborting.'.format( timeout ) )
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
    # Python 2 fails to spawn a process from a command containing unicode
    # characters on Windows.  See https://bugs.python.org/issue19264 and
    # http://bugs.python.org/issue1759845.
    # Since paths are likely to contains such characters, we convert them to
    # short ones to obtain paths with only ascii characters.
    if PY2:
      args = ConvertArgsToShortPath( args )

  kwargs.pop( 'stdin_windows', None )
  return subprocess.Popen( args, **kwargs )


# We need to convert environment variables to native strings on Windows and
# Python 2 to prevent a TypeError when passing them to a subprocess.
def SetEnviron( environ, variable, value ):
  if OnWindows() and PY2:
    environ[ native( ToBytes( variable ) ) ] = native( ToBytes( value ) )
  else:
    environ[ variable ] = value


# Convert paths in arguments command to short path ones
def ConvertArgsToShortPath( args ):
  def ConvertIfPath( arg ):
    if os.path.exists( arg ):
      return GetShortPathName( arg )
    return arg

  if isinstance( args, str ) or isinstance( args, bytes ):
    return ConvertIfPath( args )
  return [ ConvertIfPath( arg ) for arg in args ]


# Get the Windows short path name.
# Based on http://stackoverflow.com/a/23598461/200291
def GetShortPathName( path ):
  if not OnWindows():
    return path

  from ctypes import windll, wintypes, create_unicode_buffer

  # Set the GetShortPathNameW prototype
  _GetShortPathNameW = windll.kernel32.GetShortPathNameW
  _GetShortPathNameW.argtypes = [ wintypes.LPCWSTR,
                                  wintypes.LPWSTR,
                                  wintypes.DWORD ]
  _GetShortPathNameW.restype = wintypes.DWORD

  output_buf_size = 0

  while True:
    output_buf = create_unicode_buffer( output_buf_size )
    needed = _GetShortPathNameW( path, output_buf, output_buf_size )
    if output_buf_size >= needed:
      return output_buf.value
    else:
      output_buf_size = needed


# Shim for imp.load_source so that it works on both Py2 & Py3. See upstream
# Python docs for info on what this does.
def LoadPythonSource( name, pathname ):
  if PY2:
    import imp
    try:
      return imp.load_source( name, pathname )
    except UnicodeEncodeError:
      # imp.load_source doesn't handle non-ASCII characters in pathname. See
      # http://bugs.python.org/issue9425
      source = ReadFile( pathname )
      module = imp.new_module( name )
      module.__file__ = pathname
      exec( source, module.__dict__ )
      return module
  import importlib
  return importlib.machinery.SourceFileLoader( name, pathname ).load_module()


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
    if PY2:
      return os.getcwdu()
    return os.getcwd()
  # os.getcwdu throws an OSError exception when the current directory has been
  # deleted while os.getcwd throws a FileNotFoundError, which is a subclass of
  # OSError.
  except OSError:
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
      self._hash = json.dumps( self._dict, sort_keys = True ).__hash__()
      return self._hash


  def __eq__( self, other ):
    return isinstance( other, HashableDict ) and self._dict == other._dict


  def __ne__( self, other ):
    return not self == other


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
    LoadYcmCoreDependencies()
    ycm_core = ImportCore()
  except ImportError as error:
    message = str( error )
    if CORE_MISSING_ERROR_REGEX.match( message ):
      LOGGER.exception( CORE_MISSING_MESSAGE )
      return CORE_MISSING_STATUS
    if CORE_PYTHON2_ERROR_REGEX.match( message ):
      LOGGER.exception( CORE_PYTHON2_MESSAGE )
      return CORE_PYTHON2_STATUS
    if CORE_PYTHON3_ERROR_REGEX.match( message ):
      LOGGER.exception( CORE_PYTHON3_MESSAGE )
      return CORE_PYTHON3_STATUS
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
