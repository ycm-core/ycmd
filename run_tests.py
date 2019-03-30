#!/usr/bin/env python

# Passing an environment variable containing unicode literals to a subprocess
# on Windows and Python2 raises a TypeError. Since there is no unicode
# string in this script, we don't import unicode_literals to avoid the issue.
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
# Not installing aliases from python-future; it's unreliable and slow.
from builtins import *  # noqa

import argparse
import platform
import os
import glob
import subprocess
import os.path as p
import sys

DIR_OF_THIS_SCRIPT = p.dirname( p.abspath( __file__ ) )
DIR_OF_THIRD_PARTY = p.join( DIR_OF_THIS_SCRIPT, 'third_party' )
LIBCLANG_DIR = p.join( DIR_OF_THIRD_PARTY, 'clang', 'lib' )

# We skip python-future because it needs to be inserted in sys.path AFTER the
# standard library imports but we can't do that with PYTHONPATH because the std
# lib paths are always appended to PYTHONPATH. We do it correctly in ycmd
# because we have access to the right sys.path. So for dev, we rely on
# python-future being installed correctly with
#   pip install -r test_requirements.txt
#
# Pip knows how to install this correctly so that it doesn't matter where in
# sys.path the path is.
python_path = [
  p.join( DIR_OF_THIRD_PARTY, 'bottle' ),
  p.join( DIR_OF_THIRD_PARTY,
          'cregex',
          'regex_{}'.format( sys.version_info[ 0 ] ) ),
  p.join( DIR_OF_THIRD_PARTY, 'frozendict' ),
  p.join( DIR_OF_THIRD_PARTY, 'jedi_deps', 'jedi' ),
  p.join( DIR_OF_THIRD_PARTY, 'jedi_deps', 'parso' ),
  p.join( DIR_OF_THIRD_PARTY, 'requests_deps', 'certifi' ),
  p.join( DIR_OF_THIRD_PARTY, 'requests_deps', 'chardet' ),
  p.join( DIR_OF_THIRD_PARTY, 'requests_deps', 'idna' ),
  p.join( DIR_OF_THIRD_PARTY, 'requests_deps', 'requests' ),
  p.join( DIR_OF_THIRD_PARTY, 'requests_deps', 'urllib3', 'src' ),
  p.join( DIR_OF_THIRD_PARTY, 'waitress' ),
]
if os.environ.get( 'PYTHONPATH' ) is not None:
  python_path.append( os.environ[ 'PYTHONPATH' ] )
os.environ[ 'PYTHONPATH' ] = os.pathsep.join( python_path )


def OnWindows():
  return platform.system() == 'Windows'


def RunFlake8():
  print( 'Running flake8' )
  args = [ sys.executable,
           '-m',
           'flake8',
           p.join( DIR_OF_THIS_SCRIPT, 'ycmd' ) ]
  root_dir_scripts = glob.glob( p.join( DIR_OF_THIS_SCRIPT, '*.py' ) )
  args.extend( root_dir_scripts )
  subprocess.check_call( args )


# Newer completers follow a standard convention of:
#  - build: --<completer>-completer
#  - test directory: ycmd/tests/<completer>
#  - no aliases.
SIMPLE_COMPLETERS = [
  'clangd',
]

# More complex or legacy cases can specify all of:
#  - build: flags to add to build.py to include this completer
#  - test: flags to add to run_tests.py when _not_ testing this completer
#  - aliases?: list of completer aliases for the --completers option
COMPLETERS = {
  'cfamily': {
    'build': [ '--clang-completer' ],
    'test': [ '--exclude-dir=ycmd/tests/clang' ],
    'aliases': [ 'c', 'cpp', 'c++', 'objc', 'clang', ]
  },
  'cs': {
    'build': [ '--cs-completer' ],
    'test': [ '--exclude-dir=ycmd/tests/cs' ],
    'aliases': [ 'omnisharp', 'csharp', 'c#' ]
  },
  'javascript': {
    'build': [ '--js-completer' ],
    'test': [ '--exclude-dir=ycmd/tests/tern' ],
    'aliases': [ 'js', 'tern' ]
  },
  'go': {
    'build': [ '--go-completer' ],
    'test': [ '--exclude-dir=ycmd/tests/go' ],
    'aliases': [ 'gocode' ]
  },
  'rust': {
    'build': [ '--rust-completer' ],
    'test': [ '--exclude-dir=ycmd/tests/rust' ],
    'aliases': [ 'racer', 'racerd', ]
  },
  'typescript': {
    'build': [ '--ts-completer' ],
    'test': [ '--exclude-dir=ycmd/tests/javascript',
              '--exclude-dir=ycmd/tests/typescript' ],
    'aliases': [ 'ts' ]
  },
  'python': {
    'build': [],
    'test': [ '--exclude-dir=ycmd/tests/python' ],
    'aliases': [ 'jedi', 'jedihttp', ]
  },
  'java': {
    'build': [ '--java-completer' ],
    'test': [ '--exclude-dir=ycmd/tests/java' ],
    'aliases': [ 'jdt' ],
  },
}

# Add in the simple completers
for completer in SIMPLE_COMPLETERS:
  COMPLETERS[ completer ] = {
    'build': [ '--{}-completer'.format( completer ) ],
    'test': [ '--exclude-dir=ycmd/tests/{}'.format( completer ) ],
  }


def CompleterType( value ):
  value = value.lower()
  if value in COMPLETERS:
    return value
  else:
    aliases_to_completer = { i: k for k, v in COMPLETERS.items()
                             for i in v[ 'aliases' ] }
    if value in aliases_to_completer:
      return aliases_to_completer[ value ]
    else:
      raise argparse.ArgumentTypeError(
        '{0} is not a valid completer - should be one of {1}'.format(
          value, COMPLETERS.keys() ) )


def ParseArguments():
  parser = argparse.ArgumentParser()
  group = parser.add_mutually_exclusive_group()
  group.add_argument( '--no-clang-completer', action = 'store_true',
                       help = argparse.SUPPRESS ) # deprecated
  group.add_argument( '--no-completers', nargs ='*', type = CompleterType,
                       help = 'Do not build or test with listed semantic '
                       'completion engine(s). Valid values: {0}'.format(
                        COMPLETERS.keys() ) )
  group.add_argument( '--completers', nargs ='*', type = CompleterType,
                       help = 'Only build and test with listed semantic '
                       'completion engine(s). Valid values: {0}'.format(
                        COMPLETERS.keys() ) )
  parser.add_argument( '--skip-build', action = 'store_true',
                       help = 'Do not build ycmd before testing.' )
  parser.add_argument( '--msvc', type = int, choices = [ 14, 15 ],
                       default = 15, help = 'Choose the Microsoft Visual '
                       'Studio version (default: %(default)s).' )
  parser.add_argument( '--coverage', action = 'store_true',
                       help = 'Enable coverage report (requires coverage pkg)' )
  parser.add_argument( '--no-flake8', action = 'store_true',
                       help = 'Disable flake8 run.' )
  parser.add_argument( '--dump-path', action = 'store_true',
                       help = 'Dump the PYTHONPATH required to run tests '
                              'manually, then exit.' )
  parser.add_argument( '--no-retry', action = 'store_true',
                       help = 'Disable retry of flaky tests' )

  parsed_args, nosetests_args = parser.parse_known_args()

  parsed_args.completers = FixupCompleters( parsed_args )

  if 'COVERAGE' in os.environ:
    parsed_args.coverage = ( os.environ[ 'COVERAGE' ] == 'true' )

  return parsed_args, nosetests_args


def FixupCompleters( parsed_args ):
  completers = set( COMPLETERS.keys() )
  if parsed_args.completers is not None:
    completers = set( parsed_args.completers )
  elif parsed_args.no_completers is not None:
    completers = completers.difference( parsed_args.no_completers )
  elif parsed_args.no_clang_completer:
    print( 'WARNING: The "--no-clang-completer" flag is deprecated. '
           'Please use "--no-completers cfamily" instead.' )
    completers.discard( 'cfamily' )

  if 'USE_CLANG_COMPLETER' in os.environ:
    if os.environ[ 'USE_CLANG_COMPLETER' ] == 'false':
      completers.discard( 'cfamily' )
    else:
      completers.add( 'cfamily' )

  return list( completers )


def BuildYcmdLibs( args ):
  if not args.skip_build:
    if 'EXTRA_CMAKE_ARGS' in os.environ:
      os.environ[ 'EXTRA_CMAKE_ARGS' ] += ' -DUSE_DEV_FLAGS=ON'
    else:
      os.environ[ 'EXTRA_CMAKE_ARGS' ] = '-DUSE_DEV_FLAGS=ON'

    build_cmd = [
      sys.executable,
      p.join( DIR_OF_THIS_SCRIPT, 'build.py' ),
      '--core-tests',
      '--quiet',
    ]

    for key in COMPLETERS:
      if key in args.completers:
        build_cmd.extend( COMPLETERS[ key ][ 'build' ] )

    if args.msvc:
      build_cmd.extend( [ '--msvc', str( args.msvc ) ] )

    if args.coverage:
      # In order to generate coverage data for C++, we use gcov. This requires
      # some files generated when building (*.gcno), so we store the build
      # output in a known directory, which is then used by the CI infrastructure
      # to generate the c++ coverage information.
      build_cmd.extend( [ '--enable-coverage', '--build-dir', '.build' ] )

    subprocess.check_call( build_cmd )


def NoseTests( parsed_args, extra_nosetests_args ):
  # Always passing --with-id to nosetests enables non-surprising usage of
  # its --failed flag.
  # By default, nose does not include files starting with a underscore in its
  # report but we want __main__.py to be included. Only ignore files starting
  # with a dot and setup.py.
  nosetests_args = [ '-v', '--with-id', r'--ignore-files=(^\.|^setup\.py$)' ]

  for key in COMPLETERS:
    if key not in parsed_args.completers:
      nosetests_args.extend( COMPLETERS[ key ][ 'test' ] )

  if parsed_args.coverage:
    # We need to exclude the ycmd/tests/python/testdata directory since it
    # contains Python files and its base name starts with "test".
    nosetests_args += [ '--exclude-dir=ycmd/tests/python/testdata',
                        '--with-coverage',
                        '--cover-erase',
                        '--cover-package=ycmd',
                        '--cover-html',
                        '--cover-inclusive' ]

  if extra_nosetests_args:
    nosetests_args.extend( extra_nosetests_args )
  else:
    nosetests_args.append( p.join( DIR_OF_THIS_SCRIPT, 'ycmd' ) )

  env = os.environ.copy()

  if parsed_args.no_retry:
    # Useful for _writing_ tests
    env[ 'YCM_TEST_NO_RETRY' ] = '1'

  if OnWindows():
    # We prepend the Clang third-party directory to the PATH instead of
    # overwriting it so that the executable is able to find the Python library.
    env[ 'PATH' ] = LIBCLANG_DIR + ';' + env[ 'PATH' ]
  else:
    env[ 'LD_LIBRARY_PATH' ] = LIBCLANG_DIR

  subprocess.check_call( [ sys.executable, '-m', 'nose' ] + nosetests_args,
                         env=env )


def Main():
  parsed_args, nosetests_args = ParseArguments()
  if parsed_args.dump_path:
    print( os.environ[ 'PYTHONPATH' ] )
    sys.exit()
  print( 'Running tests on Python', platform.python_version() )
  if not parsed_args.no_flake8:
    RunFlake8()
  BuildYcmdLibs( parsed_args )
  NoseTests( parsed_args, nosetests_args )


if __name__ == "__main__":
  Main()
