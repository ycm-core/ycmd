import os

# These files are all a single TU 'unity.cc'
unity_files = [
  'unitya.cc',
  'unityb.cc',
  'unity.h',
]


def Settings( **kwargs ):
  filename = kwargs[ 'filename' ]
  if os.path.basename( filename ) in unity_files:
    return {
      'flags': [ '-x', 'c++', '-I', '.' ],
      'override_filename': os.path.join( os.path.dirname( filename ),
                                         'unity.cc' ),
      'include_paths_relative_to_dir': os.path.dirname( filename ),
    }

  return { 'flags': ['-x', 'c++', '-I', '.'] }
