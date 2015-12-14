#!/usr/bin/env python
#
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
