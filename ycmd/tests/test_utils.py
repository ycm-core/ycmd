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

import os
import time
from .. import handlers
from ycmd import user_options_store
from ycmd.utils import OnTravis
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
    request[ key ] = value

  return request


def Setup():
  handlers.SetServerStateToDefaults()


def ChangeSpecificOptions( options ):
  current_options = dict( user_options_store.GetAll() )
  current_options.update( options )
  handlers.UpdateUserOptions( current_options )


def PathToTestDataDir():
  dir_of_current_script = os.path.dirname( os.path.abspath( __file__ ) )
  return os.path.join( dir_of_current_script, 'testdata' )


def PathToTestFile( *args ):
  return os.path.join( PathToTestDataDir(), *args )


def StopOmniSharpServer( app, filename ):
  app.post_json( '/run_completer_command',
                 BuildRequest( completer_target = 'filetype_default',
                               command_arguments = ['StopServer'],
                               filepath = filename,
                               filetype = 'cs' ) )


def WaitUntilOmniSharpServerReady( app, filename ):
  retries = 100;
  success = False;

  # If running on Travis CI, keep trying forever. Travis will kill the worker
  # after 10 mins if nothing happens.
  while retries > 0 or OnTravis():
    result = app.get( '/ready', { 'subserver': 'cs' } ).json
    if result:
      success = True;
      break
    request = BuildRequest( completer_target = 'filetype_default',
                            command_arguments = [ 'ServerTerminated' ],
                            filepath = filename,
                            filetype = 'cs' )
    result = app.post_json( '/run_completer_command', request ).json
    if result:
      raise RuntimeError( "OmniSharp failed during startup." )
    time.sleep( 0.2 )
    retries = retries - 1

  if not success:
    raise RuntimeError( "Timeout waiting for OmniSharpServer" )


def StopGoCodeServer( app ):
  app.post_json( '/run_completer_command',
                 BuildRequest( completer_target = 'filetype_default',
                               command_arguments = ['StopServer'],
                               filetype = 'go' ) )


def ErrorMatcher( cls, msg ):
  """ Returns a hamcrest matcher for a server exception response """
  return has_entries( {
    'exception' : has_entry( 'TYPE', cls.__name__ ),
    'message': msg,
  } )
