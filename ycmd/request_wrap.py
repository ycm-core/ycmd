#!/usr/bin/env python
#
# Copyright (C) 2014 Google Inc.
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

from ycmd.utils import ToUnicodeIfNeeded, ToUtf8IfNeeded
from ycmd.identifier_utils import StartOfLongestIdentifierEndingAtIndex
from ycmd.request_validation import EnsureRequestValid

# TODO: Change the custom computed (and other) keys to be actual properties on
# the object.
class RequestWrap( object ):
  def __init__( self, request, validate = True ):
    if validate:
      EnsureRequestValid( request )
    self._request = request
    self._computed_key = {
      'line_value': self._CurrentLine,
      'start_column': self.CompletionStartColumn,
      'query': self._Query,
      'filetypes': self._Filetypes,
    }
    self._cached_computed = {}


  def __getitem__( self, key ):
    if key in self._cached_computed:
      return self._cached_computed[ key ]
    if key in self._computed_key:
      value = self._computed_key[ key ]()
      self._cached_computed[ key ] = value
      return value
    return self._request[ key ]


  def __contains__( self, key ):
    return key in self._computed_key or key in self._request


  def get( self, key, default = None ):
    try:
      return self[ key ]
    except KeyError:
      return default


  def _CurrentLine( self ):
    current_file = self._request[ 'filepath' ]
    contents = self._request[ 'file_data' ][ current_file ][ 'contents' ]

    # Handling ''.splitlines() returning [] instead of ['']
    if contents is not None and len( contents ) == 0:
      return ''
    return contents.splitlines()[ self._request[ 'line_num' ] - 1 ]


  def CompletionStartColumn( self ):
    try:
      filetype = self[ 'filetypes' ][ 0 ]
    except (KeyError, IndexError):
      filetype = None
    return CompletionStartColumn( self[ 'line_value' ],
                                  self[ 'column_num' ],
                                  filetype )


  def _Query( self ):
    return self[ 'line_value' ][
             self[ 'start_column' ] - 1 : self[ 'column_num' ] - 1 ]


  def _Filetypes( self ):
    path = self[ 'filepath' ]
    return self[ 'file_data' ][ path ][ 'filetypes' ]


def CompletionStartColumn( line_value, column_num, filetype ):
  """Returns the 1-based index where the completion query should start. So if
  the user enters:
    foo.bar^
  with the cursor being at the location of the caret (so the character *AFTER*
  'r'), then the starting column would be the index of the letter 'b'."""
  # NOTE: column_num and other numbers on the wire are byte indices, but we need
  # to walk codepoints for identifier checks.

  utf8_line_value = ToUtf8IfNeeded( line_value )
  unicode_line_value = ToUnicodeIfNeeded( line_value )
  codepoint_column_num = len(
      unicode( utf8_line_value[ : column_num -1 ], 'utf8' ) ) + 1

  # -1 and then +1 to account for difference betwen 0-based and 1-based
  # indices/columns
  codepoint_start_column = StartOfLongestIdentifierEndingAtIndex(
      unicode_line_value, codepoint_column_num - 1, filetype ) + 1

  return len(
      unicode_line_value[ : codepoint_start_column - 1 ].encode( 'utf8' ) ) + 1


