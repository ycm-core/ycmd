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

import functools
import os
from ycmd.tests.test_utils import ClearCompletionsCache, IsolatedApp, SetUpApp

shared_app = None


def PathToTestFile( *args ):
  dir_of_current_script = os.path.dirname( os.path.abspath( __file__ ) )
  return os.path.join( dir_of_current_script, 'testdata', *args )


def SharedYcmd( test ):
  global shared_app
  if shared_app is None:
    shared_app = SetUpApp()

  @functools.wraps( test )
  def Wrapper( test_case_instance, *args, **kwargs ):
    ClearCompletionsCache()
    return test( test_case_instance, shared_app, *args, **kwargs )
  return Wrapper


def IsolatedYcmd( custom_options = {} ):
  def Decorator( test ):
    @functools.wraps( test )
    def Wrapper( test_case_instance, *args, **kwargs ):
      with IsolatedApp( custom_options ) as app:
        test( test_case_instance, app, *args, **kwargs )
    return Wrapper
  return Decorator
