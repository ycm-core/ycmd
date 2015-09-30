#!/usr/bin/env python
#
# Copyright (C) 2013 Stanislav Golovanov <stgolovanov@gmail.com>
#                    Google Inc.
#
# YouCompleteMe is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# YouCompleteMe is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with YouCompleteMe.  If not, see <http://www.gnu.org/licenses/>.

import os
import re
from collections import defaultdict

from ycmd.completers.completer import Completer
from ycmd.completers.completer_utils import ( AtIncludeStatementStart,
                                              GetIncludeStatementValue )
from ycmd.completers.cpp.clang_completer import InCFamilyFile
from ycmd.completers.cpp.flags import Flags
from ycmd.utils import ToUtf8IfNeeded, ToUnicodeIfNeeded, OnWindows
from ycmd import responses

EXTRA_INFO_MAP = { 1 : '[File]', 2 : '[Dir]', 3 : '[File&Dir]' }


class FilenameCompleter( Completer ):
  """
  General completer that provides filename and filepath completions.
  """

  def __init__( self, user_options ):
    super( FilenameCompleter, self ).__init__( user_options )
    self._flags = Flags()

    # On Windows, backslashes are also valid path separators.
    self._triggers = [ '/', '\\' ] if OnWindows() else [ '/' ]

    self._path_regex = re.compile( """
      # Head part
      (?:
        # 'D:/'-like token
        [A-z]+:[%(sep)s]|

        # '/', './', '../', or '~'
        \.{0,2}[%(sep)s]|~|

        # '$var/'
        \$[A-Za-z0-9{}_]+[%(sep)s]
      )+

      # Tail part
      (?:
        # any alphanumeric, symbol or space literal
        [ %(sep)sa-zA-Z0-9(){}$+_~.\x80-\xff-\[\]]|

        # skip any special symbols
        [^\x20-\x7E]|

        # backslash and 1 char after it
        \\.
      )*$
      """ % { 'sep': '/\\\\' if OnWindows() else '/' }, re.X )


  def ShouldCompleteIncludeStatement( self, request_data ):
    start_column = request_data[ 'start_column' ] - 1
    current_line = request_data[ 'line_value' ]
    filepath = request_data[ 'filepath' ]
    filetypes = request_data[ 'file_data' ][ filepath ][ 'filetypes' ]
    return ( InCFamilyFile( filetypes ) and
             AtIncludeStatementStart( current_line[ :start_column ] ) )


  def ShouldUseNowInner( self, request_data ):
    start_column = request_data[ 'start_column' ] - 1
    current_line = request_data[ 'line_value' ]
    return ( start_column and
             ( current_line[ start_column - 1 ] in self._triggers or
               self.ShouldCompleteIncludeStatement( request_data ) ) )


  def SupportedFiletypes( self ):
    return []


  def ComputeCandidatesInner( self, request_data ):
    current_line = request_data[ 'line_value' ]
    start_column = request_data[ 'start_column' ] - 1
    orig_filepath = request_data[ 'filepath' ]
    filetypes = request_data[ 'file_data' ][ orig_filepath ][ 'filetypes' ]
    line = current_line[ :start_column ]
    utf8_filepath = ToUtf8IfNeeded( orig_filepath )

    if InCFamilyFile( filetypes ):
      path_dir, quoted_include = (
              GetIncludeStatementValue( line, check_closing = False ) )
      if path_dir is not None:
        # We do what GCC does for <> versus "":
        # http://gcc.gnu.org/onlinedocs/cpp/Include-Syntax.html
        client_data = request_data.get( 'extra_conf_data', None )
        return _GenerateCandidatesForPaths(
          self.GetPathsIncludeCase( path_dir,
                                    quoted_include,
                                    utf8_filepath,
                                    client_data ) )

    path_match = self._path_regex.search( line )
    path_dir = os.path.expanduser(
      os.path.expandvars( path_match.group() ) ) if path_match else ''

    # If the client supplied its working directory, use that instead of the
    # working directory of ycmd
    working_dir = request_data.get( 'working_dir' )

    return _GenerateCandidatesForPaths(
      _GetPathsStandardCase(
        path_dir,
        self.user_options[ 'filepath_completion_use_working_dir' ],
        utf8_filepath,
        working_dir) )


  def GetPathsIncludeCase( self, path_dir, quoted_include, filepath,
                           client_data ):
    paths = []
    quoted_include_paths, include_paths = (
            self._flags.UserIncludePaths( filepath, client_data ) )

    if quoted_include:
      include_paths.extend( quoted_include_paths )

    for include_path in include_paths:
      unicode_path = ToUnicodeIfNeeded( os.path.join( include_path, path_dir ) )
      try:
        # We need to pass a unicode string to get unicode strings out of
        # listdir.
        relative_paths = os.listdir( unicode_path )
      except:
        relative_paths = []

      paths.extend( os.path.join( include_path, path_dir, relative_path ) for
                    relative_path in relative_paths  )

    return sorted( set( paths ) )


def _GetAbsolutePathForCompletions( path_dir,
                                    use_working_dir,
                                    filepath,
                                    working_dir ):
  """
  Returns the absolute path for which completion suggestions should be returned
  (in the standard case).
  """

  if os.path.isabs( path_dir ):
    # This is already an absolute path, return it
    return path_dir
  elif use_working_dir:
    # Return paths relative to the working directory of the client, if
    # supplied, otherwise relative to the current working directory of this
    # process
    if working_dir:
      return os.path.join( working_dir, path_dir )
    else:
      return os.path.join( os.getcwd(), path_dir )
  else:
    # Return paths relative to the file
    return os.path.join( os.path.join( os.path.dirname( filepath ) ),
                         path_dir )


def _GetPathsStandardCase( path_dir, use_working_dir, filepath, working_dir ):

  absolute_path_dir = _GetAbsolutePathForCompletions( path_dir,
                                                      use_working_dir,
                                                      filepath,
                                                      working_dir )

  try:
    # We need to pass a unicode string to get unicode strings out of
    # listdir.
    relative_paths = os.listdir( ToUnicodeIfNeeded( absolute_path_dir ) )
  except:
    relative_paths = []

  return ( os.path.join( absolute_path_dir, relative_path )
           for relative_path in relative_paths )


def _GenerateCandidatesForPaths( absolute_paths ):
  extra_info = defaultdict( int )
  basenames = []
  for absolute_path in absolute_paths:
    basename = os.path.basename( absolute_path )
    if extra_info[ basename ] == 0:
      basenames.append( basename )
    is_dir = os.path.isdir( absolute_path )
    extra_info[ basename ] |= ( 2 if is_dir else 1 )

  completion_dicts = []
  # Keep original ordering
  for basename in basenames:
    completion_dicts.append(
      responses.BuildCompletionData( basename,
                                     EXTRA_INFO_MAP[ extra_info[ basename ] ] ) )

  return completion_dicts
