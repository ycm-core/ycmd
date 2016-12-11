#!/usr/bin/env python

from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
# Other imports from `future` must be placed after SetUpPythonPath.

import sys
import os

# TODO: Java 8 required (validate this)
PATH_TO_YCMD = os.path.join( os.path.dirname( __file__ ),
                             '..',
                             '..',
                             '..',
                             '..' )

sys.path.insert( 0, os.path.abspath( PATH_TO_YCMD ) )
from ycmd.server_utils import SetUpPythonPath
SetUpPythonPath()

from future import standard_library
standard_library.install_aliases()
from builtins import *  # noqa

import logging


def SetUpLogging( log_level ):
  numeric_level = getattr( logging, log_level.upper(), None )
  if not isinstance( numeric_level, int ):
    raise ValueError( 'Invalid log level: %s' % log_level )

  # Has to be called before any call to logging.getLogger()
  logging.basicConfig( format = '%(asctime)s - %(levelname)s - %(message)s',
                       level = numeric_level )


if __name__ == '__main__':
  SetUpLogging( 'debug' )

  from ycmd.completers.java.hook import GetCompleter
  from ycmd.user_options_store import DefaultOptions
  completer = GetCompleter( DefaultOptions() )

  completer.Shutdown()
