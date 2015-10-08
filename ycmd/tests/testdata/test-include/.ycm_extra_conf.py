import os.path


def FlagsForFile( filename, **kwargs ):
  d = os.path.dirname( filename )
  return {
    'flags': [ '-iquote', os.path.join( d, 'quote' ),
               '-I', os.path.join( d, 'system' ) ],
    'do_cache': True
  }
