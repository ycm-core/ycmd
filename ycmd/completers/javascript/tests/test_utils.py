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

import contextlib2, os, time
from ycmd.tests.test_utils import BuildRequest

TEST_DATA_DIR = os.path.join( os.path.dirname( __file__ ), 'testdata' )


@contextlib2.contextmanager
def with_cwd( wd ):
  # Sadly, the Tern.js server requires that its cwd is within the "project"
  # directory, so we have to set the working directory to our testdata directory
  # for each test. The following context manager just temporarily changes the
  # working directory to the supplied path.
  #
  # contextlib2 is used because it works in python 2.6 (as a decorator)
  prev_wd = os.getcwd()
  os.chdir( wd )
  try:
    yield
  finally:
    os.chdir( prev_wd )


def PathToTestFile( *args ):
  return os.path.abspath( os.path.join( TEST_DATA_DIR, *args ) )


def WaitForTernServerReady( app ):
  app.post_json( '/run_completer_command', BuildRequest(
    command_arguments = [ 'StartServer' ],
    completer_target = 'filetype_default',
    filetype = 'javascript',
    filepath = '/foo.js',
    contents = '',
    line_num = '1'
  ) )

  retries = 100
  while retries > 0:
    result = app.get( '/ready', { 'subserver': 'javascript' } ).json
    if result:
      return

    time.sleep( 0.2 )
    retries = retries - 1

  raise RuntimeError( 'Timeout waiting for Tern.js server to be ready' )
