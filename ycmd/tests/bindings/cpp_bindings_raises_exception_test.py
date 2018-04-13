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
from builtins import *  # noqaimport ycm_core

from ycmd.tests.test_utils import ClangOnly
from hamcrest import assert_that, calling, raises
import ycm_core

READONLY_MESSAGE = 'can\'t set attribute'


@ClangOnly
def CppBindings_ReadOnly_test():
  assert_that( calling( ycm_core.CompletionData().__setattr__ )
                 .with_args( 'kind_', ycm_core.CompletionData().kind_ ),
               raises( AttributeError, READONLY_MESSAGE ) )

  assert_that( calling( ycm_core.Location().__setattr__ )
                 .with_args( 'line_number_', 1 ),
               raises( AttributeError, READONLY_MESSAGE ) )
  assert_that( calling( ycm_core.Location().__setattr__ )
                 .with_args( 'column_number_', 1 ),
               raises( AttributeError, READONLY_MESSAGE ) )
  assert_that( calling( ycm_core.Location().__setattr__ )
                 .with_args( 'filename_', 'foo' ),
               raises( AttributeError, READONLY_MESSAGE ) )

  assert_that( calling( ycm_core.Range().__setattr__ )
                 .with_args( 'end_', ycm_core.Range().end_ ),
               raises( AttributeError, READONLY_MESSAGE ) )
  assert_that( calling( ycm_core.Range().__setattr__ )
                 .with_args( 'start_', ycm_core.Range().start_ ),
               raises( AttributeError, READONLY_MESSAGE ) )

  assert_that( calling( ycm_core.FixItChunk().__setattr__ )
                 .with_args( 'range', ycm_core.FixItChunk().range ),
               raises( AttributeError, READONLY_MESSAGE ) )
  assert_that( calling( ycm_core.FixItChunk().__setattr__ )
                 .with_args( 'replacement_text', 'foo' ),
               raises( AttributeError, READONLY_MESSAGE ) )

  assert_that( calling( ycm_core.FixIt().__setattr__ )
                 .with_args( 'chunks', ycm_core.FixIt().chunks ),
               raises( AttributeError, READONLY_MESSAGE ) )
  assert_that( calling( ycm_core.FixIt().__setattr__ )
                 .with_args( 'location', ycm_core.FixIt().location ),
               raises( AttributeError, READONLY_MESSAGE ) )
  assert_that( calling( ycm_core.FixIt().__setattr__ )
                 .with_args( 'text', 'foo' ),
               raises( AttributeError, READONLY_MESSAGE ) )

  assert_that( calling( ycm_core.Diagnostic().__setattr__ )
                 .with_args( 'ranges_', ycm_core.Diagnostic().ranges_ ),
               raises( AttributeError, READONLY_MESSAGE ) )
  assert_that( calling( ycm_core.Diagnostic().__setattr__ )
                 .with_args( 'location_', ycm_core.Diagnostic().location_ ),
               raises( AttributeError, READONLY_MESSAGE ) )
  assert_that( calling( ycm_core.Diagnostic().__setattr__ )
                 .with_args( 'location_extent_',
                             ycm_core.Diagnostic().location_extent_ ),
               raises( AttributeError, READONLY_MESSAGE ) )
  assert_that( calling( ycm_core.Diagnostic().__setattr__ )
                 .with_args( 'fixits_', ycm_core.Diagnostic().fixits_ ),
               raises( AttributeError, READONLY_MESSAGE ) )
  assert_that( calling( ycm_core.Diagnostic().__setattr__ )
                 .with_args( 'text_', 'foo' ),
               raises( AttributeError, READONLY_MESSAGE ) )
  assert_that( calling( ycm_core.Diagnostic().__setattr__ )
                 .with_args( 'long_formatted_text_', 'foo' ),
               raises( AttributeError, READONLY_MESSAGE ) )
  assert_that( calling( ycm_core.Diagnostic().__setattr__ )
                 .with_args( 'kind_', ycm_core.Diagnostic().kind_.WARNING ),
               raises( AttributeError, READONLY_MESSAGE ) )

  assert_that( calling( ycm_core.DocumentationData().__setattr__ )
                 .with_args( 'raw_comment', 'foo' ),
               raises( AttributeError, READONLY_MESSAGE ) )
  assert_that( calling( ycm_core.DocumentationData().__setattr__ )
                 .with_args( 'brief_comment', 'foo' ),
               raises( AttributeError, READONLY_MESSAGE ) )
  assert_that( calling( ycm_core.DocumentationData().__setattr__ )
                 .with_args( 'canonical_type', 'foo' ),
               raises( AttributeError, READONLY_MESSAGE ) )
  assert_that( calling( ycm_core.DocumentationData().__setattr__ )
                 .with_args( 'display_name', 'foo' ),
               raises( AttributeError, READONLY_MESSAGE ) )
  assert_that( calling( ycm_core.DocumentationData().__setattr__ )
                 .with_args( 'comment_xml', 'foo' ),
               raises( AttributeError, READONLY_MESSAGE ) )

  db = ycm_core.CompilationDatabase( 'foo' )
  assert_that( calling( db.__setattr__ )
                 .with_args( 'database_directory', 'foo' ),
               raises( AttributeError, READONLY_MESSAGE ) )

  compilation_info = db.GetCompilationInfoForFile( 'foo.c' )
  assert_that( calling( compilation_info.__setattr__ )
                 .with_args( 'compiler_working_dir_', 'foo' ),
               raises( AttributeError, READONLY_MESSAGE ) )
  assert_that( calling( compilation_info.__setattr__ )
                 .with_args( 'compiler_flags_', ycm_core.StringVector() ),
               raises( AttributeError, READONLY_MESSAGE ) )


@ClangOnly
def CppBindings_CompilationInfo_NoInit_test():
  assert_that( calling( ycm_core.CompilationInfoForFile ),
      raises( TypeError, 'ycm_core.CompilationInfoForFile:'
                         ' No constructor defined!' ) )
