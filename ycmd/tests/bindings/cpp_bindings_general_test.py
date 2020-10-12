# Copyright (C) 2020 ycmd contributors
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

from ycmd.completers.cpp.clang_completer import ConvertCompletionData
from ycmd.responses import BuildDiagnosticData
from ycmd.tests.bindings import PathToTestFile
from ycmd.tests.test_utils import ( ClangOnly, TemporaryTestDir,
                                    TemporaryClangProject )
from ycmd.utils import ImportCore

from hamcrest import ( assert_that,
                       contains_exactly,
                       contains_inanyorder,
                       contains_string,
                       equal_to,
                       has_entries,
                       has_properties )
ycm_core = ImportCore()
import os


def CppBindings_FilterAndSortCandidates_test():
  candidates = [ 'foo1', 'foo2', 'foo3' ]
  query = 'oo'
  candidate_property = ''

  result_full = ycm_core.FilterAndSortCandidates( candidates,
                                                  candidate_property,
                                                  query )
  result_2 = ycm_core.FilterAndSortCandidates( candidates,
                                               candidate_property,
                                               query,
                                               2 )

  del candidates
  del query
  del candidate_property

  assert_that( result_full, contains_exactly( 'foo1', 'foo2', 'foo3' ) )
  assert_that( result_2, contains_exactly( 'foo1', 'foo2' ) )


def CppBindings_IdentifierCompleter_test():
  identifier_completer = ycm_core.IdentifierCompleter()
  identifiers = ycm_core.StringVector()
  identifiers.append( 'foo' )
  identifiers.append( 'bar' )
  identifiers.append( 'baz' )
  identifier_completer.AddIdentifiersToDatabase( identifiers, 'foo', 'file' )
  del identifiers
  query_fo_10 = identifier_completer.CandidatesForQueryAndType(
                                       'fo', 'foo', 10 )
  query_fo = identifier_completer.CandidatesForQueryAndType( 'fo', 'foo' )
  query_a = identifier_completer.CandidatesForQueryAndType( 'a', 'foo' )
  assert_that( query_fo_10, contains_exactly( 'foo' ) )
  assert_that( query_fo, contains_exactly( 'foo' ) )
  assert_that( query_a, contains_exactly( 'bar', 'baz' ) )
  identifiers = ycm_core.StringVector()
  identifiers.append( 'oof' )
  identifiers.append( 'rab' )
  identifiers.append( 'zab' )
  identifier_completer.ClearForFileAndAddIdentifiersToDatabase(
                         identifiers, 'foo', 'file' )
  query_a_10 = identifier_completer.CandidatesForQueryAndType( 'a', 'foo' )
  assert_that( query_a_10, contains_exactly( 'rab', 'zab' ) )


@ClangOnly
def CppBindings_UnsavedFile_test():
  unsaved_file = ycm_core.UnsavedFile()
  filename = 'foo'
  contents = 'bar\\n'
  length = len( contents )
  unsaved_file.filename_ = filename
  unsaved_file.contents_ = contents
  unsaved_file.length_ = length
  del filename
  del contents
  del length
  assert_that( unsaved_file, has_properties( {
                               'filename_': 'foo',
                               'contents_': 'bar\\n',
                               'length_': len( 'bar\\n' )
                             } ) )


@ClangOnly
def CppBindings_DeclarationLocation_test():
  translation_unit = PathToTestFile( 'foo.c' )
  filename = PathToTestFile( 'foo.c' )
  line = 9
  column = 17
  unsaved_file_vector = ycm_core.UnsavedFileVector()
  flags = ycm_core.StringVector()
  flags.append( '-xc++' )
  reparse = True
  clang_completer = ycm_core.ClangCompleter()

  location = clang_completer.GetDeclarationLocation( translation_unit,
                                                     filename,
                                                     line,
                                                     column,
                                                     unsaved_file_vector,
                                                     flags,
                                                     reparse )

  del translation_unit
  del filename
  del line
  del column
  del unsaved_file_vector
  del flags
  del clang_completer
  del reparse
  assert_that( location,
               has_properties( { 'line_number_': 2,
                                 'column_number_': 5,
                                 'filename_': PathToTestFile( 'foo.c' ) } ) )


@ClangOnly
def CppBindings_DefinitionOrDeclarationLocation_test():
  translation_unit = PathToTestFile( 'foo.c' )
  filename = PathToTestFile( 'foo.c' )
  line = 9
  column = 17
  unsaved_file_vector = ycm_core.UnsavedFileVector()
  flags = ycm_core.StringVector()
  flags.append( '-xc++' )
  reparse = True
  clang_completer = ycm_core.ClangCompleter()

  location = ( clang_completer.
                 GetDefinitionOrDeclarationLocation( translation_unit,
                                                     filename,
                                                     line,
                                                     column,
                                                     unsaved_file_vector,
                                                     flags,
                                                     reparse ) )

  del translation_unit
  del filename
  del line
  del column
  del unsaved_file_vector
  del flags
  del clang_completer
  del reparse
  assert_that( location,
               has_properties( { 'line_number_': 2,
                                 'column_number_': 5,
                                 'filename_': PathToTestFile( 'foo.c' ) } ) )


@ClangOnly
def CppBindings_DefinitionLocation_test():
  translation_unit = PathToTestFile( 'foo.c' )
  filename = PathToTestFile( 'foo.c' )
  line = 9
  column = 17
  unsaved_file_vector = ycm_core.UnsavedFileVector()
  flags = ycm_core.StringVector()
  flags.append( '-xc++' )
  reparse = True
  clang_completer = ycm_core.ClangCompleter()

  location = clang_completer.GetDefinitionLocation( translation_unit,
                                                    filename,
                                                    line,
                                                    column,
                                                    unsaved_file_vector,
                                                    flags,
                                                    reparse )

  del translation_unit
  del filename
  del line
  del column
  del unsaved_file_vector
  del flags
  del clang_completer
  del reparse
  assert_that( location,
               has_properties( { 'line_number_': 2,
                                 'column_number_': 5,
                                 'filename_': PathToTestFile( 'foo.c' ) } ) )


@ClangOnly
def CppBindings_Candidates_test():
  translation_unit = PathToTestFile( 'foo.c' )
  filename = PathToTestFile( 'foo.c' )
  line = 11
  column = 6
  unsaved_file_vector = ycm_core.UnsavedFileVector()
  flags = ycm_core.StringVector()
  flags.append( '-xc' )
  reparse = True
  clang_completer = ycm_core.ClangCompleter()

  candidates = ( clang_completer
                   .CandidatesForLocationInFile( translation_unit,
                                                 filename,
                                                 line,
                                                 column,
                                                 unsaved_file_vector,
                                                 flags ) )

  del translation_unit
  del filename
  del line
  del column
  del unsaved_file_vector
  del flags
  del clang_completer
  del reparse
  candidates = [ ConvertCompletionData( x ) for x in candidates ]
  assert_that( candidates, contains_inanyorder(
                             has_entries( {
                               'detailed_info': 'float b\n',
                               'extra_menu_info': 'float',
                               'insertion_text': 'b',
                               'kind': 'MEMBER',
                               'menu_text': 'b'
                             } ),
                             has_entries( {
                               'detailed_info': 'int a\n',
                               'extra_menu_info': 'int',
                               'insertion_text': 'a',
                               'kind': 'MEMBER',
                               'menu_text': 'a'
                             } )
                           ) )


@ClangOnly
def CppBindings_GetType_test():
  translation_unit = PathToTestFile( 'foo.c' )
  filename = PathToTestFile( 'foo.c' )
  line = 9
  column = 17
  unsaved_file_vector = ycm_core.UnsavedFileVector()
  flags = ycm_core.StringVector()
  flags.append( '-xc++' )
  reparse = True
  clang_completer = ycm_core.ClangCompleter()

  type_at_cursor = clang_completer.GetTypeAtLocation( translation_unit,
                                                      filename,
                                                      line,
                                                      column,
                                                      unsaved_file_vector,
                                                      flags,
                                                      reparse )
  del translation_unit
  del filename
  del line
  del column
  del unsaved_file_vector
  del flags
  del clang_completer
  del reparse

  assert_that( 'int ()', equal_to( type_at_cursor ) )


@ClangOnly
def CppBindings_GetParent_test():
  translation_unit = PathToTestFile( 'foo.c' )
  filename = PathToTestFile( 'foo.c' )
  line = 9
  column = 17
  unsaved_file_vector = ycm_core.UnsavedFileVector()
  flags = ycm_core.StringVector()
  flags.append( '-xc++' )
  reparse = True
  clang_completer = ycm_core.ClangCompleter()

  enclosing_function = ( clang_completer
                           .GetEnclosingFunctionAtLocation( translation_unit,
                                                            filename,
                                                            line,
                                                            column,
                                                            unsaved_file_vector,
                                                            flags,
                                                            reparse ) )

  del translation_unit
  del filename
  del line
  del column
  del unsaved_file_vector
  del flags
  del clang_completer
  del reparse

  assert_that( 'bar', equal_to( enclosing_function ) )


@ClangOnly
def CppBindings_FixIt_test():
  translation_unit = PathToTestFile( 'foo.c' )
  filename = PathToTestFile( 'foo.c' )
  line = 3
  column = 5
  unsaved_file_vector = ycm_core.UnsavedFileVector()
  flags = ycm_core.StringVector()
  flags.append( '-xc++' )
  reparse = True
  clang_completer = ycm_core.ClangCompleter()

  fixits = clang_completer.GetFixItsForLocationInFile( translation_unit,
                                                       filename,
                                                       line,
                                                       column,
                                                       unsaved_file_vector,
                                                       flags,
                                                       reparse )
  del translation_unit
  del filename
  del line
  del column
  del unsaved_file_vector
  del flags
  del clang_completer
  del reparse

  assert_that(
    fixits,
    contains_exactly( has_properties( {
      'text': ( PathToTestFile( 'foo.c' ) +
                ':3:16: error: expected \';\' at end of declaration' ),
      'location': has_properties( {
        'line_number_': 3,
        'column_number_': 16,
        'filename_': PathToTestFile( 'foo.c' )
      } ),
      'chunks': contains_exactly( has_properties( {
        'replacement_text': ';',
        'range': has_properties( {
          'start_': has_properties( {
            'line_number_': 3,
            'column_number_': 16,
          } ),
          'end_': has_properties( {
            'line_number_': 3,
            'column_number_': 16,
          } ),
        } )
      } ) ),
      'kind': None,
    } ) ) )


@ClangOnly
def CppBindings_Docs_test():
  translation_unit = PathToTestFile( 'foo.c' )
  filename = PathToTestFile( 'foo.c' )
  line = 9
  column = 16
  unsaved_file_vector = ycm_core.UnsavedFileVector()
  flags = ycm_core.StringVector()
  flags.append( '-xc++' )
  reparse = True
  clang_completer = ycm_core.ClangCompleter()

  docs = clang_completer.GetDocsForLocationInFile( translation_unit,
                                                   filename,
                                                   line,
                                                   column,
                                                   unsaved_file_vector,
                                                   flags,
                                                   reparse )
  del translation_unit
  del filename
  del line
  del column
  del unsaved_file_vector
  del flags
  del clang_completer
  del reparse
  assert_that(
    docs,
    has_properties( {
      'comment_xml': '<Function file="' + PathToTestFile( 'foo.c' ) + '"'
                     ' line="2" column="5"><Name>foooo</Name><USR>c:@F@foooo#'
                     '</USR><Declaration>int foooo()</Declaration><Abstract>'
                     '<Para> Foo</Para></Abstract></Function>',
      'brief_comment': 'Foo',
      'raw_comment': '/// Foo',
      'canonical_type': 'int ()',
      'display_name': 'foooo' } ) )


@ClangOnly
def CppBindings_Diags_test():
  filename = PathToTestFile( 'foo.c' )
  unsaved_file_vector = ycm_core.UnsavedFileVector()
  flags = ycm_core.StringVector()
  flags.append( '-xc++' )
  reparse = True
  clang_completer = ycm_core.ClangCompleter()

  diag_vector = clang_completer.UpdateTranslationUnit( filename,
                                                       unsaved_file_vector,
                                                       flags )

  diags = [ BuildDiagnosticData( x ) for x in diag_vector ]

  del diag_vector
  del filename
  del unsaved_file_vector
  del flags
  del clang_completer
  del reparse

  assert_that(
    diags,
    contains_exactly(
      has_entries( {
        'kind': 'ERROR',
        'text': contains_string( 'expected \';\' at end of declaration' ),
        'ranges': contains_exactly(),
        'location': has_entries( {
          'line_num': 3,
          'column_num': 16,
        } ),
        'location_extent': has_entries( {
           'start': has_entries( {
             'line_num': 3,
             'column_num': 16,
           } ),
           'end': has_entries( {
             'line_num': 3,
             'column_num': 16,
           } ),
         } ),
       } ) ) )


@ClangOnly
def CppBindings_CompilationDatabase_test():
  with TemporaryTestDir() as tmp_dir:
    compile_commands = [
      {
        'directory': tmp_dir,
        'command': 'clang++ -x c++ -I. -I/absolute/path -Wall',
        'file': os.path.join( tmp_dir, 'test.cc' ),
      },
    ]
    with TemporaryClangProject( tmp_dir, compile_commands ):
      db = ycm_core.CompilationDatabase( tmp_dir )
      db_successful = db.DatabaseSuccessfullyLoaded()
      db_busy = db.AlreadyGettingFlags()
      db_dir = db.database_directory
      compilation_info = db.GetCompilationInfoForFile(
                              compile_commands[ 0 ][ 'file' ] )
      del db
      del compile_commands
      assert_that( db_successful, equal_to( True ) )
      assert_that( db_busy, equal_to( False ) )
      assert_that( db_dir, equal_to( tmp_dir ) )
      assert_that( compilation_info,
                   has_properties( {
                     'compiler_working_dir_': tmp_dir,
                     'compiler_flags_': contains_exactly( 'clang++',
                                                  '--driver-mode=g++',
                                                  '-x',
                                                  'c++',
                                                  '-I.',
                                                  '-I/absolute/path',
                                                  '-Wall' )
                   } ) )


def Dummy_test():
  # Workaround for https://github.com/pytest-dev/pytest-rerunfailures/issues/51
  assert True
