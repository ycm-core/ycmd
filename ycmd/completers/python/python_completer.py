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

from ycmd import extra_conf_store, responses
from ycmd.completers.completer import Completer, SignatureHelpAvailalability
from ycmd.utils import ( CodepointOffsetToByteOffset,
                         ExpandVariablesInPath,
                         FindExecutable,
                         LOGGER )

import difflib
import itertools
import jedi
import os
import parso
from threading import Lock


class PythonCompleter( Completer ):
  """
  A completer for the Python language using the Jedi semantic engine:
  https://jedi.readthedocs.org/en/latest/
  """

  def __init__( self, user_options ):
    super().__init__( user_options )
    self._jedi_lock = Lock()
    self._settings_for_file = {}
    self._environment_for_file = {}
    self._environment_for_interpreter_path = {}
    self._jedi_project_for_file = {}
    self.SetSignatureHelpTriggers( [ '(', ',' ] )


  def SupportedFiletypes( self ):
    return [ 'python' ]


  def OnFileReadyToParse( self, request_data ):
    # This is implicitly loading the extra conf file and caching the Jedi
    # environment and Python path.
    environment = self._EnvironmentForRequest( request_data )
    self._JediProjectForFile( request_data, environment )


  def _SettingsForRequest( self, request_data ):
    filepath = request_data[ 'filepath' ]
    client_data = request_data[ 'extra_conf_data' ]
    try:
      return self._settings_for_file[ filepath, client_data ]
    except KeyError:
      pass

    module = extra_conf_store.ModuleForSourceFile( filepath )
    settings = self._GetSettings( module, filepath, client_data )
    self._settings_for_file[ filepath, client_data ] = settings
    return settings


  def _GetSettings( self, module, filepath, client_data ):
    # We don't warn the user if no extra conf file is found.
    if module:
      if hasattr( module, 'Settings' ):
        settings = module.Settings( language = 'python',
                                    filename = filepath,
                                    client_data = client_data )
        if settings is not None:
          return settings
      LOGGER.debug( 'No Settings function defined in %s', module.__file__ )
    return {
      # NOTE: this option is only kept for backward compatibility. Setting the
      # Python interpreter path through the extra conf file is preferred.
      'interpreter_path': self.user_options[ 'python_binary_path' ]
    }


  def _EnvironmentForInterpreterPath( self, interpreter_path ):
    if interpreter_path:
      resolved_interpreter_path = FindExecutable(
        ExpandVariablesInPath( interpreter_path ) )
      if not resolved_interpreter_path:
        raise RuntimeError( 'Cannot find Python interpreter path '
                            f'{ interpreter_path }.' )
      interpreter_path = os.path.normpath( resolved_interpreter_path )

    try:
      return self._environment_for_interpreter_path[ interpreter_path ]
    except KeyError:
      pass

    # Assume paths specified by the user are safe.
    environment = ( jedi.get_default_environment() if not interpreter_path else
                    jedi.create_environment( interpreter_path, safe = False ) )
    self._environment_for_interpreter_path[ interpreter_path ] = environment
    return environment


  def _EnvironmentForRequest( self, request_data ):
    filepath = request_data[ 'filepath' ]
    client_data = request_data[ 'extra_conf_data' ]
    try:
      return self._environment_for_file[ filepath, client_data ]
    except KeyError:
      pass

    settings = self._SettingsForRequest( request_data )
    interpreter_path = settings.get( 'interpreter_path' )
    environment = self._EnvironmentForInterpreterPath( interpreter_path )
    self._environment_for_file[ filepath, client_data ] = environment
    return environment


  def _GetJediProject( self, request_data, environment ):
    settings = {
      'sys_path': []
    }
    settings.update( self._SettingsForRequest( request_data ) )
    settings[ 'interpreter_path' ] = environment.executable
    settings[ 'sys_path' ].extend( environment.get_sys_path() )

    filepath = request_data[ 'filepath' ]
    module = extra_conf_store.ModuleForSourceFile( filepath )
    # We don't warn the user if no extra conf file is found.
    if module:
      if hasattr( module, 'PythonSysPath' ):
        settings[ 'sys_path' ] = module.PythonSysPath( **settings )
      LOGGER.debug( 'No PythonSysPath function defined in %s', module.__file__ )

    project_directory = settings.get( 'project_directory' )
    if not project_directory:
      default_project = jedi.get_default_project(
        os.path.dirname( request_data[ 'filepath' ] ) )
      project_directory = default_project._path
    return jedi.Project( project_directory,
                         sys_path = settings[ 'sys_path' ],
                         environment_path = settings[ 'interpreter_path' ] )


  def _JediProjectForFile( self, request_data, environment ):
    filepath = request_data[ 'filepath' ]
    client_data = request_data[ 'extra_conf_data' ]
    try:
      return self._jedi_project_for_file[ filepath, client_data ]
    except KeyError:
      pass

    jedi_project = self._GetJediProject( request_data, environment )
    self._jedi_project_for_file[ filepath, client_data ] = jedi_project
    return jedi_project


  def _GetJediScript( self, request_data ):
    path = request_data[ 'filepath' ]
    source = request_data[ 'file_data' ][ path ][ 'contents' ]
    environment = self._EnvironmentForRequest( request_data )
    jedi_project = self._JediProjectForFile( request_data, environment )
    return jedi.Script( source,
                        path = path,
                        project = jedi_project,
                        environment = environment )


  # This method must be called under Jedi's lock.
  def _GetExtraData( self, completion ):
    if completion.module_path and completion.line and completion.column:
      return {
        'location': {
          'filepath': completion.module_path,
          'line_num': completion.line,
          'column_num': completion.column + 1
        }
      }
    return {}


  def ComputeCandidatesInner( self, request_data ):
    with self._jedi_lock:
      line = request_data[ 'line_num' ]
      # Jedi expects columns to start at 0, not 1, and for them to be Unicode
      # codepoint offsets.
      column = request_data[ 'start_codepoint' ] - 1
      completions = self._GetJediScript( request_data ).complete( line, column )
      return [ responses.BuildCompletionData(
        insertion_text = completion.complete,
        # We store the Completion object returned by Jedi in the extra_data
        # field to detail the candidates once the filtering is done.
        extra_data = completion
      ) for completion in completions ]


  def SignatureHelpAvailable( self ):
    return SignatureHelpAvailalability.AVAILABLE


  def ComputeSignaturesInner( self, request_data ):
    with self._jedi_lock:
      line = request_data[ 'line_num' ]
      # Jedi expects columns to start at 0, not 1, and for them to be Unicode
      # codepoint offsets.
      column = request_data[ 'start_codepoint' ] - 1
      signatures = self._GetJediScript( request_data ).get_signatures( line,
                                                                       column )
      # Sorting by the number or arguments makes the order stable for the tests
      # and isn't harmful. The order returned by jedi seems to be arbitrary.
      signatures.sort( key=lambda s: len( s.params ) )

      active_signature = 0
      active_parameter = 0
      for index, signature in enumerate( signatures ):
        if signature.index is not None:
          active_signature = index
          active_parameter = signature.index
          break

      def MakeSignature( s ):
        label = s.description + '( '
        parameters = []
        for index, p in enumerate( s.params ):
          # We remove 'param ' from the start of each parameter (hence the 6:)
          param = p.description[ 6: ]

          start = len( label )
          end = start + len( param )

          label += param
          if index < len( s.params ) - 1:
            label += ', '

          parameters.append( {
            'label': [ CodepointOffsetToByteOffset( label, start ),
                       CodepointOffsetToByteOffset( label, end ) ]
          } )

        label += ' )'

        return {
          'label': label,
          'parameters': parameters,
        }

      return {
        'activeSignature': active_signature,
        'activeParameter': active_parameter,
        'signatures': [ MakeSignature( s ) for s in signatures ],
      }


  def DetailCandidates( self, request_data, candidates ):
    with self._jedi_lock:
      for candidate in candidates:
        if isinstance( candidate[ 'extra_data' ], dict ):
          # This candidate is already detailed.
          continue
        completion = candidate[ 'extra_data' ]
        candidate[ 'extra_menu_info' ] = self._BuildTypeInfo( completion )
        candidate[ 'detailed_info' ] = completion.docstring()
        candidate[ 'kind' ] = completion.type
        candidate[ 'extra_data' ] = self._GetExtraData( completion )
    return candidates


  def GetSubcommandsMap( self ):
    return {
      'GoTo'           : ( lambda self, request_data, args:
                           self._GoToDefinition( request_data ) ),
      'GoToDefinition' : ( lambda self, request_data, args:
                           self._GoToDefinition( request_data ) ),
      'GoToDeclaration': ( lambda self, request_data, args:
                           self._GoToDefinition( request_data ) ),
      'GoToReferences' : ( lambda self, request_data, args:
                           self._GoToReferences( request_data ) ),
      'GoToSymbol'     : ( lambda self, request_data, args:
                           self._GoToSymbol( request_data, args ) ),
      'GoToType'       : ( lambda self, request_data, args:
                           self._GoToType( request_data ) ),
      'GetType'        : ( lambda self, request_data, args:
                           self._GetType( request_data ) ),
      'GetDoc'         : ( lambda self, request_data, args:
                           self._GetDoc( request_data ) ),
      'RefactorRename' : ( lambda self, request_data, args:
                           self._RefactorRename( request_data, args ) ),
    }


  def _BuildGoToResponse( self, definitions, request_data ):
    if len( definitions ) == 1:
      definition = definitions[ 0 ]
      column = 1
      if all( x is None for x in [ definition.column,
                                   definition.line,
                                   definition.module_path ] ):
        return None
      if definition.column is not None:
        column += definition.column
      filepath = definition.module_path or request_data[ 'filepath' ]
      return responses.BuildGoToResponse( filepath,
                                          definition.line,
                                          column,
                                          definition.description )

    gotos = []
    for definition in definitions:
      column = 1
      if all( x is None for x in [ definition.column,
                                   definition.line,
                                   definition.module_path ] ):
        continue
      if definition.column is not None:
        column += definition.column
      filepath = definition.module_path or request_data[ 'filepath' ]
      gotos.append( responses.BuildGoToResponse( filepath,
                                                 definition.line,
                                                 column,
                                                 definition.description ) )
    return gotos


  def _GoToType( self, request_data ):
    with self._jedi_lock:
      line = request_data[ 'line_num' ]
      # Jedi expects columns to start at 0, not 1, and for them to be Unicode
      # codepoint offsets.
      column = request_data[ 'start_codepoint' ] - 1
      script = self._GetJediScript( request_data )
      definitions = script.infer( line, column )
      if definitions:
        type_def = self._BuildGoToResponse( definitions, request_data )
        if type_def is not None:
          return type_def

    raise RuntimeError( 'Can\'t jump to type definition.' )


  def _GoToDefinition( self, request_data ):
    with self._jedi_lock:
      line = request_data[ 'line_num' ]
      # Jedi expects columns to start at 0, not 1, and for them to be Unicode
      # codepoint offsets.
      column = request_data[ 'start_codepoint' ] - 1
      script = self._GetJediScript( request_data )
      definitions = script.goto( line, column )
      if definitions:
        definitions = self._BuildGoToResponse( definitions, request_data )
        if definitions is not None:
          return definitions

    raise RuntimeError( 'Can\'t jump to definition.' )


  def _GoToReferences( self, request_data ):
    with self._jedi_lock:
      line = request_data[ 'line_num' ]
      # Jedi expects columns to start at 0, not 1, and for them to be Unicode
      # codepoint offsets.
      column = request_data[ 'start_codepoint' ] - 1
      definitions = self._GetJediScript( request_data ).get_references( line,
                                                                        column )
      if definitions:
        references = self._BuildGoToResponse( definitions, request_data )
        if references is not None:
          return references
    raise RuntimeError( 'Can\'t find references.' )


  def _GoToSymbol( self, request_data, args ):
    if len( args ) < 1:
      raise RuntimeError( 'Must specify something to search for' )

    query = args[ 0 ]

    # Jedi docs say:
    #   Searches a name in the whole project. If the project is very big, at
    #   some point Jedi will stop searching. However it’s also very much
    #   recommended to not exhaust the generator.
    MAX_RESULTS = self.user_options[ 'max_num_candidates' ]
    if MAX_RESULTS < 0:
      MAX_RESULTS = 100

    with self._jedi_lock:
      environent = self._EnvironmentForRequest( request_data )
      project = self._JediProjectForFile( request_data, environent )

      definitions = list( itertools.islice( project.complete_search( query ),
                                            MAX_RESULTS ) )
      if definitions:
        definitions = self._BuildGoToResponse( definitions, request_data )
        if definitions is not None:
          return definitions

    raise RuntimeError( 'Symbol not found' )


  # This method must be called under Jedi's lock.
  def _BuildTypeInfo( self, definition ):
    type_info = definition.description
    # Jedi doesn't return the signature in the description. Build the signature
    # from the params field.
    try:
      # Remove the "param " prefix from the description.
      parameters = definition.get_signatures()[ 0 ].params
      type_info += '(' + ', '.join(
        [ param.description[ 6: ] for param in parameters ] ) + ')'
    except IndexError:
      pass
    return type_info


  def _GetType( self, request_data ):
    with self._jedi_lock:
      line = request_data[ 'line_num' ]
      # Jedi expects columns to start at 0, not 1, and for them to be Unicode
      # codepoint offsets.
      column = request_data[ 'start_codepoint' ] - 1
      definitions = self._GetJediScript( request_data ).infer( line, column )
      type_info = [ self._BuildTypeInfo( definition )
                    for definition in definitions ]
    type_info = ', '.join( type_info )
    if type_info:
      return responses.BuildDisplayMessageResponse( type_info )
    raise RuntimeError( 'No type information available.' )


  def _GetDoc( self, request_data ):
    with self._jedi_lock:
      line = request_data[ 'line_num' ]
      # Jedi expects columns to start at 0, not 1, and for them to be Unicode
      # codepoint offsets.
      column = request_data[ 'start_codepoint' ] - 1
      definitions = self._GetJediScript( request_data ).goto( line, column )
      documentation = [
        definition.docstring().strip() for definition in definitions ]
    documentation = '\n---\n'.join( [ d for d in documentation if d ] )
    if documentation:
      return responses.BuildDetailedInfoResponse( documentation )
    raise RuntimeError( 'No documentation available.' )


  def _RefactorRename( self, request_data, args ):
    if len( args ) < 1:
      raise RuntimeError( 'Must specify a new name' )

    new_name = args[ 0 ]
    with self._jedi_lock:
      refactoring = self._GetJediScript( request_data ).rename(
        line = request_data[ 'line_num' ],
        column = request_data[ 'column_codepoint' ] - 1,
        new_name = new_name )

      return responses.BuildFixItResponse( [
        _RefactoringToFixIt( refactoring )
      ] )

  # Jedi has the following refactorings:
  #  - renmae (RefactorRename)
  #  - inline variable
  #  - extract variable (requires argument)
  #  - extract function (requires argument)
  #
  # We could add inline variable via FixIt, but for the others we have no way to
  # ask for the argument on "resolve" of the FixIt. We could add
  # Refactor Inline ... but that would be inconsistent.


  def DebugInfo( self, request_data ):
    environment = self._EnvironmentForRequest( request_data )

    python_interpreter = responses.DebugInfoItem(
      key = 'Python interpreter',
      value = environment.executable )

    python_root = responses.DebugInfoItem(
      key = 'Python root',
      value = str( self._JediProjectForFile( request_data,
                                             environment )._path ) )

    python_path = responses.DebugInfoItem(
      key = 'Python path',
      value = str( self._JediProjectForFile( request_data,
                                             environment )._sys_path ) )

    python_version = responses.DebugInfoItem(
      key = 'Python version',
      value = '.'.join( str( item ) for item in environment.version_info ) )

    jedi_version = responses.DebugInfoItem(
      key = 'Jedi version',
      value = jedi.__version__ )

    parso_version = responses.DebugInfoItem(
      key = 'Parso version',
      value = parso.__version__ )

    return responses.BuildDebugInfoResponse( name = 'Python',
                                             items = [ python_interpreter,
                                                       python_root,
                                                       python_path,
                                                       python_version,
                                                       jedi_version,
                                                       parso_version ] )


def _RefactoringToFixIt( refactoring ):
  """Converts a Jedi Refactoring instance to a single responses.FixIt."""

  # FIXME: refactorings can rename files (apparently). ycmd API doesn't have any
  # interface for that, so we just ignore them.
  changes = refactoring.get_changed_files()
  chunks = []

  # We sort the files to ensure the tests are stable
  for filename in sorted( changes.keys() ):
    changed_file = changes[ filename ]

    # NOTE: This is an internal API. We _could_ use GetFileContents( filename )
    # here, but using Jedi's representation means that it is always consistent
    # with get_new_code()
    old_text = changed_file._module_node.get_code()
    new_text = changed_file.get_new_code()

    # Cache the offsets of all the newlines in the file. These are used to
    # calculate the line/column values from the offsets retuned by the diff
    # scanner
    newlines = [ i for i, c in enumerate( old_text ) if c == '\n' ]
    newlines.append( len( old_text ) )

    sequence_matcher = difflib.SequenceMatcher( a = old_text,
                                                b = new_text,
                                                autojunk = False )

    for ( operation,
          old_start, old_end,
          new_start, new_end ) in sequence_matcher.get_opcodes():
      # Tag of equal means the range is identical, so nothing to do.
      if operation == 'equal':
        continue

      # operation can be 'insert', 'replace' or 'delete', the offsets actually
      # already cover that in our FixIt API (a delete has an empty new_text, an
      # insert has an empty range), so we just encode the line/column offset and
      # the replacement text extracted from new_text
      chunks.append( responses.FixItChunk(
        new_text[ new_start : new_end ],
        # FIXME: new_end must be equal to or after new_start, so we should make
        # OffsetToPosition take 2 offsets and return them rather than repeating
        # work
        responses.Range( _OffsetToPosition( old_start,
                                            filename,
                                            old_text,
                                            newlines ),
                         _OffsetToPosition( old_end,
                                            filename,
                                            old_text,
                                            newlines ) )
      ) )

  return responses.FixIt( responses.Location( 1, 1, 'none' ),
                          chunks,
                          '',
                          kind = responses.FixIt.Kind.REFACTOR )


def _OffsetToPosition( offset, filename, text, newlines ):
  """Convert the 0-based codepoint offset |offset| to a position (line/col) in
  |text|. |filename| is the full path of the file containing |text| and
  |newlines| is a cache of the 0-based character offsets of all the \n
  characters in |text| (plus one extra). Returns responses.Position."""

  for index, newline in enumerate( newlines ):
    if newline >= offset:
      start_of_line = newlines[ index - 1 ] + 1 if index > 0 else 0
      column = offset - start_of_line
      line_value = text[ start_of_line : newline ]
      return responses.Location( index + 1,
                                 CodepointOffsetToByteOffset( line_value,
                                                              column + 1 ),
                                 filename )

  # Invalid position - it's outside of the text. Just return the last
  # position in the text. This is an internal error.
  LOGGER.error( "Invalid offset %s in file %s with text %s and newlines %s",
                offset,
                filename,
                text,
                newlines )
  raise RuntimeError( "Invalid file offset in diff" )
