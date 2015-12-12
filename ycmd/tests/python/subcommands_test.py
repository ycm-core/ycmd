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

from nose.tools import eq_
from python_handlers_test import Python_Handlers_test
import os.path


class Python_Subcommands_test( Python_Handlers_test ):

  def GoTo_ZeroBasedLineAndColumn_test( self ):
    contents = """
def foo():
    pass

foo()
"""

    goto_data = self._BuildRequest( completer_target = 'filetype_default',
                                    command_arguments = ['GoToDefinition'],
                                    line_num = 5,
                                    contents = contents,
                                    filetype = 'python',
                                    filepath = '/foo.py' )

    eq_( {
      'filepath': os.path.abspath( '/foo.py' ),
      'line_num': 2,
      'column_num': 5
    }, self._app.post_json( '/run_completer_command', goto_data ).json )


  def GetDoc_Method_test( self ):
    # Testcase1
    filepath = self._PathToTestFile( 'GetDoc.py' )
    contents = open( filepath ).read()

    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'python',
                                     line_num = 17,
                                     column_num = 9,
                                     contents = contents,
                                     command_arguments = [ 'GetDoc' ],
                                     completer_target = 'filetype_default' )

    response = self._app.post_json( '/run_completer_command', event_data ).json

    eq_( response, {
      'detailed_info': '_ModuleMethod()\n\n'
                       'Module method docs\n'
                       'Are dedented, like you might expect',
    } )


  def GetDoc_Class_test( self ):
    # Testcase1
    filepath = self._PathToTestFile( 'GetDoc.py' )
    contents = open( filepath ).read()

    event_data = self._BuildRequest( filepath = filepath,
                                     filetype = 'python',
                                     line_num = 19,
                                     column_num = 2,
                                     contents = contents,
                                     command_arguments = [ 'GetDoc' ],
                                     completer_target = 'filetype_default' )

    response = self._app.post_json( '/run_completer_command', event_data ).json

    eq_( response, {
      'detailed_info': 'Class Documentation',
    } )
