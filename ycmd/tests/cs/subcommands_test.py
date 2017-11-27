# Copyright (C) 2015-2017 ycmd contributors
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


from nose import SkipTest
from nose.tools import eq_
from webtest import AppError
from hamcrest import assert_that, has_entries, contains
import pprint

from ycmd.tests.cs import ( IsolatedYcmd, PathToTestFile, SharedYcmd,
                            WrapOmniSharpServer )
from ycmd.tests.test_utils import ( BuildRequest,
                                    ChunkMatcher,
                                    LocationMatcher,
                                    StopCompleterServer )
from ycmd.utils import ReadFile


def Subcommands_GoTo_Basic_test():
  yield _Subcommands_GoTo_Basic_test, True
  yield _Subcommands_GoTo_Basic_test, False


@SharedYcmd
def _Subcommands_GoTo_Basic_test( app, use_roslyn ):
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  with WrapOmniSharpServer( app, filepath, use_roslyn ):
    contents = ReadFile( filepath )

    goto_data = BuildRequest( completer_target = 'filetype_default',
                              command_arguments = [ 'GoTo' ],
                              line_num = 9,
                              column_num = 15,
                              contents = contents,
                              filetype = 'cs',
                              filepath = filepath )

    eq_( {
      'filepath': PathToTestFile( 'testy', 'Program.cs' ),
      'line_num': 7,
      'column_num': 22 if use_roslyn else 3
    }, app.post_json( '/run_completer_command', goto_data ).json )


def Subcommands_GoTo_Unicode_test():
  yield _Subcommands_GoTo_Unicode_test, True
  yield _Subcommands_GoTo_Unicode_test, False


@SharedYcmd
def _Subcommands_GoTo_Unicode_test( app, use_roslyn ):
  filepath = PathToTestFile( 'testy', 'Unicode.cs' )
  with WrapOmniSharpServer( app, filepath, use_roslyn ):
    contents = ReadFile( filepath )

    goto_data = BuildRequest( completer_target = 'filetype_default',
                              command_arguments = [ 'GoTo' ],
                              line_num = 45,
                              column_num = 43,
                              contents = contents,
                              filetype = 'cs',
                              filepath = filepath )

    eq_( {
      'filepath': PathToTestFile( 'testy', 'Unicode.cs' ),
      'line_num': 30,
      'column_num': 54 if use_roslyn else 37
    }, app.post_json( '/run_completer_command', goto_data ).json )


def Subcommands_GoToImplementation_Basic_test():
  yield _Subcommands_GoToImplementation_Basic_test, True
  yield _Subcommands_GoToImplementation_Basic_test, False


@SharedYcmd
def _Subcommands_GoToImplementation_Basic_test( app, use_roslyn ):
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  with WrapOmniSharpServer( app, filepath, use_roslyn ):
    contents = ReadFile( filepath )

    goto_data = BuildRequest(
      completer_target = 'filetype_default',
      command_arguments = [ 'GoToImplementation' ],
      line_num = 13,
      column_num = 13,
      contents = contents,
      filetype = 'cs',
      filepath = filepath
    )

    eq_( {
      'filepath': PathToTestFile( 'testy', 'GotoTestCase.cs' ),
      'line_num': 30,
      'column_num': 15 if use_roslyn else 3
    }, app.post_json( '/run_completer_command', goto_data ).json )


def Subcommands_GoToImplementation_NoImplementation_test():
  yield _Subcommands_GoToImplementation_NoImplementation_test, True
  yield _Subcommands_GoToImplementation_NoImplementation_test, False


@SharedYcmd
def _Subcommands_GoToImplementation_NoImplementation_test( app, use_roslyn ):
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  with WrapOmniSharpServer( app, filepath, use_roslyn ):
    contents = ReadFile( filepath )

    goto_data = BuildRequest(
      completer_target = 'filetype_default',
      command_arguments = [ 'GoToImplementation' ],
      line_num = 17,
      column_num = 13,
      contents = contents,
      filetype = 'cs',
      filepath = filepath
    )

    try:
      app.post_json( '/run_completer_command', goto_data ).json
      raise Exception("Expected a 'No implementations found' error")
    except AppError as e:
      if 'No implementations found' in str(e):
        pass
      else:
        raise


def Subcommands_CsCompleter_InvalidLocation_test():
  yield _Subcommands_CsCompleter_InvalidLocation_test, True
  yield _Subcommands_CsCompleter_InvalidLocation_test, False


@SharedYcmd
def _Subcommands_CsCompleter_InvalidLocation_test( app, use_roslyn ):
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  with WrapOmniSharpServer( app, filepath, use_roslyn ):
    contents = ReadFile( filepath )

    goto_data = BuildRequest(
      completer_target = 'filetype_default',
      command_arguments = [ 'GoToImplementation' ],
      line_num = 2,
      column_num = 1,
      contents = contents,
      filetype = 'cs',
      filepath = filepath
    )

    try:
      app.post_json( '/run_completer_command', goto_data ).json
      raise Exception( 'Expected a "Can\\\'t jump to implementation" error' )
    except AppError as e:
      if 'Can\\\'t jump to implementation' in str(e):
        pass
      elif 'No implementations found' in str(e):
        pass
      else:
        raise


def Subcommands_GoToImplementationElseDeclaration_NoImpl_test():
  yield _Subcommands_GoToImplementationElseDeclaration_NoImpl_test, True
  yield _Subcommands_GoToImplementationElseDeclaration_NoImpl_test, False


@SharedYcmd
def _Subcommands_GoToImplementationElseDeclaration_NoImpl_test( app,
                                                                use_roslyn ):
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  with WrapOmniSharpServer( app, filepath, use_roslyn ):
    contents = ReadFile( filepath )

    goto_data = BuildRequest(
      completer_target = 'filetype_default',
      command_arguments = [ 'GoToImplementationElseDeclaration' ],
      line_num = 17,
      column_num = 13,
      contents = contents,
      filetype = 'cs',
      filepath = filepath
    )

    eq_( {
      'filepath': PathToTestFile( 'testy', 'GotoTestCase.cs' ),
      'line_num': 35,
      'column_num': 8 if use_roslyn else 3
    }, app.post_json( '/run_completer_command', goto_data ).json )


def Subcommands_GoToImplementationElseDeclaration_SingleImpl_test():
  yield _Subcommands_GoToImplementationElseDeclaration_SingleImpl_test, True
  yield _Subcommands_GoToImplementationElseDeclaration_SingleImpl_test, False


@SharedYcmd
def _Subcommands_GoToImplementationElseDeclaration_SingleImpl_test(
    app, use_roslyn ):
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  with WrapOmniSharpServer( app, filepath, use_roslyn ):
    contents = ReadFile( filepath )

    goto_data = BuildRequest(
      completer_target = 'filetype_default',
      command_arguments = [ 'GoToImplementationElseDeclaration' ],
      line_num = 13,
      column_num = 13,
      contents = contents,
      filetype = 'cs',
      filepath = filepath
    )

    eq_( {
      'filepath': PathToTestFile( 'testy', 'GotoTestCase.cs' ),
      'line_num': 30,
      'column_num': 15 if use_roslyn else 3
    }, app.post_json( '/run_completer_command', goto_data ).json )


def Subcommands_GoToImplementationElseDeclaration_MultipleImpls_test():
  yield _Subcommands_GoToImplementationElseDeclaration_MultipleImpls_test, True
  yield _Subcommands_GoToImplementationElseDeclaration_MultipleImpls_test, False


@SharedYcmd
def _Subcommands_GoToImplementationElseDeclaration_MultipleImpls_test(
    app, use_roslyn ):
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  with WrapOmniSharpServer( app, filepath, use_roslyn ):
    contents = ReadFile( filepath )

    goto_data = BuildRequest(
      completer_target = 'filetype_default',
      command_arguments = [ 'GoToImplementationElseDeclaration' ],
      line_num = 21,
      column_num = 13,
      contents = contents,
      filetype = 'cs',
      filepath = filepath
    )

    eq_( [ {
      'filepath': PathToTestFile( 'testy', 'GotoTestCase.cs' ),
      'line_num': 43,
      'column_num': 15 if use_roslyn else 3
    }, {
      'filepath': PathToTestFile( 'testy', 'GotoTestCase.cs' ),
      'line_num': 48,
      'column_num': 15 if use_roslyn else 3
    } ], app.post_json( '/run_completer_command', goto_data ).json )


def Subcommands_GetToImplementation_Unicode_test():
  yield _Subcommands_GetToImplementation_Unicode_test, True
  yield _Subcommands_GetToImplementation_Unicode_test, False


@SharedYcmd
def _Subcommands_GetToImplementation_Unicode_test( app, use_roslyn ):
  filepath = PathToTestFile( 'testy', 'Unicode.cs' )
  with WrapOmniSharpServer( app, filepath, use_roslyn ):
    contents = ReadFile( filepath )

    goto_data = BuildRequest(
      completer_target = 'filetype_default',
      command_arguments = [ 'GoToImplementation' ],
      line_num = 48,
      column_num = 44,
      contents = contents,
      filetype = 'cs',
      filepath = filepath
    )

    eq_( [ {
      'filepath': PathToTestFile( 'testy', 'Unicode.cs' ),
      'line_num': 49,
      'column_num': 66 if use_roslyn else 54
    }, {
      'filepath': PathToTestFile( 'testy', 'Unicode.cs' ),
      'line_num': 50,
      'column_num': 62 if use_roslyn else 50
    } ], app.post_json( '/run_completer_command', goto_data ).json )


def Subcommands_GetType_EmptyMessage_test():
  yield _Subcommands_GetType_EmptyMessage_test, True
  yield _Subcommands_GetType_EmptyMessage_test, False


@SharedYcmd
def _Subcommands_GetType_EmptyMessage_test( app, use_roslyn ):
  filepath = PathToTestFile( 'testy', 'GetTypeTestCase.cs' )
  with WrapOmniSharpServer( app, filepath, use_roslyn ):
    contents = ReadFile( filepath )

    gettype_data = BuildRequest( completer_target = 'filetype_default',
                                 command_arguments = [ 'GetType' ],
                                 line_num = 1,
                                 column_num = 1,
                                 contents = contents,
                                 filetype = 'cs',
                                 filepath = filepath )

    eq_( {
      u'message': None if use_roslyn else u""
    }, app.post_json( '/run_completer_command', gettype_data ).json )


def Subcommands_GetType_VariableDeclaration_test():
  yield _Subcommands_GetType_VariableDeclaration_test, True
  yield _Subcommands_GetType_VariableDeclaration_test, False


@SharedYcmd
def _Subcommands_GetType_VariableDeclaration_test( app, use_roslyn ):
  filepath = PathToTestFile( 'testy', 'GetTypeTestCase.cs' )
  with WrapOmniSharpServer( app, filepath, use_roslyn ):
    contents = ReadFile( filepath )

    gettype_data = BuildRequest( completer_target = 'filetype_default',
                                 command_arguments = [ 'GetType' ],
                                 line_num = 4,
                                 column_num = 5,
                                 contents = contents,
                                 filetype = 'cs',
                                 filepath = filepath )

    eq_( {
      u'message': u"System.string" if use_roslyn else u"string"
    }, app.post_json( '/run_completer_command', gettype_data ).json )


def Subcommands_GetType_VariableUsage_test():
  yield _Subcommands_GetType_VariableUsage_test, True
  yield _Subcommands_GetType_VariableUsage_test, False


@SharedYcmd
def _Subcommands_GetType_VariableUsage_test( app, use_roslyn ):
  filepath = PathToTestFile( 'testy', 'GetTypeTestCase.cs' )
  with WrapOmniSharpServer( app, filepath, use_roslyn ):
    contents = ReadFile( filepath )

    gettype_data = BuildRequest( completer_target = 'filetype_default',
                                 command_arguments = [ 'GetType' ],
                                 line_num = 5,
                                 column_num = 5,
                                 contents = contents,
                                 filetype = 'cs',
                                 filepath = filepath )

    eq_( {
      u'message': u"string str"
    }, app.post_json( '/run_completer_command', gettype_data ).json )


def Subcommands_GetType_Constant_test():
  yield _Subcommands_GetType_Constant_test, True
  yield _Subcommands_GetType_Constant_test, False


@SharedYcmd
def _Subcommands_GetType_Constant_test( app, use_roslyn ):
  filepath = PathToTestFile( 'testy', 'GetTypeTestCase.cs' )
  with WrapOmniSharpServer( app, filepath, use_roslyn ):
    contents = ReadFile( filepath )

    gettype_data = BuildRequest( completer_target = 'filetype_default',
                                 command_arguments = [ 'GetType' ],
                                 line_num = 4,
                                 column_num = 14,
                                 contents = contents,
                                 filetype = 'cs',
                                 filepath = filepath )

    eq_( {
      u'message': None if use_roslyn else u"System.String"
    }, app.post_json( '/run_completer_command', gettype_data ).json )


def Subcommands_GetType_DocsIgnored_test():
  yield _Subcommands_GetType_DocsIgnored_test, True
  yield _Subcommands_GetType_DocsIgnored_test, False


@SharedYcmd
def _Subcommands_GetType_DocsIgnored_test( app, use_roslyn ):
  filepath = PathToTestFile( 'testy', 'GetTypeTestCase.cs' )
  with WrapOmniSharpServer( app, filepath, use_roslyn ):
    contents = ReadFile( filepath )

    gettype_data = BuildRequest( completer_target = 'filetype_default',
                                 command_arguments = [ 'GetType' ],
                                 line_num = 9,
                                 column_num = 34,
                                 contents = contents,
                                 filetype = 'cs',
                                 filepath = filepath )
    if use_roslyn:
      message = u"int GetTypeTestCase.an_int_with_docs"
    else:
      message = u"int GetTypeTestCase.an_int_with_docs;"

    eq_( {
      u'message': message,
    }, app.post_json( '/run_completer_command', gettype_data ).json )


def Subcommands_GetDoc_Variable_test():
  yield _Subcommands_GetDoc_Variable_test, True
  yield _Subcommands_GetDoc_Variable_test, False


@SharedYcmd
def _Subcommands_GetDoc_Variable_test( app, use_roslyn ):
  filepath = PathToTestFile( 'testy', 'GetDocTestCase.cs' )
  with WrapOmniSharpServer( app, filepath, use_roslyn ):
    contents = ReadFile( filepath )

    getdoc_data = BuildRequest( completer_target = 'filetype_default',
                                command_arguments = [ 'GetDoc' ],
                                line_num = 13,
                                column_num = 28,
                                contents = contents,
                                filetype = 'cs',
                                filepath = filepath )

    detailed_info = ( 'int GetDocTestCase.an_int;\n'
                      'an integer, or something' )
    if use_roslyn:
      detailed_info = ( 'int GetDocTestCase.an_int\n'
                        'an integer, or something' )
    eq_( {
      'detailed_info': detailed_info
    }, app.post_json( '/run_completer_command', getdoc_data ).json )


def Subcommands_GetDoc_Function_test():
  yield _Subcommands_GetDoc_Function_test, True
  yield _Subcommands_GetDoc_Function_test, False


@SharedYcmd
def _Subcommands_GetDoc_Function_test( app, use_roslyn ):
  filepath = PathToTestFile( 'testy', 'GetDocTestCase.cs' )
  with WrapOmniSharpServer( app, filepath, use_roslyn ):
    contents = ReadFile( filepath )

    getdoc_data = BuildRequest( completer_target = 'filetype_default',
                                command_arguments = [ 'GetDoc' ],
                                line_num = 33,
                                column_num = 27,
                                contents = contents,
                                filetype = 'cs',
                                filepath = filepath )
    if use_roslyn:
      detailed_info = ( 'int GetDocTestCase.DoATest()\n'
                        'Very important method.\n\nWith multiple lines of '
                        'commentary\nAnd Format-\n-ting' )
    else:
      # It seems that Omnisharp server eats newlines
      detailed_info = ( 'int GetDocTestCase.DoATest();\n'
                        ' Very important method. With multiple lines of '
                        'commentary And Format- -ting' )


    eq_( {
      'detailed_info': detailed_info,
    }, app.post_json( '/run_completer_command', getdoc_data ).json )


def RunFixItTest( app,
                  use_roslyn,
                  line,
                  column,
                  result_matcher,
                  filepath = [ 'testy', 'FixItTestCase.cs' ] ):
  if use_roslyn:
    raise SkipTest( "Roslyn doesn't seem to support FixIt  yet" )
  filepath = PathToTestFile( *filepath )
  with WrapOmniSharpServer( app, filepath, use_roslyn ):
    contents = ReadFile( filepath )

    fixit_data = BuildRequest( completer_target = 'filetype_default',
                               command_arguments = [ 'FixIt' ],
                               line_num = line,
                               column_num = column,
                               contents = contents,
                               filetype = 'cs',
                               filepath = filepath )

    response = app.post_json( '/run_completer_command', fixit_data ).json

    pprint.pprint( response )

    assert_that( response, result_matcher )


def Subcommands_FixIt_RemoveSingleLine_test():
  yield _Subcommands_FixIt_RemoveSingleLine_test, True
  yield _Subcommands_FixIt_RemoveSingleLine_test, False


@SharedYcmd
def _Subcommands_FixIt_RemoveSingleLine_test( app, use_roslyn ):
  filepath = PathToTestFile( 'testy', 'FixItTestCase.cs' )
  RunFixItTest( app, use_roslyn, 11, 1, has_entries( {
    'fixits': contains( has_entries( {
      'location': LocationMatcher( filepath, 11, 1 ),
      'chunks': contains( ChunkMatcher( '',
                                        LocationMatcher( filepath, 10, 20 ),
                                        LocationMatcher( filepath, 11, 30 ) ) )
    } ) )
  } ) )


def Subcommands_FixIt_MultipleLines_test():
  yield _Subcommands_FixIt_MultipleLines_test, True
  yield _Subcommands_FixIt_MultipleLines_test, False


@SharedYcmd
def _Subcommands_FixIt_MultipleLines_test( app, use_roslyn ):
  filepath = PathToTestFile( 'testy', 'FixItTestCase.cs' )
  RunFixItTest( app, use_roslyn, 19, 1, has_entries( {
    'fixits': contains( has_entries ( {
      'location': LocationMatcher( filepath, 19, 1 ),
      'chunks': contains( ChunkMatcher( 'return On',
                                        LocationMatcher( filepath, 20, 13 ),
                                        LocationMatcher( filepath, 21, 35 ) ) )
    } ) )
  } ) )


def Subcommands_FixIt_SpanFileEdge_test():
  yield _Subcommands_FixIt_SpanFileEdge_test, True
  yield _Subcommands_FixIt_SpanFileEdge_test, False


@SharedYcmd
def _Subcommands_FixIt_SpanFileEdge_test( app, use_roslyn ):
  filepath = PathToTestFile( 'testy', 'FixItTestCase.cs' )
  RunFixItTest( app, use_roslyn, 1, 1, has_entries( {
    'fixits': contains( has_entries ( {
      'location': LocationMatcher( filepath, 1, 1 ),
      'chunks': contains( ChunkMatcher( 'System',
                                        LocationMatcher( filepath, 1, 7 ),
                                        LocationMatcher( filepath, 3, 18 ) ) )
    } ) )
  } ) )


def Subcommands_FixIt_AddTextInLine_test():
  yield _Subcommands_FixIt_AddTextInLine_test, True
  yield _Subcommands_FixIt_AddTextInLine_test, False


@SharedYcmd
def _Subcommands_FixIt_AddTextInLine_test( app, use_roslyn ):
  filepath = PathToTestFile( 'testy', 'FixItTestCase.cs' )
  RunFixItTest( app, use_roslyn, 9, 1, has_entries( {
    'fixits': contains( has_entries ( {
      'location': LocationMatcher( filepath, 9, 1 ),
      'chunks': contains( ChunkMatcher( ', StringComparison.Ordinal',
                                        LocationMatcher( filepath, 9, 29 ),
                                        LocationMatcher( filepath, 9, 29 ) ) )
    } ) )
  } ) )


def Subcommands_FixIt_ReplaceTextInLine_test():
  yield _Subcommands_FixIt_ReplaceTextInLine_test, True
  yield _Subcommands_FixIt_ReplaceTextInLine_test, False


@SharedYcmd
def _Subcommands_FixIt_ReplaceTextInLine_test( app, use_roslyn ):
  filepath = PathToTestFile( 'testy', 'FixItTestCase.cs' )
  RunFixItTest( app, use_roslyn, 10, 1, has_entries( {
    'fixits': contains( has_entries ( {
      'location': LocationMatcher( filepath, 10, 1 ),
      'chunks': contains( ChunkMatcher( 'const int',
                                        LocationMatcher( filepath, 10, 13 ),
                                        LocationMatcher( filepath, 10, 16 ) ) )
    } ) )
  } ) )


def Subcommands_FixIt_Unicode_test():
  yield _Subcommands_FixIt_Unicode_test, True
  yield _Subcommands_FixIt_Unicode_test, False


@SharedYcmd
def _Subcommands_FixIt_Unicode_test( app, use_roslyn ):
  filepath = PathToTestFile( 'testy', 'Unicode.cs' )
  RunFixItTest( app, use_roslyn, 30, 54, has_entries( {
    'fixits': contains( has_entries ( {
      'location': LocationMatcher( filepath, 30, 54 ),
      'chunks': contains( ChunkMatcher( ' readonly',
                                        LocationMatcher( filepath, 30, 44 ),
                                        LocationMatcher( filepath, 30, 44 ) ) )
    } ) )
  } ), filepath = [ 'testy', 'Unicode.cs' ] )


def Subcommands_StopServer_NoErrorIfNotStarted_test():
  yield _Subcommands_StopServer_NoErrorIfNotStarted_test, True
  yield _Subcommands_StopServer_NoErrorIfNotStarted_test, False


@IsolatedYcmd
def _Subcommands_StopServer_NoErrorIfNotStarted_test( app, use_roslyn ):
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  StopCompleterServer( app, 'cs', filepath )
  # Success = no raise
