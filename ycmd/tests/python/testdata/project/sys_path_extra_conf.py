import os
import sys

DIR_OF_THIS_SCRIPT = os.path.abspath( os.path.dirname( __file__ ) )


def PythonSysPath( **kwargs ):
  sys_path = kwargs[ 'sys_path' ]
  sys_path.insert( 0, os.path.join( DIR_OF_THIS_SCRIPT, 'third_party' ) )
  return sys_path
