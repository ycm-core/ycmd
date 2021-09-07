# Copyright (C) 2016-2021 ycmd contributors
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
from hamcrest import ( assert_that, contains_exactly, empty, has_entries,
                       has_entry, instance_of, matches_regexp )

from unittest import TestCase
from ycmd.tests.clang import setUpModule # noqa
from ycmd.tests.clang import IsolatedYcmd, PathToTestFile, SharedYcmd
from ycmd.tests.test_utils import ( BuildRequest, TemporaryTestDir,
                                    TemporaryClangProject )


class DebugInfoTest( TestCase ):
  @SharedYcmd
  def test_DebugInfo_FlagsWhenExtraConfLoadedAndNoCompilationDatabase(
      self, app ):
    app.post_json( '/load_extra_conf_file',
                   { 'filepath': PathToTestFile( '.ycm_extra_conf.py' ) } )
    request_data = BuildRequest( filepath = PathToTestFile( 'basic.cpp' ),
                                 filetype = 'cpp' )
    assert_that(
      app.post_json( '/debug_info', request_data ).json,
      has_entry( 'completer', has_entries( {
        'name': 'C-family',
        'servers': empty(),
        'items': contains_exactly(
          has_entries( {
            'key': 'compilation database path',
            'value': 'None'
          } ),
          has_entries( {
            'key': 'flags',
            'value': matches_regexp( "\\['-x', 'c\\+\\+', .*\\]" )
          } ),
          has_entries( {
            'key': 'translation unit',
            'value': PathToTestFile( 'basic.cpp' )
          } )
        )
      } ) )
    )


  @SharedYcmd
  def test_DebugInfo_FlagsWhenNoExtraConfAndNoCompilationDatabase( self, app ):
    request_data = BuildRequest( filetype = 'cpp' )
    # First request, FlagsForFile raises a NoExtraConfDetected exception.
    assert_that(
      app.post_json( '/debug_info', request_data ).json,
      has_entry( 'completer', has_entries( {
        'name': 'C-family',
        'servers': empty(),
        'items': contains_exactly(
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
        'items': contains_exactly(
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
  def test_DebugInfo_FlagsWhenExtraConfNotLoadedAndNoCompilationDatabase(
      self, app ):

    request_data = BuildRequest( filepath = PathToTestFile( 'basic.cpp' ),
                                 filetype = 'cpp' )
    assert_that(
      app.post_json( '/debug_info', request_data ).json,
      has_entry( 'completer', has_entries( {
        'name': 'C-family',
        'servers': empty(),
        'items': contains_exactly(
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
  def test_DebugInfo_FlagsWhenNoExtraConfAndCompilationDatabaseLoaded(
      self, app ):
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
            'items': contains_exactly(
              has_entries( {
                'key': 'compilation database path',
                'value': instance_of( str )
              } ),
              has_entries( {
                'key': 'flags',
                'value': matches_regexp(
                  "\\['clang\\+\\+', '-x', 'c\\+\\+', .*, '-Wall', .*\\]"
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
  def test_DebugInfo_FlagsWhenNoExtraConfAndInvalidCompilationDatabase(
      self, app ):
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
            'items': contains_exactly(
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
  def test_DebugInfo_FlagsWhenGlobalExtraConfAndCompilationDatabaseLoaded(
      self, app ):
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
            'items': contains_exactly(
              has_entries( {
                'key': 'compilation database path',
                'value': instance_of( str )
              } ),
              has_entries( {
                'key': 'flags',
                'value': matches_regexp(
                  "\\['clang\\+\\+', '-x', 'c\\+\\+', .*, '-Wall', .*\\]"
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
  def test_DebugInfo_FlagsWhenGlobalExtraConfAndNoCompilationDatabase(
      self, app ):
    request_data = BuildRequest( filepath = PathToTestFile( 'basic.cpp' ),
                                 filetype = 'cpp' )
    assert_that(
      app.post_json( '/debug_info', request_data ).json,
      has_entry( 'completer', has_entries( {
        'name': 'C-family',
        'servers': empty(),
        'items': contains_exactly(
          has_entries( {
            'key': 'compilation database path',
            'value': 'None'
          } ),
          has_entries( {
            'key': 'flags',
            'value': matches_regexp( "\\['-x', 'c\\+\\+', .*\\]" )
          } ),
          has_entries( {
            'key': 'translation unit',
            'value': PathToTestFile( 'basic.cpp' )
          } )
        )
      } ) )
    )


  @SharedYcmd
  def test_DebugInfo_Unity( self, app ):
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
          'items': contains_exactly(
            has_entries( {
              'key': 'compilation database path',
              'value': 'None'
            } ),
            has_entries( {
              'key': 'flags',
              'value': matches_regexp( "\\['-x', 'c\\+\\+', .*\\]" )
            } ),
            has_entries( {
              'key': 'translation unit',
              'value': PathToTestFile( 'unity.cc' )
            } )
          )
        } ) )
      )
