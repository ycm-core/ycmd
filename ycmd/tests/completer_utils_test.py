# Copyright (C) 2020 ycmd contributors
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


def FiletypeTriggerDictFromSpec_Works_test():
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


def FiletypeDictUnion_Works_test():
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


def PrepareTrigger_UnicodeTrigger_Test():
  regex = cu._PrepareTrigger( 'æ' )
  assert_that( regex.pattern, equal_to( re.escape( u'æ' ) ) )


def MatchesSemanticTrigger_Basic_test():
  triggers = [ cu._PrepareTrigger( '.' ) ]

  assert_that( not cu._MatchesSemanticTrigger( 'foo.bar', 7, 7, triggers ) )
  assert_that( not cu._MatchesSemanticTrigger( 'foo.bar', 6, 7, triggers ) )
  assert_that( not cu._MatchesSemanticTrigger( 'foo.bar', 5, 7, triggers ) )
  assert_that( cu._MatchesSemanticTrigger( 'foo.bar', 4, 7, triggers ) )
  assert_that( cu._MatchesSemanticTrigger( 'foo.bar', 3, 7, triggers ) )
  assert_that( cu._MatchesSemanticTrigger( 'foo.bar', 2, 7, triggers ) )
  assert_that( cu._MatchesSemanticTrigger( 'foo.bar', 1, 7, triggers ) )
  assert_that( cu._MatchesSemanticTrigger( 'foo.bar', 0, 7, triggers ) )

  assert_that( not cu._MatchesSemanticTrigger( 'foo.bar', 3, 3, triggers ) )
  assert_that( not cu._MatchesSemanticTrigger( 'foo.bar', 2, 3, triggers ) )
  assert_that( not cu._MatchesSemanticTrigger( 'foo.bar', 1, 3, triggers ) )
  assert_that( not cu._MatchesSemanticTrigger( 'foo.bar', 0, 3, triggers ) )


def MatchesSemanticTrigger_JustTrigger_test():
  triggers = [ cu._PrepareTrigger( '.' ) ]

  assert_that( not cu._MatchesSemanticTrigger( '.', 2, 2, triggers ) )
  assert_that( cu._MatchesSemanticTrigger( '.', 1, 1, triggers ) )
  assert_that( not cu._MatchesSemanticTrigger( '.', 0, 0, triggers ) )


def MatchesSemanticTrigger_TriggerBetweenWords_test():
  triggers = [ cu._PrepareTrigger( '.' ) ]

  assert_that( not cu._MatchesSemanticTrigger( 'foo . bar', 6, 9, triggers ) )
  assert_that( cu._MatchesSemanticTrigger( 'foo . bar', 5, 9, triggers ) )
  assert_that( cu._MatchesSemanticTrigger( 'foo . bar', 4, 9, triggers ) )


def MatchesSemanticTrigger_BadInput_test():
  triggers = [ cu._PrepareTrigger( '.' ) ]

  assert_that( not cu._MatchesSemanticTrigger( 'foo.bar', 10, 7, triggers ) )
  assert_that( not cu._MatchesSemanticTrigger( 'foo.bar', -1, 7, triggers ) )
  assert_that( not cu._MatchesSemanticTrigger( 'foo.bar', 4, -1, triggers ) )
  assert_that( not cu._MatchesSemanticTrigger( '', -1, 0, triggers ) )
  assert_that( not cu._MatchesSemanticTrigger( '', 0, 0, triggers ) )
  assert_that( not cu._MatchesSemanticTrigger( '', 1, 0, triggers ) )
  assert_that( not cu._MatchesSemanticTrigger( 'foo.bar', 4, 7, [] ) )


def MatchesSemanticTrigger_TriggerIsWrong_test():
  triggers = [ cu._PrepareTrigger( ':' ) ]

  assert_that( not cu._MatchesSemanticTrigger( 'foo.bar', 4, 7, triggers ) )


def MatchesSemanticTrigger_LongerTrigger_test():
  triggers = [ cu._PrepareTrigger( '::' ) ]

  assert_that( not cu._MatchesSemanticTrigger( 'foo::bar', 6, 8, triggers ) )
  assert_that( cu._MatchesSemanticTrigger( 'foo::bar', 5, 8, triggers ) )
  assert_that( cu._MatchesSemanticTrigger( 'foo::bar', 4, 8, triggers ) )
  assert_that( cu._MatchesSemanticTrigger( 'foo::bar', 3, 8, triggers ) )

  assert_that( not cu._MatchesSemanticTrigger( 'foo::bar', 4, 4, triggers ) )
  assert_that( not cu._MatchesSemanticTrigger( 'foo::bar', 3, 4, triggers ) )


def MatchesSemanticTrigger_OneTriggerMatches_test():
  triggers = [ cu._PrepareTrigger( '.' ),
               cu._PrepareTrigger( ';' ),
               cu._PrepareTrigger( '::' ) ]

  assert_that( cu._MatchesSemanticTrigger( 'foo::bar', 5, 8, triggers ) )


def MatchesSemanticTrigger_RegexTrigger_test():
  triggers = [ cu._PrepareTrigger( r're!\w+\.' ) ]

  assert_that( cu._MatchesSemanticTrigger( 'foo.bar', 4, 8, triggers ) )

  assert_that( not cu._MatchesSemanticTrigger( 'foo . bar', 5, 8, triggers ) )


def MatchingSemanticTrigger_Basic_test():
  triggers = [ cu._PrepareTrigger( '.' ), cu._PrepareTrigger( ';' ),
               cu._PrepareTrigger( '::' ) ]

  assert_that( cu._MatchingSemanticTrigger( 'foo->bar', 5, 9, triggers ),
               none() )
  assert_that( cu._MatchingSemanticTrigger( 'foo::bar',
                                            5,
                                            9,
                                            triggers ).pattern,
               equal_to( re.escape( '::' ) ) )


def PreparedTriggers_Basic_test():
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


def PreparedTriggers_OnlySomeFiletypesSelected_test():
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


def PreparedTriggers_UserTriggers_test():
  triggers = cu.PreparedTriggers( user_trigger_map = { 'c': [ '->' ] } )

  assert_that( triggers.MatchesForFiletype( 'foo->bar', 5, 8, 'c' ) )
  assert_that( triggers.MatchingTriggerForFiletype( 'foo->bar',
                                                    5,
                                                    8,
                                                    'c' ).pattern,
               equal_to( re.escape( '->' ) ) )


def PreparedTriggers_ObjectiveC_test():
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
