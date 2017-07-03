import os

DIR_OF_THIS_SCRIPT = os.path.dirname( os.path.abspath( __file__ ) )

def FlagsForFile( filename ):
  return { 'flags': [ '-xc++', '/c', '--driver-mode=cl', '/I', 'driver_mode_cl_include' ],
           'include_paths_relative_to_dir': DIR_OF_THIS_SCRIPT }
