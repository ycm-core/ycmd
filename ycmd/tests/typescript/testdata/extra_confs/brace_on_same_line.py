def Settings( **kwargs ):
    assert kwargs[ 'language' ] == 'typescript'
    return {
      'formatting_options': {
        'placeOpenBraceOnNewLineForFunctions': False
      }
    }

