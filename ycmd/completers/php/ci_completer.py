#/usr/bin/env python
# Copyright (C) 2015 Neo Mofoka <neo@jeteon.com>

from os.path import abspath, dirname, join
import sys

from ycmd.utils import ToUtf8IfNeeded
from ycmd.completers.completer import Completer
from ycmd import responses

# Add CodeIntel to path. Assume is residing in third party
REPO_ROOT = dirname(dirname(dirname(abspath(__file__))))
sys.path.insert(0, join(REPO_ROOT, 'third_party', 'ci2', 'codeintel'))

from codeintel2.manager import Manager

# Remove the path we just added after importing the files we need
sys.path.remove(0)

class CodeIntelCompleter( Completer ):
  """
  A Completer that uses the Code Intel code intelligence engine.
  https://jedi.readthedocs.org/en/latest/
  """

  mgr = None

  def __init__( self, user_options ):
    super( CodeIntelCompleter, self ).__init__( user_options )
    
    # Initialize CodeIntel Manager on the class
    if CodeIntelCompleter.mgr is None:
	  CodeIntelCompleter.mgr = Manager()
	  self.mgr.upgrade()
      self.mgr.initialize()

  def SupportedFiletypes( self ):
    """ Just PHP (for now) """
    return [ 'php' ]


  def _GetJediScript( self, request_data ):
      filename = request_data[ 'filepath' ]
      contents = request_data[ 'file_data' ][ filename ][ 'contents' ]
      line = request_data[ 'line_num' ]
      # Jedi expects columns to start at 0, not 1
      column = request_data[ 'column_num' ] - 1

      return jedi.Script( contents, line, column, filename )


  def ComputeCandidatesInner( self, request_data ):
	
	filename = request_data[ 'filepath' ]
	contents = request_data[ 'file_data' ][ filename ][ 'contents' ]
	line = request_data[ 'line_num' ]
	column = request_data[ 'column_num' ]
	
	buf = self.mgr.buf_from_path( filename )
	
	# Calculate position from row, column
	pos = sum([len(l) + 1 for l in contents.split('\n')[:(line-1)]]) + column - 1;

	trg = buf.trg_from_pos(pos)
	
	if trg is None:
		return []
	
	cplns = buf.cplns_from_trg(trg)
	return [ responses.BuildCompletionData( 
				ToUtf8IfNeeded( cpln[1] ),
				kind = ToUtf8IfNeeded( cpln[0] ))
			for cpln in cplns ]
	
    script = self._GetJediScript( request_data )
    return [ responses.BuildCompletionData(
                ToUtf8IfNeeded( completion.name ),
                ToUtf8IfNeeded( completion.description ),
                ToUtf8IfNeeded( completion.docstring() ) )
             for completion in script.completions() ]

  def DefinedSubcommands( self ):
    return [ 'GoToDefinition',
             'GoToDeclaration',
             'GoTo' ]


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
  
  def Shutdown():
    if self.mgr:
	  self.mgr.finalize()

