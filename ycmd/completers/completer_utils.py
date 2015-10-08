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

from collections import defaultdict
import os
import re


class PreparedTriggers( object ):
  def __init__( self,  user_trigger_map = None, filetype_set = None ):
    user_prepared_triggers = ( _FiletypeTriggerDictFromSpec(
        dict( user_trigger_map ) ) if user_trigger_map else
        defaultdict( set ) )
    final_triggers = _FiletypeDictUnion( PREPARED_DEFAULT_FILETYPE_TRIGGERS,
                                         user_prepared_triggers )
    if filetype_set:
      final_triggers = dict( ( k, v ) for k, v in final_triggers.iteritems()
                             if k in filetype_set )

    self._filetype_to_prepared_triggers = final_triggers


  def MatchesForFiletype( self, current_line, start_column, filetype ):
    try:
      triggers = self._filetype_to_prepared_triggers[ filetype ]
    except KeyError:
      return False
    return _MatchesSemanticTrigger( current_line, start_column, triggers )


def _FiletypeTriggerDictFromSpec( trigger_dict_spec ):
  triggers_for_filetype = defaultdict( set )

  for key, triggers in trigger_dict_spec.iteritems():
    filetypes = key.split( ',' )
    for filetype in filetypes:
      regexes = [ _PrepareTrigger( x ) for x in triggers ]
      triggers_for_filetype[ filetype ].update( regexes )


  return triggers_for_filetype


def _FiletypeDictUnion( dict_one, dict_two ):
  """Returns a new filetype dict that's a union of the provided two dicts.
  Dict params are supposed to be type defaultdict(set)."""
  def UpdateDict( first, second ):
    for key, value in second.iteritems():
      first[ key ].update( value )

  final_dict = defaultdict( set )
  UpdateDict( final_dict, dict_one )
  UpdateDict( final_dict, dict_two )
  return final_dict


def _StringTriggerMatches( trigger, line_value, start_column ):
  index = -1
  trigger_length = len( trigger )
  while True:
    line_index = start_column + index
    if line_index < 0 or line_value[ line_index ] != trigger[ index ]:
      break

    if abs( index ) == trigger_length:
      return True
    index -= 1
  return False


def _RegexTriggerMatches( trigger, line_value, start_column ):
  for match in trigger.finditer( line_value ):
    if match.end() == start_column:
      return True
  return False


# start_column is 0-based
def _MatchesSemanticTrigger( line_value, start_column, trigger_list ):
  line_length = len( line_value )
  if not line_length or start_column > line_length:
    return False

  match = False
  for trigger in trigger_list:
    match = ( _StringTriggerMatches( trigger, line_value, start_column )
        if isinstance( trigger, basestring ) else
        _RegexTriggerMatches( trigger, line_value, start_column ) )
    if match:
      return True
  return False


def _PrepareTrigger( trigger ):
  if trigger.startswith( TRIGGER_REGEX_PREFIX ):
    return re.compile( trigger[ len( TRIGGER_REGEX_PREFIX ) : ], re.UNICODE )
  return re.compile( re.escape( trigger ), re.UNICODE )


def _PathToCompletersFolder():
  dir_of_current_script = os.path.dirname( os.path.abspath( __file__ ) )
  return os.path.join( dir_of_current_script )


def PathToFiletypeCompleterPluginLoader( filetype ):
  return os.path.join( _PathToCompletersFolder(), filetype, 'hook.py' )


def FiletypeCompleterExistsForFiletype( filetype ):
  return os.path.exists( PathToFiletypeCompleterPluginLoader( filetype ) )


TRIGGER_REGEX_PREFIX = 're!'

DEFAULT_FILETYPE_TRIGGERS = {
  'c' : ['->', '.'],
  'objc' : ['->',
            '.',
            r're!\[[_a-zA-Z]+\w*\s',    # bracketed calls
            r're!^\s*[^\W\d]\w*\s',     # bracketless calls
            r're!\[.*\]\s',             # method composition
           ],
  'ocaml' : ['.', '#'],
  'cpp,objcpp' : ['->', '.', '::'],
  'perl' : ['->'],
  'php' : ['->', '::'],
  'cs,java,javascript,typescript,d,python,perl6,scala,vb,elixir,go' : ['.'],
  'ruby' : ['.', '::'],
  'lua' : ['.', ':'],
  'erlang' : [':'],
}

PREPARED_DEFAULT_FILETYPE_TRIGGERS = _FiletypeTriggerDictFromSpec(
    DEFAULT_FILETYPE_TRIGGERS )


INCLUDE_REGEX = re.compile( '\s*#\s*(?:include|import)\s*("|<)' )


def AtIncludeStatementStart( line ):
  match = INCLUDE_REGEX.match( line )
  if not match:
    return False
  # Check if the whole string matches the regex
  return match.end() == len( line )


def GetIncludeStatementValue( line, check_closing = True ):
  """Returns include statement value and boolean indicating whether
     include statement is quoted.
     If check_closing is True the string is scanned for statement closing
     character (" or >) and substring between opening and closing characters is
     returned. The whole string after opening character is returned otherwise"""
  match = INCLUDE_REGEX.match( line )
  include_value = None
  quoted_include = False
  if match:
    quoted_include = ( match.group( 1 ) == '"' )
    if not check_closing:
      include_value = line[ match.end(): ]
    else:
      close_char = '"' if quoted_include else '>'
      close_char_pos = line.find( close_char, match.end() )
      if close_char_pos != -1:
        include_value = line[ match.end() : close_char_pos ]
  return include_value, quoted_include
