#!/usr/bin/env python3

import argparse
import platform
import os
import glob
import subprocess
import os.path as p
import shlex
import sys
import urllib.request

BASE_UNITTEST_ARGS = [ '-cb' ]
DIR_OF_THIS_SCRIPT = p.dirname( p.abspath( __file__ ) )
DIR_OF_THIRD_PARTY = p.join( DIR_OF_THIS_SCRIPT, 'third_party' )
DIR_OF_WATCHDOG_DEPS = p.join( DIR_OF_THIRD_PARTY, 'watchdog_deps' )
LIBCLANG_DIR = p.join( DIR_OF_THIRD_PARTY, 'clang', 'lib' )

python_path = [
  p.join( DIR_OF_THIRD_PARTY, 'regex-build' ),
  p.join( DIR_OF_THIRD_PARTY, 'jedi_deps', 'jedi' ),
  p.join( DIR_OF_THIRD_PARTY, 'jedi_deps', 'parso' ),
  p.join( DIR_OF_WATCHDOG_DEPS, 'watchdog', 'build', 'lib3' ),
]
if os.environ.get( 'PYTHONPATH' ) is not None:
  python_path.append( os.environ[ 'PYTHONPATH' ] )
os.environ[ 'PYTHONPATH' ] = (
    os.pathsep.join( python_path ) +
    os.pathsep +
    p.join( DIR_OF_THIRD_PARTY, 'jedi_deps', 'numpydoc' ) )

LOMBOK_VERSION = '1.18.26'


def DownloadFileTo( download_url, file_path ):
  with urllib.request.urlopen( download_url ) as response:
    with open( file_path, 'wb' ) as package_file:
      package_file.write( response.read() )


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
#  - no aliases.
SIMPLE_COMPLETERS = [
  'clangd',
  'rust',
  'go',
]

# More complex or legacy cases can specify all of:
#  - build: flags to add to build.py to include this completer
#  - aliases?: list of completer aliases for the --completers option
COMPLETERS = {
  'cfamily': {
    'build': [ '--clang-completer' ],
    'aliases': [ 'c', 'cpp', 'c++', 'objc', 'clang', ]
  },
  'cs': {
    'build': [ '--cs-completer' ],
    'aliases': [ 'omnisharp', 'csharp', 'c#' ]
  },
  'javascript': {
    'build': [ '--js-completer' ],
    'aliases': [ 'js', 'tern' ]
  },
  'typescript': {
    'build': [ '--ts-completer' ],
    'aliases': [ 'ts' ]
  },
  'python': {
    'build': [],
    'aliases': [ 'jedi', 'jedihttp', ]
  },
  'java': {
    'build': [ '--java-completer' ],
    'aliases': [ 'jdt' ],
  },
}

# Add in the simple completers
for completer in SIMPLE_COMPLETERS:
  COMPLETERS[ completer ] = {
    'build': [ '--{}-completer'.format( completer ) ],
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
                       'completion engine(s).',
                       choices = COMPLETERS.keys() )
  group.add_argument( '--completers', nargs ='*', type = CompleterType,
                       help = 'Only build and test with listed semantic '
                       'completion engine(s).',
                       choices = COMPLETERS.keys() )
  parser.add_argument( '--skip-build', action = 'store_true',
                       help = 'Do not build ycmd before testing.' )
  parser.add_argument( '--msvc', type = int, choices = [ 15, 16, 17 ],
                       default = 16, help = 'Choose the Microsoft Visual '
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
  parser.add_argument( '--quiet', action = 'store_true',
                       help = 'Quiet installation mode. Just print overall '
                              'progress and errors' )
  parser.add_argument( '--valgrind',
                       action = 'store_true',
                       help = 'Run tests inside valgrind.' )

  parsed_args, unittest_args = parser.parse_known_args()

  parsed_args.completers = FixupCompleters( parsed_args )

  if 'COVERAGE' in os.environ:
    parsed_args.coverage = ( os.environ[ 'COVERAGE' ] == 'true' )

  return parsed_args, unittest_args


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
      '--core-tests'
    ]

    for key in COMPLETERS:
      if key in args.completers:
        build_cmd.extend( COMPLETERS[ key ][ 'build' ] )

    if args.msvc and platform.system() == 'Windows':
      build_cmd.extend( [ '--msvc', str( args.msvc ) ] )

    if args.coverage:
      # In order to generate coverage data for C++, we use gcov. This requires
      # some files generated when building (*.gcno), so we store the build
      # output in a known directory, which is then used by the CI infrastructure
      # to generate the c++ coverage information.
      build_cmd.extend( [ '--enable-coverage', '--build-dir', '.build' ] )

    if args.quiet:
      build_cmd.append( '--quiet' )

    subprocess.check_call( build_cmd )


def UnittestValgrind( parsed_args, extra_unittest_args ):
  unittest_args = BASE_UNITTEST_ARGS
  if parsed_args.quiet:
    unittest_args.append( '-q' )

  if extra_unittest_args:
    unittest_args.extend( extra_unittest_args )
  else:
    unittest_args += glob.glob(
      p.join( DIR_OF_THIS_SCRIPT, 'ycmd', 'tests', 'bindings', '*_test.py' ) )
    unittest_args += glob.glob(
      p.join( DIR_OF_THIS_SCRIPT, 'ycmd', 'tests', 'clang', '*_test.py' ) )
    unittest_args += glob.glob(
      p.join( DIR_OF_THIS_SCRIPT, 'ycmd', 'tests', '*_test.py' ) )
    # # Avoids needing all completers for a valgrind run
    # unittest_args += [ '-m', 'not valgrind_skip' ]

  new_env = os.environ.copy()
  new_env[ 'PYTHONMALLOC' ] = 'malloc'
  new_env[ 'LD_LIBRARY_PATH' ] = LIBCLANG_DIR
  new_env[ 'YCM_VALGRIND_RUN' ] = '1'
  cmd = [ 'valgrind',
          '--gen-suppressions=all',
          '--error-exitcode=1',
          '--leak-check=full',
          '--show-leak-kinds=definite,indirect',
          '--errors-for-leak-kinds=definite,indirect',
          '--suppressions=' + p.join( DIR_OF_THIS_SCRIPT,
                                      'valgrind.suppressions' ) ]
  subprocess.check_call( cmd +
                         [ sys.executable, '-m', 'unittest' ] +
                         unittest_args,
                         env = new_env )


def UnittestTests( parsed_args, extra_unittest_args ):
  # if any extra arg is a specific file, or the '--' token, then assume the
  # arguments are unittest-aware test selection:
  #  - don't use discover
  #  - don't set the pattern to search for
  prefer_regular = any( arg == '--' or p.isfile( arg )
                        for arg in extra_unittest_args )
  unittest_args = BASE_UNITTEST_ARGS

  if not prefer_regular:
    unittest_args += [ '-p', '*_test.py' ]

  if parsed_args.quiet:
    unittest_args.append( '-q' )

  if extra_unittest_args:
    unittest_args.extend( extra_unittest_args )

  if not ( extra_unittest_args or prefer_regular ):
    unittest_args.append( '-s' )
    unittest_args.append( 'ycmd.tests' )

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

  if parsed_args.coverage:
    executable = [ sys.executable, '-m', 'coverage', 'run' ]
  else:
    executable = [ sys.executable ]

  unittest = [ '-m', 'unittest' ]
  if not prefer_regular:
    unittest.append( 'discover' )

  unittest_cmd = executable + unittest + unittest_args
  cmd_string = ' '.join( shlex.quote( arg ) for arg in unittest_cmd )
  print( f"Running unittest:\n{ cmd_string }",
         file = sys.stderr )
  subprocess.check_call( unittest_cmd, env=env )


# On Windows, distutils.spawn.find_executable only works for .exe files
# but .bat and .cmd files are also executables, so we use our own
# implementation.
def FindExecutable( executable ):
  # Executable extensions used on Windows
  WIN_EXECUTABLE_EXTS = [ '.exe', '.bat', '.cmd' ]

  paths = os.environ[ 'PATH' ].split( os.pathsep )
  base, extension = os.path.splitext( executable )

  if OnWindows() and extension.lower() not in WIN_EXECUTABLE_EXTS:
    extensions = WIN_EXECUTABLE_EXTS
  else:
    extensions = [ '' ]

  for extension in extensions:
    executable_name = executable + extension
    if not os.path.isfile( executable_name ):
      for path in paths:
        executable_path = os.path.join( path, executable_name )
        if os.path.isfile( executable_path ):
          return executable_path
    else:
      return executable_name
  return None


def FindExecutableOrDie( executable, message ):
  path = FindExecutable( executable )

  if not path:
    sys.exit( "ERROR: Unable to find executable '{0}'. {1}".format(
      executable,
      message ) )

  return path


def SetUpGenericLSPCompleter():
  old_cwd = os.getcwd()
  os.chdir( os.path.join( DIR_OF_THIRD_PARTY, 'generic_server' ) )
  npm = FindExecutableOrDie( 'npm', 'npm is required to'
                                    'run GenericLSPCompleter tests.' )
  subprocess.check_call( [ npm, 'install' ] )
  subprocess.check_call( [ npm, 'run', 'compile' ] )
  os.chdir( old_cwd )


def SetUpJavaCompleter():
  LOMBOR_DIR = p.join( DIR_OF_THIRD_PARTY, 'lombok', )
  CACHE = p.join( LOMBOR_DIR, 'cache' )

  jar_name = f'lombok-{ LOMBOK_VERSION }.jar'
  url = (
    f'https://github.com/ycm-core/llvm/releases/download/16.0.1/{ jar_name }'
  )
  file_name = p.join( CACHE, jar_name )

  if not p.exists( CACHE ):
    os.makedirs( CACHE )

  if not p.exists( file_name ):
    print( f"Downloading lombok from { url }..." )
    DownloadFileTo( url, file_name )


def Main():
  parsed_args, unittest_args = ParseArguments()
  if parsed_args.dump_path:
    print( os.environ[ 'PYTHONPATH' ] )
    sys.exit()

  print( 'Running tests on Python', platform.python_version() )
  if not parsed_args.skip_build:
    SetUpGenericLSPCompleter()
    SetUpJavaCompleter()
  if not parsed_args.no_flake8:
    RunFlake8()
  BuildYcmdLibs( parsed_args )
  if parsed_args.valgrind:
    UnittestValgrind( parsed_args, unittest_args )
  else:
    UnittestTests( parsed_args, unittest_args )


if __name__ == "__main__":
  Main()
