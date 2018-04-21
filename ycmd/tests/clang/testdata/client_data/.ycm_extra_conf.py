def FlagsForFile( filename, **kwargs ):
  return { 'flags': kwargs[ 'client_data' ].get( 'flags', [] ) }
