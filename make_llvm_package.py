#!/usr/bin/env python

# Passing an environment variable containing unicode literals to a subprocess
# on Windows and Python2 raises a TypeError. Since there is no unicode
# string in this script, we don't import unicode_literals to avoid the issue.
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import subprocess
import contextlib
import os
import os.path as p
import platform
import shutil
import sys
import tempfile
import tarfile
import hashlib

try:
  import lzma
except:
  from backports import lzma

DIR_OF_THIS_SCRIPT = p.dirname( p.abspath( __file__ ) )
sys.path.insert( 0, os.path.join( DIR_OF_THIS_SCRIPT, 'ycmd' ) )
from ycmd import server_utils
server_utils.SetUpPythonPath()

# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa
from future.utils import iteritems
import argparse
import requests
from io import BytesIO


def OnWindows():
  return platform.system() == 'Windows'


def OnMac():
  return platform.system() == 'Darwin'


LLVM_DOWNLOAD_DATA = {
  'win32': {
    'format': 'nsis',
    'llvm_package': 'LLVM-{llvm_version}-{os_name}.exe',
    'ycmd_package': 'libclang-{llvm_version}-{os_name}.tar.bz2',
    'files_to_copy': [
      os.path.join( 'bin', 'libclang.dll' ),
      os.path.join( 'lib', 'libclang.lib' ),
    ]
  },
  'win64': {
    'format': 'nsis',
    'llvm_package': 'LLVM-{llvm_version}-{os_name}.exe',
    'ycmd_package': 'libclang-{llvm_version}-{os_name}.tar.bz2',
    'files_to_copy': [
      os.path.join( 'bin', 'libclang.dll' ),
      os.path.join( 'lib', 'libclang.lib' ),
    ]
  },
  'x86_64-apple-darwin': {
    'format': 'lzma',
    'llvm_package': 'clang+llvm-{llvm_version}-{os_name}.tar.xz',
    'ycmd_package': 'libclang-{llvm_version}-{os_name}.tar.bz2',
    'files_to_copy': [
      os.path.join( 'lib', 'libclang.dylib' ),
    ]
  },
  'x86_64-linux-gnu-ubuntu-14.04': {
    'format': 'lzma',
    'llvm_package': 'clang+llvm-{llvm_version}-{os_name}.tar.xz',
    'ycmd_package': 'libclang-{llvm_version}-{os_name}.tar.bz2',
    'files_to_copy': [
      os.path.join( 'lib', 'libclang.so' ),
      os.path.join( 'lib', 'libclang.so.5' ),
      os.path.join( 'lib', 'libclang.so.5.0' ),
    ]
  },
}


@contextlib.contextmanager
def TemporaryDirectory():
  temp_dir = tempfile.mkdtemp()
  try:
    yield temp_dir
  finally:
    shutil.rmtree( temp_dir )


def DownloadClangLicense( version, destination ):
  print( 'Downloading license...' )
  request = requests.get(
    'https://releases.llvm.org/{version}/LICENSE.TXT'.format( version=version ),
    stream = True )
  request.raise_for_status()

  file_name = os.path.join( destination, 'LICENSE.TXT' )
  with open( file_name, 'wb' ) as f:
    f.write( request.content )

  request.close()

  return file_name


def DownloadClang( url ):
  print( 'Downloading {0}'.format( url ) )

  request = requests.get( url, stream=True )
  request.raise_for_status()
  content = request.content
  request.close()
  return content


def ExtractClangLZMA( compressed_data, destination ):
  uncompressed_data = BytesIO( lzma.decompress( compressed_data ) )

  print( 'Extracting...' )
  with tarfile.TarFile( fileobj=uncompressed_data, mode='r' ) as tar_file:
    a_member = tar_file.getmembers()[ 0 ]
    tar_file.extractall( destination )

  # Determine the directory name
  return os.path.join( destination,
                       a_member.name.split( os.path.sep )[ 0 ] )


def ExtractClang7Z( llvm_package, archive, destination ):
  # Extract with appropriate tool
  if OnWindows():
    command = [ '7z.exe' ]
  elif OnMac():
    command = [ '/Applications/Keka.app/Contents/Resources/keka7z' ]
  else:
    raise AssertionError( 'Dont know where to find 7zip on this platform' )

  command.extend( [
    '-y',
    'x',
    archive,
    '-o' + destination
  ] )

  subprocess.check_call( command )

  return destination


def MakeBundle( files_to_copy,
                license_file_name,
                source_dir,
                bundle_file_name,
                hashes ):
  print( "Bundling files from {0}".format( source_dir ) )
  with tarfile.open( name=bundle_file_name, mode='w:bz2' ) as tar_file:
    tar_file.add( license_file_name, arcname='LICENSE.TXT' )
    for file_name in files_to_copy:
      tar_file.add( name = os.path.join( source_dir, file_name ),
                    arcname = file_name )

  print( "Calculating checksum: " )
  with open( bundle_file_name, 'rb' ) as f:
    hashes[ bundle_file_name ] = hashlib.sha256( f.read() ).hexdigest()
    print( 'Hash is: {0}'.format( hashes[ bundle_file_name ] ) )


def UploadBundleToBintray( user_name,
                           api_token,
                           os_name,
                           version,
                           bundle_file_name ):
  print( 'Uploading to bintray...' )
  with open( bundle_file_name, 'rb' ) as bundle:
    request = requests.put(
      'https://api.bintray.com/content/{subject}/{repo}/{file_path}'.format(
        subject = user_name,
        repo = 'libclang',
        file_path = os.path.basename( bundle_file_name ) ),
      data = bundle,
      auth = ( user_name, api_token ),
      headers = {
        'X-Bintray-Package': 'libclang',
        'X-Bintray-Version': version,
        'X-Bintray-Publish': 1,
        'X-Bintray-Override': 1,
      } )
    request.raise_for_status()


def ParseArguments():
  parser = argparse.ArgumentParser()

  parser.add_argument( 'version', action='store',
                       help = 'The LLVM version' )

  parser.add_argument( '--bt-user', action='store',
                       help = 'Bintray user name. Defaults to environment '
                              'variable: YCMD_BINTRAY_USERNAME' )
  parser.add_argument( '--bt-token', action='store',
                       help = 'Bintray api token. Defaults to environment '
                              'variable: YCMD_BINTRAY_API_TOKEN.' )
  parser.add_argument( '--from-cache', action='store',
                       help = 'Use the clang packages from this dir. Useful '
                              'if releases.llvm.org is unreliable.' )
  parser.add_argument( '--output-dir', action='store',
                       help = 'For testing, directory to put bundles in.' )
  parser.add_argument( '--no-upload', action='store_true',
                       help = "For testing, just build the bundles; don't "
                              "upload to bintray. Useful with --output-dir." )

  args = parser.parse_args()

  if not args.bt_user:
    if 'YCMD_BINTRAY_USERNAME' not in os.environ:
      raise RuntimeError( 'ERROR: Must specify either --bt-user or '
                          'YCMD_BINTRAY_USERNAME in environment' )
    args.bt_user = os.environ[ 'YCMD_BINTRAY_USERNAME' ]

  if not args.bt_token:
    if 'YCMD_BINTRAY_API_TOKEN' not in os.environ:
      raise RuntimeError( 'ERROR: Must specify either --bt-token or '
                          'YCMD_BINTRAY_API_TOKEN in environment' )
    args.bt_token = os.environ[ 'YCMD_BINTRAY_API_TOKEN' ]

  return args


def PrepareBundleLZMA( cache_dir, llvm_package, download_url, temp_dir ):
  package_dir = None
  if cache_dir:
    archive = os.path.join( cache_dir, llvm_package )
    print( 'Loading cached archive: {0}'.format( archive ) )
    try:
      with open( archive, 'rb' ) as f:
        package_dir = ExtractClangLZMA( f.read(), temp_dir )
    except IOError:
      pass

  if not package_dir:
    compressed_data = DownloadClang( download_url )
    package_dir = ExtractClangLZMA( compressed_data, temp_dir )

  return package_dir


def PrepareBundleNSIS( cache_dir, llvm_package, download_url, temp_dir ):
  if cache_dir:
    archive = os.path.join( cache_dir, llvm_package )
    print( 'Loading cached archive: {0}'.format( archive ) )
  else:
    compressed_data = DownloadClang( download_url )
    archive = os.path.join( temp_dir, llvm_package )
    with open( archive, 'wb' ) as f:
      f.write( compressed_data )

  return ExtractClang7Z( llvm_package, archive, temp_dir )


def BundleAndUpload( args, output_dir, os_name, download_data, hashes ):
  llvm_package = download_data[ 'llvm_package' ].format(
    os_name = os_name,
    llvm_version = args.version )
  ycmd_package = download_data[ 'ycmd_package' ].format(
    os_name = os_name,
    llvm_version = args.version )
  download_url = (
    'http://releases.llvm.org/{llvm_version}/{llvm_package}'.format(
      llvm_version = args.version,
      llvm_package = llvm_package ) )

  ycmd_package_file = os.path.join( output_dir, ycmd_package )
  with TemporaryDirectory() as temp_dir:
    license_file_name = DownloadClangLicense( args.version, temp_dir )

    if download_data[ 'format' ] == 'lzma':
      package_dir = PrepareBundleLZMA( args.from_cache,
                                       llvm_package,
                                       download_url,
                                       temp_dir )
    elif download_data[ 'format' ] == 'nsis':
      package_dir = PrepareBundleNSIS( args.from_cache,
                                       llvm_package,
                                       download_url,
                                       temp_dir )
    else:
      raise AssertionError( 'Format not yet implemented: {0}'.format(
        download_data[ 'format' ] ) )

    MakeBundle( download_data[ 'files_to_copy' ],
                license_file_name,
                package_dir,
                ycmd_package_file,
                hashes )

    if not args.no_upload:
      UploadBundleToBintray( args.bt_user,
                             args.bt_token,
                             os_name,
                             args.version,
                             ycmd_package_file )


def Main():
  args = ParseArguments()

  output_dir = args.output_dir if args.output_dir else tempfile.mkdtemp()

  try:
    hashes = dict()
    for os_name, download_data in iteritems( LLVM_DOWNLOAD_DATA ):
      BundleAndUpload( args, output_dir, os_name, download_data, hashes )
  finally:
    if not args.output_dir:
      shutil.rmtree( output_dir )

  for bundle_file_name, sha256 in iteritems( hashes ):
    print( "Checksum for {bundle_file_name}: {sha256}".format(
      bundle_file_name = bundle_file_name,
      sha256 = sha256 ) )


if __name__ == "__main__":
  Main()
