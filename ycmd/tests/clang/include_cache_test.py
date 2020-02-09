# Copyright (C) 2017 Davit Samvelyan davitsamvelyan@gmail.com
#                    Synopsys.
#               2020 ycmd contributors
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

import os
from time import sleep

from hamcrest import ( assert_that,
                       contains_exactly,
                       contains_inanyorder,
                       equal_to,
                       has_entries,
                       has_entry,
                       has_properties,
                       not_ )

from ycmd.completers.cpp.include_cache import IncludeCache
from ycmd.tests.clang import PathToTestFile
from ycmd.tests.test_utils import TemporaryTestDir


def IncludeCache_NotCached_DirInaccessible_test():
  include_cache = IncludeCache()
  assert_that( include_cache._cache, equal_to( {} ) )
  includes = include_cache.GetIncludes( PathToTestFile( 'unknown_dir' ) )
  assert_that( includes, equal_to( [] ) )
  assert_that( include_cache._cache, equal_to( {} ) )


def IncludeCache_NotCached_DirAccessible_test():
  include_cache = IncludeCache()
  assert_that( include_cache._cache, equal_to( {} ) )
  includes = include_cache.GetIncludes( PathToTestFile( 'cache_test' ) )
  mtime = os.path.getmtime( PathToTestFile( 'cache_test' ) )
  assert_that( includes, contains_exactly( has_properties( {
                                     'name': 'foo.h',
                                     'entry_type': 1
                                   } ) ) )
  assert_that( include_cache._cache,
               has_entry( PathToTestFile( 'cache_test' ),
                          has_entries( { 'mtime': mtime,
                            'includes': contains_exactly( has_properties( {
                                                    'name': 'foo.h',
                                                    'entry_type': 1
                                                  } ) ) } ) ) )


def IncludeCache_Cached_NoNewMtime_test():
  include_cache = IncludeCache()
  assert_that( include_cache._cache, equal_to( {} ) )
  old_includes = include_cache.GetIncludes( PathToTestFile( 'cache_test' ) )
  old_mtime = os.path.getmtime( PathToTestFile( 'cache_test' ) )

  assert_that( old_includes, contains_exactly( has_properties( {
                                         'name': 'foo.h',
                                         'entry_type': 1
                                       } ) ) )
  assert_that( include_cache._cache,
               has_entry( PathToTestFile( 'cache_test' ),
                          has_entries( { 'mtime': old_mtime,
                            'includes': contains_exactly( has_properties( {
                                                    'name': 'foo.h',
                                                    'entry_type': 1
                                                  } ) ) } ) ) )

  new_includes = include_cache.GetIncludes( PathToTestFile( 'cache_test' ) )
  new_mtime = os.path.getmtime( PathToTestFile( 'cache_test' ) )

  assert_that( new_mtime, equal_to( old_mtime ) )
  assert_that( new_includes, contains_exactly( has_properties( {
                                         'name': 'foo.h',
                                         'entry_type': 1
                                       } ) ) )
  assert_that( include_cache._cache,
               has_entry( PathToTestFile( 'cache_test' ),
                          has_entries( { 'mtime': new_mtime,
                            'includes': contains_exactly( has_properties( {
                                                    'name': 'foo.h',
                                                    'entry_type': 1
                                                  } ) ) } ) ) )


def IncludeCache_Cached_NewMtime_test():
  with TemporaryTestDir() as tmp_dir:
    include_cache = IncludeCache()
    assert_that( include_cache._cache, equal_to( {} ) )
    foo_path = os.path.join( tmp_dir, 'foo' )
    with open( foo_path, 'w' ) as foo_file:
      foo_file.write( 'foo' )

    old_includes = include_cache.GetIncludes( tmp_dir )
    old_mtime = os.path.getmtime( tmp_dir )
    assert_that( old_includes, contains_exactly( has_properties( {
                                           'name': 'foo',
                                           'entry_type': 1
                                         } ) ) )
    assert_that( include_cache._cache,
                 has_entry( tmp_dir,
                   has_entries( {
                     'mtime': old_mtime,
                     'includes': contains_exactly( has_properties( {
                       'name': 'foo',
                       'entry_type': 1
                     } ) )
                   } ) ) )

    sleep( 2 )

    bar_path = os.path.join( tmp_dir, 'bar' )
    with open( bar_path, 'w' ) as bar_file:
      bar_file.write( 'bar' )

    new_includes = include_cache.GetIncludes( tmp_dir )
    new_mtime = os.path.getmtime( tmp_dir )
    assert_that( old_mtime, not_( equal_to( new_mtime ) ) )
    assert_that( new_includes, contains_inanyorder(
                                 has_properties( {
                                   'name': 'foo',
                                   'entry_type': 1
                                 } ),
                                 has_properties( {
                                   'name': 'bar',
                                   'entry_type': 1
                                 } )
                               ) )
    assert_that( include_cache._cache,
        has_entry( tmp_dir, has_entries( {
                              'mtime': new_mtime,
                              'includes': contains_inanyorder(
                                has_properties( {
                                  'name': 'foo',
                                  'entry_type': 1
                                } ),
                                has_properties( {
                                  'name': 'bar',
                                  'entry_type': 1
                                } ) )
                            } ) ) )
