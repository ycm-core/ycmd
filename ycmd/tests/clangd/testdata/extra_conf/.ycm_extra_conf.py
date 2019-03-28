import os

DIR_OF_THIS_SCRIPT = os.path.abspath( os.path.dirname( __file__ ) )


def Settings( **kwargs ):
  if kwargs[ 'language' ] == 'cfamily':
    basename = os.path.basename( kwargs[ 'filename' ] )

    if basename == 'foo.cpp':
      return {
        'flags': ['-I', 'include', '-DFOO']
      }
    if basename == 'bar.cpp':
      return {
        'flags': ['g++', '-I', 'include', '-DBAR'],
        'include_paths_relative_to_dir': os.path.join( DIR_OF_THIS_SCRIPT,
                                                       'subdir' )
      }
