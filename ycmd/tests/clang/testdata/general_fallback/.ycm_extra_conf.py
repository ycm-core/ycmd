ftopts = {
  'cpp': [
    '-Wall',
    '-Wextra',
    '-x', 'c++',
    '-std=c++11',
  ],
  'c': [
    '-Wall',
    '-Wextra',
    '-std=c99',
    '-x', 'c',
    '-I', '.',
  ],
  'cuda': [
    '-Wall',
    '-Wextra',
    '-x', 'cuda',
    '--std=c++11',
  ],
  'objc': [
    '-x', 'objective-c',
    '-I', '.',
  ],
}

def Settings(**kwargs):
  client_data = kwargs['client_data']
  ft = client_data['&filetype']

  try:
    opts = ftopts[ft]
  except:
    opts = ftopts['cpp']

  if 'throw' in client_data:
    raise ValueError( client_data['throw'] )

  return { 'flags': opts }
