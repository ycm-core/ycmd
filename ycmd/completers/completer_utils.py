# Copyright (C) 2013-2018 ycmd contributors
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

# Must not import ycm_core here! Vim imports completer, which imports this file.
# We don't want ycm_core inside Vim.
from collections import defaultdict
from future.utils import iteritems
from ycmd.utils import ( LOGGER, ToCppStringCompatible, ToUnicode, re, ReadFile,
                         SplitLines )


class PreparedTriggers( object ):
  def __init__( self, user_trigger_map = None, filetype_set = None ):
    self._user_trigger_map = user_trigger_map
    self._server_trigger_map = None
    self._filetype_set = filetype_set

    self._CombineTriggers()


  def _CombineTriggers( self ):
    user_prepared_triggers = ( _FiletypeTriggerDictFromSpec(
      dict( self._user_trigger_map ) ) if self._user_trigger_map else
      defaultdict( set ) )
    server_prepared_triggers = ( _FiletypeTriggerDictFromSpec(
      dict( self._server_trigger_map ) ) if self._server_trigger_map else
      defaultdict( set ) )

    # Combine all of the defaults, server-supplied and user-supplied triggers
    final_triggers = _FiletypeDictUnion( PREPARED_DEFAULT_FILETYPE_TRIGGERS,
                                         server_prepared_triggers,
                                         user_prepared_triggers )

    if self._filetype_set:
      final_triggers = { k: v for k, v in iteritems( final_triggers )
                         if k in self._filetype_set }

    self._filetype_to_prepared_triggers = final_triggers


  def SetServerSemanticTriggers( self, server_trigger_characters ):
    self._server_trigger_map = {
      ','.join( self._filetype_set ): server_trigger_characters
    }
    self._CombineTriggers()


  def MatchingTriggerForFiletype( self,
                                  current_line,
                                  start_codepoint,
                                  column_codepoint,
                                  filetype ):
    try:
      triggers = self._filetype_to_prepared_triggers[ filetype ]
    except KeyError:
      return None
    return _MatchingSemanticTrigger( current_line,
                                     start_codepoint,
                                     column_codepoint,
                                     triggers )


  def MatchesForFiletype( self,
                          current_line,
                          start_codepoint,
                          column_codepoint,
                          filetype ):
    return self.MatchingTriggerForFiletype( current_line,
                                            start_codepoint,
                                            column_codepoint,
                                            filetype ) is not None


def _FiletypeTriggerDictFromSpec( trigger_dict_spec ):
  triggers_for_filetype = defaultdict( set )

  for key, triggers in iteritems( trigger_dict_spec ):
    filetypes = key.split( ',' )
    for filetype in filetypes:
      regexes = [ _PrepareTrigger( x ) for x in triggers ]
      triggers_for_filetype[ filetype ].update( regexes )


  return triggers_for_filetype


def _FiletypeDictUnion( *args ):
  """Returns a new filetype dict that's a union of the provided two dicts.
  Dict params are supposed to be type defaultdict(set)."""
  def UpdateDict( first, second ):
    for key, value in iteritems( second ):
      first[ key ].update( value )

  final_dict = defaultdict( set )
  for d in args:
    UpdateDict( final_dict, d )
  return final_dict


# start_codepoint and column_codepoint are codepoint offsets in the unicode
# string line_value.
def _RegexTriggerMatches( trigger,
                          line_value,
                          start_codepoint,
                          column_codepoint ):
  for match in trigger.finditer( line_value ):
    # By definition of 'start_codepoint', we know that the character just before
    # 'start_codepoint' is not an identifier character but all characters
    # between 'start_codepoint' and 'column_codepoint' are. This means that if
    # our trigger ends with an identifier character, its tail must match between
    # 'start_codepoint' and 'column_codepoint', 'start_codepoint' excluded. But
    # if it doesn't, its tail must match exactly at 'start_codepoint'. Both
    # cases are mutually exclusive hence the following condition.
    if start_codepoint <= match.end() and match.end() <= column_codepoint:
      return True
  return False


# start_codepoint and column_codepoint are 0-based and are codepoint offsets
# into the unicode string line_value.
def _MatchingSemanticTrigger( line_value, start_codepoint, column_codepoint,
                              trigger_list ):
  if start_codepoint < 0 or column_codepoint < 0:
    return None

  line_length = len( line_value )
  if not line_length or start_codepoint > line_length:
    return None

  # Ignore characters after user's caret column
  line_value = line_value[ : column_codepoint ]

  for trigger in trigger_list:
    if _RegexTriggerMatches( trigger,
                             line_value,
                             start_codepoint,
                             column_codepoint ):
      return trigger
  return None


def _MatchesSemanticTrigger( line_value, start_codepoint, column_codepoint,
                             trigger_list ):
  return _MatchingSemanticTrigger( line_value,
                                   start_codepoint,
                                   column_codepoint,
                                   trigger_list ) is not None


def _PrepareTrigger( trigger ):
  trigger = ToUnicode( trigger )
  if trigger.startswith( TRIGGER_REGEX_PREFIX ):
    return re.compile( trigger[ len( TRIGGER_REGEX_PREFIX ) : ], re.UNICODE )
  return re.compile( re.escape( trigger ), re.UNICODE )


def FilterAndSortCandidatesWrap( candidates, sort_property, query,
                                 max_candidates ):
  from ycm_core import FilterAndSortCandidates

  # The c++ interface we use only understands the (*native*) 'str' type (i.e.
  # not the 'str' type from python-future. If we pass it a 'unicode' or
  # 'bytes' instance then various things blow up, such as converting to
  # std::string. Therefore all strings passed into the c++ API must pass through
  # ToCppStringCompatible (or more strictly all strings which the C++ code
  # needs to use and convert. In this case, just the insertion text property)
  # For efficiency, the conversion of the insertion text property is done in the
  # C++ layer.
  return FilterAndSortCandidates( candidates,
                                  ToCppStringCompatible( sort_property ),
                                  ToCppStringCompatible( query ),
                                  max_candidates )


TRIGGER_REGEX_PREFIX = 're!'

DEFAULT_FILETYPE_TRIGGERS = {
  'c' : [ '->', '.' ],
  'objc,objcpp' : [
    '->',
    '.',
    r're!\[[_a-zA-Z]+\w*\s',    # bracketed calls
    r're!^\s*[^\W\d]\w*\s',     # bracketless calls
    r're!\[.*\]\s',             # method composition
  ],
  'ocaml' : [ '.', '#' ],
  'cpp,cuda,objcpp' : [ '->', '.', '::' ],
  'perl' : [ '->' ],
  'php' : [ '->', '::' ],
  ( 'cs,'
    'd,'
    'elixir,'
    'go,'
    'groovy,'
    'java,'
    'javascript,'
    'julia,'
    'perl6,'
    'python,'
    'scala,'
    'typescript,'
    'vb' ) : [ '.' ],
  'ruby,rust' : [ '.', '::' ],
  'lua' : [ '.', ':' ],
  'erlang' : [ ':' ],
}

PREPARED_DEFAULT_FILETYPE_TRIGGERS = _FiletypeTriggerDictFromSpec(
    DEFAULT_FILETYPE_TRIGGERS )


def GetFileContents( request_data, filename ):
  """Returns the contents of the absolute path |filename| as a unicode
  string. If the file contents exist in |request_data| (i.e. it is open and
  potentially modified/dirty in the user's editor), then it is returned,
  otherwise the file is read from disk (assuming a UTF-8 encoding) and its
  contents returned."""
  file_data = request_data[ 'file_data' ]
  if filename in file_data:
    return ToUnicode( file_data[ filename ][ 'contents' ] )

  try:
    return ToUnicode( ReadFile( filename ) )
  except IOError:
    LOGGER.exception( 'Error reading file %s', filename )
    return ''


def GetFileLines( request_data, filename ):
  """Like GetFileContents but return the contents as a list of lines. Avoid
  splitting the lines if they have already been split for the current file."""
  if filename == request_data[ 'filepath' ]:
    return request_data[ 'lines' ]
  return SplitLines( GetFileContents( request_data, filename ) )
