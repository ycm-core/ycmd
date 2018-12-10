#!/usr/bin/env python
# coding: utf8
#
# Copyright (C) 2018 ycmd contributors
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

import re
import pprint
import sys
from collections import defaultdict, OrderedDict
from os import path as p
from io import StringIO


DIR_OF_THIS_SCRIPT = p.dirname( p.abspath( __file__ ) )
DIR_OF_THIRD_PARTY = p.join( DIR_OF_THIS_SCRIPT, 'third_party' )

sys.path[ 0:0 ] = [ p.join( DIR_OF_THIRD_PARTY, 'requests_deps', 'requests' ),
                    p.join( DIR_OF_THIRD_PARTY,
                            'requests_deps',
                            'urllib3',
                            'src' ),
                    p.join( DIR_OF_THIRD_PARTY, 'requests_deps', 'chardet' ),
                    p.join( DIR_OF_THIRD_PARTY, 'requests_deps', 'certifi' ),
                    p.join( DIR_OF_THIRD_PARTY, 'requests_deps', 'idna' ) ]

import requests

DIR_OF_CPP_SOURCES = p.join( DIR_OF_THIS_SCRIPT, 'cpp', 'ycm' )
UNICODE_TABLE_TEMPLATE = (
  """// This file was automatically generated with the update_unicode.py script
// using version {unicode_version} of the Unicode Character Database.
#include <array>
struct RawCodePointArray {{
std::array< char[{original_size}], {size} > original;
std::array< char[{normal_size}], {size} > normal;
std::array< char[{folded_case_size}], {size} > folded_case;
std::array< char[{swapped_case_size}], {size} > swapped_case;
std::array< bool, {size} > is_letter;
std::array< bool, {size} > is_punctuation;
std::array< bool, {size} > is_uppercase;
std::array< uint8_t, {size} > break_property;
std::array< uint8_t, {size} > combining_class;
}};
static const RawCodePointArray code_points = {{
{code_points}
}};""" )
UNICODE_VERSION_REGEX = re.compile( r'Version (?P<version>\d+(?:\.\d+){2})' )
GRAPHEME_BREAK_PROPERTY_REGEX = re.compile(
  r'^(?P<value>[A-F0-9.]+)\s+; (?P<property>\w+) # .*$' )
GRAPHEME_BREAK_PROPERTY_TOTAL = re.compile(
  r'# Total code points: (?P<total>\d+)' )
# See
# https://www.unicode.org/reports/tr29/#Grapheme_Cluster_Break_Property_Values
GRAPHEME_BREAK_PROPERTY_MAP = {
  # "Other" is the term used in the Unicode data while "Any" is used in the
  # docs.
  'Other'              :  0,
  'CR'                 :  1,
  'LF'                 :  2,
  'Control'            :  3,
  'Extend'             :  4,
  'ZWJ'                :  5,
  'Regional_Indicator' :  6,
  'Prepend'            :  7,
  'SpacingMark'        :  8,
  'L'                  :  9,
  'V'                  : 10,
  'T'                  : 11,
  'LV'                 : 12,
  'LVT'                : 13,
  # "ExtPict" is used in the GraphemeBreakTest.txt file for
  # Extended_Pictographic.
  'ExtPict'            : 18,
}
SPECIAL_FOLDING_REGEX = re.compile(
  r'^(?P<code>[A-F0-9]+); (?P<lower>.*); (?P<title>.*); (?P<upper>.*); '
   '(?:.*; )?# .*$' )
CASE_FOLDING_REGEX = re.compile(
  r'^(?P<code>[A-F0-9]+); (?P<status>[CFST]); (?P<mapping>[A-F0-9 ]+); # '
   '(?P<name>.*)$' )
EMOJI_PROPERTY_REGEX = re.compile(
  r'^(?P<code>[A-F0-9.]+)\s*; (?P<property>[\w_]+)\s*# .*$' )
EMOJI_PROPERTY_TOTAL = re.compile( r'# Total elements: (?P<total>\d+)' )
HANGUL_BASE = 0xAC00
HANGUL_L_BASE = 0x1100
HANGUL_V_BASE = 0x1161
HANGUL_T_BASE = 0x11A7
HANGUL_L_COUNT = 19
HANGUL_V_COUNT = 21
HANGUL_T_COUNT = 28
HANGUL_VT_COUNT = HANGUL_V_COUNT * HANGUL_T_COUNT
HANGUL_LVT_COUNT = HANGUL_L_COUNT * HANGUL_VT_COUNT


def Download( url ):
  request = requests.get( url )
  request.raise_for_status()
  return request.text.splitlines()


# Encode a Unicode code point in UTF-8 binary form.
def UnicodeToBinaryUtf8( code_point ):
  binary = bin( int( code_point, 16 ) )[ 2: ]
  binary_length = len( binary )
  if binary_length <= 7:
    return binary.zfill( 8 )
  if binary_length <= 11:
    binary = binary.zfill( 11 )
    return '110' + binary[ :5 ] + '10' + binary[ 5: ]
  if binary_length <= 16:
    binary = binary.zfill( 16 )
    return '1110' + binary[ :4 ] + '10' + binary[ 4:10 ] + '10' + binary[ 10: ]
  if binary_length <= 21:
    binary = binary.zfill( 21 )
    return ( '11110' + binary[ :3 ] + '10' + binary[ 3:9 ] +
             '10' + binary[ 9:15 ] + '10' + binary[ 15: ] )
  raise RuntimeError( 'Cannot encode a Unicode code point to UTF-8 on more '
                      'than 4 bytes.' )


# Convert a Unicode code point into a UTF-8 string that can be included in a C++
# file when surrounded with double quotes.
def UnicodeToUtf8( code_point ):
  utf8_binary = UnicodeToBinaryUtf8( code_point )
  utf8_binary_length = ( len( utf8_binary ) + 1 ) // 4
  # Strip the L from the hexa value that Python adds for big numbers.
  utf8_hex = hex( int( utf8_binary, 2 ) )[ 2: ].rstrip( 'L' )
  utf8_hex = utf8_hex.zfill( utf8_binary_length )
  # GCC and Clang raises the warning "null character(s) preserved in string
  # literal" if we don't escape the null character.
  if utf8_hex == '00':
    return '\\x00'
  # Escape newline characters.
  if utf8_hex == '0a':
    return '\\n'
  if utf8_hex == '0d':
    return '\\r'
  # Escape the " character.
  if utf8_hex == '22':
    return '\\"'
  # Escape the \ character.
  if utf8_hex == '5c':
    return '\\\\'
  # MSVC fails to compile with error "unexpected end-of-file found" if we don't
  # escape that character.
  if utf8_hex == '1a':
    return '\\x1a'
  try:
    return bytearray.fromhex( utf8_hex ).decode( 'utf8' )
  except UnicodeDecodeError:
    # If Python fails to encode the character, we insert it with the \x
    # notation.
    return pprint.pformat( bytearray.fromhex( utf8_hex ) )[ 12: -2 ]


def JoinUnicodeToUtf8( code_points ):
  return ''.join( [ UnicodeToUtf8( code_point.strip() )
                    for code_point in code_points ] )


def DecToHex( code_point ):
  return hex( code_point )[ 2: ].zfill( 4 ).upper()


def GetUnicodeVersion():
  readme = Download(
    'https://www.unicode.org/Public/UCD/latest/ReadMe.txt' )
  for line in readme:
    match = UNICODE_VERSION_REGEX.search( line )
    if match:
      return match.group( 'version' )
  raise RuntimeError( 'Cannot find the version of the Unicode Standard.' )


# See https://www.unicode.org/reports/tr44/tr44-20.html#UnicodeData.txt
def GetUnicodeData():
  data = Download(
    'https://www.unicode.org/Public/UCD/latest/ucd/UnicodeData.txt' )

  unicode_data = OrderedDict()

  previous_value = None
  for line in data:
    ( value, name, general_category, ccc, _, decomposition, _, _, _, _, _, _,
      uppercase, lowercase, _ ) = line.split( ';' )

    # Some pairs of lines correspond to a range. Add all code points in that
    # range.
    if name.endswith( 'First>' ):
      previous_value = value
      continue
    if name.endswith( 'Last>' ):
      range_start = int( previous_value, 16 )
      range_end = int( value, 16 ) + 1
      for dec_value in range( range_start, range_end ):
        unicode_data[ DecToHex( dec_value ) ] = {
          'name': name,
          'general_category': general_category,
          'ccc': ccc,
          'decomposition': decomposition,
          'uppercase': uppercase,
          'lowercase': lowercase
        }
      continue

    unicode_data[ value ] = {
      'name': name,
      'general_category': general_category,
      'ccc': ccc,
      'decomposition': decomposition,
      'uppercase': uppercase,
      'lowercase': lowercase
    }

  return unicode_data


# See
# https://www.unicode.org/reports/tr44/tr44-20.html#GraphemeBreakProperty.txt
def GetGraphemeBreakProperty():
  data = Download( 'https://www.unicode.org/'
    'Public/UCD/latest/ucd/auxiliary/GraphemeBreakProperty.txt' )

  nb_code_points = 0
  break_data = {}
  for line in data:
    # Check if the number of code points collected for each property is the same
    # as the number indicated in the document.
    match = GRAPHEME_BREAK_PROPERTY_TOTAL.search( line )
    if match:
      total = int( match.group( 'total' ) )
      if nb_code_points != total:
        raise RuntimeError(
          'Expected {} code points. Got {}.'.format( total, nb_code_points ) )
      nb_code_points = 0

    match = GRAPHEME_BREAK_PROPERTY_REGEX.search( line )
    if not match:
      continue

    value = match.group( 'value' )
    prop = match.group( 'property' )

    if '..' not in value:
      break_data[ value ] = prop
      nb_code_points += 1
      continue

    range_start, range_end = value.split( '..' )
    range_start = int( range_start, 16 )
    range_end = int( range_end, 16 ) + 1
    for value in range( range_start, range_end ):
      break_data[ DecToHex( value ) ] = prop
      nb_code_points += 1

  return break_data


# See https://www.unicode.org/reports/tr44/tr44-20.html#SpecialCasing.txt
def GetSpecialFolding():
  data = Download(
    'https://www.unicode.org/Public/UCD/latest/ucd/SpecialCasing.txt' )

  folding_data = {}
  for line in data:
    # Ignore all context-sensitive and language-sensitive mappings.
    if line.startswith( '# Conditional Mappings' ):
      break

    match = SPECIAL_FOLDING_REGEX.search( line )
    if not match:
      continue

    code = match.group( 'code' )

    folding_data[ code ] = {
      'lowercase': match.group( 'lower' ),
      'titlecase': match.group( 'title' ),
      'uppercase': match.group( 'upper' )
    }

  return folding_data


# See https://www.unicode.org/reports/tr44/tr44-20.html#CaseFolding.txt
def GetCaseFolding():
  data = Download(
    'https://www.unicode.org/Public/UCD/latest/ucd/CaseFolding.txt' )

  folding_data = {}
  for line in data:
    match = CASE_FOLDING_REGEX.search( line )
    if not match:
      continue

    code = match.group( 'code' )
    status = match.group( 'status' )
    mapping = match.group( 'mapping' )

    # Support full case folding.
    if status in [ 'C', 'F' ]:
      folding_data[ code ] = mapping

  return folding_data


def GetEmojiData():
  data = Download( 'https://unicode.org/Public/emoji/latest/emoji-data.txt' )

  nb_code_points = 0
  emoji_data = defaultdict( list )
  for line in data:
    # Check if the number of code points collected for the property is the same
    # as the number indicated in the document.
    match = EMOJI_PROPERTY_TOTAL.search( line )
    if match:
      total = int( match.group( 'total' ) )
      if nb_code_points != total:
        raise RuntimeError(
          'Expected {} code points. Got {}.'.format( total, nb_code_points ) )
      nb_code_points = 0

    match = EMOJI_PROPERTY_REGEX.search( line )
    if not match:
      continue

    code = match.group( 'code' )
    prop = match.group( 'property' )

    if '..' not in code:
      emoji_data[ code ].append( prop )
      nb_code_points += 1
      continue

    range_start, range_end = code.split( '..' )
    range_start = int( range_start, 16 )
    range_end = int( range_end, 16 ) + 1
    for value in range( range_start, range_end ):
      emoji_data[ DecToHex( value ) ].append( prop )
      nb_code_points += 1

  return emoji_data


# Decompose a hangul syllable using the algorithm described in
# https://www.unicode.org/versions/Unicode10.0.0/ch03.pdf#G61399
def DecomposeHangul( code_point ):
  index = int( code_point, 16 ) - HANGUL_BASE
  if index < 0 or index >= HANGUL_LVT_COUNT:
    return None

  hangul_l = HANGUL_L_BASE + index // HANGUL_VT_COUNT
  hangul_v = HANGUL_V_BASE + ( index % HANGUL_VT_COUNT ) // HANGUL_T_COUNT
  hangul_t = HANGUL_T_BASE + index % HANGUL_T_COUNT
  code_points = [ DecToHex( hangul_l ), DecToHex( hangul_v ) ]
  if hangul_t != HANGUL_T_BASE:
    code_points.append( DecToHex( hangul_t ) )
  return code_points


# Recursively decompose a Unicode code point into a list of code points
# according to canonical decomposition.
# See https://www.unicode.org/versions/Unicode10.0.0/ch03.pdf#G733
def Decompose( code_point, unicode_data ):
  code_points = DecomposeHangul( code_point )
  if code_points:
    return code_points

  raw_decomposition = unicode_data[ code_point ][ 'decomposition' ]
  if not raw_decomposition:
    return [ code_point ]
  # Ignore compatibility decomposition.
  if raw_decomposition.startswith( '<' ):
    return [ code_point ]
  decomposition = []
  for code_point in raw_decomposition.split( ' ' ):
    decomposition.extend( Decompose( code_point, unicode_data ) )
  return decomposition


def Lowercase( code_points, unicode_data, special_folding ):
  lower_code_points = []
  for code_point in code_points:
    lowercase = special_folding.get( code_point,
                                     unicode_data[ code_point ] )[ 'lowercase' ]
    lower_code_point = lowercase if lowercase else code_point
    lower_code_points.extend( lower_code_point.split( ' ' ) )
  return lower_code_points


def Uppercase( code_points, unicode_data, special_folding ):
  upper_code_points = []
  for code_point in code_points:

    uppercase = special_folding.get( code_point,
                                     unicode_data[ code_point ] )[ 'uppercase' ]
    upper_code_point = uppercase if uppercase else code_point
    upper_code_points.extend( upper_code_point.split( ' ' ) )
  return upper_code_points


def Foldcase( code_points, unicode_data, case_folding ):
  decomposed_code_points = []
  for code_point in code_points:
    folded_code_points = case_folding.get( code_point, code_point ).split( ' ' )
    for folded_code_point in folded_code_points:
      decomposed_code_point = Decompose( folded_code_point, unicode_data )
      decomposed_code_points.extend( decomposed_code_point )
  return decomposed_code_points


def GetCodePoints():
  code_points = []
  unicode_data = GetUnicodeData()
  break_data = GetGraphemeBreakProperty()
  special_folding = GetSpecialFolding()
  case_folding = GetCaseFolding()
  emoji_data = GetEmojiData()
  for key, value in unicode_data.items():
    general_category = value[ 'general_category' ]

    normal_code_points = Decompose( key, unicode_data )
    folded_code_points = Foldcase( normal_code_points,
                                   unicode_data,
                                   case_folding )
    lower_code_points = Lowercase( normal_code_points,
                                   unicode_data,
                                   special_folding )
    upper_code_points = Uppercase( normal_code_points,
                                   unicode_data,
                                   special_folding )

    code_point = UnicodeToUtf8( key )
    normal_code_point = JoinUnicodeToUtf8( normal_code_points )
    folded_code_point = JoinUnicodeToUtf8( folded_code_points )
    lower_code_point = JoinUnicodeToUtf8( lower_code_points )
    upper_code_point = JoinUnicodeToUtf8( upper_code_points )
    is_uppercase = normal_code_point != lower_code_point
    swapped_code_point = lower_code_point if is_uppercase else upper_code_point
    is_letter = general_category.startswith( 'L' )
    is_punctuation = general_category.startswith( 'P' )
    break_property = break_data.get( key, 'Other' )
    emoji_property = emoji_data.get( key, [] )
    if 'Extended_Pictographic' in emoji_property:
      if break_property == 'Other':
        break_property = 'ExtPict'
      else:
        raise RuntimeError( 'Cannot handle Extended_Pictographic combined with '
                            '{} property'.format( break_property ) )
    break_property = GRAPHEME_BREAK_PROPERTY_MAP[ break_property ]
    combining_class = int( value[ 'ccc' ] )
    # See https://unicode.org/reports/tr44/#General_Category_Values for the
    # list of categories.
    if ( code_point != normal_code_point or
         code_point != folded_code_point or
         code_point != swapped_code_point or
         is_letter or
         is_punctuation or
         is_uppercase or
         break_property or
         combining_class ):
      code_points.append( {
        'original': code_point,
        'normal': normal_code_point,
        'folded_case': folded_code_point,
        'swapped_case': swapped_code_point,
        'is_letter': is_letter,
        'is_punctuation': is_punctuation,
        'is_uppercase': is_uppercase,
        'break_property': break_property,
        'combining_class': combining_class
      } )
  return code_points


def CppChar( character ):
  return '"{}"'.format( character )


def CppBool( statement ):
  # We use 1/0 for C++ booleans instead of true/false to reduce the size of the
  # generated table.
  if statement:
    return '1'
  return '0'


# If a codepoint is written in hex (\x61) instead of a literal (a)
# then the backslash needs to be escaped in order for the correct
# string end up in the generated C++ file.
# To calculate the actual length for these, we can't count bytes.
# Instead, we split on '\\x', leaving only the an array of hex values.
# \\x61 would end up as [ '', '61' ]
def CppLength( utf8_code_point ):
  nb_utf8_hex = len( utf8_code_point.split( '\\x' )[ 1: ] )
  if nb_utf8_hex > 0:
    # +1 for NULL terminator
    return nb_utf8_hex + 1
  return len( bytearray( utf8_code_point, encoding = 'utf8' ) ) + 1


def GenerateUnicodeTable( header_path, code_points ):
  unicode_version = GetUnicodeVersion()
  size = len( code_points )
  table = {
    'original': { 'output': StringIO(), 'size': 0, 'converter': CppChar },
    'normal': { 'output': StringIO(), 'size': 0, 'converter': CppChar },
    'folded_case': { 'output': StringIO(), 'size': 0, 'converter': CppChar },
    'swapped_case': { 'output': StringIO(), 'size': 0, 'converter': CppChar },
    'is_letter': { 'output': StringIO(), 'converter': CppBool },
    'is_punctuation': { 'output': StringIO(), 'converter': CppBool },
    'is_uppercase': { 'output': StringIO(), 'converter': CppBool },
    'break_property': { 'output': StringIO(), 'converter': str },
    'combining_class': { 'output': StringIO(), 'converter': str },
  }

  for d in table.values():
    d[ 'output' ].write( '{{' )

  for code_point in code_points:
    for t, d in table.items():
      cp = code_point[ t ]
      d[ 'output' ].write( d[ 'converter' ]( cp ) )
      d[ 'output' ].write( ',' )
      if d[ 'converter' ] == CppChar:
        d[ 'size' ] = max( CppLength( cp ), d[ 'size' ] )

  for t, d in table.items():
    if t == 'combining_class':
      d[ 'output' ] = d[ 'output' ].getvalue().rstrip( ',' ) + '}}'
    else:
      d[ 'output' ] = d[ 'output' ].getvalue().rstrip( ',' ) + '}},'

  code_points = '\n'.join( [ table[ 'original' ][ 'output' ],
                             table[ 'normal' ][ 'output' ],
                             table[ 'folded_case' ][ 'output' ],
                             table[ 'swapped_case' ][ 'output' ],
                             table[ 'is_letter' ][ 'output' ],
                             table[ 'is_punctuation' ][ 'output' ],
                             table[ 'is_uppercase' ][ 'output' ],
                             table[ 'break_property' ][ 'output' ],
                             table[ 'combining_class' ][ 'output' ] ] )

  contents = UNICODE_TABLE_TEMPLATE.format(
    unicode_version = unicode_version,
    size = size,
    original_size = table[ 'original' ][ 'size' ],
    normal_size = table[ 'normal' ][ 'size' ],
    folded_case_size = table[ 'folded_case' ][ 'size' ],
    swapped_case_size = table[ 'swapped_case' ][ 'size' ],
    code_points = code_points )

  with open( header_path, 'w', newline = '\n', encoding='utf8' ) as header_file:
    header_file.write( contents )


def Main():
  code_points = GetCodePoints()
  table_path = p.join( DIR_OF_CPP_SOURCES, 'UnicodeTable.inc' )
  GenerateUnicodeTable( table_path, code_points )


if __name__ == '__main__':
  Main()
