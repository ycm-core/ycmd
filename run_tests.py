#!/usr/bin/env python

import os
import subprocess
import os.path as p
import sys

DIR_OF_THIS_SCRIPT = p.dirname( p.abspath( __file__ ) )
DIR_OF_THIRD_PARTY = p.join( DIR_OF_THIS_SCRIPT, 'third_party' )

python_path = []
for folder in os.listdir( DIR_OF_THIRD_PARTY ):
  python_path.append( p.abspath( p.join( DIR_OF_THIRD_PARTY, folder ) ) )
if os.environ.get( 'PYTHONPATH' ) is not None:
  python_path.append( os.environ['PYTHONPATH'] )
os.environ[ 'PYTHONPATH' ] = os.pathsep.join( python_path )

sys.path.insert( 1, p.abspath( p.join( DIR_OF_THIRD_PARTY, 'argparse' ) ) )

import argparse


def RunFlake8():
  print( 'Running flake8' )
  subprocess.check_call( [
    'flake8',
    '--select=F,C9',
    '--max-complexity=10',
    '--exclude=testdata',
    p.join( DIR_OF_THIS_SCRIPT, 'ycmd' )
  ] )


def ParseArguments():
  parser = argparse.ArgumentParser()
  parser.add_argument( '--no-clang-completer', action = 'store_true',
                       help = 'Do not test C-family '
                       'semantic completion engine.' )
  parser.add_argument( '--skip-build', action = 'store_true',
                       help = 'Do not build ycmd before testing.' )
  parser.add_argument( '--msvc', type = int, choices = [ 11, 12, 14 ],
                       help = 'Choose the Microsoft Visual '
                       'Studio version. (default: 14).' )
  parser.add_argument( '--arch', type = int, choices = [ 32, 64 ],
                       help = 'Force architecture to 32 or 64 bits on '
                       'Windows (default: python interpreter architecture).' )
  parsed_args, nosetests_args = parser.parse_known_args()

  if 'USE_CLANG_COMPLETER' in os.environ:
    parsed_args.no_clang_completer = ( os.environ[ 'USE_CLANG_COMPLETER' ]
                                       == 'false' )

  return parsed_args, nosetests_args


def BuildYcmdLibs( args ):
  if not args.skip_build:
    extra_cmake_args = [ '-DUSE_DEV_FLAGS=ON' ]
    if not args.no_clang_completer:
      extra_cmake_args.append( '-DUSE_CLANG_COMPLETER=ON' )

    os.environ[ 'EXTRA_CMAKE_ARGS' ] = ' '.join(extra_cmake_args)
    os.environ[ 'YCM_TESTRUN' ] = '1'

    build_cmd = [
      sys.executable,
      p.join( DIR_OF_THIS_SCRIPT, 'build.py' ),
      '--omnisharp-completer',
      '--gocode-completer'
    ]

    if args.msvc:
      build_cmd.extend( [ '--msvc', str( args.msvc ) ] )

    if args.arch:
      build_cmd.extend( [ '--arch', str( args.arch ) ] )

    subprocess.check_call( build_cmd )


def NoseTests( parsed_args, extra_nosetests_args ):
  nosetests_args = [ '-v' ]
  if parsed_args.no_clang_completer:
    nosetests_args.append( '--exclude=.*Clang.*' )
  if extra_nosetests_args:
    nosetests_args.extend( extra_nosetests_args )
  else:
    nosetests_args.append( p.join( DIR_OF_THIS_SCRIPT, 'ycmd' ) )

  subprocess.check_call( [ 'nosetests' ] + nosetests_args )


def Main():
  parsed_args, nosetests_args = ParseArguments()
  RunFlake8()
  BuildYcmdLibs( parsed_args )
  NoseTests( parsed_args, nosetests_args )

if __name__ == "__main__":
  Main()
