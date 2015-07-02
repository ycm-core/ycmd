#!/usr/bin/env python
#
# Copyright (C) 2013  Google Inc.
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

from server_utils import SetUpPythonPath, CompatibleWithCurrentCoreVersion
SetUpPythonPath()

import sys
import logging
import json
import argparse
import waitress
import signal
import os
import base64
from ycmd import user_options_store
from ycmd import extra_conf_store
from ycmd import utils
from ycmd.watchdog_plugin import WatchdogPlugin
from ycmd.hmac_plugin import HmacPlugin

def YcmCoreSanityCheck():
  if 'ycm_core' in sys.modules:
    raise RuntimeError( 'ycm_core already imported, ycmd has a bug!' )


# We manually call sys.exit() on SIGTERM and SIGINT so that atexit handlers are
# properly executed.
def SetUpSignalHandler( stdout, stderr, keep_logfiles ):
  def SignalHandler( signum, frame ):
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

    sys.exit()

  for sig in [ signal.SIGTERM,
               signal.SIGINT ]:
    signal.signal( sig, SignalHandler )


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
                       help = 'server hostname')
  # Default of 0 will make the OS pick a free port for us
  parser.add_argument( '--port', type = int, default = 0,
                       help = 'server port')
  parser.add_argument( '--log', type = str, default = 'info',
                       help = 'log level, one of '
                              '[debug|info|warning|error|critical]' )
  parser.add_argument( '--idle_suicide_seconds', type = int, default = 0,
                       help = 'num idle seconds before server shuts down')
  parser.add_argument( '--options_file', type = str, default = '',
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
  if options_file:
    user_options = json.load( open( options_file, 'r' ) )
    options.update( user_options )
  utils.RemoveIfExists( options_file )
  hmac_secret = base64.b64decode( options[ 'hmac_secret' ] )
  del options[ 'hmac_secret' ]
  user_options_store.SetAll( options )
  return options, hmac_secret


def CloseStdin():
  sys.stdin.close()
  os.close(0)


def Main():
  args = ParseArguments()

  if args.stdout is not None:
    sys.stdout = open( args.stdout, 'w' )
  if args.stderr is not None:
    sys.stderr = open( args.stderr, 'w' )

  SetupLogging( args.log )
  options, hmac_secret = SetupOptions( args.options_file )

  # This ensures that ycm_core is not loaded before extra conf
  # preload was run.
  YcmCoreSanityCheck()
  extra_conf_store.CallGlobalExtraConfYcmCorePreloadIfExists()

  if not CompatibleWithCurrentCoreVersion():
    # ycm_core.[so|dll|dylib] is too old and needs to be recompiled.
    sys.exit( 2 )

  PossiblyDetachFromTerminal()

  # This can't be a top-level import because it transitively imports
  # ycm_core which we want to be imported ONLY after extra conf
  # preload has executed.
  from ycmd import handlers
  handlers.UpdateUserOptions( options )
  handlers.SetHmacSecret( hmac_secret )
  SetUpSignalHandler( args.stdout, args.stderr, args.keep_logfiles )
  handlers.app.install( WatchdogPlugin( args.idle_suicide_seconds ) )
  handlers.app.install( HmacPlugin( hmac_secret ) )
  CloseStdin()
  waitress.serve( handlers.app,
                  host = args.host,
                  port = args.port,
                  threads = 30 )


if __name__ == "__main__":
  Main()

