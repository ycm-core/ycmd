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
from time import time

from ycmd.utils import ToUtf8IfNeeded
from ycmd.completers.completer import Completer
from ycmd import responses

# Add CodeIntel to path. Assume is residing in third party
REPO_ROOT = dirname( dirname( dirname( dirname( abspath( __file__ ) ) ) ) )
CI_BASE = join( REPO_ROOT, 'third_party', 'codeintel' )
CI_DIR = join( CI_BASE, 'codeintel' )
sys.path.insert( 0, CI_DIR )
sys.path.insert( 0, CI_BASE )

from codeintel2.manager import Manager
from codeintel2.environment import SimplePrefsEnvironment

# Set up logger
logger = logging.getLogger(__name__)

#fh = logging.FileHandler('/tmp/cicompleter.log', 'a')
#fh.setLevel(logging.DEBUG)

#formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

#fh.setFormatter(formatter)
#logger.addHandler(fh)

#logger.addHandler(fh)
logger.setLevel(logging.ERROR)

class CodeIntelCompleter( Completer ):
  """
  A Completer that uses the Code Intel code intelligence engine.
  """

  mgr = None

  def __init__( self, user_options ):
    super( CodeIntelCompleter, self ).__init__( user_options )
    
    # Initialize CodeIntel Manager on the class
    if CodeIntelCompleter.mgr is None:
      env = SimplePrefsEnvironment()
	  
      CodeIntelCompleter.mgr = Manager( 
		  db_base_dir = join( CI_DIR, 'db' ),
		  extra_module_dirs = [ join( CI_DIR, 'codeintel2' ), ],
		  db_import_everything_langs = None,
		  db_catalog_dirs = [],
		  env = env
	  )
      self.mgr.upgrade()
      self.mgr.initialize()
      logger.debug('Manager initialized: %s' % user_options)


  def SupportedFiletypes( self ):
    """ Just PHP (for now) """
    logger.debug('SupportedFiletypes called')
    return [ 'php' ]


  def ComputeCandidatesInner( self, request_data ):
	
	logger.debug('ComputeCandidatesInner called')
	
	filename = request_data[ 'filepath' ]
	contents = request_data[ 'file_data' ][ filename ][ 'contents' ]
	line = request_data[ 'line_num' ]
	column = request_data[ 'column_num' ]
	
	#buf = self.mgr.buf_from_path( filename, 'php' )
	buf = self.mgr.buf_from_content(contents, 'PHP', path = filename, env = self.mgr.env )
	logger.debug('Buffer obtained from filename: "%s"' % buf)
	
	# Calculate position from row, column
	pos = sum([len(l) + 1 for l in contents.split('\n')[:(line-1)]]) + column - 1;
	logger.debug('Trigger pos: "%i"' % pos)

	trg = buf.preceding_trg_from_pos(pos, pos)
	logger.debug('Trigger from buffer: "%s"' % trg)
	
	if trg is None:
		return []
	
	pre = time()
	
	cplns = buf.cplns_from_trg(trg)
	logger.debug('Raw completions [%.2fs]: "%s"' % (time() - pre, cplns))
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
    return []

  def Shutdown(self):
    if self.mgr:
	  self.mgr.finalize()
