# Copyright (C) 2017 ycmd contributors
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

import functools
import os

from ycmd.completers.language_server import language_server_completer as lsc
from ycmd.tests.test_utils import ( IgnoreExtraConfOutsideTestsFolder,
                                    IsolatedApp,
                                    StopCompleterServer )


def PathToTestFile( *args ):
  dir_of_current_script = os.path.dirname( os.path.abspath( __file__ ) )
  return os.path.join( dir_of_current_script, 'testdata', *args )


class MockConnection( lsc.LanguageServerConnection ):

  def TryServerConnectionBlocking( self ):
    return True


  def Shutdown( self ):
    pass


  def WriteData( self, data ):
    pass


  def ReadData( self, size = -1 ):
    return bytes( b'' )


def IsolatedYcmd( custom_options = {} ):
  """Defines a decorator to be attached to tests of this package. This decorator
  passes a unique ycmd application as a parameter. It should be used on tests
  that change the server state in a irreversible way (ex: a semantic subserver
  is stopped or restarted) or expect a clean state (ex: no semantic subserver
  started, no .ycm_extra_conf.py loaded, etc).

  Do NOT attach it to test generators but directly to the yielded tests."""
  def Decorator( test ):
    @functools.wraps( test )
    def Wrapper( *args, **kwargs ):
      with IgnoreExtraConfOutsideTestsFolder():
        with IsolatedApp( custom_options ) as app:
          try:
            test( app, *args, **kwargs )
          finally:
            StopCompleterServer( app, 'foo' )
    return Wrapper
  return Decorator
