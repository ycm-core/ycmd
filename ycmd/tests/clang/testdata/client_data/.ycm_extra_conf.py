def Settings( **kwargs ):
  return { 'flags': kwargs[ 'client_data' ].get( 'flags', [] ) }
