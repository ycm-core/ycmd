# coding: utf-8
#
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

# Intentionally not importing unicode_literals!
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa

from collections import defaultdict
from future.utils import iteritems
from nose.tools import eq_, ok_

from ycmd.completers import completer_utils as cu
from ycmd.utils import re


def _ExtractPatternsFromFiletypeTriggerDict( triggerDict ):
  """Returns a copy of the dictionary with the _sre.SRE_Pattern instances in
  each set value replaced with the pattern strings. Needed for equality test of
  two filetype trigger dictionaries."""
  copy = triggerDict.copy()
  for key, values in iteritems( triggerDict ):
    copy[ key ] = { sre_pattern.pattern for sre_pattern in values }
  return copy


def FiletypeTriggerDictFromSpec_Works_test():
  eq_( defaultdict( set, {
         'foo': { cu._PrepareTrigger( 'zoo' ).pattern,
                  cu._PrepareTrigger( 'bar' ).pattern },
         'goo': { cu._PrepareTrigger( 'moo' ).pattern },
         'moo': { cu._PrepareTrigger( 'moo' ).pattern },
         'qux': { cu._PrepareTrigger( 'q' ).pattern }
       } ),
       _ExtractPatternsFromFiletypeTriggerDict(
         cu._FiletypeTriggerDictFromSpec( {
           'foo': [ 'zoo', 'bar' ],
           'goo,moo': [ 'moo' ],
           'qux': [ 'q' ]
         } ) ) )


def FiletypeDictUnion_Works_test():
  eq_( defaultdict( set, {
         'foo': { 'zoo', 'bar', 'maa' },
         'goo': { 'moo' },
         'bla': { 'boo' },
         'qux': { 'q' }
       } ),
       cu._FiletypeDictUnion( defaultdict( set, {
         'foo': { 'zoo', 'bar' },
         'goo': { 'moo' },
         'qux': { 'q' }
       } ), defaultdict( set, {
         'foo': { 'maa' },
         'bla': { 'boo' },
         'qux': { 'q' }
       } ) ) )


def PrepareTrigger_UnicodeTrigger_Test():
  regex = cu._PrepareTrigger( 'æ' )
  eq_( regex.pattern, re.escape( u'æ' ) )


def MatchesSemanticTrigger_Basic_test():
  triggers = [ cu._PrepareTrigger( '.' ) ]

  ok_( not cu._MatchesSemanticTrigger( 'foo.bar', 7, 7, triggers ) )
  ok_( not cu._MatchesSemanticTrigger( 'foo.bar', 6, 7, triggers ) )
  ok_( not cu._MatchesSemanticTrigger( 'foo.bar', 5, 7, triggers ) )
  ok_( cu._MatchesSemanticTrigger( 'foo.bar', 4, 7, triggers ) )
  ok_( cu._MatchesSemanticTrigger( 'foo.bar', 3, 7, triggers ) )
  ok_( cu._MatchesSemanticTrigger( 'foo.bar', 2, 7, triggers ) )
  ok_( cu._MatchesSemanticTrigger( 'foo.bar', 1, 7, triggers ) )
  ok_( cu._MatchesSemanticTrigger( 'foo.bar', 0, 7, triggers ) )

  ok_( not cu._MatchesSemanticTrigger( 'foo.bar', 3, 3, triggers ) )
  ok_( not cu._MatchesSemanticTrigger( 'foo.bar', 2, 3, triggers ) )
  ok_( not cu._MatchesSemanticTrigger( 'foo.bar', 1, 3, triggers ) )
  ok_( not cu._MatchesSemanticTrigger( 'foo.bar', 0, 3, triggers ) )


def MatchesSemanticTrigger_JustTrigger_test():
  triggers = [ cu._PrepareTrigger( '.' ) ]

  ok_( not cu._MatchesSemanticTrigger( '.', 2, 2, triggers ) )
  ok_( cu._MatchesSemanticTrigger( '.', 1, 1, triggers ) )
  ok_( not cu._MatchesSemanticTrigger( '.', 0, 0, triggers ) )


def MatchesSemanticTrigger_TriggerBetweenWords_test():
  triggers = [ cu._PrepareTrigger( '.' ) ]

  ok_( not cu._MatchesSemanticTrigger( 'foo . bar', 6, 9, triggers ) )
  ok_( cu._MatchesSemanticTrigger( 'foo . bar', 5, 9, triggers ) )
  ok_( cu._MatchesSemanticTrigger( 'foo . bar', 4, 9, triggers ) )


def MatchesSemanticTrigger_BadInput_test():
  triggers = [ cu._PrepareTrigger( '.' ) ]

  ok_( not cu._MatchesSemanticTrigger( 'foo.bar', 10, 7, triggers ) )
  ok_( not cu._MatchesSemanticTrigger( 'foo.bar', -1, 7, triggers ) )
  ok_( not cu._MatchesSemanticTrigger( 'foo.bar', 4, -1, triggers ) )
  ok_( not cu._MatchesSemanticTrigger( '', -1, 0, triggers ) )
  ok_( not cu._MatchesSemanticTrigger( '', 0, 0, triggers ) )
  ok_( not cu._MatchesSemanticTrigger( '', 1, 0, triggers ) )
  ok_( not cu._MatchesSemanticTrigger( 'foo.bar', 4, 7, [] ) )


def MatchesSemanticTrigger_TriggerIsWrong_test():
  triggers = [ cu._PrepareTrigger( ':' ) ]

  ok_( not cu._MatchesSemanticTrigger( 'foo.bar', 4, 7, triggers ) )


def MatchesSemanticTrigger_LongerTrigger_test():
  triggers = [ cu._PrepareTrigger( '::' ) ]

  ok_( not cu._MatchesSemanticTrigger( 'foo::bar', 6, 8, triggers ) )
  ok_( cu._MatchesSemanticTrigger( 'foo::bar', 5, 8, triggers ) )
  ok_( cu._MatchesSemanticTrigger( 'foo::bar', 4, 8, triggers ) )
  ok_( cu._MatchesSemanticTrigger( 'foo::bar', 3, 8, triggers ) )

  ok_( not cu._MatchesSemanticTrigger( 'foo::bar', 4, 4, triggers ) )
  ok_( not cu._MatchesSemanticTrigger( 'foo::bar', 3, 4, triggers ) )


def MatchesSemanticTrigger_OneTriggerMatches_test():
  triggers = [ cu._PrepareTrigger( '.' ),
               cu._PrepareTrigger( ';' ),
               cu._PrepareTrigger( '::' ) ]

  ok_( cu._MatchesSemanticTrigger( 'foo::bar', 5, 8, triggers ) )


def MatchesSemanticTrigger_RegexTrigger_test():
  triggers = [ cu._PrepareTrigger( r're!\w+\.' ) ]

  ok_( cu._MatchesSemanticTrigger( 'foo.bar', 4, 8, triggers ) )

  ok_( not cu._MatchesSemanticTrigger( 'foo . bar', 5, 8, triggers ) )


def MatchingSemanticTrigger_Basic_test():
  triggers = [ cu._PrepareTrigger( '.' ), cu._PrepareTrigger( ';' ),
               cu._PrepareTrigger( '::' ) ]

  eq_( cu._MatchingSemanticTrigger( 'foo->bar', 5, 9, triggers ), None )
  eq_( cu._MatchingSemanticTrigger( 'foo::bar', 5, 9, triggers ).pattern,
       re.escape( '::' ) )


def PreparedTriggers_Basic_test():
  triggers = cu.PreparedTriggers()

  ok_( triggers.MatchesForFiletype( 'foo.bar', 4, 8, 'c' ) )
  eq_( triggers.MatchingTriggerForFiletype( 'foo.bar', 4, 8, 'c' ).pattern,
       re.escape( '.' ) )
  ok_( triggers.MatchesForFiletype( 'foo->bar', 5, 9, 'cpp' ) )
  eq_( triggers.MatchingTriggerForFiletype( 'foo->bar', 5, 9, 'cpp' ).pattern,
       re.escape( '->' ) )


def PreparedTriggers_OnlySomeFiletypesSelected_test():
  triggers = cu.PreparedTriggers( filetype_set = set( 'c' ) )

  ok_( triggers.MatchesForFiletype( 'foo.bar', 4, 7, 'c' ) )
  eq_( triggers.MatchingTriggerForFiletype( 'foo.bar', 4, 7, 'c' ).pattern,
       re.escape( '.' ) )
  ok_( not triggers.MatchesForFiletype( 'foo->bar', 5, 8, 'cpp' ) )
  eq_( triggers.MatchingTriggerForFiletype( 'foo->bar', 5, 8, 'cpp' ),
       None )


def PreparedTriggers_UserTriggers_test():
  triggers = cu.PreparedTriggers( user_trigger_map = { 'c': [ '->' ] } )

  ok_( triggers.MatchesForFiletype( 'foo->bar', 5, 8, 'c' ) )
  eq_( triggers.MatchingTriggerForFiletype( 'foo->bar', 5, 8, 'c' ).pattern,
       re.escape( '->' ) )


def PreparedTriggers_ObjectiveC_test():
  triggers = cu.PreparedTriggers()

  # Bracketed calls
  ok_( triggers.MatchesForFiletype( '[foo ', 5, 6, 'objc' ) )
  ok_( not triggers.MatchesForFiletype( '[foo', 4, 5, 'objc' ) )
  ok_( not triggers.MatchesForFiletype( '[3foo ', 6, 6, 'objc' ) )
  ok_( triggers.MatchesForFiletype( '[f3oo ', 6, 6, 'objc' ) )
  ok_( triggers.MatchesForFiletype( '[[foo ', 6, 6, 'objc' ) )

  # Bracketless calls
  ok_( not triggers.MatchesForFiletype( '3foo ', 5, 5, 'objc' ) )
  ok_( triggers.MatchesForFiletype( 'foo3 ', 5, 5, 'objc' ) )
  ok_( triggers.MatchesForFiletype( 'foo ', 4, 4, 'objc' ) )

  # Method composition
  ok_( triggers.MatchesForFiletype(
      '[NSString stringWithFormat:@"Test %@", stuff] ', 46, 46, 'objc' ) )
  ok_( triggers.MatchesForFiletype(
      '   [NSString stringWithFormat:@"Test"] ', 39, 39, 'objc' ) )
  ok_( triggers.MatchesForFiletype(
      '   [[NSString stringWithFormat:@"Test"] stringByAppendingString:%@] ',
      68,
      68,
      'objc' ) )

  ok_( not triggers.MatchesForFiletype( '// foo ', 8, 8, 'objc' ) )
