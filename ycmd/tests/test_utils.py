# Copyright (C) 2013 Google Inc.
#               2015 ycmd contributors
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
from future import standard_library
from future.utils import iteritems
standard_library.install_aliases()
from builtins import *  # noqa

from future.utils import PY2
from hamcrest import contains_string, has_entry, has_entries
from mock import patch
from webtest import TestApp
import bottle
import contextlib

from ycmd import handlers, user_options_store
from ycmd.completers.completer import Completer
from ycmd.responses import BuildCompletionData
from ycmd.utils import OnMac, OnWindows
import ycm_core

try:
  from unittest import skipIf
except ImportError:
  from unittest2 import skipIf

Py2Only = skipIf( not PY2, 'Python 2 only' )
Py3Only = skipIf( PY2, 'Python 3 only' )
WindowsOnly = skipIf( not OnWindows(), 'Windows only' )
ClangOnly = skipIf( not ycm_core.HasClangSupport(),
                    'Only when Clang support available' )
MacOnly = skipIf( not OnMac(), 'Mac only' )


def BuildRequest( **kwargs ):
  filepath = kwargs[ 'filepath' ] if 'filepath' in kwargs else '/foo'
  contents = kwargs[ 'contents' ] if 'contents' in kwargs else ''
  filetype = kwargs[ 'filetype' ] if 'filetype' in kwargs else 'foo'

  request = {
    'line_num': 1,
    'column_num': 1,
    'filepath': filepath,
    'file_data': {
      filepath: {
        'contents': contents,
        'filetypes': [ filetype ]
      }
    }
  }

  for key, value in iteritems( kwargs ):
    if key in [ 'contents', 'filetype', 'filepath' ]:
      continue

    if key in request and isinstance( request[ key ], dict ):
      # allow updating the 'file_data' entry
      request[ key ].update( value )
    else:
      request[ key ] = value

  return request


def ErrorMatcher( cls, msg = None ):
  """ Returns a hamcrest matcher for a server exception response """
  entry = { 'exception': has_entry( 'TYPE', cls.__name__ ) }

  if msg:
    entry.update( { 'message': msg } )

  return has_entries( entry )


def CompletionEntryMatcher( insertion_text,
                            extra_menu_info = None,
                            extra_params = None ):
  match = { 'insertion_text': insertion_text }

  if extra_menu_info:
    match.update( { 'extra_menu_info': extra_menu_info } )

  if extra_params:
    match.update( extra_params )

  return has_entries( match )


def CompletionLocationMatcher( location_type, value ):
  return has_entry( 'extra_data',
                    has_entry( 'location',
                               has_entry( location_type, value ) ) )


def MessageMatcher( msg ):
  return has_entry( 'message', contains_string( msg ) )


def LocationMatcher( filepath, line_num, column_num ):
  return has_entries( {
    'line_num': line_num,
    'column_num': column_num,
    'filepath': filepath
  } )


def ChunkMatcher( replacement_text, start, end ):
  return has_entries( {
    'replacement_text': replacement_text,
    'range': has_entries( {
      'start': start,
      'end': end
    } )
  } )


@contextlib.contextmanager
def PatchCompleter( completer, filetype ):
  user_options = handlers._server_state._user_options
  with patch.dict( 'ycmd.handlers._server_state._filetype_completers',
                   { filetype: completer( user_options ) } ):
    yield


@contextlib.contextmanager
def UserOption( key, value ):
  try:
    current_options = dict( user_options_store.GetAll() )
    user_options = current_options.copy()
    user_options.update( { key: value } )
    handlers.UpdateUserOptions( user_options )
    yield
  finally:
    handlers.UpdateUserOptions( current_options )


def SetUpApp():
  bottle.debug( True )
  handlers.SetServerStateToDefaults()
  return TestApp( handlers.app )


class DummyCompleter( Completer ):
  def __init__( self, user_options ):
    super( DummyCompleter, self ).__init__( user_options )

  def SupportedFiletypes( self ):
    return []


  def ComputeCandidatesInner( self, request_data ):
    return [ BuildCompletionData( candidate )
             for candidate in self.CandidatesList() ]


  # This method is here for testing purpose, so it can be mocked during tests
  def CandidatesList( self ):
    return []
