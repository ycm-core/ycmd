#!/usr/bin/env python

# Passing an environment variable containing unicode literals to a subprocess
# on Windows and Python2 raises a TypeError. Since there is no unicode
# string in this script, we don't import unicode_literals to avoid the issue.
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import argparse
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
from distutils.spawn import find_executable

try:
  import lzma
except ImportError:
  from backports import lzma

DIR_OF_THIS_SCRIPT = p.dirname( p.abspath( __file__ ) )
DIR_OF_THIRD_PARTY = p.join( DIR_OF_THIS_SCRIPT, 'third_party' )


def GetStandardLibraryIndexInSysPath():
  for index, path in enumerate( sys.path ):
    if p.isfile( p.join( path, 'os.py' ) ):
      return index
  raise RuntimeError( 'Could not find standard library path in Python path.' )


sys.path[ 0:0 ] = [ p.join( DIR_OF_THIRD_PARTY, 'requests_deps', 'requests' ),
                    p.join( DIR_OF_THIRD_PARTY,
                            'requests_deps',
                            'urllib3',
                            'src' ),
                    p.join( DIR_OF_THIRD_PARTY, 'requests_deps', 'chardet' ),
                    p.join( DIR_OF_THIRD_PARTY, 'requests_deps', 'certifi' ),
                    p.join( DIR_OF_THIRD_PARTY, 'requests_deps', 'idna' ) ]
sys.path.insert( GetStandardLibraryIndexInSysPath() + 1,
                 p.abspath( p.join( DIR_OF_THIRD_PARTY, 'python-future',
                                    'src' ) ) )

import requests
# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa
from future.utils import iteritems
from io import BytesIO


def OnWindows():
  return platform.system() == 'Windows'


def OnMac():
  return platform.system() == 'Darwin'


LLVM_DOWNLOAD_DATA = {
  'win32': {
    'url': 'https://releases.llvm.org/{llvm_version}/{llvm_package}',
    'format': 'nsis',
    'llvm_package': 'LLVM-{llvm_version}-{os_name}.exe',
    'ycmd_package': 'libclang-{llvm_version}-{os_name}.tar.bz2',
    'files_to_copy': [
      os.path.join( 'bin', 'libclang.dll' ),
      os.path.join( 'lib', 'libclang.lib' ),
    ]
  },
  'win64': {
    'url': 'https://releases.llvm.org/{llvm_version}/{llvm_package}',
    'format': 'nsis',
    'llvm_package': 'LLVM-{llvm_version}-{os_name}.exe',
    'ycmd_package': 'libclang-{llvm_version}-{os_name}.tar.bz2',
    'files_to_copy': [
      os.path.join( 'bin', 'libclang.dll' ),
      os.path.join( 'lib', 'libclang.lib' ),
    ]
  },
  'x86_64-apple-darwin': {
    'url': 'https://releases.llvm.org/{llvm_version}/{llvm_package}',
    'format': 'lzma',
    'llvm_package': 'clang+llvm-{llvm_version}-{os_name}.tar.xz',
    'ycmd_package': 'libclang-{llvm_version}-{os_name}.tar.bz2',
    'files_to_copy': [
      os.path.join( 'lib', 'libclang.dylib' )
    ]
  },
  'x86_64-unknown-linux-gnu': {
    'url': ( 'https://github.com/micbou/llvm/releases/download/{llvm_version}/'
             '{llvm_package}' ),
    'format': 'lzma',
    'llvm_package': 'clang+llvm-{llvm_version}-{os_name}.tar.xz',
    'ycmd_package': 'libclang-{llvm_version}-{os_name}.tar.bz2',
    'files_to_copy': [
      os.path.join( 'lib', 'libclang.so' ),
      os.path.join( 'lib', 'libclang.so.{llvm_version:.1}' )
    ]
  },
  'i386-unknown-freebsd11': {
    'url': 'https://releases.llvm.org/{llvm_version}/{llvm_package}',
    'format': 'lzma',
    'llvm_package': 'clang+llvm-{llvm_version}-{os_name}.tar.xz',
    'ycmd_package': 'libclang-{llvm_version}-{os_name}.tar.bz2',
    'files_to_copy': [
      os.path.join( 'lib', 'libclang.so' ),
      os.path.join( 'lib', 'libclang.so.{llvm_version:.1}' )
    ]
  },
  'amd64-unknown-freebsd11': {
    'url': 'https://releases.llvm.org/{llvm_version}/{llvm_package}',
    'format': 'lzma',
    'llvm_package': 'clang+llvm-{llvm_version}-{os_name}.tar.xz',
    'ycmd_package': 'libclang-{llvm_version}-{os_name}.tar.bz2',
    'files_to_copy': [
      os.path.join( 'lib', 'libclang.so' ),
      os.path.join( 'lib', 'libclang.so.{llvm_version:.1}' )
    ]
  },
  'aarch64-linux-gnu': {
    'url': 'https://releases.llvm.org/{llvm_version}/{llvm_package}',
    'format': 'lzma',
    'llvm_package': 'clang+llvm-{llvm_version}-{os_name}.tar.xz',
    'ycmd_package': 'libclang-{llvm_version}-{os_name}.tar.bz2',
    'files_to_copy': [
      os.path.join( 'lib', 'libclang.so' ),
      os.path.join( 'lib', 'libclang.so.{llvm_version:.1}' )
    ]
  },
  'armv7a-linux-gnueabihf': {
    'url': 'https://releases.llvm.org/{llvm_version}/{llvm_package}',
    'format': 'lzma',
    'llvm_package': 'clang+llvm-{llvm_version}-{os_name}.tar.xz',
    'ycmd_package': 'libclang-{llvm_version}-{os_name}.tar.bz2',
    'files_to_copy': [
      os.path.join( 'lib', 'libclang.so' ),
      os.path.join( 'lib', 'libclang.so.{llvm_version:.1}' )
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


def Download( url ):
  print( 'Downloading {}'.format( url.rsplit( '/', 1 )[ -1 ] ) )
  request = requests.get( url, stream=True )
  request.raise_for_status()
  content = request.content
  request.close()
  return content


def ExtractLZMA( compressed_data, destination ):
  uncompressed_data = BytesIO( lzma.decompress( compressed_data ) )

  with tarfile.TarFile( fileobj=uncompressed_data, mode='r' ) as tar_file:
    a_member = tar_file.getmembers()[ 0 ]
    tar_file.extractall( destination )

  # Determine the directory name
  return os.path.join( destination, a_member.name.split( '/' )[ 0 ] )


def Extract7Z( llvm_package, archive, destination ):
  # Extract with appropriate tool
  if OnWindows():
    # The winreg module is named _winreg on Python 2.
    try:
      import winreg
    except ImportError:
      import _winreg as winreg

    with winreg.OpenKey( winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\7-Zip' ) as key:
      executable = os.path.join( winreg.QueryValueEx( key, "Path" )[ 0 ],
                                '7z.exe' )
  elif OnMac():
    executable = '/Applications/Keka.app/Contents/Resources/keka7z'
  else:
    # On Linux, p7zip 16.02 is required.
    executable = find_executable( '7z' )

  command = [
    executable,
    '-y',
    'x',
    archive,
    '-o' + destination
  ]

  # Silence 7-Zip output.
  subprocess.check_call( command, stdout = subprocess.PIPE )

  return destination


def MakeBundle( files_to_copy,
                license_file_name,
                source_dir,
                bundle_file_name,
                hashes,
                version ):
  archive_name = os.path.basename( bundle_file_name )
  print( 'Bundling files to {}'.format( archive_name ) )
  with tarfile.open( name=bundle_file_name, mode='w:bz2' ) as tar_file:
    tar_file.add( license_file_name, arcname='LICENSE.TXT' )
    for file_name in files_to_copy:
      arcname = file_name.format( llvm_version = version )
      name = os.path.join( source_dir, arcname )
      if not os.path.exists( name ):
        raise RuntimeError( 'File {} does not exist.'.format( name ) )
      tar_file.add( name = name, arcname = arcname )

  sys.stdout.write( 'Calculating checksum: ' )
  with open( bundle_file_name, 'rb' ) as f:
    hashes[ archive_name ] = hashlib.sha256( f.read() ).hexdigest()
    print( hashes[ archive_name ] )


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
    print( 'Extracting cached {}'.format( llvm_package ) )
    try:
      with open( archive, 'rb' ) as f:
        package_dir = ExtractLZMA( f.read(), temp_dir )
    except IOError:
      pass

  if not package_dir:
    compressed_data = Download( download_url )
    print( 'Extracting {}'.format( llvm_package ) )
    package_dir = ExtractLZMA( compressed_data, temp_dir )

  return package_dir


def PrepareBundleNSIS( cache_dir, llvm_package, download_url, temp_dir ):
  if cache_dir:
    archive = os.path.join( cache_dir, llvm_package )
    print( 'Extracting cached {}'.format( llvm_package ) )
  else:
    compressed_data = Download( download_url )
    archive = os.path.join( temp_dir, llvm_package )
    with open( archive, 'wb' ) as f:
      f.write( compressed_data )
    print( 'Extracting {}'.format( llvm_package ) )

  return Extract7Z( llvm_package, archive, temp_dir )


def BundleAndUpload( args, temp_dir, output_dir, os_name, download_data,
                     license_file_name, hashes ):
  llvm_package = download_data[ 'llvm_package' ].format(
    os_name = os_name,
    llvm_version = args.version )
  ycmd_package = download_data[ 'ycmd_package' ].format(
    os_name = os_name,
    llvm_version = args.version )
  download_url = download_data[ 'url' ].format( llvm_version = args.version,
                                                llvm_package = llvm_package )

  ycmd_package_file = os.path.join( output_dir, ycmd_package )

  try:
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
      raise AssertionError( 'Format not yet implemented: {}'.format(
        download_data[ 'format' ] ) )
  except requests.exceptions.HTTPError as error:
    if error.response.status_code != 404:
      raise
    print( 'Cannot download {}'.format( llvm_package ) )
    return

  MakeBundle( download_data[ 'files_to_copy' ],
              license_file_name,
              package_dir,
              ycmd_package_file,
              hashes,
              args.version )

  if not args.no_upload:
    UploadBundleToBintray( args.bt_user,
                           args.bt_token,
                           os_name,
                           args.version,
                           ycmd_package_file )


def Overwrite( src, dest ):
  if os.path.exists( dest ):
    shutil.rmtree( dest )
  shutil.copytree( src, dest )


def UpdateClangHeaders( args, temp_dir ):
  src_name = 'cfe-{version}.src'.format( version = args.version )
  archive_name = src_name + '.tar.xz'

  compressed_data = Download( 'https://releases.llvm.org/{version}/'
                              '{archive}'.format( version = args.version,
                                                  archive = archive_name ) )
  print( 'Extracting {}'.format( archive_name ) )
  src = ExtractLZMA( compressed_data, temp_dir )

  print( 'Updating Clang headers...' )
  includes_dir = os.path.join(
    DIR_OF_THIRD_PARTY, 'clang', 'lib', 'clang', args.version, 'include' )
  Overwrite( os.path.join( src, 'lib', 'Headers' ), includes_dir )
  os.remove( os.path.join( includes_dir, 'CMakeLists.txt' ) )

  Overwrite( os.path.join( src, 'include', 'clang-c' ),
             os.path.join( DIR_OF_THIS_SCRIPT, 'cpp', 'llvm', 'include',
                           'clang-c' ) )


def Main():
  args = ParseArguments()

  output_dir = args.output_dir if args.output_dir else tempfile.mkdtemp()

  try:
    hashes = {}
    with TemporaryDirectory() as temp_dir:
      license_file_name = DownloadClangLicense( args.version, temp_dir )
      for os_name, download_data in iteritems( LLVM_DOWNLOAD_DATA ):
        BundleAndUpload( args, temp_dir, output_dir, os_name, download_data,
                         license_file_name, hashes )
      UpdateClangHeaders( args, temp_dir )
  finally:
    if not args.output_dir:
      shutil.rmtree( output_dir )

  for bundle_file_name, sha256 in iteritems( hashes ):
    print( 'Checksum for {bundle_file_name}: {sha256}'.format(
      bundle_file_name = bundle_file_name,
      sha256 = sha256 ) )


if __name__ == "__main__":
  Main()
