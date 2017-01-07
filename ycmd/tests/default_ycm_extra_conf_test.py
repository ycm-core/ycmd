# Copyright (C) 2016 ycmd contributors.
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

from hamcrest import assert_that, contains

import tempfile

from ycmd import extra_conf_store
# NOTE: We must not import default_ycm_extra_conf directly;  we
# don't want Python to generate a .pyc or __pycache__ entry for it.
#
# This is because the extra_conf_store turns off such generation and its tests
# require that the filename of the loaded module is the py file not any
# associated pyc file.


class DefaultYcmExtraConf_test():
  def __init__( self ):
    self.mod = None


  def setUp( self ):
    extra_conf_store.Reset()
    self.mod = extra_conf_store.ModuleForSourceFile(
      extra_conf_store._RandomName() )


  def _MakeRelativePathsInFlagsAvsoluteTest( self, test ):
    wd = test[ 'wd' ] if 'wd' in test else tempfile.gettempdir()
    assert_that(
      self.mod.MakeRelativePathsInFlagsAbsolute( test[ 'flags' ], wd ),
      contains( *test[ 'expect' ] ) )


  def MakeRelativePathsInFlagsAbsolute_test( self ):
    tests = [
      # Already absolute, positional arguments
      {
        'flags':  [ '-isystem', '/test' ],
        'expect': [ '-isystem', '/test' ],
      },
      {
        'flags':  [ '-I', '/test' ],
        'expect': [ '-I', '/test' ],
      },
      {
        'flags':  [ '-iquote', '/test' ],
        'expect': [ '-iquote', '/test' ],
      },
      {
        'flags':  [ '-isysroot', '/test' ],
        'expect': [ '-isysroot', '/test' ],
      },

      # Already absolute, single arguments
      {
        'flags':  [ '-isystem/test' ],
        'expect': [ '-isystem/test' ],
      },
      {
        'flags':  [ '-I/test' ],
        'expect': [ '-I/test' ],
      },
      {
        'flags':  [ '-iquote/test' ],
        'expect': [ '-iquote/test' ],
      },
      {
        'flags':  [ '-isysroot/test' ],
        'expect': [ '-isysroot/test' ],
      },

      # Already absolute, double-dash arguments
      {
        'flags':  [ '--isystem=/test' ],
        'expect': [ '--isystem=/test' ],
      },
      {
        'flags':  [ '--I=/test' ],
        'expect': [ '--I=/test' ],
      },
      {
        'flags':  [ '--iquote=/test' ],
        'expect': [ '--iquote=/test' ],
      },
      {
        'flags':  [ '--sysroot=/test' ],
        'expect': [ '--sysroot=/test' ],
      },

      # Relative, positional arguments
      {
        'flags':  [ '-isystem', 'test' ],
        'expect': [ '-isystem', '/test/test' ],
        'wd':     '/test',
      },
      {
        'flags':  [ '-I', 'test' ],
        'expect': [ '-I', '/test/test' ],
        'wd':     '/test',
      },
      {
        'flags':  [ '-iquote', 'test' ],
        'expect': [ '-iquote', '/test/test' ],
        'wd':     '/test',
      },
      {
        'flags':  [ '-isysroot', 'test' ],
        'expect': [ '-isysroot', '/test/test' ],
        'wd':     '/test',
      },

      # Relative, single arguments
      {
        'flags':  [ '-isystemtest' ],
        'expect': [ '-isystem/test/test' ],
        'wd':     '/test',
      },
      {
        'flags':  [ '-Itest' ],
        'expect': [ '-I/test/test' ],
        'wd':     '/test',
      },
      {
        'flags':  [ '-iquotetest' ],
        'expect': [ '-iquote/test/test' ],
        'wd':     '/test',
      },
      {
        'flags':  [ '-isysroottest' ],
        'expect': [ '-isysroot/test/test' ],
        'wd':     '/test',
      },

      # Already absolute, double-dash arguments
      {
        'flags':  [ '--isystem=test' ],
        'expect': [ '--isystem=test' ],
        'wd':     '/test',
      },
      {
        'flags':  [ '--I=test' ],
        'expect': [ '--I=test' ],
        'wd':     '/test',
      },
      {
        'flags':  [ '--iquote=test' ],
        'expect': [ '--iquote=test' ],
        'wd':     '/test',
      },
      {
        'flags':  [ '--sysroot=test' ],
        'expect': [ '--sysroot=/test/test' ],
        'wd':     '/test',
      },
    ]

    for test in tests:
      yield self._MakeRelativePathsInFlagsAvsoluteTest, test


  def MakeRelativePathsInFlagsAbsolute_IgnoreUnknown_test( self ):
    tests = [
      {
        'flags': [
          'ignored',
          '-isystem',
          '/test',
          '-ignored',
          '-I',
          '/test',
          '--ignored=ignored'
        ],
        'expect': [
          'ignored',
          '-isystem',
          '/test',
          '-ignored',
          '-I',
          '/test',
          '--ignored=ignored'
        ]
      },
      {
        'flags': [
          'ignored',
          '-isystem/test',
          '-ignored',
          '-I/test',
          '--ignored=ignored'
        ],
        'expect': [
          'ignored',
          '-isystem/test',
          '-ignored',
          '-I/test',
          '--ignored=ignored'
        ]
      },
      {
        'flags': [
          'ignored',
          '--isystem=/test',
          '-ignored',
          '--I=/test',
          '--ignored=ignored'
        ],
        'expect': [
          'ignored',
          '--isystem=/test',
          '-ignored',
          '--I=/test',
          '--ignored=ignored'
        ]
      },
      {
        'flags': [
          'ignored',
          '-isystem', 'test',
          '-ignored',
          '-I', 'test',
          '--ignored=ignored'
        ],
        'expect': [
          'ignored',
          '-isystem', '/test/test',
          '-ignored',
          '-I', '/test/test',
          '--ignored=ignored'
        ],
        'wd': '/test',
      },
      {
        'flags': [
          'ignored',
          '-isystemtest',
          '-ignored',
          '-Itest',
          '--ignored=ignored'
        ],
        'expect': [
          'ignored',
          '-isystem/test/test',
          '-ignored',
          '-I/test/test',
          '--ignored=ignored'
        ],
        'wd': '/test',
      },
      {
        'flags': [
          'ignored',
          '--isystem=test',
          '-ignored',
          '--I=test',
          '--ignored=ignored',
          '--sysroot=test'
        ],
        'expect': [
          'ignored',
          '--isystem=test',
          '-ignored',
          '--I=test',
          '--ignored=ignored',
          '--sysroot=/test/test'
        ],
        'wd': '/test',
      },
    ]

    for test in tests:
      yield self._MakeRelativePathsInFlagsAvsoluteTest, test
