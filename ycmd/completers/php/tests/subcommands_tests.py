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

from ycmd.server_utils import SetUpPythonPath
SetUpPythonPath()
from ycmd.tests.test_utils import ( Setup, BuildRequest )
from webtest import TestApp
from nose.tools import eq_, with_setup
from ycmd import handlers
import bottle
import os

bottle.debug( True )

TEST_DIR = os.path.dirname( os.path.abspath( __file__ ) )
DATA_DIR = os.path.join( TEST_DIR, "testdata" )
PATH_TO_BASIC_TEST_FILE = os.path.join( DATA_DIR, "test.php" )
PATH_TO_INCL_TEST_FILE = os.path.join( DATA_DIR, "includes.php" )
PATH_TO_INCLUDED_TEST_FILE = os.path.join( DATA_DIR, "included.php" )
PATH_TO_REQUIRED_TEST_FILE = os.path.join( DATA_DIR, "required.php" )

# TODO: Test go to in included and required file
# TODO: Test go to in general project file (? determine definition in ycmd)


@with_setup( Setup )
def DefinedSubcommands_Works_test():
  app = TestApp( handlers.app )
  subcommands_data = BuildRequest( completer_target = 'php' )

  eq_( [ 'GoTo' ],
       app.post_json( '/defined_subcommands', subcommands_data ).json )


@with_setup( Setup )
def DefinedSubcommands_WorksWhenNoExplicitCompleterTargetSpecified_test():
  app = TestApp( handlers.app )
  subcommands_data = BuildRequest( filetype = 'php' )

  eq_( [ 'GoTo' ],
       app.post_json( '/defined_subcommands', subcommands_data ).json )


@with_setup( Setup )
def RunCompleterCommand_GoTo_CodeIntelCompleter_test():
  app = TestApp( handlers.app )
  filepath = PATH_TO_BASIC_TEST_FILE
  with open( filepath, 'r' ) as src_file:
    contents = src_file.read()

  goto_data = BuildRequest( completer_target = 'filetype_default',
                            command_arguments = ['GoTo'],
                            line_num = 23,
                            column_num = 6,
                            contents = contents,
                            filetype = 'php',
                            filepath = filepath )

  eq_( {
         'filepath': filepath,
         'line_num': 3,
         'column_num': 1
       },
       app.post_json( '/run_completer_command', goto_data ).json )
 

@with_setup( Setup )
def RunCompleterCommand_GoTo_IncludedFile_CodeIntelCompleter_test():
  app = TestApp( handlers.app )
  filepath = PATH_TO_INCL_TEST_FILE
  with open( filepath, 'r' ) as src_file:
    contents = src_file.read()

  goto_data = BuildRequest( completer_target = 'filetype_default',
                            command_arguments = ['GoTo'],
                            line_num = 24,
                            column_num = 23,
                            contents = contents,
                            filetype = 'php',
                            filepath = filepath )

  eq_( {
         'filepath': PATH_TO_INCLUDED_TEST_FILE,
         'line_num': 10,
         'column_num': 1
       },
       app.post_json( '/run_completer_command', goto_data ).json )


@with_setup( Setup )
def RunCompleterCommand_GoTo_RequiredFile_CodeIntelCompleter_test():
  app = TestApp( handlers.app )
  filepath = PATH_TO_INCL_TEST_FILE
  with open( filepath, 'r' ) as src_file:
    contents = src_file.read()

  goto_data = BuildRequest( completer_target = 'filetype_default',
                            command_arguments = ['GoTo'],
                            line_num = 20,
                            column_num = 22,
                            contents = contents,
                            filetype = 'php',
                            filepath = filepath )

  eq_( {
         'filepath': PATH_TO_REQUIRED_TEST_FILE,
         'line_num': 6,
         'column_num': 1
       },
       app.post_json( '/run_completer_command', goto_data ).json )