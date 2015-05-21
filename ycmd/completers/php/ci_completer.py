#!/usr/bin/env python
#
# Copyright (C) 2015  Neo Mofoka <neo@jeteon.com>
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
from os.path import abspath, dirname, join
import sys
from ycmd.utils import ToUtf8IfNeeded
from ycmd.completers.completer import Completer
from ycmd import responses

# Add CodeIntel to path. Assume is residing in third party
REPO_ROOT = dirname( dirname( dirname( dirname( abspath( __file__ ) ) ) ) )
CI_BASE = join( REPO_ROOT, 'third_party', 'codeintel' )
CI_DIR = join( CI_BASE, 'codeintel' )
sys.path.insert( 0, CI_DIR )
sys.path.insert( 0, CI_BASE )

from codeintel2.common import EvalController
from codeintel2.manager import Manager
from codeintel2.environment import SimplePrefsEnvironment

# Set up logger
logger = logging.getLogger( __name__ )

class CodeIntelCompleter( Completer ):
  """
  A Completer that uses the Code Intel code intelligence engine.
  """

  mgr = None


  def __init__( self, user_options ):
    super( CodeIntelCompleter, self ).__init__( user_options )

    # Initialize CodeIntel Manager on the class
    if CodeIntelCompleter.mgr is None:
      CodeIntelCompleter.mgr = Manager(
          db_base_dir = join( CI_DIR, 'db' ),
          extra_module_dirs = [ join( CI_DIR, 'codeintel2' ), ],
          db_import_everything_langs = None,
          db_catalog_dirs = [],
          env = SimplePrefsEnvironment()
      )
      self.mgr.upgrade()
      self.mgr.initialize()
      logger.debug('Manager initialized: %s' % user_options)


  def SupportedFiletypes( self ):
    """ Just PHP (for now) """
    return [ 'php' ]


  def ComputeCandidatesInner( self, request_data ):
    buf, pos = self._GetCodeIntelBufAndPos( request_data )
    trg = buf.preceding_trg_from_pos( pos, pos )

    if trg is None:
      return []

    cplns = buf.cplns_from_trg( trg )

    return [ responses.BuildCompletionData(
                ToUtf8IfNeeded( cpln[1] ),
                kind = ToUtf8IfNeeded( cpln[0] ))
            for cpln in cplns ]


  def ShouldUseNowInner( self, request_data ):
    res = super( CodeIntelCompleter, self ).ShouldUseNowInner( request_data )
    logger.debug('ShouldUseNowInner called. Returns %s' % res)

    # Don't complete for empty lines
    if not len( request_data[ 'line_value' ] ):
      return False

    # TODO: Fix this to check request data
    return True


  def DefinedSubcommands( self ):
    return ['GoTo']


  def OnUserCommand( self, arguments, request_data ):
    if not arguments:
      raise ValueError( self.UserCommandsHelpMessage() )

    command = arguments[ 0 ]
    if command == 'GoTo':
      return self._GoTo( request_data )
    raise ValueError( self.UserCommandsHelpMessage() )


  def _GetCodeIntelBufAndPos( self, request_data ):
    filename = request_data[ 'filepath' ]
    contents = request_data[ 'file_data' ][ filename ][ 'contents' ]
    line = request_data[ 'line_num' ]
    column = request_data[ 'column_num' ]

    buf = self.mgr.buf_from_content(contents, 'PHP', path = filename )
    pos = ( sum( [ 
				   len( l ) + 1 for l in 
				      contents.split( '\n' )[ : ( line - 1 ) ] ] )  + 
	        column - 1)

    return buf, pos 


  def _GoTo( self, request_data ):
    definitions = self._GetDefinitionsList( request_data )
    if definitions:
      return self._BuildGoToResponse( definitions )
    else:
      raise RuntimeError( 'Can\'t jump to definition.' )


  def _GetDefinitionsList( self, request_data ):
    buf, pos = self._GetCodeIntelBufAndPos( request_data )
    trg = buf.defn_trg_from_pos( pos )
    definitions = buf.defns_from_trg( trg, ctlr = _CaptureEvalController() )

    if not definitions:
      raise RuntimeError(
                  'Cannot follow nothing. Put your cursor on a valid name.' )
    return definitions


  def _BuildGoToResponse( self, definition_list ):
    defs = []
    for definition in definition_list:
	  # TODO: Prevent use for built in functions and Classes
	  defs.append(
	  responses.BuildGoToResponse( definition.path,
									definition.line,
									definition.scopestart ) )
    if len(defs) == 1:
      return defs[0]
    return defs


  def Shutdown(self):
    if self.mgr:
      self.mgr.finalize()


class _CaptureEvalController( EvalController ):
  def debug(self, msg, *args): logger.debug( msg, *args )
  def  info(self, msg, *args): logger.info( msg, *args )
  def  warn(self, msg, *args): logger.warn( msg, *args )
  def error(self, msg, *args): logger.error( msg, *args )
