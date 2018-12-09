# Copyright (C) 2016-2018 ycmd contributors
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
# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa

import os
from hamcrest import ( assert_that, contains, empty, has_entries, has_entry,
                       instance_of, matches_regexp )

from ycmd.tests.clang import IsolatedYcmd, PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import ( BuildRequest, TemporaryTestDir,
                                    TemporaryClangProject )


@SharedYcmd
def DebugInfo_FlagsWhenExtraConfLoadedAndNoCompilationDatabase_test( app ):
  app.post_json( '/load_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
  request_data = BuildRequest( filepath = PathToTestFile( 'basic.cpp' ),
                               filetype = 'cpp' )
  assert_that(
    app.post_json( '/debug_info', request_data ).json,
    has_entry( 'completer', has_entries( {
      'name': 'C-family',
      'servers': empty(),
      'items': contains(
        has_entries( {
          'key': 'compilation database path',
          'value': 'None'
        } ),
        has_entries( {
          'key': 'flags',
          'value': matches_regexp( "\\[u?'-x', u?'c\\+\\+', .*\\]" )
        } ),
        has_entries( {
          'key': 'translation unit',
          'value': PathToTestFile( 'basic.cpp' )
        } )
      )
    } ) )
  )


@SharedYcmd
def DebugInfo_FlagsWhenNoExtraConfAndNoCompilationDatabase_test( app ):
  request_data = BuildRequest( filetype = 'cpp' )
  # First request, FlagsForFile raises a NoExtraConfDetected exception.
  assert_that(
    app.post_json( '/debug_info', request_data ).json,
    has_entry( 'completer', has_entries( {
      'name': 'C-family',
      'servers': empty(),
      'items': contains(
        has_entries( {
          'key': 'compilation database path',
          'value': 'None'
        } ),
        has_entries( {
          'key': 'flags',
          'value': '[]'
        } ),
        has_entries( {
          'key': 'translation unit',
          'value': instance_of( str )
        } )
      )
    } ) )
  )
  # Second request, FlagsForFile returns None.
  assert_that(
    app.post_json( '/debug_info', request_data ).json,
    has_entry( 'completer', has_entries( {
      'name': 'C-family',
      'servers': empty(),
      'items': contains(
        has_entries( {
          'key': 'compilation database path',
          'value': 'None'
        } ),
        has_entries( {
          'key': 'flags',
          'value': '[]'
        } ),
        has_entries( {
          'key': 'translation unit',
          'value': instance_of( str )
        } )
      )
    } ) )
  )


@IsolatedYcmd()
def DebugInfo_FlagsWhenExtraConfNotLoadedAndNoCompilationDatabase_test(
  app ):

  request_data = BuildRequest( filepath = PathToTestFile( 'basic.cpp' ),
                               filetype = 'cpp' )
  assert_that(
    app.post_json( '/debug_info', request_data ).json,
    has_entry( 'completer', has_entries( {
      'name': 'C-family',
      'servers': empty(),
      'items': contains(
        has_entries( {
          'key': 'compilation database path',
          'value': 'None'
        } ),
        has_entries( {
          'key': 'flags',
          'value': '[]'
        } ),
        has_entries( {
          'key': 'translation unit',
          'value': PathToTestFile( 'basic.cpp' )
        } )
      )
    } ) )
  )


@IsolatedYcmd()
def DebugInfo_FlagsWhenNoExtraConfAndCompilationDatabaseLoaded_test( app ):
  with TemporaryTestDir() as tmp_dir:
    compile_commands = [
      {
        'directory': tmp_dir,
        'command': 'clang++ -I. -I/absolute/path -Wall',
        'file': os.path.join( tmp_dir, 'test.cc' ),
      },
    ]
    with TemporaryClangProject( tmp_dir, compile_commands ):
      request_data = BuildRequest(
        filepath = os.path.join( tmp_dir, 'test.cc' ),
        filetype = 'cpp' )

      assert_that(
        app.post_json( '/debug_info', request_data ).json,
        has_entry( 'completer', has_entries( {
          'name': 'C-family',
          'servers': empty(),
          'items': contains(
            has_entries( {
              'key': 'compilation database path',
              'value': instance_of( str )
            } ),
            has_entries( {
              'key': 'flags',
              'value': matches_regexp(
                "\\[u?'clang\\+\\+', u?'-x', u?'c\\+\\+', .*, u?'-Wall', .*\\]"
              )
            } ),
            has_entries( {
              'key': 'translation unit',
              'value': os.path.join( tmp_dir, 'test.cc' ),
            } )
          )
        } ) )
      )


@IsolatedYcmd()
def DebugInfo_FlagsWhenNoExtraConfAndInvalidCompilationDatabase_test( app ):
  with TemporaryTestDir() as tmp_dir:
    compile_commands = 'garbage'
    with TemporaryClangProject( tmp_dir, compile_commands ):
      request_data = BuildRequest(
        filepath = os.path.join( tmp_dir, 'test.cc' ),
        filetype = 'cpp' )

      assert_that(
        app.post_json( '/debug_info', request_data ).json,
        has_entry( 'completer', has_entries( {
          'name': 'C-family',
          'servers': empty(),
          'items': contains(
            has_entries( {
              'key': 'compilation database path',
              'value': 'None'
            } ),
            has_entries( {
              'key': 'flags',
              'value': '[]'
            } ),
            has_entries( {
              'key': 'translation unit',
              'value': os.path.join( tmp_dir, 'test.cc' )
            } )
          )
        } ) )
      )


@IsolatedYcmd(
  { 'global_ycm_extra_conf': PathToTestFile( '.ycm_extra_conf.py' ) } )
def DebugInfo_FlagsWhenGlobalExtraConfAndCompilationDatabaseLoaded_test( app ):
  with TemporaryTestDir() as tmp_dir:
    compile_commands = [
      {
        'directory': tmp_dir,
        'command': 'clang++ -I. -I/absolute/path -Wall',
        'file': os.path.join( tmp_dir, 'test.cc' ),
      },
    ]
    with TemporaryClangProject( tmp_dir, compile_commands ):
      request_data = BuildRequest(
        filepath = os.path.join( tmp_dir, 'test.cc' ),
        filetype = 'cpp' )

      assert_that(
        app.post_json( '/debug_info', request_data ).json,
        has_entry( 'completer', has_entries( {
          'name': 'C-family',
          'servers': empty(),
          'items': contains(
            has_entries( {
              'key': 'compilation database path',
              'value': instance_of( str )
            } ),
            has_entries( {
              'key': 'flags',
              'value': matches_regexp(
                "\\[u?'clang\\+\\+', u?'-x', u?'c\\+\\+', .*, u?'-Wall', .*\\]"
              )
            } ),
            has_entries( {
              'key': 'translation unit',
              'value': os.path.join( tmp_dir, 'test.cc' ),
            } )
          )
        } ) )
      )


@IsolatedYcmd(
  { 'global_ycm_extra_conf': PathToTestFile( '.ycm_extra_conf.py' ) } )
def DebugInfo_FlagsWhenGlobalExtraConfAndNoCompilationDatabase_test( app ):
  request_data = BuildRequest( filepath = PathToTestFile( 'basic.cpp' ),
                               filetype = 'cpp' )
  assert_that(
    app.post_json( '/debug_info', request_data ).json,
    has_entry( 'completer', has_entries( {
      'name': 'C-family',
      'servers': empty(),
      'items': contains(
        has_entries( {
          'key': 'compilation database path',
          'value': 'None'
        } ),
        has_entries( {
          'key': 'flags',
          'value': matches_regexp( "\\[u?'-x', u?'c\\+\\+', .*\\]" )
        } ),
        has_entries( {
          'key': 'translation unit',
          'value': PathToTestFile( 'basic.cpp' )
        } )
      )
    } ) )
  )


@SharedYcmd
def DebugInfo_Unity_test( app ):
  # Main TU
  app.post_json( '/load_extra_conf_file',
                 { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )

  for filename in [ 'unity.cc', 'unity.h', 'unitya.cc' ]:
    request_data = BuildRequest( filepath = PathToTestFile( filename ),
                                 filetype = 'cpp' )
    assert_that(
      app.post_json( '/debug_info', request_data ).json,
      has_entry( 'completer', has_entries( {
        'name': 'C-family',
        'servers': empty(),
        'items': contains(
          has_entries( {
            'key': 'compilation database path',
            'value': 'None'
          } ),
          has_entries( {
            'key': 'flags',
            'value': matches_regexp( "\\[u?'-x', u?'c\\+\\+', .*\\]" )
          } ),
          has_entries( {
            'key': 'translation unit',
            'value': PathToTestFile( 'unity.cc' )
          } )
        )
      } ) )
    )
