# Copyright (C) 2015 ycmd contributors
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

from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import division
from future import standard_library
standard_library.install_aliases()
from builtins import *  # noqa

from nose.tools import eq_
from hamcrest import ( assert_that,
                       contains,
                       contains_inanyorder,
                       has_entries )
from .javascript_handlers_test import Javascript_Handlers_test
from ycmd.utils import ReadFile
from pprint import pformat
import http.client


def LocationMatcher( filepath, column_num, line_num ):
  return has_entries( {
    'line_num': line_num,
    'column_num': column_num,
    'filepath': filepath
  } )


def ChunkMatcher( replacement_text, start, end ):
  return has_entries( {
    'replacement_text': replacement_text,
    'range': has_entries( {
      'start': start,
      'end': end
    } )
  } )


class Javascript_Subcommands_test( Javascript_Handlers_test ):

  def _RunTest( self, test ):
    contents = ReadFile( test[ 'request' ][ 'filepath' ] )

    def CombineRequest( request, data ):
      kw = request
      request.update( data )
      return self._BuildRequest( **kw )

    # Because we aren't testing this command, we *always* ignore errors. This
    # is mainly because we (may) want to test scenarios where the completer
    # throws an exception and the easiest way to do that is to throw from
    # within the FlagsForFile function.
    self._app.post_json( '/event_notification',
                         CombineRequest( test[ 'request' ], {
                                         'event_name': 'FileReadyToParse',
                                         'contents': contents,
                                         } ),
                         expect_errors = True )

    # We also ignore errors here, but then we check the response code
    # ourself. This is to allow testing of requests returning errors.
    response = self._app.post_json(
      '/run_completer_command',
      CombineRequest( test[ 'request' ], {
        'completer_target': 'filetype_default',
        'contents': contents,
        'filetype': 'javascript',
        'command_arguments': ( [ test[ 'request' ][ 'command' ] ]
                               + test[ 'request' ].get( 'arguments', [] ) )
      } ),
      expect_errors = True
    )

    print( 'completer response: {0}'.format( pformat( response.json ) ) )

    eq_( response.status_code, test[ 'expect' ][ 'response' ] )

    assert_that( response.json, test[ 'expect' ][ 'data' ] )


  def DefinedSubcommands_test( self ):
    subcommands_data = self._BuildRequest( completer_target = 'javascript' )

    self._WaitUntilTernServerReady()

    eq_( sorted( [ 'GoToDefinition',
                   'GoTo',
                   'GetDoc',
                   'GetType',
                   'StartServer',
                   'StopServer',
                   'GoToReferences',
                   'RefactorRename' ] ),
         self._app.post_json( '/defined_subcommands',
                              subcommands_data ).json )


  def GoToDefinition_test( self ):
    self._RunTest( {
      'description': 'GoToDefinition works within file',
      'request': {
        'command': 'GoToDefinition',
        'line_num': 13,
        'column_num': 25,
        'filepath': self._PathToTestFile( 'simple_test.js' ),
      },
      'expect': {
        'response': http.client.OK,
        'data': has_entries( {
          'filepath': self._PathToTestFile( 'simple_test.js' ),
          'line_num': 1,
          'column_num': 5,
        } )
      }
    } )


  def GoTo_test( self ):
    self._RunTest( {
      'description': 'GoTo works the same as GoToDefinition within file',
      'request': {
        'command': 'GoTo',
        'line_num': 13,
        'column_num': 25,
        'filepath': self._PathToTestFile( 'simple_test.js' ),
      },
      'expect': {
        'response': http.client.OK,
        'data': has_entries( {
          'filepath': self._PathToTestFile( 'simple_test.js' ),
          'line_num': 1,
          'column_num': 5,
        } )
      }
    } )


  def GetDoc_test( self ):
    self._RunTest( {
      'description': 'GetDoc works within file',
      'request': {
        'command': 'GetDoc',
        'line_num': 7,
        'column_num': 16,
        'filepath': self._PathToTestFile( 'coollib', 'cool_object.js' ),
      },
      'expect': {
        'response': http.client.OK,
        'data': has_entries( {
          'detailed_info': (
            'Name: mine_bitcoin\n'
            'Type: fn(how_much: ?) -> number\n\n'
            'This function takes a number and invests it in bitcoin. It '
            'returns\nthe expected value (in notional currency) after 1 year.'
          )
        } )
      }
    } )


  def GetType_test( self ):
    self._RunTest( {
      'description': 'GetType works within file',
      'request': {
        'command': 'GetType',
        'line_num': 11,
        'column_num': 14,
        'filepath': self._PathToTestFile( 'coollib', 'cool_object.js' ),
      },
      'expect': {
        'response': http.client.OK,
        'data': has_entries( {
          'message': 'number'
        } )
      }
    } )


  def GoToReferences_test( self ):
    self._RunTest( {
      'description': 'GoToReferences works within file',
      'request': {
        'command': 'GoToReferences',
        'line_num': 17,
        'column_num': 29,
        'filepath': self._PathToTestFile( 'coollib', 'cool_object.js' ),
      },
      'expect': {
        'response': http.client.OK,
        'data': contains_inanyorder(
          has_entries( {
            'filepath': self._PathToTestFile( 'coollib', 'cool_object.js' ),
            'line_num':  17,
            'column_num': 29,
          } ),
          has_entries( {
            'filepath': self._PathToTestFile( 'coollib', 'cool_object.js' ),
            'line_num': 12,
            'column_num': 9,
          } )
        )
      }
    } )


  def GetDocWithNoItendifier_test( self ):
    self._RunTest( {
      'description': 'GetDoc works when no identifier',
      'request': {
        'command': 'GetDoc',
        'filepath': self._PathToTestFile( 'simple_test.js' ),
        'line_num': 12,
        'column_num': 1,
      },
      'expect': {
        'response': http.client.INTERNAL_SERVER_ERROR,
        'data': self._ErrorMatcher( RuntimeError, 'TernError: No type found '
                                                  'at the given position.' ),
      }
    } )


  def RefactorRename_Simple_test( self ):
    filepath = self._PathToTestFile( 'simple_test.js' )
    self._RunTest( {
      'description': 'RefactorRename works within a single scope/file',
      'request': {
        'command': 'RefactorRename',
        'arguments': [ 'test' ],
        'filepath': filepath,
        'line_num': 15,
        'column_num': 32,
      },
      'expect': {
        'response': http.client.OK,
        'data': {
          'fixits': contains( has_entries( {
            'chunks': contains(
                ChunkMatcher( 'test',
                              LocationMatcher( filepath, 1, 5 ),
                              LocationMatcher( filepath, 1, 22 ) ),
                ChunkMatcher( 'test',
                              LocationMatcher( filepath, 13, 25 ),
                              LocationMatcher( filepath, 13, 42 ) ),
                ChunkMatcher( 'test',
                              LocationMatcher( filepath, 14, 24 ),
                              LocationMatcher( filepath, 14, 41 ) ),
                ChunkMatcher( 'test',
                              LocationMatcher( filepath, 15, 24 ),
                              LocationMatcher( filepath, 15, 41 ) ),
                ChunkMatcher( 'test',
                              LocationMatcher( filepath, 21, 7 ),
                              LocationMatcher( filepath, 21, 24 ) ),
                # On the same line, ensuring offsets are as expected (as
                # unmodified source, similar to clang)
                ChunkMatcher( 'test',
                              LocationMatcher( filepath, 21, 28 ),
                              LocationMatcher( filepath, 21, 45 ) ),
            ) ,
            'location': LocationMatcher( filepath, 15, 32 )
          } ) )
        }
      }
    } )


  def RefactorRename_MultipleFiles_test( self ):
    file1 = self._PathToTestFile( 'file1.js' )
    file2 = self._PathToTestFile( 'file2.js' )
    file3 = self._PathToTestFile( 'file3.js' )

    self._RunTest( {
      'description': 'RefactorRename works across files',
      'request': {
        'command': 'RefactorRename',
        'arguments': [ 'a-quite-long-string' ],
        'filepath': file1,
        'line_num': 3,
        'column_num': 14,
      },
      'expect': {
        'response': http.client.OK,
        'data': {
          'fixits': contains( has_entries( {
            'chunks': contains(
              ChunkMatcher(
                'a-quite-long-string',
                LocationMatcher( file1, 1, 5 ),
                LocationMatcher( file1, 1, 11 ) ),
              ChunkMatcher(
                'a-quite-long-string',
                LocationMatcher( file1, 3, 14 ),
                LocationMatcher( file1, 3, 19 ) ),
              ChunkMatcher(
                'a-quite-long-string',
                LocationMatcher( file2, 2, 14 ),
                LocationMatcher( file2, 2, 19 ) ),
              ChunkMatcher(
                'a-quite-long-string',
                LocationMatcher( file3, 3, 12 ),
                LocationMatcher( file3, 3, 17 ) )
            ) ,
            'location': LocationMatcher( file1, 3, 14 )
          } ) )
        }
      }
    } )


  def RefactorRename_MultipleFiles_OnFileReadyToParse_test( self ):
    file1 = self._PathToTestFile( 'file1.js' )
    file2 = self._PathToTestFile( 'file2.js' )
    file3 = self._PathToTestFile( 'file3.js' )

    # This test is roughly the same as the previous one, except here file4.js is
    # pushed into the Tern engine via 'opening it in the editor' (i.e.
    # FileReadyToParse event). The first 3 are loaded into the tern server
    # because they are listed in the .tern-project file's loadEagerly option.
    file4 = self._PathToTestFile( 'file4.js' )

    self._app.post_json( '/event_notification',
                         self._BuildRequest( **{
                           'filetype': 'javascript',
                           'event_name': 'FileReadyToParse',
                           'contents': ReadFile( file4 ),
                           'filepath': file4,
                         } ),
                         expect_errors = False )

    self._RunTest( {
      'description': 'FileReadyToParse loads files into tern server',
      'request': {
        'command': 'RefactorRename',
        'arguments': [ 'a-quite-long-string' ],
        'filepath': file1,
        'line_num': 3,
        'column_num': 14,
      },
      'expect': {
        'response': http.client.OK,
        'data': {
          'fixits': contains( has_entries( {
            'chunks': contains(
              ChunkMatcher(
                'a-quite-long-string',
                LocationMatcher( file1, 1, 5 ),
                LocationMatcher( file1, 1, 11 ) ),
              ChunkMatcher(
                'a-quite-long-string',
                LocationMatcher( file1, 3, 14 ),
                LocationMatcher( file1, 3, 19 ) ),
              ChunkMatcher(
                'a-quite-long-string',
                LocationMatcher( file2, 2, 14 ),
                LocationMatcher( file2, 2, 19 ) ),
              ChunkMatcher(
                'a-quite-long-string',
                LocationMatcher( file3, 3, 12 ),
                LocationMatcher( file3, 3, 17 ) ),
              ChunkMatcher(
                'a-quite-long-string',
                LocationMatcher( file4, 4, 22 ),
                LocationMatcher( file4, 4, 28 ) )
            ) ,
            'location': LocationMatcher( file1, 3, 14 )
          } ) )
        }
      }
    } )


  def RefactorRename_Missing_New_Name_test( self ):
    self._RunTest( {
      'description': 'FixItRename raises an error without new name',
      'request': {
        'command': 'FixItRename',
        'line_num': 17,
        'column_num': 29,
        'filepath': self._PathToTestFile( 'coollib', 'cool_object.js' ),
      },
      'expect': {
        'response': http.client.INTERNAL_SERVER_ERROR,
        'data': {
          'exception': self._ErrorMatcher(
                                  ValueError,
                                  'Please specify a new name to rename it to.\n'
                                  'Usage: RefactorRename <new name>' ),
        },
      }
    } )
