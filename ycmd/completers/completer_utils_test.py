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
from nose.tools import eq_, ok_
from ycmd.completers import completer_utils as cu


def _ExtractPatternsFromFiletypeTriggerDict( triggerDict ):
  """Returns a copy of the dictionary with the _sre.SRE_Pattern instances in 
  each set value replaced with the pattern strings. Needed for equality test of
  two filetype trigger dictionaries."""
  copy = triggerDict.copy()
  for key, values in triggerDict.items():
    copy[ key ] = set( [ sre_pattern.pattern for sre_pattern in values ] )
  return copy


def FiletypeTriggerDictFromSpec_Works_test():
  eq_( defaultdict( set, {
         'foo': set( [ cu._PrepareTrigger( 'zoo').pattern,
                       cu._PrepareTrigger( 'bar' ).pattern ] ),
         'goo': set( [ cu._PrepareTrigger( 'moo' ).pattern ] ),
         'moo': set( [ cu._PrepareTrigger( 'moo' ).pattern ] ),
         'qux': set( [ cu._PrepareTrigger( 'q' ).pattern ] )
       } ),
       _ExtractPatternsFromFiletypeTriggerDict(
         cu._FiletypeTriggerDictFromSpec( {
           'foo': ['zoo', 'bar'],
           'goo,moo': ['moo'],
           'qux': ['q']
       } ) ) )


def FiletypeDictUnion_Works_test():
  eq_( defaultdict( set, {
         'foo': set(['zoo', 'bar', 'maa']),
         'goo': set(['moo']),
         'bla': set(['boo']),
         'qux': set(['q'])
       } ),
       cu._FiletypeDictUnion( defaultdict( set, {
         'foo': set(['zoo', 'bar']),
         'goo': set(['moo']),
         'qux': set(['q'])
       } ), defaultdict( set, {
         'foo': set(['maa']),
         'bla': set(['boo']),
         'qux': set(['q'])
       } ) ) )


def MatchesSemanticTrigger_Basic_test():
  ok_( not cu._MatchesSemanticTrigger( 'foo.bar', 7, ['.'] ) )
  ok_( not cu._MatchesSemanticTrigger( 'foo.bar', 6, ['.'] ) )
  ok_( not cu._MatchesSemanticTrigger( 'foo.bar', 5, ['.'] ) )

  ok_( cu._MatchesSemanticTrigger( 'foo.bar', 4, ['.'] ) )

  ok_( not cu._MatchesSemanticTrigger( 'foo.bar', 3, ['.'] ) )
  ok_( not cu._MatchesSemanticTrigger( 'foo.bar', 2, ['.'] ) )
  ok_( not cu._MatchesSemanticTrigger( 'foo.bar', 1, ['.'] ) )
  ok_( not cu._MatchesSemanticTrigger( 'foo.bar', 0, ['.'] ) )


def MatchesSemanticTrigger_JustTrigger_test():
  ok_( cu._MatchesSemanticTrigger( '.', 1, ['.'] ) )
  ok_( not cu._MatchesSemanticTrigger( '.', 0, ['.'] ) )


def MatchesSemanticTrigger_TriggerBetweenWords_test():
  ok_( cu._MatchesSemanticTrigger( 'foo . bar', 5, ['.'] ) )


def MatchesSemanticTrigger_BadInput_test():
  ok_( not cu._MatchesSemanticTrigger( 'foo.bar', 10, ['.'] ) )
  ok_( not cu._MatchesSemanticTrigger( 'foo.bar', -1, ['.'] ) )
  ok_( not cu._MatchesSemanticTrigger( '', -1, ['.'] ) )
  ok_( not cu._MatchesSemanticTrigger( '', 0, ['.'] ) )
  ok_( not cu._MatchesSemanticTrigger( '', 1, ['.'] ) )
  ok_( not cu._MatchesSemanticTrigger( 'foo.bar', 4, [] ) )


def MatchesSemanticTrigger_TriggerIsWrong_test():
  ok_( not cu._MatchesSemanticTrigger( 'foo.bar', 4, [':'] ) )


def MatchesSemanticTrigger_LongerTrigger_test():
  ok_( cu._MatchesSemanticTrigger( 'foo::bar', 5, ['::'] ) )
  ok_( not cu._MatchesSemanticTrigger( 'foo::bar', 4, ['::'] ) )


def MatchesSemanticTrigger_OneTriggerMatches_test():
  ok_( cu._MatchesSemanticTrigger( 'foo::bar', 5, ['.', ';', '::'] ) )


def MatchesSemanticTrigger_RegexTrigger_test():
  ok_( cu._MatchesSemanticTrigger( 'foo.bar',
                                   4,
                                   [ cu._PrepareTrigger( r're!\w+\.' ) ] ) )

  ok_( not cu._MatchesSemanticTrigger( 'foo . bar',
                                       5,
                                       [ cu._PrepareTrigger( r're!\w+\.' ) ] ) )


def PreparedTriggers_Basic_test():
  triggers = cu.PreparedTriggers()
  ok_( triggers.MatchesForFiletype( 'foo.bar', 4, 'c' ) )
  ok_( triggers.MatchesForFiletype( 'foo->bar', 5, 'cpp' ) )


def PreparedTriggers_OnlySomeFiletypesSelected_test():
  triggers = cu.PreparedTriggers( filetype_set = set( 'c' ) )
  ok_( triggers.MatchesForFiletype( 'foo.bar', 4, 'c' ) )
  ok_( not triggers.MatchesForFiletype( 'foo->bar', 5, 'cpp' ) )


def PreparedTriggers_UserTriggers_test():
  triggers = cu.PreparedTriggers( user_trigger_map = { 'c': ['->'] } )
  ok_( triggers.MatchesForFiletype( 'foo->bar', 5, 'c' ) )


def PreparedTriggers_ObjectiveC_test():
  triggers = cu.PreparedTriggers()
  # bracketed calls
  ok_( triggers.MatchesForFiletype( '[foo ', 5, 'objc' ) )
  ok_( not triggers.MatchesForFiletype( '[foo', 4, 'objc' ) )
  ok_( not triggers.MatchesForFiletype( '[3foo ', 6, 'objc' ) )
  ok_( triggers.MatchesForFiletype( '[f3oo ', 6, 'objc' ) )
  ok_( triggers.MatchesForFiletype( '[[foo ', 6, 'objc' ) )

  # bracketless calls
  ok_( not triggers.MatchesForFiletype( '3foo ', 5, 'objc' ) )
  ok_( triggers.MatchesForFiletype( 'foo3 ', 5, 'objc' ) )
  ok_( triggers.MatchesForFiletype( 'foo ', 4, 'objc' ) )

  # method composition
  ok_( triggers.MatchesForFiletype(
      '[NSString stringWithFormat:@"Test %@", stuff] ', 46, 'objc' ) )
  ok_( triggers.MatchesForFiletype(
      '   [NSString stringWithFormat:@"Test"] ', 39, 'objc' ) )
  ok_( triggers.MatchesForFiletype(
      '   [[NSString stringWithFormat:@"Test"] stringByAppendingString:%@] ',
      68,
      'objc' ) )

  ok_( not triggers.MatchesForFiletype( '// foo ', 8, 'objc' ) )

