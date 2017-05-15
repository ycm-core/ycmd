# Copyright (C) 2017 ycmd contributors
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

from hamcrest import assert_that, equal_to

from ycmd.completers.swift.swift_flags import Flags
from ycmd.tests.swift import PathToTestFile
from ycmd.tests.swift import BasicTest


EXAMPLE_DIR = 'iOS/Basic/Basic/'


def BasicExampleNamed( file_name ):
  return PathToTestFile( EXAMPLE_DIR, file_name )


@BasicTest
def Basic_flags_test():
  test_file = BasicExampleNamed( 'AppDelegate.swift' )
  cmds = Flags().FlagsForFile( test_file )
  assert_that( cmds[ 0 ], equal_to( '-primary-file' ) )
  assert_that( cmds[ 1 ], equal_to( test_file ) )


@BasicTest
def PrimaryFile_dependent_flags_test():
  test_file = BasicExampleNamed( 'ViewController.swift' )
  cmds = Flags().FlagsForFile( test_file )
  assert_that( cmds[ 0 ], equal_to( '-primary-file' ) )
  assert_that( cmds[ 1 ], equal_to( test_file ) )
  # This file is a 'primary-file' of ViewController
  assert_that( cmds[ 2 ], equal_to( BasicExampleNamed( 'AppDelegate.swift' ) ) )


@BasicTest
def PrimaryFile_dependent_flags_caching_test():
  dep_file = BasicExampleNamed( 'AppDelegate.swift' )
  test_file = BasicExampleNamed( 'ViewController.swift' )
  flags = Flags()
  cmds = flags.FlagsForFile( dep_file )
  cmds = flags.FlagsForFile( test_file )
  assert_that( cmds[ 0 ], equal_to( '-primary-file' ) )
  assert_that( cmds[ 1 ], equal_to( test_file ) )
  assert_that( cmds[ 2 ], equal_to( dep_file ) )
