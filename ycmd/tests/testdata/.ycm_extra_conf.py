def FlagsForFile( filename ):
  return {
    'flags': ['-x', 'c++',
              '-I', 'test-gotoinclude',
              '-I', 'test-gotoinclude/OtherDirectory',
              '-isystem', 'test-gotoinclude'
    ],
    'do_cache': True
  }
