#
# Copyright (C) 2015 ycmd contributors
#
# This file is part of YouCompleteMe.
#
# YouCompleteMe is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# YouCompleteMe is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with YouCompleteMe.  If not, see <http://www.gnu.org/licenses/>.

from ycmd.server_utils import SetUpPythonPath
SetUpPythonPath()

import bottle

from webtest import TestApp
from nose.tools import ( eq_, with_setup )

from ycmd import handlers
from ycmd.tests.test_utils import ( BuildRequest, Setup )

from .test_utils import ( with_cwd,
                          TEST_DATA_DIR,
                          WaitForTernServerReady  )

bottle.debug( True )

@with_setup( Setup )
@with_cwd( TEST_DATA_DIR )
def Subcommands_TernCompleter_Defined_Subcommands_test():
  app = TestApp( handlers.app )
  subcommands_data = BuildRequest( completer_target = 'javascript' )

  WaitForTernServerReady( app )

  eq_( sorted ( [ 'ConnectToServer',
                  'GoToDefinition',
                  'GoTo',
                  'GetDoc',
                  'GetType',
                  'StartServer',
                  'StopServer'] ),
        app.post_json( '/defined_subcommands', subcommands_data ).json )
