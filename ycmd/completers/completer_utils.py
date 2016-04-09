# Copyright (C) 2013 Google Inc.
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
standard_library.install_aliases()
from builtins import *  # noqa
from future.utils import iteritems

# Must not import ycm_core here! Vim imports completer, which imports this file.
# We don't want ycm_core inside Vim.
import os
import re
import copy
from collections import defaultdict
from ycmd.utils import ToCppStringCompatible, ToUnicode, ReadFile


class PreparedTriggers( object ):
  def __init__( self, user_trigger_map = None, filetype_set = None ):
    user_prepared_triggers = ( _FiletypeTriggerDictFromSpec(
        dict( user_trigger_map ) ) if user_trigger_map else
        defaultdict( set ) )
    final_triggers = _FiletypeDictUnion( PREPARED_DEFAULT_FILETYPE_TRIGGERS,
                                         user_prepared_triggers )
    if filetype_set:
      final_triggers = dict( ( k, v ) for k, v in iteritems( final_triggers )
                             if k in filetype_set )

    self._filetype_to_prepared_triggers = final_triggers


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


def _FiletypeDictUnion( dict_one, dict_two ):
  """Returns a new filetype dict that's a union of the provided two dicts.
  Dict params are supposed to be type defaultdict(set)."""
  def UpdateDict( first, second ):
    for key, value in iteritems( second ):
      first[ key ].update( value )

  final_dict = defaultdict( set )
  UpdateDict( final_dict, dict_one )
  UpdateDict( final_dict, dict_two )
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


def _PathToCompletersFolder():
  dir_of_current_script = os.path.dirname( os.path.abspath( __file__ ) )
  return os.path.join( dir_of_current_script )


def PathToFiletypeCompleterPluginLoader( filetype ):
  return os.path.join( _PathToCompletersFolder(), filetype, 'hook.py' )


def FiletypeCompleterExistsForFiletype( filetype ):
  return os.path.exists( PathToFiletypeCompleterPluginLoader( filetype ) )


def FilterAndSortCandidatesWrap( candidates, sort_property, query ):
  from ycm_core import FilterAndSortCandidates

  # The c++ interface we use only understands the (*native*) 'str' type (i.e.
  # not the 'str' type from python-future. If we pass it a 'unicode' or
  # 'bytes' instance then various things blow up, such as converting to
  # std::string. Therefore all strings passed into the c++ API must pass through
  # ToCppStringCompatible (or more strictly all strings which the C++ code
  # needs to use and convert. In this case, just the insertion text property)

  # FIXME: This is actually quite inefficient in an area which is used
  # constantly and the key performance critical part of the system. There is
  # code in the C++ layer (see PythonSupport.cpp:GetUtf8String) which attempts
  # to work around this limitation. Unfortunately it has issues which cause the
  # above problems, and we work around it by converting here in the python
  # layer until we can come up with a better solution in the C++ layer.

  # Note: we must deep copy candidates because we do not want to clobber the
  # data that is passed in. It is actually used directly by the cache, so if
  # we change the data pointed to by the elements of candidates, then this will
  # be reflected in a subsequent response from the cache. This is particularly
  # important for those candidates which are *not* returned after the filter, as
  # they are not converted back to unicode.
  cpp_compatible_candidates = _ConvertCandidatesToCppCompatible(
    copy.deepcopy( candidates ),
    sort_property )

  # However, the reset of the python layer expects all the candidates properties
  # to be some form of unicode string - a python-future str() instance.
  # So we need to convert the insertion text property back to a unicode string
  # before returning it.
  filtered_candidates = FilterAndSortCandidates(
    cpp_compatible_candidates,
    ToCppStringCompatible( sort_property ),
    ToCppStringCompatible( query ) )

  return _ConvertCandidatesToPythonCompatible( filtered_candidates,
                                               sort_property )


def _ConvertCandidatesToCppCompatible( candidates, sort_property ):
  """Convert the candidates to the format expected by the C++ layer."""
  return _ConvertCandidates( candidates, sort_property, ToCppStringCompatible )


def _ConvertCandidatesToPythonCompatible( candidates, sort_property ):
  """Convert the candidates to the format expected by the python layer."""
  return _ConvertCandidates( candidates, sort_property, ToUnicode )


def _ConvertCandidates( candidates, sort_property, converter ):
  """Apply the conversion function |converter| to the logical insertion text
  field within the candidates in the candidate list |candidates|. The
  |sort_property| is required to determine the format of |candidates|.

  The conversion function should take a single argument (the string) and return
  the converted string. It should be one of ycmd.utils.ToUnicode or
  ycmd.utils.ToCppStringCompatible.

  Typically this method is not called directly, rather it is used via
  _ConvertCandidatesToCppCompatible and _ConvertCandidatesToPythonCompatible."""

  if sort_property:
    for candidate in candidates:
      candidate[ sort_property ] = converter( candidate[ sort_property ] )
    return candidates

  return [ converter( c ) for c in candidates ]


TRIGGER_REGEX_PREFIX = 're!'

DEFAULT_FILETYPE_TRIGGERS = {
  'c' : [ '->', '.' ],
  'objc' : [
    '->',
    '.',
    r're!\[[_a-zA-Z]+\w*\s',    # bracketed calls
    r're!^\s*[^\W\d]\w*\s',     # bracketless calls
    r're!\[.*\]\s',             # method composition
  ],
  'ocaml' : [ '.', '#' ],
  'cpp,objcpp' : [ '->', '.', '::' ],
  'perl' : [ '->' ],
  'php' : [ '->', '::' ],
  'cs,java,javascript,typescript,d,python,perl6,scala,vb,elixir,go,groovy' : [
    '.'
  ],
  'ruby,rust' : [ '.', '::' ],
  'lua' : [ '.', ':' ],
  'erlang' : [ ':' ],
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


def GetFileContents( request_data, filename ):
  """Returns the contents of the absolute path |filename| as a unicode
  string. If the file contents exist in |request_data| (i.e. it is open and
  potentially modified/dirty in the user's editor), then it is returned,
  otherwise the file is read from disk (assuming a UTF-8 encoding) and its
  contents returned."""
  file_data = request_data[ 'file_data' ]
  if filename in file_data:
    return ToUnicode( file_data[ filename ][ 'contents' ] )

  return ToUnicode( ReadFile( filename ) )
