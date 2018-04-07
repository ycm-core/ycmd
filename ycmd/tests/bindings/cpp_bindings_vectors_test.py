# Copyright (C) 2018 ycmd contributors
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

from ycmd.utils import ToCppStringCompatible as ToCppStr
from ycmd.completers.cpp.clang_completer import ConvertCompletionData
from ycmd.responses import BuildDiagnosticData
from ycmd.tests.bindings import PathToTestFile
from ycmd.tests.test_utils import ClangOnly

from hamcrest import ( assert_that,
                       contains,
                       contains_inanyorder,
                       contains_string,
                       has_entries,
                       has_properties )
import ycm_core


def EmplaceBack( vector, element ):
  vector.append( element )


def CppBindings_StringVector_test():
  str1 = 'foo'
  str2 = 'bar'
  str3 = 'baz'
  string_vector = ycm_core.StringVector()
  string_vector.append( ToCppStr( str1 ) )
  EmplaceBack( string_vector, ToCppStr( str2 ) )
  string_vector.append( ToCppStr( str3 ) )
  del str1
  del str2
  del str3
  assert_that( string_vector, contains( 'foo', 'bar', 'baz' ) )


@ClangOnly
def CppBindings_UnsavedFileVector_test():
  unsaved_file_vector = ycm_core.UnsavedFileVector()
  unsaved_file = ycm_core.UnsavedFile()
  unsaved_file.filename_ = ToCppStr( 'foo' )
  unsaved_file.contents_ = ToCppStr( 'bar' )
  unsaved_file.length_ = 3
  unsaved_file_vector.append( unsaved_file )
  EmplaceBack( unsaved_file_vector, unsaved_file )
  del unsaved_file
  assert_that( unsaved_file_vector,
               contains(
                 has_properties( {
                   'filename_': 'foo',
                   'contents_': 'bar',
                   'length_': len( 'bar' )
                 } ),
                 has_properties( {
                   'filename_': 'foo',
                   'contents_': 'bar',
                   'length_': len( 'bar' )
                 } )
               ) )


@ClangOnly
def CppBindings_FixItVector_test():
  flags = ycm_core.StringVector()
  flags.append( ToCppStr( '-xc++' ) )
  clang_completer = ycm_core.ClangCompleter()
  translation_unit = PathToTestFile( 'foo.c' )
  filename = ToCppStr( PathToTestFile( 'foo.c' ) )
  fixits = ( clang_completer
               .GetFixItsForLocationInFile( ToCppStr( translation_unit ),
                                            ToCppStr( filename ),
                                            3,
                                            5,
                                            ycm_core.UnsavedFileVector(),
                                            flags,
                                            True ) )

  fixits = fixits[ 0:1 ]
  EmplaceBack( fixits, fixits[ 0 ] )
  del translation_unit
  del flags
  del filename
  del clang_completer
  assert_that(
    fixits,
    contains(
      has_properties( {
        'text': ( PathToTestFile( 'foo.c' ) +
                  ':3:16: error: expected \';\' at end of declaration' ),
        'location': has_properties( {
          'line_number_': 3,
          'column_number_': 16,
          'filename_': PathToTestFile( 'foo.c' )
        } ),
        'chunks': contains( has_properties( {
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
      } ),
      has_properties( {
        'text': ( PathToTestFile( 'foo.c' ) +
                  ':3:16: error: expected \';\' at end of declaration' ),
        'location': has_properties( {
          'line_number_': 3,
          'column_number_': 16,
          'filename_': PathToTestFile( 'foo.c' )
        } ),
        'chunks': contains( has_properties( {
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
      } ) ) )


@ClangOnly
def CppBindings_FixItChunkVector_test():
  flags = ycm_core.StringVector()
  flags.append( ToCppStr( '-xc++' ) )
  clang_completer = ycm_core.ClangCompleter()
  translation_unit = PathToTestFile( 'foo.c' )
  filename = PathToTestFile( 'foo.c' )
  fixits = ( clang_completer
               .GetFixItsForLocationInFile( ToCppStr( translation_unit ),
                                            ToCppStr( filename ),
                                            3,
                                            5,
                                            ycm_core.UnsavedFileVector(),
                                            flags,
                                            True ) )

  fixit_chunks = fixits[ 0 ].chunks[ 0:1 ]
  EmplaceBack( fixit_chunks, fixit_chunks[ 0 ] )
  del translation_unit
  del flags
  del filename
  del clang_completer
  del fixits
  assert_that( fixit_chunks, contains(
                               has_properties( {
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
                                 } ),
                               } ),
                               has_properties( {
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
                                 } ),
                               } ) ) )


@ClangOnly
def CppBindings_RangeVector_test():
  flags = ycm_core.StringVector()
  flags.append( ToCppStr( '-xc++' ) )
  clang_completer = ycm_core.ClangCompleter()
  translation_unit = PathToTestFile( 'foo.c' )
  filename = PathToTestFile( 'foo.c' )

  fixits = ( clang_completer
               .GetFixItsForLocationInFile( ToCppStr( translation_unit ),
                                            ToCppStr( filename ),
                                            3,
                                            5,
                                            ycm_core.UnsavedFileVector(),
                                            flags,
                                            True ) )
  fixit_range = fixits[ 0 ].chunks[ 0 ].range
  ranges = ycm_core.RangeVector()
  ranges.append( fixit_range )
  EmplaceBack( ranges, fixit_range )
  del flags
  del translation_unit
  del filename
  del clang_completer
  del fixits
  del fixit_range
  assert_that( ranges, contains(
                         has_properties( {
                           'start_': has_properties( {
                             'line_number_': 3,
                             'column_number_': 16,
                           } ),
                           'end_': has_properties( {
                             'line_number_': 3,
                             'column_number_': 16,
                           } ),
                         } ),
                         has_properties( {
                           'start_': has_properties( {
                             'line_number_': 3,
                             'column_number_': 16,
                           } ),
                           'end_': has_properties( {
                             'line_number_': 3,
                             'column_number_': 16,
                           } ),
                         } ),
                       ) )


@ClangOnly
def CppBindings_DiagnosticVector_test():
  filename = PathToTestFile( 'foo.c' )
  unsaved_file_vector = ycm_core.UnsavedFileVector()
  flags = ycm_core.StringVector()
  flags.append( ToCppStr( '-xc++' ) )
  clang_completer = ycm_core.ClangCompleter()

  diag_vector = clang_completer.UpdateTranslationUnit( ToCppStr( filename ),
                                                       unsaved_file_vector,
                                                       flags )

  del filename
  del unsaved_file_vector
  del flags
  del clang_completer

  diag_vector = diag_vector[ 0:1 ]
  EmplaceBack( diag_vector, diag_vector[ 0 ] )

  diags = [ BuildDiagnosticData( x ) for x in diag_vector ]

  del diag_vector

  assert_that(
    diags,
    contains(
      has_entries( {
        'kind': 'ERROR',
        'text': contains_string( 'expected \';\' at end of declaration' ),
        'ranges': contains(),
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
      } ),
      has_entries( {
        'kind': 'ERROR',
        'text': contains_string( 'expected \';\' at end of declaration' ),
        'ranges': contains(),
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
      } ),
    ) )


@ClangOnly
def CppBindings_CompletionDataVector_test():
  translation_unit = ToCppStr( PathToTestFile( 'foo.c' ) )
  filename = ToCppStr( PathToTestFile( 'foo.c' ) )
  line = 11
  column = 6
  unsaved_file_vector = ycm_core.UnsavedFileVector()
  flags = ycm_core.StringVector()
  flags.append( ToCppStr( '-xc' ) )
  clang_completer = ycm_core.ClangCompleter()

  candidates = ( clang_completer
                   .CandidatesForLocationInFile( translation_unit,
                                                 filename,
                                                 line,
                                                 column,
                                                 unsaved_file_vector,
                                                 flags ) )


  if candidates[ 0 ].TextToInsertInBuffer() == 'a':
    candidate = candidates[ 0 ]
  else:
    candidate = candidates[ 1 ]
  candidates = ycm_core.CompletionVector()
  candidates.append( candidate )
  EmplaceBack( candidates, candidate )

  del translation_unit
  del filename
  del candidate
  del clang_completer
  del line
  del column
  del flags
  del unsaved_file_vector
  candidates = [ ConvertCompletionData( x ) for x in candidates ]
  assert_that( candidates, contains_inanyorder(
                             has_entries( {
                               'detailed_info': 'int a\n',
                               'extra_menu_info': 'int',
                               'insertion_text': 'a',
                               'kind': 'MEMBER',
                               'menu_text': 'a'
                             } ),
                             has_entries( {
                               'detailed_info': 'int a\n',
                               'extra_menu_info': 'int',
                               'insertion_text': 'a',
                               'kind': 'MEMBER',
                               'menu_text': 'a'
                             } )
                           ) )
