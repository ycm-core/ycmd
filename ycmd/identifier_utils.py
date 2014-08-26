#!/usr/bin/env python
#
# Copyright (C) 2014  Google Inc.
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

import re

# TODO: utils.IsIdentifierChar() needs to be language-aware as well. It will
# also need to be replaced by something that tests the whole identifier, not a
# single char.

COMMENT_AND_STRING_REGEX = re.compile(
  "//.*?$" # Anything following '//'
  "|"
  "#.*?$"  # Anything following '#'
  "|"
  "/\*(?:\n|.)*?\*/"  # C-style comments, '/* ... */'
  "|"
  # Python-style multi-line single-quote string
  "'''(?:\n|.)*?'''"
  "|"
  # Python-style multi-line double-quote string
  '"""(?:\n|.)*?"""'
  "|"
  # Anything inside single quotes, '...', but mind:
  #  1. that the starting single quote is not escaped
  #  2. the escaped slash (\\)
  #  3. the escaped single quote inside the string
  r"(?<!\\)'(?:\\\\|\\'|.)*?'"
  "|"
  # Anything inside double quotes, "...", but mind:
  #  1. that the starting double quote is not escaped
  #  2. the escaped slash (\\)
  #  3. the escaped double quote inside the string
  r'(?<!\\)"(?:\\\\|\\"|.)*?"', re.MULTILINE )

DEFAULT_IDENTIFIER_REGEX = re.compile( r"[_a-zA-Z]\w*", re.UNICODE )

FILETYPE_TO_IDENTIFIER_REGEX = {
    # Spec: http://www.w3.org/TR/CSS2/syndata.html#characters
    'css': re.compile( r"[-_a-zA-Z][-\w]*", re.UNICODE ),

    # Spec: http://www.w3.org/TR/html5/syntax.html#tag-name-state
    # But not quite since not everything we want to pull out is a tag name. We
    # also want attribute names (and probably unquoted attribute values).
    'html': re.compile( r"[a-zA-Z][^\s/>='\"]*", re.UNICODE )
}


def _IdentifierRegexForFiletype( filetype ):
  return FILETYPE_TO_IDENTIFIER_REGEX.get( filetype, DEFAULT_IDENTIFIER_REGEX )


def RemoveIdentifierFreeText( text ):
  return COMMENT_AND_STRING_REGEX.sub( '', text )


def ExtractIdentifiersFromText( text, filetype = None ):
  return re.findall( _IdentifierRegexForFiletype( filetype ), text )


def IsIdentifier( text, filetype = None ):
  if not text:
    return False
  regex = _IdentifierRegexForFiletype( filetype )
  match = regex.match( text )
  return match and match.end() == len( text )


# index is 0-based and EXCLUSIVE, so ("foo.", 3) -> 0
# Works with both unicode and str objects.
# Returns the index on bad input.
def StartOfLongestIdentifierEndingAtIndex( text, index, filetype = None ):
  if not text or index < 1 or index > len( text ):
    return index

  for i in xrange( index ):
    if IsIdentifier( text[ i : index ], filetype ):
      return i
  return index

