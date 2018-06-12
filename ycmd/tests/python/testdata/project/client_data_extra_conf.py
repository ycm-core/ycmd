import os


def Settings( **kwargs ):
  return {
    'sys_path': kwargs[ 'client_data' ].get( 'sys_path', [] )
  }
