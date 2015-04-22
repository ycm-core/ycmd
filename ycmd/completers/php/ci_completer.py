#/usr/bin/env python
# Copyright (C) 2015 Neo Mofoka <neo@jeteon.com>

import logging
from os.path import abspath, dirname, join
import sys

from ycmd.utils import ToUtf8IfNeeded
from ycmd.completers.completer import Completer
from ycmd import responses

# Add CodeIntel to path. Assume is residing in third party
REPO_ROOT = dirname( dirname( dirname( dirname( abspath( __file__ ) ) ) ) )
CI_BASE = join( REPO_ROOT, 'third_party', 'ci2')
CI_DIR = join( CI_BASE, 'codeintel' )
sys.path.insert( 0, CI_DIR )
sys.path.insert( 0, CI_BASE )

from codeintel2.manager import Manager
from codeintel2.environment import SimplePrefsEnvironment

# Remove the path we just added after importing the files we need
#sys.path.remove( CI_DIR )
#sys.path.remove( CI_BASE )

# Set up logger
logger = logging.getLogger(__name__)

fh = logging.FileHandler('/tmp/cicompleter.log', 'a')
fh.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

fh.setFormatter(formatter)
logger.addHandler(fh)

logger.addHandler(fh)
logger.setLevel(logging.DEBUG)

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


  #def _GetJediScript( self, request_data ):
      #filename = request_data[ 'filepath' ]
      #contents = request_data[ 'file_data' ][ filename ][ 'contents' ]
      #line = request_data[ 'line_num' ]
      ## Jedi expects columns to start at 0, not 1
      #column = request_data[ 'column_num' ] - 1

      #return jedi.Script( contents, line, column, filename )


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
	pos = sum([len(l) + 1 for l in contents.split('\n')[:(line-1)]]) + column;
	logger.debug('Trigger pos: "%i"' % pos)

	trg = buf.trg_from_pos(pos)
	logger.debug('Trigger from buffer: "%s"' % trg)
	
	if trg is None:
		return []
	
	cplns = buf.cplns_from_trg(trg)
	logger.debug('Raw completions: "%s"' % cplns)
	return [ responses.BuildCompletionData( 
				ToUtf8IfNeeded( cpln[1] ),
				kind = ToUtf8IfNeeded( cpln[0] ))
			for cpln in cplns ]

  def ShouldUseNowInner( self, request_data ):
	res = super( CodeIntelCompleter, self ).ShouldUseNowInner( request_data )
	logger.debug('ShouldUseNowInner called. Returns %s' % res)
	# TODO: Fix this to check request data
	return True

  def DefinedSubcommands( self ):
    return []


  def OnUserCommand( self, arguments, request_data ):
    if not arguments:
      raise ValueError( self.UserCommandsHelpMessage() )

    command = arguments[ 0 ]
    if command == 'GoToDefinition':
      return self._GoToDefinition( request_data )
    elif command == 'GoToDeclaration':
      return self._GoToDeclaration( request_data )
    elif command == 'GoTo':
      return self._GoTo( request_data )
    raise ValueError( self.UserCommandsHelpMessage() )


  def _GoToDefinition( self, request_data ):
    definitions = self._GetDefinitionsList( request_data )
    if definitions:
      return self._BuildGoToResponse( definitions )
    else:
      raise RuntimeError( 'Can\'t jump to definition.' )


  def _GoToDeclaration( self, request_data ):
    definitions = self._GetDefinitionsList( request_data, declaration = True )
    if definitions:
      return self._BuildGoToResponse( definitions )
    else:
      raise RuntimeError( 'Can\'t jump to declaration.' )


  def _GoTo( self, request_data ):
    definitions = ( self._GetDefinitionsList( request_data ) or
        self._GetDefinitionsList( request_data, declaration = True ) )
    if definitions:
      return self._BuildGoToResponse( definitions )
    else:
      raise RuntimeError( 'Can\'t jump to definition or declaration.' )


  def _GetDefinitionsList( self, request_data, declaration = False ):
    definitions = []
    script = self._GetJediScript( request_data )
    try:
      if declaration:
        definitions = script.goto_assignments()
      else:
        definitions = script.goto_definitions()
    except jedi.NotFoundError:
      raise RuntimeError(
                  'Cannot follow nothing. Put your cursor on a valid name.' )

    return definitions


  def _BuildGoToResponse( self, definition_list ):
    if len( definition_list ) == 1:
      definition = definition_list[ 0 ]
      if definition.in_builtin_module():
        if definition.is_keyword:
          raise RuntimeError(
                  'Cannot get the definition of Python keywords.' )
        else:
          raise RuntimeError( 'Builtin modules cannot be displayed.' )
      else:
        return responses.BuildGoToResponse( definition.module_path,
                                            definition.line,
                                            definition.column + 1 )
    else:
      # multiple definitions
      defs = []
      for definition in definition_list:
        if definition.in_builtin_module():
          defs.append( responses.BuildDescriptionOnlyGoToResponse(
                       'Builtin ' + definition.description ) )
        else:
          defs.append(
            responses.BuildGoToResponse( definition.module_path,
                                         definition.line,
                                         definition.column + 1,
                                         definition.description ) )
      return defs
  
  def Shutdown(self):
    if self.mgr:
	  self.mgr.finalize()


if __name__ == '__main__':
	completer = CodeIntelCompleter({
		'min_num_of_chars_for_completion' : 2,
		'auto_trigger' : False
	})