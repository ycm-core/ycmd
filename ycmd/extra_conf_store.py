# Copyright (C) 2011-2018 ycmd contributors
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

# NOTE: This module is used as a Singleton

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa

import os
import random
import string
import sys
from threading import Lock
from ycmd import user_options_store
from ycmd.responses import UnknownExtraConf, YCM_EXTRA_CONF_FILENAME
from ycmd.utils import ( ExpandVariablesInPath, LoadPythonSource, LOGGER,
                         PathsToAllParentFolders )
from fnmatch import fnmatch


# Singleton variables
_module_for_module_file = {}
_module_for_module_file_lock = Lock()
_module_file_for_source_file = {}
_module_file_for_source_file_lock = Lock()


def Get():
  return _module_for_module_file, _module_file_for_source_file


def Set( state ):
  global _module_for_module_file, _module_file_for_source_file
  _module_for_module_file, _module_file_for_source_file = state


def Reset():
  global _module_for_module_file, _module_file_for_source_file
  _module_for_module_file = {}
  _module_file_for_source_file = {}


def ModuleForSourceFile( filename ):
  return Load( ModuleFileForSourceFile( filename ) )


def ModuleFileForSourceFile( filename ):
  """This will try all files returned by _ExtraConfModuleSourceFilesForFile in
  order and return the filename of the first module that was allowed to load.
  If no module was found or allowed to load, None is returned."""

  with _module_file_for_source_file_lock:
    if filename not in _module_file_for_source_file:
      for module_file in _ExtraConfModuleSourceFilesForFile( filename ):
        if Load( module_file ):
          _module_file_for_source_file[ filename ] = module_file
          break

  return _module_file_for_source_file.setdefault( filename )


def CallGlobalExtraConfYcmCorePreloadIfExists():
  _CallGlobalExtraConfMethod( 'YcmCorePreload' )


def Shutdown():
  # VimClose is for the sake of backwards compatibility; it's a no-op when it
  # doesn't exist.
  _CallGlobalExtraConfMethod( 'VimClose' )
  _CallGlobalExtraConfMethod( 'Shutdown' )


def _CallGlobalExtraConfMethod( function_name ):
  global_ycm_extra_conf = _GlobalYcmExtraConfFileLocation()
  if not ( global_ycm_extra_conf and
           os.path.exists( global_ycm_extra_conf ) ):
    LOGGER.debug( 'No global extra conf, not calling method %s', function_name )
    return

  try:
    module = Load( global_ycm_extra_conf, force = True )
  except Exception:
    LOGGER.exception( 'Error occurred while loading global extra conf %s',
                      global_ycm_extra_conf )
    return

  if not module or not hasattr( module, function_name ):
    LOGGER.debug( 'Global extra conf not loaded or no function %s',
                  function_name )
    return

  try:
    LOGGER.info( 'Calling global extra conf method %s on conf file %s',
                 function_name,
                 global_ycm_extra_conf )
    getattr( module, function_name )()
  except Exception:
    LOGGER.exception(
      'Error occurred while calling global extra conf method %s '
      'on conf file %s', function_name, global_ycm_extra_conf )


def Disable( module_file ):
  """Disables the loading of a module for the current session."""
  with _module_for_module_file_lock:
    _module_for_module_file[ module_file ] = None


def _ShouldLoad( module_file, is_global ):
  """Checks if a module is safe to be loaded. By default this will try to
  decide using a white-/blacklist and ask the user for confirmation as a
  fallback."""

  if is_global or not user_options_store.Value( 'confirm_extra_conf' ):
    return True

  globlist = user_options_store.Value( 'extra_conf_globlist' )
  for glob in globlist:
    is_blacklisted = glob[ 0 ] == '!'
    if _MatchesGlobPattern( module_file, glob.lstrip( '!' ) ):
      return not is_blacklisted

  raise UnknownExtraConf( module_file )


def Load( module_file, force = False ):
  """Load and return the module contained in a file.
  Using force = True the module will be loaded regardless
  of the criteria in _ShouldLoad.
  This will return None if the module was not allowed to be loaded."""

  if not module_file:
    return None

  with _module_for_module_file_lock:
    if module_file in _module_for_module_file:
      return _module_for_module_file[ module_file ]

  is_global = module_file == _GlobalYcmExtraConfFileLocation()
  if not force and not _ShouldLoad( module_file, is_global ):
    Disable( module_file )
    return None

  # This has to be here because a long time ago, the ycm_extra_conf.py files
  # used to import clang_helpers.py from the cpp folder. This is not needed
  # anymore, but there are a lot of old ycm_extra_conf.py files that we don't
  # want to break.
  sys.path.insert( 0, _PathToCppCompleterFolder() )

  # By default, the Python interpreter compiles source files into bytecode to
  # load them faster next time they are run. These *.pyc files are generated
  # along the source files prior to Python 3.2 or in a __pycache__ folder for
  # newer versions. We disable the generation of these files when loading
  # ycm_extra_conf.py files as users do not want them inside their projects.
  # The drawback is negligible since ycm_extra_conf.py files are generally small
  # files thus really fast to compile and only loaded once by editing session.
  old_dont_write_bytecode = sys.dont_write_bytecode
  sys.dont_write_bytecode = True
  try:
    module = LoadPythonSource( _RandomName(), module_file )
    module.is_global_ycm_extra_conf = is_global
  finally:
    sys.dont_write_bytecode = old_dont_write_bytecode

  del sys.path[ 0 ]

  with _module_for_module_file_lock:
    _module_for_module_file[ module_file ] = module
  return module


def _MatchesGlobPattern( filename, glob ):
  """Returns true if a filename matches a given pattern. Environment variables
  and a '~' in glob will be expanded and checking will be performed using
  absolute paths with symlinks resolved (except on Windows). See the
  documentation of fnmatch for the supported patterns."""

  # NOTE: os.path.realpath does not resolve symlinks on Windows.
  # See https://bugs.python.org/issue9949
  realpath = os.path.realpath( filename )
  return fnmatch( realpath, os.path.realpath( ExpandVariablesInPath( glob ) ) )


def _ExtraConfModuleSourceFilesForFile( filename ):
  """For a given filename, search all parent folders for YCM_EXTRA_CONF_FILENAME
  files that will compute the flags necessary to compile the file.
  If _GlobalYcmExtraConfFileLocation() exists it is returned as a fallback."""

  for folder in PathsToAllParentFolders( filename ):
    candidate = os.path.join( folder, YCM_EXTRA_CONF_FILENAME )
    if os.path.exists( candidate ):
      yield candidate
  global_ycm_extra_conf = _GlobalYcmExtraConfFileLocation()
  if ( global_ycm_extra_conf
       and os.path.exists( global_ycm_extra_conf ) ):
    yield global_ycm_extra_conf


def _PathToCppCompleterFolder():
  """Returns the path to the 'cpp' completer folder. This is necessary
  because ycm_extra_conf files need it on the path."""
  return os.path.join( _DirectoryOfThisScript(), 'completers', 'cpp' )


def _DirectoryOfThisScript():
  return os.path.dirname( os.path.abspath( __file__ ) )


def _RandomName():
  """Generates a random module name."""
  return ''.join( random.choice( string.ascii_lowercase ) for x in range( 15 ) )


def _GlobalYcmExtraConfFileLocation():
  return ExpandVariablesInPath(
    user_options_store.Value( 'global_ycm_extra_conf' ) )


def IsGlobalExtraConfModule( module ):
  return module.is_global_ycm_extra_conf
