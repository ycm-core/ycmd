#!/usr/bin/env python3

from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals
from __future__ import absolute_import

import argparse
import platform
import os
import os.path as p
import subprocess
import sys

DIR_OF_THIS_SCRIPT = p.dirname( p.abspath( __file__ ) )


def ParseArguments():
  parser = argparse.ArgumentParser()
  parser.add_argument( '--msvc', type = int, choices = [ 15, 16, 17 ],
                       default = 16, help = 'Choose the Microsoft Visual '
                       'Studio version (default: %(default)s).' )

  return parser.parse_known_args()


def BuildYcmdLibsAndRunBenchmark( args, extra_args ):
  build_cmd = [
    sys.executable,
    p.join( DIR_OF_THIS_SCRIPT, 'build.py' ),
  ] + extra_args

  os.environ[ 'YCM_BENCHMARK' ] = '1'

  if args.msvc and platform.system() == 'Windows':
    build_cmd.extend( [ '--msvc', str( args.msvc ) ] )

  subprocess.check_call( build_cmd )


def Main():
  args, extra_args = ParseArguments()
  BuildYcmdLibsAndRunBenchmark( args, extra_args )


if __name__ == "__main__":
  Main()
