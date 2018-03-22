import os
import sys

DIR_OF_THIS_SCRIPT = os.path.abspath( os.path.dirname( __file__ ) )


def Settings( **kwargs ):
  return {
    'interpreter_path': sys.executable,
    'sys_path': [ os.path.join( DIR_OF_THIS_SCRIPT, 'third_party' ) ]
  }
