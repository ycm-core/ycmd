#!/usr/bin/env python3

import argparse
import contextlib
from os import mkdir
import os.path as p
import shutil
import tempfile
import hashlib
import urllib.error
import urllib.request

DIR_OF_THIS_SCRIPT = p.dirname( p.abspath( __file__ ) )
DIR_OF_THIRD_PARTY = p.join( DIR_OF_THIS_SCRIPT, 'third_party' )




URL_FORMAT = {
  'release': ( "https://github.com/OmniSharp/omnisharp-roslyn/"
               "releases/download/{version}/{file_name}" ),
       'ci': ( "https://roslynomnisharp.blob.core.windows.net/"
               "releases/{version}/{file_name}" ),
}
FILE_NAME = {
    'win32': 'omnisharp-win-x86-net6.0.zip',
    'win64': 'omnisharp-win-x64-net6.0.zip',
    'macos': 'omnisharp-osx-arm64-net6.0.tar.gz',
  'linux64': 'omnisharp-linux-x64-net6.0.tar.gz',
}


@contextlib.contextmanager
def TemporaryDirectory():
  temp_dir = tempfile.mkdtemp()
  try:
    yield temp_dir
  finally:
    shutil.rmtree( temp_dir )


def Download( url ):
  print( 'Downloading {}'.format( url.rsplit( '/', 1 )[ -1 ] ) )
  with urllib.request.urlopen( url ) as response:
    return response.read()


def ParseArguments():
  parser = argparse.ArgumentParser()

  parser.add_argument( 'version', action='store',
                       help = 'The Omnisharp version' )
  parser.add_argument( '--cache-dir', action='store',
                       help = 'For testing, directory to cache packages.' )

  args = parser.parse_args()

  return args


def GetDownloadUrl( version, file_name ):
  download_url_key =  'ci' if "-" in version else 'release'

  return URL_FORMAT[ download_url_key ].format( version = version,
                                                file_name = file_name )


def FetchAndHash( download_url, output_dir, file_name ):
  try:
    archive = p.join( output_dir, file_name )
    if not p.exists( archive ):
      compressed_data = Download( download_url )
      with open( archive, 'wb' ) as f:
        f.write( compressed_data )
  except urllib.error.HTTPError as error:
    if error.status != 404:
      raise
    print( 'Cannot download {}'.format( file_name ) )
    return

  with open( archive, 'rb' ) as f:
    return hashlib.sha256( f.read() ).hexdigest()


def Process( output_dir, version ):
  result = {}

  for os_name, file_name in FILE_NAME.items():
    download_url = GetDownloadUrl( version, file_name )
    result[ os_name ] = {
        'version': version,
        'download_url': download_url,
        'file_name': file_name,
        'check_sum': FetchAndHash( download_url, output_dir, file_name )
    }

  return result


def MkDirIfMissing( dir ):
  try:
    mkdir( dir )
  except OSError:
    pass


def Main():
  args = ParseArguments()
  version = args.version

  if args.cache_dir:
    MkDirIfMissing( args.cache_dir )
    cache_dir = p.join( args.cache_dir, version )
    MkDirIfMissing( cache_dir )
    output = Process( cache_dir, version )
  else:
    with TemporaryDirectory() as temp_dir:
      output = Process( temp_dir, version )

  print( "Omnisharp configuration for {} is:".format( version ) )
  for os_name, os_data in output.items():
    print( "    {}: {{".format( repr( os_name ) ) )
    for key, value in os_data.items():
      line = "      {}: {},".format( repr( key ), repr( value ) )
      if len( line ) > 80:
        line = "      {}: ( {} ),".format( repr( key ), repr( value ) )
        format_index = line.index( '(' ) + 2
        while len( line ) > 80:
          print( line[ 0:78 ] + "'" )
          line = ( ' ' * format_index ) + "'" + line[ 78: ]
      print( line )
    print( "    }," )


if __name__ == "__main__":
  Main()
