#!/usr/bin/env python3

import argparse
import contextlib
import lzma
import os
import shutil
import tempfile
import tarfile


DIR_OF_THIS_SCRIPT = os.path.dirname( os.path.abspath( __file__ ) )
DIR_OF_THIRD_PARTY = os.path.join( DIR_OF_THIS_SCRIPT, 'third_party' )


import urllib.error
import urllib.request
from io import BytesIO


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


def ExtractTar( uncompressed_data, destination ):
  with tarfile.TarFile( fileobj=uncompressed_data, mode='r' ) as tar_file:
    a_member = tar_file.getmembers()[ 0 ]
    tar_file.extractall( destination )

  # Determine the directory name
  return os.path.join( destination, a_member.name.split( '/', 1 )[ 0 ] )


def ExtractLZMA( compressed_data, destination ):
  uncompressed_data = BytesIO( lzma.decompress( compressed_data ) )
  return ExtractTar( uncompressed_data, destination )


def ParseArguments():
  parser = argparse.ArgumentParser()

  parser.add_argument( 'version', action='store',
                       help = 'The LLVM version' )

  args = parser.parse_args()

  return args


def Overwrite( src, dest ):
  if os.path.exists( dest ):
    shutil.rmtree( dest )
  shutil.copytree( src, dest )


def UpdateClangHeaders( version, temp_dir ):
  # The headers do not seem to differ between archives, so pick the smallest
  archive_name = f'clang+llvm-{ version }-arm64-apple-darwin.tar.xz'

  compressed_data = Download( 'https://github.com/ycm-core/llvm/releases/'
                              f'download/{ version }/{ archive_name }' )
  print( f'Extracting { archive_name }' )
  src = ExtractLZMA( compressed_data, temp_dir )

  print( 'Updating Clang headers...' )
  includes_dir = os.path.join(
    DIR_OF_THIRD_PARTY, 'clang', 'lib', 'clang', version, 'include' )
  Overwrite( os.path.join(
                src, 'lib', 'clang', version.split( '.', 1 )[ 0 ], 'include' ),
             includes_dir )

  Overwrite( os.path.join( src, 'include', 'clang-c' ),
             os.path.join( DIR_OF_THIS_SCRIPT, 'cpp', 'llvm', 'include',
                           'clang-c' ) )


def Main():
  args = ParseArguments()

  with TemporaryDirectory() as temp_dir:
    UpdateClangHeaders( args.version, temp_dir )


if __name__ == "__main__":
  Main()
