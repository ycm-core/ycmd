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

import os
from ycmd.tests.clang.conftest import * # noqa

shared_app = None


def PathToTestFile( *args ):
  dir_of_current_script = os.path.dirname( os.path.abspath( __file__ ) )
  return os.path.join( dir_of_current_script, 'testdata', *args )


# A mock of ycm_core.ClangCompleter with translation units still being parsed.
class MockCoreClangCompleter:

  def GetDefinitionLocation( self, *args ):
    pass

  def GetDeclarationLocation( self, *args ):
    pass

  def GetDefinitionOrDeclarationLocation( self, *args ):
    pass

  def GetTypeAtLocation( self, *args ):
    pass

  def GetEnclosingFunctionAtLocation( self, *args ):
    pass

  def GetDocsForLocationInFile( self, *args ):
    pass

  def GetFixItsForLocationInFile( self, *args ):
    pass

  def UpdatingTranslationUnit( self, filename ):
    return True
