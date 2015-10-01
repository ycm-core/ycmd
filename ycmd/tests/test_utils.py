#!/usr/bin/env python
#
# Copyright (C) 2013  Google Inc.
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

from .. import handlers
from ycmd import user_options_store
from hamcrest import has_entries, has_entry


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

  for key, value in kwargs.iteritems():
    if key in [ 'contents', 'filetype', 'filepath' ]:
      continue

    if key in request and isinstance( request[ key ], dict ):
      # allow updating the 'file_data' entry
      request[ key ].update( value )
    else:
      request[ key ] = value

  return request


def CompletionEntryMatcher( insertion_text, extra_menu_info = None ):
  match = { 'insertion_text': insertion_text }
  if extra_menu_info:
    match.update( { 'extra_menu_info': extra_menu_info } )
  return has_entries( match )


def CompletionLocationMatcher( location_type, value ):
  return has_entry( 'extra_data',
                    has_entry( 'location',
                               has_entry( location_type, value ) ) )


def Setup():
  handlers.SetServerStateToDefaults()


def ChangeSpecificOptions( options ):
  current_options = dict( user_options_store.GetAll() )
  current_options.update( options )
  handlers.UpdateUserOptions( current_options )


def ErrorMatcher( cls, msg ):
  """ Returns a hamcrest matcher for a server exception response """
  return has_entries( {
    'exception': has_entry( 'TYPE', cls.__name__ ),
    'message': msg,
  } )
