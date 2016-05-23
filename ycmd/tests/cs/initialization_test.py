# Copyright (C) 2016 ycmd contributors
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
from future import standard_library
standard_library.install_aliases()
from builtins import *  # noqa

import time
import threading
from nose.tools import ok_

from ycmd.tests.cs import ( IsolatedYcmd, PathToTestFile, StopOmniSharpServer,
                            WrapOmniSharpServer )


@IsolatedYcmd
def Initialization_StopServer_NoErrorIfNotStarted_test( app ):
  filepath = PathToTestFile( 'testy', 'GotoTestCase.cs' )
  StopOmniSharpServer( app, filepath )
  # Success = no raise


@IsolatedYcmd
def Initialization_StopServer_LoggingThreadsStops_test( app ):
  preexisting_threads = threading.enumerate()

  def has_existing_log_threads( desired_result ):
    log_thread_name = 'Omnisharp_Log_'
    for _ in range(0, 10):
      threads = threading.enumerate()
      new_threads = [ thread for thread in threads
                      if not any( [ thread.ident == t.ident
                                    for t in preexisting_threads ] ) ]
      has_log_threads = any( [ log_thread_name in thread.name
                           for thread in new_threads ] )
      if has_log_threads == desired_result:
        return desired_result
      time.sleep( .1 )
    return not desired_result

  filepath = PathToTestFile( 'testy', 'GetDocTestCase.cs' )
  # This starts Omnisharp server
  with WrapOmniSharpServer( app, filepath ):
    ok_( has_existing_log_threads( True ),
        "Omnisharp logging threads didn't start" )
  StopOmniSharpServer( app, filepath )

  ok_( not has_existing_log_threads( False ),
       "Omnisharp logging threads didn't die" )
