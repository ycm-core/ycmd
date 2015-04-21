#!/usr/bin/env python
#
# Copyright (C) 2015 Google Inc.
#
# This file is part of YouCompleteMe.
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

import json
import logging
import os
import subprocess

from ycmd import responses
from ycmd import utils
from ycmd.completers.completer import Completer

GO_FILETYPES = set( [ 'go' ] )
COMPLETION_ERROR_MESSAGE = "Gocode shell call failed."
PARSE_ERROR_MESSAGE = "Gocode returned invalid JSON response."
NO_COMPLETIONS_MESSAGE = "Gocode returned empty JSON response."
GOCODE_PANIC_MESSAGE = "Gocode panicked trying to find completions, "\
    +"you likely have a syntax error."
PATH_TO_GOCODE_BINARY = os.path.join(
  os.path.abspath( os.path.dirname( __file__ ) ),
  '../../../third_party/gocode/gocode' )

_logger = logging.getLogger( __name__ )


def FindGoCodeBinary( user_options ):
  ''' Find the path to the gocode binary.

  TODO(ekfriis): Test.

  If 'gocode_binary_path' in the options is blank,
  use the version installed with YCM, if it exists,
  then the one on the path, if not.

  If the 'gocode_binary_path' is specified, use it
  as an absolute path.

  If the resolved binary exists, return the path,
  otherwise return None.
  '''
  if user_options.get( 'gocode_binary_path' ):
    # The user has explicitly specified a path.
    if os.path.exists( user_options[ 'gocode_binary_path' ] ):
      return user_options[ 'gocode_binary_path' ]
    else:
      return None
  # Try to use the bundled binary or one on the path.
  if os.path.exists( PATH_TO_GOCODE_BINARY ):
    return PATH_TO_GOCODE_BINARY
  return utils.PathToFirstExistingExecutable( [ 'gocode' ] )



class GoCodeCompleter( Completer ):
  def __init__( self, user_options ):
    super( GoCodeCompleter, self ).__init__( user_options )
    self._popener = utils.SafePopen # Overridden in test.
    self._binary = FindGoCodeBinary( user_options )


  def SupportedFiletypes( self ):
    return GO_FILETYPES


  def ComputeCandidatesInner( self, request_data ):
    filename = request_data[ 'filepath' ]
    _logger.info( "gocode completion request %s" % filename )
    if not filename:
      return

    contents = utils.ToUtf8IfNeeded(
        request_data['file_data'][ filename ][ 'contents' ] )
    offset = _ComputeOffset( contents, request_data[ 'line_num' ],
                            request_data[ 'column_num' ] )

    cmd = [self._binary, '-f=json', 'autocomplete', filename, str( offset )]
    proc = self._popener( cmd, stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdoutdata, stderrdata = proc.communicate( contents )
    if proc.returncode:
      _logger.error( COMPLETION_ERROR_MESSAGE + " code %i stderr: %s",
                    proc.returncode, stderrdata)
      raise RuntimeError( COMPLETION_ERROR_MESSAGE )

    try:
      resultdata = json.loads( stdoutdata )
    except ValueError:
      _logger.error( PARSE_ERROR_MESSAGE )
      raise RuntimeError( PARSE_ERROR_MESSAGE )
    if len(resultdata) != 2:
      _logger.error( NO_COMPLETIONS_MESSAGE )
      raise RuntimeError( NO_COMPLETIONS_MESSAGE )
    for result in resultdata[1]:
      if result.get('class') == "PANIC":
        raise RuntimeError( GOCODE_PANIC_MESSAGE )

    return [ _ConvertCompletionData( x ) for x in resultdata[1] ]


# Compute the byte offset in the file given the line and column.
# TODO(ekfriis): If this is slow, consider moving this to C++ ycm_core,
# perhaps in RequestWrap.
def _ComputeOffset( contents, line, col ):
  curline = 1
  curcol = 1
  for i, byte in enumerate( contents ):
    if curline == line and curcol == col:
      return i
    curcol += 1
    if byte == '\n':
      curline += 1
      curcol = 1
  _logger.error( "GoCode completer - could not compute byte offset " +
                "corresponding to L%i C%i", line, col )
  return -1


def _ConvertCompletionData( completion_data ):
  return responses.BuildCompletionData(
    insertion_text = completion_data[ 'name' ],
    menu_text = completion_data[ 'name' ],
    extra_menu_info = completion_data[ 'type' ],
    kind = completion_data[ 'class' ])


