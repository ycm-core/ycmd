# Copyright (C) 2021 ycmd contributors
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

import functools
import os
import unittest
from ycmd.tests.test_utils import ( ClearCompletionsCache,
                                    IgnoreExtraConfOutsideTestsFolder,
                                    IsolatedApp,
                                    SetUpApp )
from ycmd.utils import ImportCore

shared_app = None


def PathToTestFile( *args ):
  dir_of_current_script = os.path.dirname( os.path.abspath( __file__ ) )
  return os.path.join( dir_of_current_script, 'testdata', *args )


def setUpModule():
  global shared_app
  shared_app = SetUpApp( { 'use_clangd': 0 } )


def SharedYcmd( test ):
  global shared_app

  @functools.wraps( test )
  def Wrapper( test_case_instance, *args, **kwargs ):
    ClearCompletionsCache()
    with IgnoreExtraConfOutsideTestsFolder():
      return test( test_case_instance, shared_app, *args, **kwargs )
  return Wrapper


def IsolatedYcmd( custom_options = {} ):
  def Decorator( test ):
    @functools.wraps( test )
    def Wrapper( test_case_instance, *args, **kwargs ):
      custom_options.update( { 'use_clangd': 0 } )
      with IsolatedApp( custom_options ) as app:
        test( test_case_instance, app, *args, **kwargs )
    return Wrapper
  return Decorator


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


def load_tests( loader: unittest.TestLoader, standard_tests, pattern ):
  if not ImportCore().HasClangSupport():
    return unittest.TestSuite()
  this_dir = os.path.dirname( __file__ )
  package_tests = loader.discover( this_dir, pattern )
  standard_tests.addTests( package_tests )
  return standard_tests
