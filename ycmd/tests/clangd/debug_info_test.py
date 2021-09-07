# Copyright (C) 2011-2021 ycmd contributors
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

from hamcrest import ( assert_that,
                       contains_exactly,
                       empty,
                       has_entries,
                       has_entry,
                       has_items )
from unittest import TestCase

from ycmd.tests.clangd import setUpModule, tearDownModule # noqa
from ycmd.tests.clangd import ( IsolatedYcmd,
                                PathToTestFile,
                                SharedYcmd,
                                RunAfterInitialized )
from ycmd.tests.test_utils import ( BuildRequest,
                                    TemporaryClangProject,
                                    TemporaryTestDir,
                                    MacOnly )

import os


class DebugInfoTest( TestCase ):
  @IsolatedYcmd()
  def test_DebugInfo_NotInitialized( self, app ):
    request_data = BuildRequest( filepath = PathToTestFile( 'basic.cpp' ),
                                 filetype = 'cpp' )
    assert_that(
      app.post_json( '/debug_info', request_data ).json,
      has_entry( 'completer', has_entries( {
        'name': 'C-family',
        'servers': contains_exactly( has_entries( {
          'name': 'Clangd',
          'pid': None,
          'is_running': False,
          'extras': contains_exactly(
            has_entries( {
              'key': 'Server State',
              'value': 'Dead',
            } ),
            has_entries( {
              'key': 'Project Directory',
              'value': None,
            } ),
            has_entries( {
              'key': 'Settings',
              'value': '{}',
            } ),
            has_entries( {
              'key': 'Compilation Command',
              'value': False,
            } ),
          ),
        } ) ),
        'items': empty(),
      } ) )
    )


  @SharedYcmd
  def test_DebugInfo_Initialized( self, app ):
    request_data = BuildRequest( filepath = PathToTestFile( 'basic.cpp' ),
                                 filetype = 'cpp' )
    test = { 'request': request_data }
    RunAfterInitialized( app, test )
    assert_that(
      app.post_json( '/debug_info', request_data ).json,
      has_entry( 'completer', has_entries( {
        'name': 'C-family',
        'servers': contains_exactly( has_entries( {
          'name': 'Clangd',
          'is_running': True,
          'extras': contains_exactly(
            has_entries( {
              'key': 'Server State',
              'value': 'Initialized',
            } ),
            has_entries( {
              'key': 'Project Directory',
              'value': PathToTestFile(),
            } ),
            has_entries( {
              'key': 'Settings',
              'value': '{}',
            } ),
            has_entries( {
              'key': 'Compilation Command',
              'value': False,
            } ),
          ),
        } ) ),
        'items': empty()
      } ) )
    )


  @IsolatedYcmd( { 'extra_conf_globlist': [
    PathToTestFile( 'extra_conf', '.ycm_extra_conf.py' ) ] } )
  def test_DebugInfo_ExtraConf_ReturningFlags( self, app ):
    request_data = BuildRequest( filepath = PathToTestFile( 'extra_conf',
                                                            'foo.cpp' ),
                                 filetype = 'cpp' )
    test = { 'request': request_data }
    RunAfterInitialized( app, test )
    assert_that(
      app.post_json( '/debug_info', request_data ).json,
      has_entry( 'completer', has_entries( {
        'name': 'C-family',
        'servers': contains_exactly( has_entries( {
          'name': 'Clangd',
          'is_running': True,
          'extras': contains_exactly(
            has_entries( {
              'key': 'Server State',
              'value': 'Initialized',
            } ),
            has_entries( {
              'key': 'Project Directory',
              'value': PathToTestFile( 'extra_conf' ),
            } ),
            has_entries( {
              'key': 'Settings',
              'value': '{}',
            } ),
            has_entries( {
              'key': 'Compilation Command',
              'value': has_items( '-I', 'include', '-DFOO' ),
            } ),
          ),
        } ) ),
        'items': empty()
      } ) )
    )


  @IsolatedYcmd( { 'extra_conf_globlist': [
    PathToTestFile( 'extra_conf', '.ycm_extra_conf.py' ) ] } )
  def test_DebugInfo_ExtraConf_NotReturningFlags( self, app ):
    request_data = BuildRequest( filepath = PathToTestFile( 'extra_conf',
                                                            'xyz.cpp' ),
                                 filetype = 'cpp' )
    request_data[ 'contents' ] = ''
    test = { 'request': request_data }
    RunAfterInitialized( app, test )
    assert_that(
      app.post_json( '/debug_info', request_data ).json,
      has_entry( 'completer', has_entries( {
        'name': 'C-family',
        'servers': contains_exactly( has_entries( {
          'name': 'Clangd',
          'is_running': True,
          'extras': contains_exactly(
            has_entries( {
              'key': 'Server State',
              'value': 'Initialized',
            } ),
            has_entries( {
              'key': 'Project Directory',
              'value': PathToTestFile( 'extra_conf' ),
            } ),
            has_entries( {
              'key': 'Settings',
              'value': '{}',
            } ),
            has_entries( {
              'key': 'Compilation Command',
              'value': False
            } ),
          ),
        } ) ),
        'items': empty()
      } ) )
    )


  @IsolatedYcmd( {
    'global_ycm_extra_conf': PathToTestFile( 'extra_conf',
                                             'global_extra_conf.py' ),
  } )
  def test_DebugInfo_ExtraConf_Global( self, app ):
    request_data = BuildRequest( filepath = PathToTestFile( 'foo.cpp' ),
                                 contents = '',
                                 filetype = 'cpp' )
    test = { 'request': request_data }
    request_data[ 'contents' ] = ''
    RunAfterInitialized( app, test )
    assert_that(
      app.post_json( '/debug_info', request_data ).json,
      has_entry( 'completer', has_entries( {
        'name': 'C-family',
        'servers': contains_exactly( has_entries( {
          'name': 'Clangd',
          'is_running': True,
          'extras': contains_exactly(
            has_entries( {
              'key': 'Server State',
              'value': 'Initialized',
            } ),
            has_entries( {
              'key': 'Project Directory',
              'value': PathToTestFile(),
            } ),
            has_entries( {
              'key': 'Settings',
              'value': '{}',
            } ),
            has_entries( {
              'key': 'Compilation Command',
              'value': has_items( '-I', 'test' ),
            } ),
          ),
        } ) ),
        'items': empty()
      } ) )
    )


  @IsolatedYcmd( {
    'global_ycm_extra_conf': PathToTestFile( 'extra_conf',
                                             'global_extra_conf.py' ),
   'extra_conf_globlist': [ PathToTestFile( 'extra_conf',
                                            '.ycm_extra_conf.py' ) ]
  } )
  def test_DebugInfo_ExtraConf_LocalOverGlobal( self, app ):
    request_data = BuildRequest( filepath = PathToTestFile( 'extra_conf',
                                                            'foo.cpp' ),
                                 filetype = 'cpp' )
    test = { 'request': request_data }
    RunAfterInitialized( app, test )
    assert_that(
      app.post_json( '/debug_info', request_data ).json,
      has_entry( 'completer', has_entries( {
        'name': 'C-family',
        'servers': contains_exactly( has_entries( {
          'name': 'Clangd',
          'is_running': True,
          'extras': contains_exactly(
            has_entries( {
              'key': 'Server State',
              'value': 'Initialized',
            } ),
            has_entries( {
              'key': 'Project Directory',
              'value': PathToTestFile( 'extra_conf' ),
            } ),
            has_entries( {
              'key': 'Settings',
              'value': '{}',
            } ),
            has_entries( {
              'key': 'Compilation Command',
              'value': has_items( '-I', 'include', '-DFOO' ),
            } ),
          ),
        } ) ),
        'items': empty()
      } ) )
    )


  @IsolatedYcmd()
  def test_DebugInfo_ExtraConf_Database( self, app ):
    with TemporaryTestDir() as tmp_dir:
      database = [
        {
          'directory': tmp_dir,
          'command': 'clang++ -x c++ -I test foo.cpp' ,
          'file': os.path.join( tmp_dir, 'foo.cpp' ),
        }
      ]

      with TemporaryClangProject( tmp_dir, database ):
        request_data = BuildRequest( filepath = os.path.join( tmp_dir,
                                                              'foo.cpp' ),
                                     filetype = 'cpp' )
        request_data[ 'contents' ] = ''
        test = { 'request': request_data }
        RunAfterInitialized( app, test )
        assert_that(
          app.post_json( '/debug_info', request_data ).json,
          has_entry( 'completer', has_entries( {
            'name': 'C-family',
            'servers': contains_exactly( has_entries( {
              'name': 'Clangd',
              'is_running': True,
              'extras': contains_exactly(
                has_entries( {
                  'key': 'Server State',
                  'value': 'Initialized',
                } ),
                has_entries( {
                  'key': 'Project Directory',
                  'value': tmp_dir,
                } ),
                has_entries( {
                  'key': 'Settings',
                  'value': '{}',
                } ),
                has_entries( {
                  'key': 'Compilation Command',
                  'value': False
                } ),
              ),
            } ) ),
            'items': empty()
          } ) )
        )


  @IsolatedYcmd( { 'confirm_extra_conf': 0 } )
  def test_DebugInfo_ExtraConf_UseLocalOverDatabase( self, app ):
    with TemporaryTestDir() as tmp_dir:
      database = [
        {
          'directory': tmp_dir,
          'command': 'clang++ -x c++ -I test foo.cpp' ,
          'file': os.path.join( tmp_dir, 'foo.cpp' ),
        }
      ]

      with TemporaryClangProject( tmp_dir, database ):
        extra_conf = os.path.join( tmp_dir, '.ycm_extra_conf.py' )
        with open( extra_conf, 'w' ) as f:
          f.write( '''
def Settings( **kwargs ):
  return { 'flags': [ '-x', 'c++', '-I', 'ycm' ] }
  ''' )

        try:
          request_data = BuildRequest( filepath = os.path.join( tmp_dir,
                                                                'foo.cpp' ),
                                       filetype = 'cpp' )
          request_data[ 'contents' ] = ''
          test = { 'request': request_data }
          RunAfterInitialized( app, test )
          assert_that(
            app.post_json( '/debug_info', request_data ).json,
            has_entry( 'completer', has_entries( {
              'name': 'C-family',
              'servers': contains_exactly( has_entries( {
                'name': 'Clangd',
                'is_running': True,
                'extras': contains_exactly(
                  has_entries( {
                    'key': 'Server State',
                    'value': 'Initialized',
                  } ),
                  has_entries( {
                    'key': 'Project Directory',
                    'value': tmp_dir,
                  } ),
                  has_entries( {
                    'key': 'Settings',
                    'value': '{}',
                  } ),
                  has_entries( {
                    'key': 'Compilation Command',
                    'value': has_items( '-x', 'c++', '-I', 'ycm' )
                  } ),
                ),
              } ) ),
              'items': empty()
            } ) )
          )
        finally:
          os.remove( extra_conf )


  @IsolatedYcmd( {
    'global_ycm_extra_conf': PathToTestFile( 'extra_conf',
                                             'global_extra_conf.py' ),
  } )
  def test_DebugInfo_ExtraConf_UseDatabaseOverGlobal( self, app ):
    with TemporaryTestDir() as tmp_dir:
      database = [
        {
          'directory': tmp_dir,
          'command': 'clang++ -x c++ -I test foo.cpp' ,
          'file': os.path.join( tmp_dir, 'foo.cpp' ),
        }
      ]

      with TemporaryClangProject( tmp_dir, database ):
        request_data = BuildRequest( filepath = os.path.join( tmp_dir,
                                                              'foo.cpp' ),
                                     filetype = 'cpp' )
        request_data[ 'contents' ] = ''
        test = { 'request': request_data }
        RunAfterInitialized( app, test )
        assert_that(
          app.post_json( '/debug_info', request_data ).json,
          has_entry( 'completer', has_entries( {
            'name': 'C-family',
            'servers': contains_exactly( has_entries( {
              'name': 'Clangd',
              'is_running': True,
              'extras': contains_exactly(
                has_entries( {
                  'key': 'Server State',
                  'value': 'Initialized',
                } ),
                has_entries( {
                  'key': 'Project Directory',
                  'value': tmp_dir,
                } ),
                has_entries( {
                  'key': 'Settings',
                  'value': '{}',
                } ),
                has_entries( {
                  'key': 'Compilation Command',
                  'value': False
                } ),
              ),
            } ) ),
            'items': empty()
          } ) )
        )


  @MacOnly
  @IsolatedYcmd( { 'extra_conf_globlist': [
    PathToTestFile( 'extra_conf', '.ycm_extra_conf.py' ) ] } )
  def test_DebugInfo_ExtraConf_MacIncludeFlags( self, app ):
    request_data = BuildRequest( filepath = PathToTestFile( 'extra_conf',
                                                            'foo.cpp' ),
                                 filetype = 'cpp' )
    test = { 'request': request_data }
    RunAfterInitialized( app, test )
    assert_that(
      app.post_json( '/debug_info', request_data ).json,
      has_entry( 'completer', has_entries( {
        'name': 'C-family',
        'servers': contains_exactly( has_entries( {
          'name': 'Clangd',
          'is_running': True,
          'extras': contains_exactly(
            has_entries( {
              'key': 'Server State',
              'value': 'Initialized',
            } ),
            has_entries( {
              'key': 'Project Directory',
              'value': PathToTestFile( 'extra_conf' ),
            } ),
            has_entries( {
              'key': 'Settings',
              'value': '{}',
            } ),
            has_entries( {
              'key': 'Compilation Command',
              'value': has_items( '-isystem', '-iframework' )
            } ),
          ),
        } ) ),
        'items': empty()
      } ) )
    )
