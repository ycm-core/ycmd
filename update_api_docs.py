#!/usr/bin/env python

from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals
from __future__ import absolute_import

import os
import platform
import sys
import subprocess

DIR_OF_THIS_SCRIPT = os.path.dirname( os.path.abspath( __file__ ) )
DIR_OF_DOCS = os.path.join( DIR_OF_THIS_SCRIPT, 'docs' )


def OnWindows():
  return platform.system() == 'Windows'


# On Windows, distutils.spawn.find_executable only works for .exe files
# but .bat and .cmd files are also executables, so we use our own
# implementation.
def FindExecutable( executable ):
  # Executable extensions used on Windows
  WIN_EXECUTABLE_EXTS = [ '.exe', '.bat', '.cmd' ]

  paths = os.environ[ 'PATH' ].split( os.pathsep )
  base, extension = os.path.splitext( executable )

  if OnWindows() and extension.lower() not in WIN_EXECUTABLE_EXTS:
    extensions = WIN_EXECUTABLE_EXTS
  else:
    extensions = [ '' ]

  for extension in extensions:
    executable_name = executable + extension
    if not os.path.isfile( executable_name ):
      for path in paths:
        executable_path = os.path.join( path, executable_name )
        if os.path.isfile( executable_path ):
          return executable_path
    else:
      return executable_name
  return None


def GenerateApiDocs():
  npm = FindExecutable( 'npm' )
  if not npm:
    sys.exit( 'ERROR: NPM is required to generate API docs.' )

  os.chdir( os.path.join( DIR_OF_DOCS ) )
  subprocess.call( [ npm, 'install', '--production' ] )

  bootprint = FindExecutable( os.path.join( DIR_OF_DOCS, 'node_modules',
                                            '.bin', 'bootprint' ) )
  api = os.path.join( DIR_OF_DOCS, 'openapi.yml' )
  subprocess.call( [ bootprint, 'openapi', api, DIR_OF_DOCS ] )


if __name__ == '__main__':
  GenerateApiDocs()
