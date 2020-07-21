# Copyright (C) 2020 ycmd contributors
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

from ycmd.responses import ServerError


# Throws an exception if request doesn't have all the required fields.
# TODO: Accept a request_type param so that we can also verify missing
# command_arguments and completer_target fields if necessary.
def EnsureRequestValid( request_json ):
  required_fields = { 'line_num', 'column_num', 'filepath', 'file_data' }
  missing = { x for x in required_fields if x not in request_json }

  if 'filepath' not in missing and 'file_data' not in missing:
    missing.update( _MissingFieldsForFileData( request_json ) )
  if not missing:
    return True
  message = '\n'.join( _FieldMissingMessage( field ) for field in missing )
  raise ServerError( message )


def _FieldMissingMessage( field ):
  return f'Request missing required field: { field }'


def _FilepathInFileDataSpec( request_json ):
  filepath = request_json[ 'filepath' ]
  return f'file_data[ "{ filepath }" ]'


def _SingleFileDataFieldSpec( request_json, field ):
  return f'{ _FilepathInFileDataSpec( request_json ) }[ "{ field }" ]'


def _MissingFieldsForFileData( request_json ):
  missing = set()
  data_for_file = request_json[ 'file_data' ].get( request_json[ 'filepath' ] )
  if data_for_file:
    required_data = [ 'filetypes', 'contents' ]
    for required in required_data:
      if required not in data_for_file:
        missing.add( _SingleFileDataFieldSpec( request_json, required ) )
    filetypes = data_for_file.get( 'filetypes', [] )
    if not filetypes:
      missing.add(
        f'{ _SingleFileDataFieldSpec( request_json, "filetypes" ) }[ 0 ]' )
  else:
    missing.add( _FilepathInFileDataSpec( request_json ) )
  return missing
