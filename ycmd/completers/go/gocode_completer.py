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

import logging
import json
import os
import subprocess

from ycmd import responses
from ycmd import utils
from ycmd.completers.completer import Completer

GO_FILETYPES = set( [ 'go' ] )
COMPLETION_ERROR_MESSAGE = "gocode call failed"
NO_COMPLETIONS_MESSAGE = "gocode failed returned no completions"

_logger = logging.getLogger( __name__ )

class GoCodeCompleter( Completer ):
  def __init__( self, user_options ):
    _logger.info("initializing gocode")
    super( GoCodeCompleter, self ).__init__( user_options )


  def SupportedFiletypes( self ):
    return GO_FILETYPES


  def ComputeCandidatesInner( self, request_data ):
    filename = request_data[ 'filepath' ]
    _logger.info("gocode completion request %s" % filename)
    if not filename:
      _logger.info("blarg")
      return

    _logger.info("converting contests for %s bytes" % len( request_data['file_data'][ filename ][ 'contents' ] ))
    contents = utils.ToUtf8IfNeeded( request_data['file_data'][ filename ][ 'contents' ] )
    _logger.info("converted contests")
    offset = _ComputeOffset( contents, request_data[ 'line_num' ], 
                            request_data[ 'column_num' ] )
    _logger.info("got offset at %s" % offset)

    filename_format = os.path.join( utils.PathToTempDir(), u'gocode_{std}.log' )
    stdout_file = filename_format.format(std='stdout')
    stderr_file = filename_format.format(std='stderr')
    
    _logger.info("stdout %s %s" % (stdout_file, stderr_file))

    with open(stdout_file, 'w') as stdout:
      with open(stderr_file, 'w') as stderr:
        cmd = ['gocode', '-f=json', 'autocomplete', filename, str(offset)]
        _logger.info("spawning gocode command %s" % cmd)
        proc = utils.SafePopen(cmd, stdout=stdout, stderr=stderr, stdin=subprocess.PIPE)
        _logger.info("writing")
        proc.stdin.write(contents)
        _logger.info("closing")
        proc.stdin.close()
        _logger.info("waiting")
        retcode = proc.wait()
        _logger.info("done %i" % retcode)
        if retcode:
          _logger.error("gocode failed with code %i" % retcode)
          raise RuntimeError( COMPLETION_ERROR_MESSAGE )

    with open(stdout_file, 'r') as results_file:
      resultdata = json.load(results_file)
      if not resultdata:
        _logger.error("gocode failed to parse results")
        raise RuntimeError( NO_COMPLETIONS_MESSAGE )

    _logger.error("gocode results done")
    return [ _ConvertCompletionData( x ) for x in resultdata[1] ]


def _ComputeOffset(contents, line, col):
  curline = 1
  curcol = 1
  for i, byte in enumerate(contents):
    if curline == line and curcol == col:
      return i
    curcol += 1
    if byte == '\n':
      curline += 1
      curcol = 1
  return -1


def _ConvertCompletionData( completion_data ):
  return responses.BuildCompletionData(
    insertion_text = completion_data[ 'name' ],
    menu_text = completion_data[ 'name' ],
    extra_menu_info = completion_data[ 'type' ])


