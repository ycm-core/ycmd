import os

DIR_OF_THIS_SCRIPT = os.path.dirname( os.path.abspath( __file__ ) )


def Settings( **kwargs ):
  return {
    'flags': [ '-isystem', os.path.join( DIR_OF_THIS_SCRIPT, 'include' ) ]
  }
