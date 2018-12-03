# Copyright (C) 2013-2019 ycmd contributors
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

from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
# Other imports from `future` must be placed after SetUpPythonPath.

import sys
import os

sys.path.insert( 0, os.path.dirname( os.path.abspath( __file__ ) ) )
from server_utils import SetUpPythonPath
SetUpPythonPath()

# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa

import atexit
import sys
import logging
import json
import argparse
import signal
import os
import base64

from ycmd import extra_conf_store, user_options_store, utils
from ycmd.hmac_plugin import HmacPlugin
from ycmd.utils import ( ImportAndCheckCore,
                         OpenForStdHandle,
                         ReadFile,
                         ToBytes )
from ycmd.wsgi_server import StoppableWSGIServer


def YcmCoreSanityCheck():
  if 'ycm_core' in sys.modules:
    raise RuntimeError( 'ycm_core already imported, ycmd has a bug!' )


# We manually call sys.exit() on SIGTERM and SIGINT so that atexit handlers are
# properly executed.
def SetUpSignalHandler():
  def SignalHandler( signum, frame ):
    sys.exit()

  for sig in [ signal.SIGTERM,
               signal.SIGINT ]:
    signal.signal( sig, SignalHandler )


def CleanUpLogfiles( stdout, stderr, keep_logfiles ):
  # We reset stderr & stdout, just in case something tries to use them
  if stderr:
    tmp = sys.stderr
    sys.stderr = sys.__stderr__
    tmp.close()
  if stdout:
    tmp = sys.stdout
    sys.stdout = sys.__stdout__
    tmp.close()

  if not keep_logfiles:
    if stderr:
      utils.RemoveIfExists( stderr )
    if stdout:
      utils.RemoveIfExists( stdout )


def PossiblyDetachFromTerminal():
  # If not on windows, detach from controlling terminal to prevent
  # SIGINT from killing us.
  if not utils.OnWindows():
    try:
      os.setsid()
    # setsid() can fail if the user started ycmd directly from a shell.
    except OSError:
      pass


def ParseArguments():
  parser = argparse.ArgumentParser()
  # Not using 'localhost' on purpose; see #987 and #1130
  parser.add_argument( '--host', type = str, default = '127.0.0.1',
                       help = 'server hostname' )
  # Default of 0 will make the OS pick a free port for us
  parser.add_argument( '--port', type = int, default = 0,
                       help = 'server port' )
  parser.add_argument( '--log', type = str, default = 'info',
                       help = 'log level, one of '
                              '[debug|info|warning|error|critical]' )
  parser.add_argument( '--idle_suicide_seconds', type = int, default = 0,
                       help = 'num idle seconds before server shuts down' )
  parser.add_argument( '--check_interval_seconds', type = int, default = 600,
                       help = 'interval in seconds to check server '
                              'inactivity and keep subservers alive' )
  parser.add_argument( '--options_file', type = str, required = True,
                       help = 'file with user options, in JSON format' )
  parser.add_argument( '--stdout', type = str, default = None,
                       help = 'optional file to use for stdout' )
  parser.add_argument( '--stderr', type = str, default = None,
                       help = 'optional file to use for stderr' )
  parser.add_argument( '--keep_logfiles', action = 'store_true', default = None,
                       help = 'retain logfiles after the server exits' )
  return parser.parse_args()


def SetupLogging( log_level ):
  numeric_level = getattr( logging, log_level.upper(), None )
  if not isinstance( numeric_level, int ):
    raise ValueError( 'Invalid log level: %s' % log_level )

  # Has to be called before any call to logging.getLogger()
  logging.basicConfig( format = '%(asctime)s - %(levelname)s - %(message)s',
                       level = numeric_level )


def SetupOptions( options_file ):
  options = user_options_store.DefaultOptions()
  user_options = json.loads( ReadFile( options_file ) )
  options.update( user_options )
  utils.RemoveIfExists( options_file )
  hmac_secret = ToBytes( base64.b64decode( options[ 'hmac_secret' ] ) )
  del options[ 'hmac_secret' ]
  user_options_store.SetAll( options )
  return options, hmac_secret


def CloseStdin():
  sys.stdin.close()
  os.close( 0 )


def Main():
  args = ParseArguments()

  if args.stdout is not None:
    sys.stdout = OpenForStdHandle( args.stdout )
  if args.stderr is not None:
    sys.stderr = OpenForStdHandle( args.stderr )

  SetupLogging( args.log )
  options, hmac_secret = SetupOptions( args.options_file )

  # This ensures that ycm_core is not loaded before extra conf
  # preload was run.
  YcmCoreSanityCheck()
  extra_conf_store.CallGlobalExtraConfYcmCorePreloadIfExists()

  code = ImportAndCheckCore()
  if code:
    sys.exit( code )

  PossiblyDetachFromTerminal()

  # These can't be top-level imports because they transitively import
  # ycm_core which we want to be imported ONLY after extra conf
  # preload has executed.
  from ycmd import handlers
  from ycmd.watchdog_plugin import WatchdogPlugin
  handlers.UpdateUserOptions( options )
  handlers.SetHmacSecret( hmac_secret )
  handlers.KeepSubserversAlive( args.check_interval_seconds )
  SetUpSignalHandler()
  # Functions registered by the atexit module are called at program termination
  # in last in, first out order.
  atexit.register( CleanUpLogfiles, args.stdout,
                                    args.stderr,
                                    args.keep_logfiles )
  atexit.register( handlers.ServerCleanup )
  handlers.app.install( WatchdogPlugin( args.idle_suicide_seconds,
                                        args.check_interval_seconds ) )
  handlers.app.install( HmacPlugin( hmac_secret ) )
  CloseStdin()
  handlers.wsgi_server = StoppableWSGIServer( handlers.app,
                                              host = args.host,
                                              port = args.port,
                                              threads = 30 )
  handlers.wsgi_server.Run()


if __name__ == "__main__":
  Main()
