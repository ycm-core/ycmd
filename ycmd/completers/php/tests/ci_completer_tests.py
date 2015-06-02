#!/usr/bin/env python
# -*- coding: utf-8 -*-
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

import os

from ycmd.server_utils import SetUpPythonPath
SetUpPythonPath()
from ycmd.tests.test_utils import Setup, BuildRequest
from webtest import TestApp
from nose.tools import with_setup
from hamcrest import assert_that, has_items, has_entry
from ycmd import handlers
import bottle

bottle.debug( True )

TEST_DIR = os.path.dirname( os.path.abspath( __file__ ) )
DATA_DIR = os.path.join( TEST_DIR, "testdata" )
PATH_TO_BASIC_TEST_FILE = os.path.join( DATA_DIR, "test.php" )
PATH_TO_INCL_TEST_FILE = os.path.join( DATA_DIR, "includes.php" )

# TODO: Test go to in current file
# TODO: Test go to in included and required file
# TODO: Test go to in general project file (? determine definition in ycmd)

def CompletionEntryMatcher( insertion_text ):
  return has_entry( 'insertion_text', insertion_text )

@with_setup( Setup )
def GetClassAttributes_test():
  app = TestApp( handlers.app )
  completion_data = BuildRequest( filepath = PATH_TO_BASIC_TEST_FILE,
                                  filetype = 'php',
                                  contents = open( PATH_TO_BASIC_TEST_FILE ).read(),
                                  line_num = 19,
                                  column_num = 16)

  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]
  assert_that( results, has_items( CompletionEntryMatcher( 'x' ),
                                   CompletionEntryMatcher( 'y' ), ) )


@with_setup( Setup )
def GetStaticClassAttributes_test():
  app = TestApp( handlers.app )
  completion_data = BuildRequest( filepath = PATH_TO_BASIC_TEST_FILE,
                                  filetype = 'php',
                                  contents = open( PATH_TO_BASIC_TEST_FILE ).read(),
                                  line_num = 23,
                                  column_num = 6)

  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]
  assert_that( results, has_items( CompletionEntryMatcher( 'c' ),
                                   CompletionEntryMatcher( 'members' ), ) )


@with_setup( Setup )
def CompleteBuiltinClass_test():
  app = TestApp( handlers.app )
  completion_data = BuildRequest( filepath = PATH_TO_BASIC_TEST_FILE,
                                  filetype = 'php',
                                  contents = open( PATH_TO_BASIC_TEST_FILE ).read(),
                                  line_num = 46,
                                  column_num = 5)

  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]
  assert_that( results, has_items( CompletionEntryMatcher( 'DateInterval' ),
                                   CompletionEntryMatcher( 'DatePeriod' ),
                                   CompletionEntryMatcher( 'DateTime' ),
                                   CompletionEntryMatcher( 'DateTimeImmutable' ),
                                   CompletionEntryMatcher( 'DateTimeZone' ), ) )


@with_setup( Setup )
def CompleteBuiltinFunction_test():
  app = TestApp( handlers.app )
  completion_data = BuildRequest( filepath = PATH_TO_BASIC_TEST_FILE,
                                  filetype = 'php',
                                  contents = open( PATH_TO_BASIC_TEST_FILE ).read(),
                                  line_num = 34,
                                  column_num = 7)

  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]
  assert_that( results, has_items( CompletionEntryMatcher( 'class_alias' ),
                                   CompletionEntryMatcher( 'class_exists' ),
                                   CompletionEntryMatcher( 'class_implements' ),
                                   CompletionEntryMatcher( 'class_parents' ),
                                   CompletionEntryMatcher( 'class_uses' ), ) )


@with_setup( Setup )
def CompleteFromIncludedFile_test():
  app = TestApp( handlers.app )
  
  # Check variables
  completion_data = BuildRequest( filepath = PATH_TO_INCL_TEST_FILE,
                                  filetype = 'php',
                                  contents = open( PATH_TO_INCL_TEST_FILE ).read(),
                                  line_num = 8,
                                  column_num = 11)

  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]
  assert_that( results, has_items( CompletionEntryMatcher( 'variable_a' ),
                                   CompletionEntryMatcher( 'variable_b' ),
                                   CompletionEntryMatcher( 'variable_c' ),
                                   CompletionEntryMatcher( 'variable_d' ), ) )
  
  # Check variables
  completion_data = BuildRequest( filepath = PATH_TO_INCL_TEST_FILE,
                                  filetype = 'php',
                                  contents = open( PATH_TO_INCL_TEST_FILE ).read(),
                                  line_num = 12,
                                  column_num = 9)

  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]
  assert_that( results, has_items( CompletionEntryMatcher( 'requiredFunction' ),
                                   CompletionEntryMatcher( 'requiredClass' ), ) )
  
  # Check variables
  completion_data = BuildRequest( filepath = PATH_TO_INCL_TEST_FILE,
                                  filetype = 'php',
                                  contents = open( PATH_TO_INCL_TEST_FILE ).read(),
                                  line_num = 16,
                                  column_num = 9)

  results = app.post_json( '/completions',
                           completion_data ).json[ 'completions' ]
  assert_that( results, has_items( CompletionEntryMatcher( 'includedFunction' ),
                                   CompletionEntryMatcher( 'includedClass' ), ) )