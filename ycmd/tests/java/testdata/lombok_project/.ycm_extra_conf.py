import os
import os.path as p

DIR_OF_THIS_SCRIPT = p.dirname( p.abspath( __file__ ) )
DIR_OF_THIRD_PARTY = p.join( DIR_OF_THIS_SCRIPT, '..', '..', '..', '..', '..', 'third_party' )
PATH_TO_LOMBOK = p.join( DIR_OF_THIRD_PARTY, 'lombok', 'cache', 'lombok-1.18.16.jar' )


def Settings( **kwargs ):
  if not os.path.exists( PATH_TO_LOMBOK ):
    raise RuntimeError( "No lombok jar located at " + PATH_TO_LOMBOK )

  jvm_args = [
    '-noverify',
    '-Xmx1G',
    '-XX:+UseG1GC',
    '-XX:+UseStringDeduplication',
  ]

  return {
    'server': {
      'jvm_args': [ '-javaagent:' + PATH_TO_LOMBOK ] + jvm_args
    }
  }
