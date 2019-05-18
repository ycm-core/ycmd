import glob
import os

srcdir = os.path.join( os.path.dirname( os.path.abspath( __file__ ) ), 'src' )

def FlagsForFile( filename, **kwargs ):
  files = set( glob.glob( os.path.join( srcdir, '*.vala' ) ) )
  filename = os.path.abspath( filename )
  if not filename in files:
    # Tests and benchmarks
    files.add( filename )
  return {
      'vala_flags': [
        '--enable-experimental',
        '--enable-experimental-non-null',
        '--pkg=libvala-0.46', # You may want to change this flag
      ] + list( files )
  }
