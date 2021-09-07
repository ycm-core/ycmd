# Copyright (C) 2021 ycmd contributors
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

from collections import defaultdict
from hamcrest import assert_that, equal_to, none
from unittest import TestCase

from ycmd.completers import completer_utils as cu
from ycmd.utils import re


def _ExtractPatternsFromFiletypeTriggerDict( triggerDict ):
  """Returns a copy of the dictionary with the _sre.SRE_Pattern instances in
  each set value replaced with the pattern strings. Needed for equality test of
  two filetype trigger dictionaries."""
  copy = triggerDict.copy()
  for key, values in triggerDict.items():
    copy[ key ] = { sre_pattern.pattern for sre_pattern in values }
  return copy


class CompleterUtilsTest( TestCase ):
  def test_FiletypeTriggerDictFromSpec_Works( self ):
    assert_that( defaultdict( set, {
                   'foo': { cu._PrepareTrigger( 'zoo' ).pattern,
                            cu._PrepareTrigger( 'bar' ).pattern },
                   'goo': { cu._PrepareTrigger( 'moo' ).pattern },
                   'moo': { cu._PrepareTrigger( 'moo' ).pattern },
                   'qux': { cu._PrepareTrigger( 'q' ).pattern }
                 } ),
                 equal_to( _ExtractPatternsFromFiletypeTriggerDict(
                   cu._FiletypeTriggerDictFromSpec( {
                     'foo': [ 'zoo', 'bar' ],
                     'goo,moo': [ 'moo' ],
                     'qux': [ 'q' ]
                   } ) ) ) )


  def test_FiletypeDictUnion_Works( self ):
    assert_that( defaultdict( set, {
                   'foo': { 'zoo', 'bar', 'maa' },
                   'goo': { 'moo' },
                   'bla': { 'boo' },
                   'qux': { 'q' }
                 } ),
                 equal_to( cu._FiletypeDictUnion( defaultdict( set, {
                   'foo': { 'zoo', 'bar' },
                   'goo': { 'moo' },
                   'qux': { 'q' }
                 } ), defaultdict( set, {
                   'foo': { 'maa' },
                   'bla': { 'boo' },
                   'qux': { 'q' }
                 } ) ) ) )


  def test_PrepareTrigger_UnicodeTrigger( self ):
    regex = cu._PrepareTrigger( 'æ' )
    assert_that( regex.pattern, equal_to( re.escape( 'æ' ) ) )


  def test_MatchingSemanticTrigger_Basic( self ):
    triggers = [ cu._PrepareTrigger( '.' ), cu._PrepareTrigger( ';' ),
                 cu._PrepareTrigger( '::' ) ]

    assert_that( cu._MatchingSemanticTrigger( 'foo->bar', 5, 9, triggers ),
                 none() )
    assert_that( cu._MatchingSemanticTrigger( 'foo::bar',
                                              5,
                                              9,
                                              triggers ).pattern,
                 equal_to( re.escape( '::' ) ) )


  def test_MatchingSemanticTrigger_JustTrigger( self ):
    triggers = [ cu._PrepareTrigger( '.' ) ]

    assert_that( cu._MatchingSemanticTrigger( '.', 2, 2, triggers ), none() )
    assert_that( cu._MatchingSemanticTrigger( '.', 1, 1, triggers ),
                 re.escape( '.' ) )
    assert_that( cu._MatchingSemanticTrigger( '.', 0, 0, triggers ), none() )


  def test_MatchingSemanticTrigger_TriggerBetweenWords( self ):
    triggers = [ cu._PrepareTrigger( '.' ) ]

    assert_that( cu._MatchingSemanticTrigger( 'foo . bar', 6, 9, triggers ),
                 none() )
    assert_that( cu._MatchingSemanticTrigger( 'foo . bar', 5, 9, triggers ),
                 re.escape( '.' ) )
    assert_that( cu._MatchingSemanticTrigger( 'foo . bar', 4, 9, triggers ),
                 re.escape( '.' ) )


  def test_MatchingSemanticTrigger_BadInput( self ):
    triggers = [ cu._PrepareTrigger( '.' ) ]

    assert_that( cu._MatchingSemanticTrigger( 'foo.bar', 10, 7, triggers ),
                 none() )
    assert_that( cu._MatchingSemanticTrigger( 'foo.bar', -1, 7, triggers ),
                 none() )
    assert_that( cu._MatchingSemanticTrigger( 'foo.bar', 4, -1, triggers ),
                 none() )
    assert_that( cu._MatchingSemanticTrigger( '', -1, 0, triggers ), none() )
    assert_that( cu._MatchingSemanticTrigger( '', 0, 0, triggers ), none() )
    assert_that( cu._MatchingSemanticTrigger( '', 1, 0, triggers ), none() )
    assert_that( cu._MatchingSemanticTrigger( 'foo.bar', 4, 7, [] ), none() )


  def test_MatchingSemanticTrigger_RegexTrigger( self ):
    triggers = [ cu._PrepareTrigger( r're!\w+\.' ) ]

    assert_that( cu._MatchingSemanticTrigger( 'foo.bar', 4, 8, triggers ),
                 re.escape( r'\w+\.' ) )
    assert_that( cu._MatchingSemanticTrigger( 'foo . bar', 5, 8, triggers ),
                 none() )


  def test_PreparedTriggers_Basic( self ):
    triggers = cu.PreparedTriggers()

    assert_that( triggers.MatchesForFiletype( 'foo.bar', 4, 8, 'c' ) )
    assert_that( triggers.MatchingTriggerForFiletype( 'foo.bar',
                                                      4,
                                                      8,
                                                      'c' ).pattern,
                 equal_to( re.escape( '.' ) ) )
    assert_that( triggers.MatchesForFiletype( 'foo->bar', 5, 9, 'cpp' ) )
    assert_that( triggers.MatchingTriggerForFiletype( 'foo->bar',
                                                      5,
                                                      9,
                                                      'cpp' ).pattern,
                 equal_to( re.escape( '->' ) ) )


  def test_PreparedTriggers_OnlySomeFiletypesSelected( self ):
    triggers = cu.PreparedTriggers( filetype_set = set( 'c' ) )

    assert_that( triggers.MatchesForFiletype( 'foo.bar', 4, 7, 'c' ) )
    assert_that( triggers.MatchingTriggerForFiletype( 'foo.bar',
                                                      4,
                                                      7,
                                                      'c' ).pattern,
                 equal_to( re.escape( '.' ) ) )
    assert_that( not triggers.MatchesForFiletype( 'foo->bar', 5, 8, 'cpp' ) )
    assert_that( triggers.MatchingTriggerForFiletype( 'foo->bar',
                                                      5,
                                                      8,
                                                      'cpp' ),
                 none() )


  def test_PreparedTriggers_UserTriggers( self ):
    triggers = cu.PreparedTriggers( user_trigger_map = { 'c': [ '->' ] } )

    assert_that( triggers.MatchesForFiletype( 'foo->bar', 5, 8, 'c' ) )
    assert_that( triggers.MatchingTriggerForFiletype( 'foo->bar',
                                                      5,
                                                      8,
                                                      'c' ).pattern,
                 equal_to( re.escape( '->' ) ) )


  def test_PreparedTriggers_ObjectiveC( self ):
    triggers = cu.PreparedTriggers()

    # Bracketed calls
    assert_that( triggers.MatchesForFiletype( '[foo ', 5, 6, 'objc' ) )
    assert_that( not triggers.MatchesForFiletype( '[foo', 4, 5, 'objc' ) )
    assert_that( not triggers.MatchesForFiletype( '[3foo ', 6, 6, 'objc' ) )
    assert_that( triggers.MatchesForFiletype( '[f3oo ', 6, 6, 'objc' ) )
    assert_that( triggers.MatchesForFiletype( '[[foo ', 6, 6, 'objc' ) )

    # Bracketless calls
    assert_that( not triggers.MatchesForFiletype( '3foo ', 5, 5, 'objc' ) )
    assert_that( triggers.MatchesForFiletype( 'foo3 ', 5, 5, 'objc' ) )
    assert_that( triggers.MatchesForFiletype( 'foo ', 4, 4, 'objc' ) )

    # Method composition
    assert_that( triggers.MatchesForFiletype(
        '[NSString stringWithFormat:@"Test %@", stuff] ', 46, 46, 'objc' ) )
    assert_that( triggers.MatchesForFiletype(
        '   [NSString stringWithFormat:@"Test"] ', 39, 39, 'objc' ) )
    assert_that( triggers.MatchesForFiletype(
        '   [[NSString stringWithFormat:@"Test"] stringByAppendingString:%@] ',
        68,
        68,
        'objc' ) )

    assert_that( not triggers.MatchesForFiletype( '// foo ', 8, 8, 'objc' ) )
