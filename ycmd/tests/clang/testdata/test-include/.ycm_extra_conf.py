import os.path


def Settings( **kwargs ):
  d = os.path.dirname( kwargs[ 'filename' ] )
  return { 'flags': [ '-iquote', os.path.join( d, 'quote' ),
                      '-I', os.path.join( d, 'system' ),
                      '-iframework', os.path.join( d, 'Frameworks' ) ] }
