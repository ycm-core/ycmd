#!/usr/bin/env python
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals

import argparse
import contextlib
from os import ( listdir, mkdir )
import os.path as p
import shutil
import sys
import tempfile
import hashlib

DIR_OF_THIS_SCRIPT = p.dirname( p.abspath( __file__ ) )
DIR_OF_THIRD_PARTY = p.join( DIR_OF_THIS_SCRIPT, 'third_party' )


def GetStandardLibraryIndexInSysPath():
  for index, path in enumerate( sys.path ):
    if p.isfile( p.join( path, 'os.py' ) ):
      return index
  raise RuntimeError( 'Could not find standard library path in Python path.' )


def AddRequestDependencies():
  request_dep_root = p.abspath( p.join( DIR_OF_THIRD_PARTY,
                                        'requests_deps' ) )
  for path in listdir( request_dep_root ):
    sys.path.insert( 0, p.join( request_dep_root, path ) )

  sys.path.insert( 0, p.abspath( p.join( DIR_OF_THIRD_PARTY,
                                         'requests_deps',
                                         'urllib3',
                                         'src' ) ) )


sys.path.insert( GetStandardLibraryIndexInSysPath() + 1,
                 p.abspath( p.join( DIR_OF_THIRD_PARTY, 'python-future',
                                    'src' ) ) )
AddRequestDependencies()

# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa
from future.utils import iteritems
import requests


URL_FORMAT = {
  'release': ( "https://github.com/OmniSharp/omnisharp-roslyn/"
               "releases/download/{version}/{file_name}" ),
       'ci': ( "https://roslynomnisharp.blob.core.windows.net/"
               "releases/{version}/{file_name}" ),
}
FILE_NAME = {
    'win32': 'omnisharp.http-win-x86.zip',
    'win64': 'omnisharp.http-win-x64.zip',
    'macos': 'omnisharp.http-osx.tar.gz',
  'linux32': 'omnisharp.http-linux-x86.tar.gz',
  'linux64': 'omnisharp.http-linux-x64.tar.gz',
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
  request = requests.get( url, stream=True )
  request.raise_for_status()
  content = request.content
  request.close()
  return content


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
  except requests.exceptions.HTTPError as error:
    if error.response.status_code != 404:
      raise
    print( 'Cannot download {}'.format( file_name ) )
    return

  with open( archive, 'rb' ) as f:
    return hashlib.sha256( f.read() ).hexdigest()


def Process( output_dir, version ):
  result = {}

  for os_name, file_name in iteritems( FILE_NAME ):
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

  print( "Omnisharp configration for {} is:".format( version ) )
  for os_name, os_data in iteritems( output ):
    print( "    {}: {{".format( repr( os_name ) ) )
    for key, value in iteritems( os_data ):
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
