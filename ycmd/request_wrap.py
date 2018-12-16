# encoding: utf8
#
# Copyright (C) 2014-2018 ycmd contributors
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

from future.utils import iteritems

from ycmd.utils import ( ByteOffsetToCodepointOffset,
                         CodepointOffsetToByteOffset,
                         HashableDict,
                         LOGGER,
                         ToUnicode,
                         ToBytes,
                         SplitLines )
from ycmd.identifier_utils import StartOfLongestIdentifierEndingAtIndex
from ycmd.request_validation import EnsureRequestValid


# TODO: Change the custom computed (and other) keys to be actual properties on
# the object.
class RequestWrap( object ):
  def __init__( self, request, validate = True ):
    if validate:
      EnsureRequestValid( request )
    self._request = request

    # Maps the keys returned by this objects __getitem__ to a # tuple of
    # ( getter_method, setter_method ). Values computed by getter_method (or set
    # by setter_method) are cached in _cached_computed.  setter_method may be
    # None for read-only items.
    self._computed_key = {
      # Unicode string representation of the current line. If the line requested
      # is not in the file, returns ''.
      'line_value': ( self._CurrentLine, None ),

      # The calculated start column, as a codepoint offset into the
      # unicode string line_value
      'start_codepoint': ( self._GetCompletionStartCodepoint,
                           self._SetCompletionStartCodepoint ),

      # The 'column_num' as a unicode codepoint offset
      'column_codepoint': ( lambda: ByteOffsetToCodepointOffset(
                              self[ 'line_bytes' ],
                              self[ 'column_num' ] ),
                            None ),

      # Bytes string representation of the current line
      'line_bytes': ( lambda: ToBytes( self[ 'line_value' ] ),
                      None ),

      # The calculated start column, as a byte offset into the UTF-8 encoded
      # bytes returned by line_bytes
      'start_column': ( self._GetCompletionStartColumn,
                        self._SetCompletionStartColumn ),

      # Note: column_num is the byte offset into the UTF-8 encoded bytes
      # returned by line_bytes

      # unicode string representation of the 'query' after the beginning
      # of the identifier to be completed
      'query': ( self._Query, None ),

      # Unicode string representation of the line value up to the character
      # before the start of 'query'
      'prefix': ( self._Prefix, None ),

      'filetypes': ( self._Filetypes, None ),

      'first_filetype': ( self._FirstFiletype, None ),

      'force_semantic': ( self._GetForceSemantic, None ),

      'lines': ( self._CurrentLines, None ),

      'extra_conf_data': ( self._GetExtraConfData, None )
    }
    self._cached_computed = {}


  def __getitem__( self, key ):
    if key in self._cached_computed:
      return self._cached_computed[ key ]
    if key in self._computed_key:
      getter, _ = self._computed_key[ key ]
      value = getter()
      self._cached_computed[ key ] = value
      return value
    return self._request[ key ]


  def __setitem__( self, key, value ):
    if key in self._computed_key:
      _, setter = self._computed_key[ key ]
      if setter:
        setter( value )
        return

    raise ValueError( 'Key "{0}" is read-only'.format( key ) )


  def __contains__( self, key ):
    return key in self._computed_key or key in self._request


  def __eq__( self, other ):
    if ( self[ 'filepath' ]         != other[ 'filepath' ] or
         self[ 'filetypes' ]        != other[ 'filetypes' ] or
         self[ 'line_num' ]         != other[ 'line_num' ] or
         self[ 'start_column' ]     != other[ 'start_column' ] or
         self[ 'prefix' ]           != other[ 'prefix' ] or
         self[ 'force_semantic' ]   != other[ 'force_semantic' ] or
         self[ 'extra_conf_data' ]  != other[ 'extra_conf_data' ] or
         len( self[ 'file_data' ] ) != len( other[ 'file_data' ] ) ):
      return False

    for filename, file_data in iteritems( self[ 'file_data' ] ):
      if filename == self[ 'filepath' ]:
        lines = self[ 'lines' ]
        other_lines = other[ 'lines' ]
        if len( lines ) != len( other_lines ):
          return False

        line_num = self[ 'line_num' ]
        if ( lines[ : line_num - 1 ] != other_lines[ : line_num - 1 ] or
             lines[ line_num : ] != other_lines[ line_num : ] ):
          return False

      elif ( filename not in other[ 'file_data' ] or
             file_data != other[ 'file_data' ][ filename ] ):
        return False

    return True


  def get( self, key, default = None ):
    try:
      return self[ key ]
    except KeyError:
      return default


  def _CurrentLines( self ):
    current_file = self[ 'filepath' ]
    contents = self[ 'file_data' ][ current_file ][ 'contents' ]
    return SplitLines( contents )


  def _CurrentLine( self ):
    try:
      return self[ 'lines' ][ self[ 'line_num' ] - 1 ]
    except IndexError:
      LOGGER.exception( 'Client returned invalid line number %s '
                        'for file %s. Assuming empty',
                        self[ 'line_num' ],
                        self[ 'filepath' ] )
      return ''


  def _GetCompletionStartColumn( self ):
    return CompletionStartColumn( self[ 'line_value' ],
                                  self[ 'column_num' ],
                                  self[ 'first_filetype' ] )


  def _SetCompletionStartColumn( self, column_num ):
    self._cached_computed[ 'start_column' ] = column_num

    # Note: We must pre-compute (and cache) the codepoint equivalent. This is
    # because the value calculated by the getter (_GetCompletionStartCodepoint)
    # would be based on self[ 'column_codepoint' ] which would be incorrect; it
    # does not know that the user has forced this value to be independent of the
    # column.
    self._cached_computed[ 'start_codepoint' ] = ByteOffsetToCodepointOffset(
      self[ 'line_value' ],
      column_num )

    # The same applies to the 'prefix' (the bit before the start column) and the
    # 'query' (the bit after the start column up to the cursor column). They are
    # dependent on the 'start_codepoint' so we must reset them.
    self._cached_computed.pop( 'prefix', None )
    self._cached_computed.pop( 'query', None )


  def _GetCompletionStartCodepoint( self ):
    return CompletionStartCodepoint( self[ 'line_value' ],
                                     self[ 'column_num' ],
                                     self[ 'first_filetype' ] )


  def _SetCompletionStartCodepoint( self, codepoint_offset ):
    self._cached_computed[ 'start_codepoint' ] = codepoint_offset

    # Note: We must pre-compute (and cache) the byte equivalent. This is because
    # the value calculated by the getter (_GetCompletionStartColumn) would be
    # based on self[ 'column_num' ], which would be incorrect; it does not know
    # that the user has forced this value to be independent of the column.
    self._cached_computed[ 'start_column' ] = CodepointOffsetToByteOffset(
      self[ 'line_value' ],
      codepoint_offset )

    # The same applies to the 'prefix' (the bit before the start column) and the
    # 'query' (the bit after the start column up to the cursor column). They are
    # dependent on the 'start_codepoint' so we must reset them.
    self._cached_computed.pop( 'prefix', None )
    self._cached_computed.pop( 'query', None )


  def _Query( self ):
    return self[ 'line_value' ][
        self[ 'start_codepoint' ] - 1 : self[ 'column_codepoint' ] - 1
    ]


  def _Prefix( self ):
    return self[ 'line_value' ][ : ( self[ 'start_codepoint' ] - 1 ) ]


  def _FirstFiletype( self ):
    try:
      return self[ 'filetypes' ][ 0 ]
    except ( KeyError, IndexError ):
      return None


  def _Filetypes( self ):
    path = self[ 'filepath' ]
    return self[ 'file_data' ][ path ][ 'filetypes' ]


  def _GetForceSemantic( self ):
    return bool( self._request.get( 'force_semantic', False ) )


  def _GetExtraConfData( self ):
    return HashableDict( self._request.get( 'extra_conf_data', {} ) )


def CompletionStartColumn( line_value, column_num, filetype ):
  """Returns the 1-based byte index where the completion query should start.
  So if the user enters:
    foo.bar^
  with the cursor being at the location of the caret (so the character *AFTER*
  'r'), then the starting column would be the index of the letter 'b'.

  NOTE: if the line contains multi-byte characters, then the result is not
  the 'character' index (see CompletionStartCodepoint for that), and therefore
  it is not safe to perform any character-relevant arithmetic on the result
  of this method."""
  return CodepointOffsetToByteOffset(
      ToUnicode( line_value ),
      CompletionStartCodepoint( line_value, column_num, filetype ) )


def CompletionStartCodepoint( line_value, column_num, filetype ):
  """Returns the 1-based codepoint index where the completion query should
  start.  So if the user enters:
    ƒøø.∫å®^
  with the cursor being at the location of the caret (so the character *AFTER*
  '®'), then the starting column would be the index of the character '∫'
  (i.e. 5, not its byte index)."""

  # NOTE: column_num and other numbers on the wire are byte indices, but we need
  # to walk codepoints for identifier checks.
  codepoint_column_num = ByteOffsetToCodepointOffset( line_value, column_num )

  unicode_line_value = ToUnicode( line_value )
  # -1 and then +1 to account for difference betwen 0-based and 1-based
  # indices/columns
  codepoint_start_column = StartOfLongestIdentifierEndingAtIndex(
      unicode_line_value, codepoint_column_num - 1, filetype ) + 1

  return codepoint_start_column
