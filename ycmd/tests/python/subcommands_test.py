#!/usr/bin/env python
#
# Copyright (C) 2015 ycmd contributors.
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

from ...server_utils import SetUpPythonPath
SetUpPythonPath()
from ..test_utils import Setup, BuildRequest
from .utils import PathToTestFile
from webtest import TestApp
from nose.tools import eq_, with_setup
from ... import handlers
import bottle
import os.path

bottle.debug( True )


@with_setup( Setup )
def RunCompleterCommand_GoTo_Python_ZeroBasedLineAndColumn_test():
  app = TestApp( handlers.app )
  contents = """
def foo():
  pass

foo()
"""

  goto_data = BuildRequest( completer_target = 'filetype_default',
                            command_arguments = ['GoToDefinition'],
                            line_num = 5,
                            contents = contents,
                            filetype = 'python',
                            filepath = '/foo.py' )

  eq_( {
    'filepath': os.path.abspath( '/foo.py' ),
    'line_num': 2,
    'column_num': 5
  }, app.post_json( '/run_completer_command', goto_data ).json )


@with_setup( Setup )
def RunCompleterCommand_GetDoc_Python_Works_Method_test():
  # Testcase1
  app = TestApp( handlers.app )

  filepath = PathToTestFile( 'GetDoc.py' )
  contents = open( filepath ).read()

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'python',
                             line_num = 17,
                             column_num = 9,
                             contents = contents,
                             command_arguments = [ 'GetDoc' ],
                             completer_target = 'filetype_default' )

  response = app.post_json( '/run_completer_command', event_data ).json

  eq_( response, {
    'detailed_info': '_ModuleMethod()\n\n'
                     'Module method docs\n'
                     'Are dedented, like you might expect',
  } )


@with_setup( Setup )
def RunCompleterCommand_GetDoc_Python_Works_Class_test():
  # Testcase1
  app = TestApp( handlers.app )

  filepath = PathToTestFile( 'GetDoc.py' )
  contents = open( filepath ).read()

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'python',
                             line_num = 19,
                             column_num = 2,
                             contents = contents,
                             command_arguments = [ 'GetDoc' ],
                             completer_target = 'filetype_default' )

  response = app.post_json( '/run_completer_command', event_data ).json

  eq_( response, {
    'detailed_info': 'Class Documentation',
  } )
