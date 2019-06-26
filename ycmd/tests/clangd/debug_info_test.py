# Copyright (C) 2011-2019 ycmd contributors
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

from hamcrest import ( assert_that,
                       contains,
                       empty,
                       has_entries,
                       has_entry,
                       has_items )

from ycmd.tests.clangd import ( IsolatedYcmd, PathToTestFile, SharedYcmd,
                                RunAfterInitialized )
from ycmd.tests.test_utils import ( BuildRequest,
                                    TemporaryClangProject,
                                    TemporaryTestDir,
                                    MacOnly )

import os


@IsolatedYcmd()
def DebugInfo_NotInitialized_test( app ):
  request_data = BuildRequest( filepath = PathToTestFile( 'basic.cpp' ),
                               filetype = 'cpp' )
  assert_that(
    app.post_json( '/debug_info', request_data ).json,
    has_entry( 'completer', has_entries( {
      'name': 'C-family',
      'servers': contains( has_entries( {
        'name': 'Clangd',
        'pid': None,
        'is_running': False,
        'extras': contains(
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
def DebugInfo_Initialized_test( app ):
  request_data = BuildRequest( filepath = PathToTestFile( 'basic.cpp' ),
                               filetype = 'cpp' )
  test = { 'request': request_data }
  RunAfterInitialized( app, test )
  assert_that(
    app.post_json( '/debug_info', request_data ).json,
    has_entry( 'completer', has_entries( {
      'name': 'C-family',
      'servers': contains( has_entries( {
        'name': 'Clangd',
        'is_running': True,
        'extras': contains(
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
def DebugInfo_ExtraConf_ReturningFlags_test( app ):
  request_data = BuildRequest( filepath = PathToTestFile( 'extra_conf',
                                                          'foo.cpp' ),
                               filetype = 'cpp' )
  test = { 'request': request_data }
  RunAfterInitialized( app, test )
  assert_that(
    app.post_json( '/debug_info', request_data ).json,
    has_entry( 'completer', has_entries( {
      'name': 'C-family',
      'servers': contains( has_entries( {
        'name': 'Clangd',
        'is_running': True,
        'extras': contains(
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
def DebugInfo_ExtraConf_NotReturningFlags_test( app ):
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
      'servers': contains( has_entries( {
        'name': 'Clangd',
        'is_running': True,
        'extras': contains(
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
def DebugInfo_ExtraConf_Global_test( app ):
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
      'servers': contains( has_entries( {
        'name': 'Clangd',
        'is_running': True,
        'extras': contains(
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
def DebugInfo_ExtraConf_LocalOverGlobal_test( app ):
  request_data = BuildRequest( filepath = PathToTestFile( 'extra_conf',
                                                          'foo.cpp' ),
                               filetype = 'cpp' )
  test = { 'request': request_data }
  RunAfterInitialized( app, test )
  assert_that(
    app.post_json( '/debug_info', request_data ).json,
    has_entry( 'completer', has_entries( {
      'name': 'C-family',
      'servers': contains( has_entries( {
        'name': 'Clangd',
        'is_running': True,
        'extras': contains(
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


def DebugInfo_ExtraConf_Database_test():
  with TemporaryTestDir() as tmp_dir:
    database = [
      {
        'directory': tmp_dir,
        'command': 'clang++ -x c++ -I test foo.cpp' ,
        'file': os.path.join( tmp_dir, 'foo.cpp' ),
      }
    ]

    with TemporaryClangProject( tmp_dir, database ):
      @IsolatedYcmd()
      def Test( app ):
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
            'servers': contains( has_entries( {
              'name': 'Clangd',
              'is_running': True,
              'extras': contains(
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

      yield Test


def DebugInfo_ExtraConf_UseLocalOverDatabase_test():
  with TemporaryTestDir() as tmp_dir:
    database = [
      {
        'directory': tmp_dir,
        'command': 'clang++ -x c++ -I test foo.cpp' ,
        'file': os.path.join( tmp_dir, 'foo.cpp' ),
      }
    ]

    with TemporaryClangProject( tmp_dir, database ):
      @IsolatedYcmd( { 'confirm_extra_conf': 0 } )
      def Test( app ):
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
              'servers': contains( has_entries( {
                'name': 'Clangd',
                'is_running': True,
                'extras': contains(
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

      yield Test


def DebugInfo_ExtraConf_UseDatabaseOverGlobal_test():
  with TemporaryTestDir() as tmp_dir:
    database = [
      {
        'directory': tmp_dir,
        'command': 'clang++ -x c++ -I test foo.cpp' ,
        'file': os.path.join( tmp_dir, 'foo.cpp' ),
      }
    ]

    with TemporaryClangProject( tmp_dir, database ):
      @IsolatedYcmd( {
        'global_ycm_extra_conf': PathToTestFile( 'extra_conf',
                                                 'global_extra_conf.py' ),
      } )
      def Test( app ):
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
            'servers': contains( has_entries( {
              'name': 'Clangd',
              'is_running': True,
              'extras': contains(
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

      yield Test


@MacOnly
@IsolatedYcmd( { 'extra_conf_globlist': [
  PathToTestFile( 'extra_conf', '.ycm_extra_conf.py' ) ] } )
def DebugInfo_ExtraConf_MacIncludeFlags_test( app ):
  request_data = BuildRequest( filepath = PathToTestFile( 'extra_conf',
                                                          'foo.cpp' ),
                               filetype = 'cpp' )
  test = { 'request': request_data }
  RunAfterInitialized( app, test )
  assert_that(
    app.post_json( '/debug_info', request_data ).json,
    has_entry( 'completer', has_entries( {
      'name': 'C-family',
      'servers': contains( has_entries( {
        'name': 'Clangd',
        'is_running': True,
        'extras': contains(
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
