#!/usr/bin/env python

from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals
from __future__ import absolute_import

import argparse
import os
import platform
import re
import subprocess
import sys
import tarfile
from tempfile import mkdtemp
from shutil import rmtree
from distutils.dir_util import copy_tree
from multiprocessing import cpu_count
from os import path as p

DIR_OF_THIS_SCRIPT = p.abspath( p.dirname( __file__ ) )
DIR_OF_THIRD_PARTY = p.join( DIR_OF_THIS_SCRIPT, 'third_party' )

sys.path[ 0:0 ] = [ p.join( DIR_OF_THIRD_PARTY, 'requests_deps', 'requests' ),
                    p.join( DIR_OF_THIRD_PARTY,
                            'requests_deps',
                            'urllib3',
                            'src' ),
                    p.join( DIR_OF_THIRD_PARTY, 'requests_deps', 'chardet' ),
                    p.join( DIR_OF_THIRD_PARTY, 'requests_deps', 'certifi' ),
                    p.join( DIR_OF_THIRD_PARTY, 'requests_deps', 'idna' ) ]

import requests

CHUNK_SIZE = 1024 * 1024 # 1 MB

BOOST_VERSION_REGEX = re.compile( r'Version (\d+\.\d+\.\d+)' )
BOOST_URL = (
  'http://dl.bintray.com/boostorg/release/{version}/source/{archive}' )
BOOST_NAME = 'boost_{version_}'
BOOST_ARCHIVE = BOOST_NAME + '.tar.bz2'
BOOST_PARTS = [
  'boost/algorithm/string/regex.hpp',
  'boost/filesystem.hpp',
  'boost/regex.hpp'
]
BOOST_LIBS_FOLDERS_TO_REMOVE = [
  'assign',
  'atomic',
  'build',
  'chrono',
  'config',
  'date_time',
  'doc',
  'examples',
  'exception',
  'lockfree',
  'mpi',
  'python',
  'serialization',
  'smart_ptr',
  'system',
  'test',
  'thread',
  'timer',
  # Numpy support was added in Boost 1.63.0. We remove its folder since it
  # breaks the build and we don't need it.
  'numpy'
]
BOOST_LIBS_EXTENSIONS_TO_KEEP = [
  '.hpp',
  '.cpp',
  '.ipp',
  '.inl'
]


def OnWindows():
  return platform.system() == 'Windows'


def Download( url, dest ):
  print( 'Downloading {0}.'.format( p.basename( dest ) ) )
  r = requests.get( url, stream = True )
  with open( dest, 'wb' ) as f:
    for chunk in r.iter_content( chunk_size = CHUNK_SIZE ):
      if chunk:
        f.write( chunk )
  r.close()


def Extract( path, folder = os.curdir ):
  print( 'Extracting {0}.'.format( p.basename( path ) ) )
  with tarfile.open( path ) as f:
    f.extractall( folder )


def GetLatestBoostVersion():
  download_page = requests.get( 'http://www.boost.org/users/download/' )
  version_match = BOOST_VERSION_REGEX.search( download_page.text )
  if not version_match:
    return None
  return version_match.group( 1 )


def GetBoostName( version ):
  return BOOST_NAME.format( version_ = version.replace( '.', '_' ) )


def GetBoostArchiveName( version ):
  return BOOST_ARCHIVE.format( version_ = version.replace( '.', '_' ) )


def GetBoostArchiveUrl( version ):
  return BOOST_URL.format( version = version,
                           archive = GetBoostArchiveName( version ) )


def DownloadBoostLibrary( version, folder ):
  archive_path = p.join( folder, GetBoostArchiveName( version ) )
  Download( GetBoostArchiveUrl( version ), archive_path )


def CleanBoostParts( boost_libs_dir ):
  for root, dirs, files in os.walk( boost_libs_dir ):
    for directory in dirs:
      if directory in BOOST_LIBS_FOLDERS_TO_REMOVE:
        rmtree( p.join( root, directory ) )
    for filename in files:
      extension = p.splitext( filename )[ 1 ]
      if extension not in BOOST_LIBS_EXTENSIONS_TO_KEEP:
        os.remove( p.join( root, filename ) )


def ExtractBoostParts( args ):
  print( 'Updating Boost to version {0}.'.format( args.version ) )
  boost_dir = mkdtemp( prefix = 'boost.' )

  try:
    os.chdir( boost_dir )

    DownloadBoostLibrary( args.version, os.curdir )
    Extract( p.join( os.curdir, GetBoostArchiveName( args.version ) ),
             os.curdir )

    os.chdir( p.join( os.curdir, GetBoostName( args.version ) ) )

    bootstrap = p.join( os.curdir,
                        'bootstrap' + ( '.bat' if OnWindows() else
                                        '.sh' ) )
    subprocess.call( [ bootstrap ] )
    subprocess.call( [ p.join( os.curdir, 'b2' ),
                       '-j' + str( cpu_count() ),
                       p.join( 'tools', 'bcp' ) ] )
    boost_parts_dir = p.join( os.curdir, 'boost_parts' )
    os.mkdir( boost_parts_dir )
    subprocess.call( [ p.join( os.curdir, 'dist', 'bin', 'bcp' ) ]
                     + BOOST_PARTS
                     + [ boost_parts_dir ] )

    CleanBoostParts( p.join( boost_parts_dir, 'libs' ) )

    dest_libs_dir = p.join( DIR_OF_THIS_SCRIPT, 'cpp', 'BoostParts',
                            'libs' )
    dest_boost_dir = p.join( DIR_OF_THIS_SCRIPT, 'cpp', 'BoostParts',
                             'boost' )
    if p.exists( dest_libs_dir ):
      rmtree( dest_libs_dir )
    if p.exists( dest_boost_dir ):
      rmtree( dest_boost_dir )
    copy_tree( p.join( boost_parts_dir, 'libs' ), dest_libs_dir )
    copy_tree( p.join( boost_parts_dir, 'boost' ), dest_boost_dir )
  finally:
    os.chdir( DIR_OF_THIS_SCRIPT )
    rmtree( boost_dir )


def ParseArguments():
  parser = argparse.ArgumentParser(
    description = 'Update Boost parts to the latest Boost version '
                  'or the specified one.' )
  parser.add_argument( '--version',
                       help = 'Set Boost version. '
                              'Default to latest version.' )

  args = parser.parse_args()

  if not args.version:
    latest_version = GetLatestBoostVersion()
    if not latest_version:
      sys.exit( 'No latest version found. Set Boost version with '
                'the --version option.' )
    args.version = latest_version

  return args


def Main():
  args = ParseArguments()
  ExtractBoostParts( args )


if __name__ == '__main__':
  Main()
