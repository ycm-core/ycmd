#!/usr/bin/env python

from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals
from __future__ import absolute_import

import os
import platform
import re
import subprocess
import sys
import tarfile
from tempfile import mkdtemp
from shutil import rmtree
from distutils.dir_util import copy_tree

DIR_OF_THIS_SCRIPT = os.path.dirname( os.path.abspath( __file__ ) )
DIR_OF_THIRD_PARTY = os.path.join( DIR_OF_THIS_SCRIPT, 'third_party' )

sys.path.insert(
  1, os.path.abspath( os.path.join( DIR_OF_THIRD_PARTY, 'argparse' ) ) )
sys.path.insert(
  1, os.path.abspath( os.path.join( DIR_OF_THIRD_PARTY, 'requests' ) ) )

import argparse
import requests

CHUNK_SIZE = 1024 * 1024 # 1 MB

BOOST_VERSION_REGEX = re.compile( 'Version (\d+\.\d+\.\d+)' )
BOOST_URL = ( 'https://sourceforge.net/projects/boost/files/boost/'
              '{version}/{archive}/download' )
BOOST_NAME = 'boost_{version_}'
BOOST_ARCHIVE = BOOST_NAME + '.tar.bz2'
BOOST_PARTS = [
  'boost/utility.hpp',
  'boost/python.hpp',
  'boost/bind.hpp',
  'boost/lambda/lambda.hpp',
  'boost/exception/all.hpp',
  'boost/tuple/tuple_io.hpp',
  'boost/tuple/tuple_comparison.hpp',
  'boost/regex.hpp',
  'boost/foreach.hpp',
  'boost/smart_ptr.hpp',
  'boost/algorithm/string_regex.hpp',
  'boost/thread.hpp',
  'boost/unordered_map.hpp',
  'boost/unordered_set.hpp',
  'boost/format.hpp',
  'boost/ptr_container/ptr_container.hpp',
  'boost/filesystem.hpp',
  'boost/filesystem/fstream.hpp',
  'boost/utility.hpp',
  'boost/algorithm/cxx11/any_of.hpp',
  'atomic',
  'lockfree',
  'assign',
  'system'
]
BOOST_LIBS_FOLDERS_TO_REMOVE = [
  'assign',
  'mpi',
  'config',
  'lockfree',
  'doc',
  'test',
  'examples',
  'build',
  # Numpy support was added in Boost 1.63.0. We remove its folder since it
  # breaks the build and we don't need it.
  'numpy'
]
BOOST_LIBS_FILES_TO_REMOVE = [
  # Extracted with Boost 1.61.0 and breaks the build on Windows.
  'xml_woarchive.cpp'
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
  print( 'Downloading {0}.'.format( os.path.basename( dest ) ) )
  r = requests.get( url, stream = True )
  with open( dest, 'wb') as f:
    for chunk in r.iter_content( chunk_size = CHUNK_SIZE ):
      if chunk:
        f.write( chunk )
  r.close()


def Extract( path, folder = os.curdir ):
  print( 'Extracting {0}.'.format( os.path.basename( path ) ) )
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
  archive_path = os.path.join( folder, GetBoostArchiveName( version ) )
  Download( GetBoostArchiveUrl( version ), archive_path )


def CleanBoostParts( boost_libs_dir ):
  for root, dirs, files in os.walk( boost_libs_dir ):
    for directory in dirs:
      if directory in BOOST_LIBS_FOLDERS_TO_REMOVE:
        rmtree( os.path.join( root, directory ) )
    for filename in files:
      extension = os.path.splitext( filename )[ 1 ]
      if ( filename in BOOST_LIBS_FILES_TO_REMOVE or
           extension not in BOOST_LIBS_EXTENSIONS_TO_KEEP ):
        os.remove( os.path.join( root, filename ) )


def ExtractBoostParts( args ):
  print( 'Updating Boost to version {0}.'.format( args.version ) )
  boost_dir = mkdtemp( prefix = 'boost.' )

  try:
    os.chdir( boost_dir )

    DownloadBoostLibrary( args.version, os.curdir )
    Extract( os.path.join( os.curdir, GetBoostArchiveName( args.version ) ),
             os.curdir )

    os.chdir( os.path.join( os.curdir, GetBoostName( args.version ) ) )

    bootstrap = os.path.join( os.curdir,
                              'bootstrap' + ( '.bat' if OnWindows() else
                                              '.sh' ) )
    subprocess.call( [ bootstrap ] )
    subprocess.call( [ os.path.join( os.curdir, 'b2' ),
                       os.path.join( 'tools', 'bcp' ) ] )
    boost_parts_dir = os.path.join( os.curdir, 'boost_parts' )
    os.mkdir( boost_parts_dir )
    subprocess.call( [ os.path.join( os.curdir, 'dist', 'bin', 'bcp' ) ]
                     + BOOST_PARTS
                     + [ boost_parts_dir ] )

    CleanBoostParts( os.path.join( boost_parts_dir, 'libs' ) )

    dest_libs_dir = os.path.join( DIR_OF_THIS_SCRIPT, 'cpp', 'BoostParts',
                                  'libs' )
    dest_boost_dir = os.path.join( DIR_OF_THIS_SCRIPT, 'cpp', 'BoostParts',
                                   'boost' )
    if os.path.exists( dest_libs_dir ):
      rmtree( dest_libs_dir )
    if os.path.exists( dest_boost_dir ):
      rmtree( dest_boost_dir )
    copy_tree( os.path.join( boost_parts_dir, 'libs' ), dest_libs_dir )
    copy_tree( os.path.join( boost_parts_dir, 'boost' ), dest_boost_dir )
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
