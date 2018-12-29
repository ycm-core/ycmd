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

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa

from ycmd import extra_conf_store, responses
from ycmd.completers.completer import Completer
from ycmd.utils import ExpandVariablesInPath, FindExecutable, LOGGER

import os
import jedi
import parso
from threading import Lock


class PythonCompleter( Completer ):
  """
  A completer for the Python language using the Jedi semantic engine:
  https://jedi.readthedocs.org/en/latest/
  """

  def __init__( self, user_options ):
    super( PythonCompleter, self ).__init__( user_options )
    self._jedi_lock = Lock()
    self._settings_for_file = {}
    self._environment_for_file = {}
    self._environment_for_interpreter_path = {}
    self._sys_path_for_file = {}


  def SupportedFiletypes( self ):
    return [ 'python' ]


  def OnFileReadyToParse( self, request_data ):
    # This is implicitly loading the extra conf file and caching the Jedi
    # environment and Python path.
    environment = self._EnvironmentForRequest( request_data )
    self._SysPathForFile( request_data, environment )


  def _SettingsForRequest( self, request_data ):
    filepath = request_data[ 'filepath' ]
    client_data = request_data[ 'extra_conf_data' ]
    try:
      return self._settings_for_file[ filepath, client_data ]
    except KeyError:
      pass

    module = extra_conf_store.ModuleForSourceFile( filepath )
    settings = self._GetSettings( module, client_data )
    self._settings_for_file[ filepath, client_data ] = settings
    return settings


  def _GetSettings( self, module, client_data ):
    # We don't warn the user if no extra conf file is found.
    if module:
      if hasattr( module, 'Settings' ):
        settings = module.Settings( language = 'python',
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
        raise RuntimeError( 'Cannot find Python interpreter path {}.'.format(
          interpreter_path ) )
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


  def _GetSysPath( self, request_data, environment ):
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
        return module.PythonSysPath( **settings )
      LOGGER.debug( 'No PythonSysPath function defined in %s', module.__file__ )
    return settings[ 'sys_path' ]


  def _SysPathForFile( self, request_data, environment ):
    filepath = request_data[ 'filepath' ]
    client_data = request_data[ 'extra_conf_data' ]
    try:
      return self._sys_path_for_file[ filepath, client_data ]
    except KeyError:
      pass

    sys_path = self._GetSysPath( request_data, environment )
    self._sys_path_for_file[ filepath, client_data ] = sys_path
    return sys_path


  def _GetJediScript( self, request_data ):
    path = request_data[ 'filepath' ]
    source = request_data[ 'file_data' ][ path ][ 'contents' ]
    line = request_data[ 'line_num' ]
    # Jedi expects columns to start at 0, not 1, and for them to be Unicode
    # codepoint offsets.
    col = request_data[ 'start_codepoint' ] - 1
    environment = self._EnvironmentForRequest( request_data )
    sys_path = self._SysPathForFile( request_data, environment )
    return jedi.Script( source,
                        line,
                        col,
                        path,
                        sys_path = sys_path,
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
      return [ responses.BuildCompletionData(
        insertion_text = completion.name,
        # We store the Completion object returned by Jedi in the extra_data
        # field to detail the candidates once the filtering is done.
        extra_data = completion
      ) for completion in self._GetJediScript( request_data ).completions() ]


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
      'GoToDefinition' : ( lambda self, request_data, args:
                           self._GoToDefinition( request_data ) ),
      'GoToDeclaration': ( lambda self, request_data, args:
                           self._GoToDeclaration( request_data ) ),
      'GoTo'           : ( lambda self, request_data, args:
                           self._GoTo( request_data ) ),
      'GoToReferences' : ( lambda self, request_data, args:
                           self._GoToReferences( request_data ) ),
      'GetType'        : ( lambda self, request_data, args:
                           self._GetType( request_data ) ),
      'GetDoc'         : ( lambda self, request_data, args:
                           self._GetDoc( request_data ) )
    }


  def _GoToDefinition( self, request_data ):
    with self._jedi_lock:
      definitions = self._GetJediScript( request_data ).goto_definitions()
      if definitions:
        return self._BuildGoToResponse( definitions )
    raise RuntimeError( 'Can\'t jump to definition.' )


  def _GoToDeclaration( self, request_data ):
    with self._jedi_lock:
      definitions = self._GetJediScript( request_data ).goto_assignments()
      if definitions:
        return self._BuildGoToResponse( definitions )
    raise RuntimeError( 'Can\'t jump to declaration.' )


  def _GoTo( self, request_data ):
    try:
      return self._GoToDefinition( request_data )
    except Exception:
      LOGGER.exception( 'Failed to jump to definition' )

    try:
      return self._GoToDeclaration( request_data )
    except Exception:
      LOGGER.exception( 'Failed to jump to declaration' )
      raise RuntimeError( 'Can\'t jump to definition or declaration.' )


  # This method must be called under Jedi's lock.
  def _BuildTypeInfo( self, definition ):
    type_info = definition.description
    # Jedi doesn't return the signature in the description. Build the signature
    # from the params field.
    try:
      # Remove the "param " prefix from the description.
      type_info += '(' + ', '.join(
        [ param.description[ 6: ] for param in definition.params ] ) + ')'
    except AttributeError:
      pass
    return type_info


  def _GetType( self, request_data ):
    with self._jedi_lock:
      definitions = self._GetJediScript( request_data ).goto_definitions()
      type_info = [ self._BuildTypeInfo( definition )
                    for definition in definitions ]
    type_info = ', '.join( type_info )
    if type_info:
      return responses.BuildDisplayMessageResponse( type_info )
    raise RuntimeError( 'No type information available.' )


  def _GetDoc( self, request_data ):
    with self._jedi_lock:
      definitions = self._GetJediScript( request_data ).goto_definitions()
      documentation = [ definition.docstring() for definition in definitions ]
    documentation = '\n---\n'.join( documentation )
    if documentation:
      return responses.BuildDetailedInfoResponse( documentation )
    raise RuntimeError( 'No documentation available.' )


  def _GoToReferences( self, request_data ):
    with self._jedi_lock:
      definitions = self._GetJediScript( request_data ).usages()
      if definitions:
        return self._BuildGoToResponse( definitions )
    raise RuntimeError( 'Can\'t find references.' )


  def _BuildGoToResponse( self, definitions ):
    if len( definitions ) == 1:
      definition = definitions[ 0 ]
      if definition.in_builtin_module():
        raise RuntimeError( 'Can\'t jump to builtin module.' )
      return responses.BuildGoToResponse( definition.module_path,
                                          definition.line,
                                          definition.column + 1 )

    gotos = []
    for definition in definitions:
      if definition.in_builtin_module():
        gotos.append( responses.BuildDescriptionOnlyGoToResponse(
          'Builtin {}'.format( definition.description ) ) )
      else:
        gotos.append( responses.BuildGoToResponse( definition.module_path,
                                                   definition.line,
                                                   definition.column + 1,
                                                   definition.description ) )
    return gotos


  def DebugInfo( self, request_data ):
    environment = self._EnvironmentForRequest( request_data )

    python_interpreter = responses.DebugInfoItem(
      key = 'Python interpreter',
      value = environment.executable )

    python_path = responses.DebugInfoItem(
      key = 'Python path',
      value = str( self._SysPathForFile( request_data, environment ) ) )

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
                                                       python_path,
                                                       python_version,
                                                       jedi_version,
                                                       parso_version ] )
