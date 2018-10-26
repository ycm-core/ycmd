# encoding: utf-8
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

from ycmd.utils import re, SplitLines

C_STYLE_COMMENT = '/\\*(?:\n|.)*?\\*/'
CPP_STYLE_COMMENT = '//.*?$'
PYTHON_STYLE_COMMENT = '#.*?$'
# Anything inside single quotes, '...', but mind:
#  1. that the starting single quote is not escaped
#  2. the escaped slash (\\)
#  3. the escaped single quote inside the string
SINGLE_QUOTE_STRING = r"(?<!\\)'(?:\\\\|\\'|.)*?'"
# Anything inside double quotes, "...", but mind:
#  1. that the starting double quote is not escaped
#  2. the escaped slash (\\)
#  3. the escaped double quote inside the string
DOUBLE_QUOTE_STRING = r'(?<!\\)"(?:\\\\|\\"|.)*?"'
# Anything inside back quotes, `...`, but mind:
#  1. that the starting back quote is not escaped
#  2. the escaped slash (\\)
#  3. the escaped back quote inside the string
BACK_QUOTE_STRING = r'(?<!\\)`(?:\\\\|\\`|.)*?`'
# Python-style multiline single-quote string
MULTILINE_SINGLE_QUOTE_STRING = "'''(?:\n|.)*?'''"
# Python-style multiline double-quote string
MULTILINE_DOUBLE_QUOTE_STRING = '"""(?:\n|.)*?"""'

DEFAULT_COMMENT_AND_STRING_REGEX = re.compile( "|".join( [
  C_STYLE_COMMENT,
  CPP_STYLE_COMMENT,
  PYTHON_STYLE_COMMENT,
  MULTILINE_SINGLE_QUOTE_STRING,
  MULTILINE_DOUBLE_QUOTE_STRING,
  SINGLE_QUOTE_STRING,
  DOUBLE_QUOTE_STRING ] ), re.MULTILINE )

FILETYPE_TO_COMMENT_AND_STRING_REGEX = {
  # Spec:
  # http://www.open-std.org/jtc1/sc22/wg21/docs/papers/2013/n3690.pdf
  'cpp': re.compile( "|".join( [ C_STYLE_COMMENT,
                                 CPP_STYLE_COMMENT,
                                 SINGLE_QUOTE_STRING,
                                 DOUBLE_QUOTE_STRING ] ), re.MULTILINE ),

  # Spec:
  # https://golang.org/ref/spec#Comments
  # https://golang.org/ref/spec#String_literals
  # https://golang.org/ref/spec#Rune_literals
  'go': re.compile( "|".join( [ C_STYLE_COMMENT,
                                CPP_STYLE_COMMENT,
                                SINGLE_QUOTE_STRING,
                                DOUBLE_QUOTE_STRING,
                                BACK_QUOTE_STRING ] ), re.MULTILINE ),

  # Spec:
  # https://docs.python.org/3.6/reference/lexical_analysis.html#comments
  # https://docs.python.org/3.6/reference/lexical_analysis.html#literals
  'python': re.compile( "|".join( [ PYTHON_STYLE_COMMENT,
                                    MULTILINE_SINGLE_QUOTE_STRING,
                                    MULTILINE_DOUBLE_QUOTE_STRING,
                                    SINGLE_QUOTE_STRING,
                                    DOUBLE_QUOTE_STRING ] ), re.MULTILINE ),

  # Spec:
  # https://doc.rust-lang.org/reference.html#comments
  # https://doc.rust-lang.org/reference.html#character-and-string-literals
  'rust': re.compile( "|".join( [ CPP_STYLE_COMMENT,
                                  SINGLE_QUOTE_STRING,
                                  DOUBLE_QUOTE_STRING ] ), re.MULTILINE )
}

for filetype in [ 'c', 'cuda', 'objc', 'objcpp', 'javascript', 'typescript' ]:
  FILETYPE_TO_COMMENT_AND_STRING_REGEX[ filetype ] = (
    FILETYPE_TO_COMMENT_AND_STRING_REGEX[ 'cpp' ] )

# At least c++ and javascript support unicode identifiers, and identifiers may
# start with unicode character, e.g. ålpha. So we need to accept any identifier
# starting with an 'alpha' character or underscore. i.e. not starting with a
# 'digit'. The following regex will match:
#   - A character which is alpha or _. That is a character which is NOT:
#     - a digit (\d)
#     - non-alphanumeric
#     - not an underscore
#       (The latter two come from \W which is the negation of \w)
#   - Followed by any alphanumeric or _ characters
DEFAULT_IDENTIFIER_REGEX = re.compile( r"[^\W\d]\w*", re.UNICODE )

FILETYPE_TO_IDENTIFIER_REGEX = {
    # Spec:
    # http://www.ecma-international.org/ecma-262/6.0/#sec-names-and-keywords
    # Default identifier plus the dollar sign.
    'javascript': re.compile( r"(?:[^\W\d]|\$)[\w$]*", re.UNICODE ),

    # Spec: https://www.w3.org/TR/css-syntax-3/#ident-token-diagram
    'css': re.compile( r"-?[^\W\d][\w-]*", re.UNICODE ),

    # Spec: http://www.w3.org/TR/html5/syntax.html#tag-name-state
    # But not quite since not everything we want to pull out is a tag name. We
    # also want attribute names (and probably unquoted attribute values).
    # And we also want to ignore common template chars like `}` and `{`.
    'html': re.compile( r"[a-zA-Z][^\s/>='\"}{\.]*", re.UNICODE ),

    # Spec: http://cran.r-project.org/doc/manuals/r-release/R-lang.pdf
    # Section 10.3.2.
    # Can be any sequence of '.', '_' and alphanum BUT can't start with:
    #   - '.' followed by digit
    #   - digit
    #   - '_'
    'r': re.compile( r"(?!(?:\.\d|\d|_))[\.\w]+", re.UNICODE ),

    # Spec: http://clojure.org/reader
    # Section: Symbols
    'clojure': re.compile(
         r"[-\*\+!_\?:\.a-zA-Z][-\*\+!_\?:\.\w]*/?[-\*\+!_\?:\.\w]*",
         re.UNICODE ),

    # Spec: http://www.haskell.org/onlinereport/lexemes.html
    # Section 2.4
    'haskell': re.compile( r"[_a-zA-Z][\w']+", re.UNICODE ),

    # Spec: ?
    # Colons are often used in labels (e.g. \label{fig:foobar}) so we accept
    # them in the middle of an identifier but not at its extremities. We also
    # accept dashes for compound words.
    'tex': re.compile( r"[^\W\d](?:[\w:-]*\w)?", re.UNICODE ),

    # Spec: http://doc.perl6.org/language/syntax
    'perl6': re.compile( r"[_a-zA-Z](?:\w|[-'](?=[_a-zA-Z]))*", re.UNICODE ),

    # https://www.scheme.com/tspl4/grammar.html#grammar:symbols
    'scheme': re.compile( r"\+|\-|\.\.\.|"
                          r"(?:->|(:?\\x[0-9A-Fa-f]+;|[!$%&*/:<=>?~^]|[^\W\d]))"
                          r"(?:\\x[0-9A-Fa-f]+;|[-+.@!$%&*/:<=>?~^\w])*",
                          re.UNICODE ),
}

FILETYPE_TO_IDENTIFIER_REGEX[ 'typescript' ] = (
  FILETYPE_TO_IDENTIFIER_REGEX[ 'javascript' ] )
FILETYPE_TO_IDENTIFIER_REGEX[ 'scss' ] = FILETYPE_TO_IDENTIFIER_REGEX[ 'css' ]
FILETYPE_TO_IDENTIFIER_REGEX[ 'sass' ] = FILETYPE_TO_IDENTIFIER_REGEX[ 'css' ]
FILETYPE_TO_IDENTIFIER_REGEX[ 'less' ] = FILETYPE_TO_IDENTIFIER_REGEX[ 'css' ]
FILETYPE_TO_IDENTIFIER_REGEX[ 'elisp' ] = (
  FILETYPE_TO_IDENTIFIER_REGEX[ 'clojure' ] )
FILETYPE_TO_IDENTIFIER_REGEX[ 'lisp' ] = (
  FILETYPE_TO_IDENTIFIER_REGEX[ 'clojure' ] )


def CommentAndStringRegexForFiletype( filetype ):
  return FILETYPE_TO_COMMENT_AND_STRING_REGEX.get(
    filetype, DEFAULT_COMMENT_AND_STRING_REGEX )


def IdentifierRegexForFiletype( filetype ):
  return FILETYPE_TO_IDENTIFIER_REGEX.get( filetype, DEFAULT_IDENTIFIER_REGEX )


def ReplaceWithEmptyLines( regex_match ):
  return '\n' * ( len( SplitLines( regex_match.group( 0 ) ) ) - 1 )


def RemoveIdentifierFreeText( text, filetype = None ):
  return CommentAndStringRegexForFiletype( filetype ).sub(
    ReplaceWithEmptyLines, text )


def ExtractIdentifiersFromText( text, filetype = None ):
  return re.findall( IdentifierRegexForFiletype( filetype ), text )


def IsIdentifier( text, filetype = None ):
  if not text:
    return False
  regex = IdentifierRegexForFiletype( filetype )
  match = regex.match( text )
  return match and match.end() == len( text )


# index is 0-based and EXCLUSIVE, so ("foo.", 3) -> 0
# Works with both unicode and str objects.
# Returns the index on bad input.
def StartOfLongestIdentifierEndingAtIndex( text, index, filetype = None ):
  if not text or index < 1 or index > len( text ):
    return index

  for i in range( index ):
    if IsIdentifier( text[ i : index ], filetype ):
      return i
  return index


# If the index is not on a valid identifer, it searches forward until a valid
# identifier is found. Returns the identifier.
def IdentifierAtIndex( text, index, filetype = None ):
  if index > len( text ):
    return ''

  for match in IdentifierRegexForFiletype( filetype ).finditer( text ):
    if match.end() > index:
      return match.group()
  return ''
