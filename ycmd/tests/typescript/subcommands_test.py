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
from webtest import TestApp, AppError
from nose.tools import eq_, with_setup
from hamcrest import assert_that, raises, calling
from ... import handlers
import bottle

bottle.debug( True )


@with_setup( Setup )
def RunCompleterCommand_GetType_TypeScriptCompleter_test():
  app = TestApp( handlers.app )

  filepath = PathToTestFile( 'test.ts' )
  contents = open( filepath ).read()

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'typescript',
                             contents = contents,
                             event_name = 'BufferVisit' )

  app.post_json( '/event_notification', event_data )

  gettype_data = BuildRequest( completer_target = 'filetype_default',
                               command_arguments = [ 'GetType' ],
                               line_num = 12,
                               column_num = 1,
                               contents = contents,
                               filetype = 'typescript',
                               filepath = filepath )

  eq_( {
    'message': 'var foo: Foo'
  }, app.post_json( '/run_completer_command', gettype_data ).json )


@with_setup( Setup )
def RunCompleterCommand_GetType_HasNoType_TypeScriptCompleter_test():
  app = TestApp( handlers.app )

  filepath = PathToTestFile( 'test.ts' )
  contents = open( filepath ).read()

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'typescript',
                             contents = contents,
                             event_name = 'BufferVisit' )

  app.post_json( '/event_notification', event_data )

  gettype_data = BuildRequest( completer_target = 'filetype_default',
                               command_arguments = [ 'GetType' ],
                               line_num = 2,
                               column_num = 1,
                               contents = contents,
                               filetype = 'typescript',
                               filepath = filepath )

  assert_that( calling( app.post_json ).with_args( '/run_completer_command',
                                                   gettype_data ),
               raises( AppError, 'RuntimeError.*No content available' ) )


@with_setup( Setup )
def RunCompleterCommand_GetDoc_TypeScriptCompleter_Works_Method_test():
  app = TestApp( handlers.app )

  filepath = PathToTestFile( 'test.ts' )
  contents = open( filepath ).read()

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'typescript',
                             contents = contents,
                             event_name = 'BufferVisit' )

  app.post_json( '/event_notification', event_data )

  gettype_data = BuildRequest( completer_target = 'filetype_default',
                               command_arguments = [ 'GetDoc' ],
                               line_num = 29,
                               column_num = 9,
                               contents = contents,
                               filetype = 'typescript',
                               filepath = filepath )

  eq_( {
    'detailed_info': '(method) Bar.testMethod(): void\n\n'
                     'Method documentation',
  }, app.post_json( '/run_completer_command', gettype_data ).json )


@with_setup( Setup )
def RunCompleterCommand_GetDoc_TypeScriptCompleter_Works_Class_test():
  app = TestApp( handlers.app )

  filepath = PathToTestFile( 'test.ts' )
  contents = open( filepath ).read()

  event_data = BuildRequest( filepath = filepath,
                             filetype = 'typescript',
                             contents = contents,
                             event_name = 'BufferVisit' )

  app.post_json( '/event_notification', event_data )

  gettype_data = BuildRequest( completer_target = 'filetype_default',
                               command_arguments = [ 'GetDoc' ],
                               line_num = 31,
                               column_num = 2,
                               contents = contents,
                               filetype = 'typescript',
                               filepath = filepath )

  eq_( {
    'detailed_info': 'class Bar\n\n'
                     'Class documentation\n\n'
                     'Multi-line',
  }, app.post_json( '/run_completer_command', gettype_data ).json )
