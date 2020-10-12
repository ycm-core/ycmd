# Copyright (C) 2016-2020 ycmd contributors.
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

from ycmd.tests.test_utils import DummyCompleter
from ycmd.user_options_store import DefaultOptions
from unittest.mock import patch
from hamcrest import assert_that, contains_exactly, equal_to


def _FilterAndSortCandidates_Match( candidates, query, expected_matches ):
  completer = DummyCompleter( DefaultOptions() )
  matches = completer.FilterAndSortCandidates( candidates, query )
  assert_that( expected_matches, equal_to( matches ) )


def FilterAndSortCandidates_OmniCompleter_List_test():
  _FilterAndSortCandidates_Match( [ 'password' ],
                                  'p',
                                  [ 'password' ] )
  _FilterAndSortCandidates_Match( [ 'words' ],
                                  'w',
                                  [ 'words' ] )


def FilterAndSortCandidates_OmniCompleter_Dictionary_test():
  _FilterAndSortCandidates_Match( { 'words': [ 'password' ] },
                                  'p',
                                  [ 'password' ] )
  _FilterAndSortCandidates_Match( { 'words': [ { 'word': 'password' } ] },
                                  'p',
                                  [ { 'word': 'password' } ] )


def FilterAndSortCandidates_ServerCompleter_test():
  _FilterAndSortCandidates_Match( [ { 'insertion_text': 'password' } ],
                                  'p',
                                  [ { 'insertion_text': 'password' } ] )


def FilterAndSortCandidates_SortOnEmptyQuery_test():
  _FilterAndSortCandidates_Match( [ 'foo', 'bar' ],
                                  '',
                                  [ 'bar', 'foo' ] )


def FilterAndSortCandidates_IgnoreEmptyCandidate_test():
  _FilterAndSortCandidates_Match( [ '' ],
                                  '',
                                  [] )


def FilterAndSortCandidates_Unicode_test():
  _FilterAndSortCandidates_Match( [ { 'insertion_text': 'ø' } ],
                                  'ø',
                                  [ { 'insertion_text': 'ø' } ] )


@patch( 'ycmd.tests.test_utils.DummyCompleter.GetSubcommandsMap',
        return_value = { 'Foo': '', 'StopServer': '' } )
def DefinedSubcommands_RemoveStopServerSubcommand_test( subcommands_map ):
  completer = DummyCompleter( DefaultOptions() )
  assert_that( completer.DefinedSubcommands(), contains_exactly( 'Foo' ) )


def Dummy_test():
  # Workaround for https://github.com/pytest-dev/pytest-rerunfailures/issues/51
  assert True
