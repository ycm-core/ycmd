# Copyright (C) 2015 ycmd contributors
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

from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from future import standard_library
standard_library.install_aliases()
from builtins import *  # noqa

from ..server_utils import SetUpPythonPath
SetUpPythonPath()
from webtest import TestApp
from .. import handlers
from ycmd import user_options_store
from hamcrest import has_entries, has_entry, contains_string
from .test_utils import BuildRequest
from mock import patch
import contextlib
import bottle
import os


class Handlers_test( object ):

  def __init__( self ):
    self._file = __file__


  def setUp( self ):
    bottle.debug( True )
    handlers.SetServerStateToDefaults()
    self._app = TestApp( handlers.app )


  @contextlib.contextmanager
  def PatchCompleter( self, completer, filetype ):
    user_options = handlers._server_state._user_options
    with patch.dict( 'ycmd.handlers._server_state._filetype_completers',
                     { filetype: completer( user_options ) } ):
      yield


  @contextlib.contextmanager
  def UserOption( self, key, value ):
    try:
      current_options = dict( user_options_store.GetAll() )
      user_options = current_options.copy()
      user_options.update( { key: value } )
      handlers.UpdateUserOptions( user_options )
      yield
    finally:
      handlers.UpdateUserOptions( current_options )


  @staticmethod
  def _BuildRequest( **kwargs ):
    return BuildRequest( **kwargs )


  @staticmethod
  def _CompletionEntryMatcher( insertion_text,
                               extra_menu_info = None,
                               extra_params = None ):
    match = { 'insertion_text': insertion_text }

    if extra_menu_info:
      match.update( { 'extra_menu_info': extra_menu_info } )

    if extra_params:
      match.update( extra_params )

    return has_entries( match )


  @staticmethod
  def _CompletionLocationMatcher( location_type, value ):
    return has_entry( 'extra_data',
                      has_entry( 'location',
                                 has_entry( location_type, value ) ) )


  @staticmethod
  def _ErrorMatcher( cls, msg = None ):
    """ Returns a hamcrest matcher for a server exception response """
    entry = { 'exception': has_entry( 'TYPE', cls.__name__ ) }

    if msg:
      entry.update( { 'message': msg } )

    return has_entries( entry )


  @staticmethod
  def _MessageMatcher( msg ):
    return has_entry( 'message', contains_string( msg ) )


  def _PathToTestFile( self, *args ):
    dir_of_current_script = os.path.dirname( os.path.abspath( self._file ) )
    return os.path.join( dir_of_current_script, 'testdata', *args )
