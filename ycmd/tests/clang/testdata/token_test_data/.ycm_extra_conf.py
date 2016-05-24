def FlagsForFile( filename, **kwargs ):

  flags = [ '-x', 'c++', '-I', '.' ]

  client_data = kwargs[ 'client_data' ]
  if client_data:
    flags.extend( client_data )

  return {
    'flags': flags,
    'do_cache': False
  }
