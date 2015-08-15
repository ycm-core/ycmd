#!/usr/bin/env python

import os
import subprocess
import os.path as p
import sys

major, minor = sys.version_info[ 0 : 2 ]
if major != 2 or minor < 6:
  sys.exit( 'The build script requires Python version >= 2.6 and < 3.0; '
            'your version of Python is ' + sys.version )

DIR_OF_THIS_SCRIPT = p.dirname( p.abspath( __file__ ) )
DIR_OF_THIRD_PARTY = p.join( DIR_OF_THIS_SCRIPT, 'third_party' )

for folder in os.listdir( DIR_OF_THIRD_PARTY ):
  abs_folder_path = p.join( DIR_OF_THIRD_PARTY, folder )
  if p.isdir( abs_folder_path ) and not os.listdir( abs_folder_path ):
    sys.exit( 'Some folders in ' + DIR_OF_THIRD_PARTY + ' are empty; '
              'you probably forgot to run:'
              '\n\tgit submodule update --init --recursive\n\n' )

sys.path.insert( 1, p.abspath( p.join( DIR_OF_THIRD_PARTY, 'argparse' ) ) )

from tempfile import mkdtemp
from shutil import rmtree
import platform
import argparse
import multiprocessing
from distutils.spawn import find_executable


def OnMac():
  return platform.system() == 'Darwin'


def OnWindows():
  return platform.system() == 'Windows'


def PathToFirstExistingExecutable( executable_name_list ):
  for executable_name in executable_name_list:
    path = find_executable( executable_name )
    if path:
      return path
  return None


def NumCores():
  ycm_cores = os.environ.get( 'YCM_CORES' )
  if ycm_cores:
    return int( ycm_cores )
  try:
    return multiprocessing.cpu_count()
  except NotImplementedError:
    return 1


def CheckDeps():
  if not PathToFirstExistingExecutable( [ 'cmake' ] ):
    sys.exit( 'Please install CMake and retry.')


# Shamelessly stolen from https://gist.github.com/edufelipe/1027906
def _CheckOutput( *popen_args, **kwargs ):
  """Run command with arguments and return its output as a byte string.
  Backported from Python 2.7."""

  process = subprocess.Popen( stdout=subprocess.PIPE, *popen_args, **kwargs )
  output, unused_err = process.communicate()
  retcode = process.poll()
  if retcode:
    command = kwargs.get( 'args' )
    if command is None:
      command = popen_args[ 0 ]
    error = subprocess.CalledProcessError( retcode, command )
    error.output = output
    raise error
  return output


def CustomPythonCmakeArgs():
  # The CMake 'FindPythonLibs' Module does not work properly.
  # So we are forced to do its job for it.

  print( 'Searching for python libraries...' )

  python_prefix = _CheckOutput( [
      'python-config',
      '--prefix'
  ] ).strip()

  if p.isfile( p.join( python_prefix, '/Python' ) ):
    python_library = p.join( python_prefix, '/Python' )
    python_include = p.join( python_prefix, '/Headers' )
    print( 'Using OSX-style libs from {0}'.format( python_prefix ) )
  else:
    which_python = _CheckOutput( [
      'python',
      '-c',
      'import sys;i=sys.version_info;print( "python%d.%d" % (i[0], i[1]) )'
    ] ).strip()
    lib_python = '{0}/lib/lib{1}'.format( python_prefix, which_python ).strip()

    print( 'Searching for python with prefix: {0} and lib {1}:'.format(
      python_prefix, which_python ) )

    if p.isfile( '{0}.a'.format( lib_python ) ):
      python_library = '{0}.a'.format( lib_python )
    # This check is for CYGWIN
    elif p.isfile( '{0}.dll.a'.format( lib_python ) ):
      python_library = '{0}.dll.a'.format( lib_python )
    elif p.isfile( '{0}.dylib'.format( lib_python ) ):
      python_library = '{0}.dylib'.format( lib_python )
    elif p.isfile( '/usr/lib/lib{0}.dylib'.format( which_python ) ):
      # For no clear reason, python2.6 only exists in /usr/lib on OS X and
      # not in the python prefix location
      python_library = '/usr/lib/lib{0}.dylib'.format( which_python )
    else:
      sys.exit( 'ERROR: Unable to find an appropriate python library' )

    python_include = '{0}/include/{1}'.format( python_prefix, which_python )

  print( 'Using PYTHON_LIBRARY={0} PYTHON_INCLUDE_DIR={1}'.format(
      python_library, python_include ) )
  return [
    '-DPYTHON_LIBRARY={0}'.format( python_library ),
    '-DPYTHON_INCLUDE_DIR={0}'.format( python_include )
  ]


def GetGenerator( args ):
  if OnWindows():
    if args.msvc == 14:
      generator = 'Visual Studio 14 2015'
    elif args.msvc == 12:
      generator = 'Visual Studio 12 2013'
    else:
      generator = 'Visual Studio 11 2012'

    if ( not args.arch and platform.architecture()[ 0 ] == '64bit'
         or args.arch == 64 ):
      generator = generator + ' Win64'

    return generator

  return 'Unix Makefiles'


def ParseArguments():
  parser = argparse.ArgumentParser()
  parser.add_argument( '--clang-completer', action = 'store_true',
                       help = 'Build C-family semantic completion engine.' )
  parser.add_argument( '--system-libclang', action = 'store_true',
                       help = 'Use system libclang instead of downloading one '
                       'from llvm.org. NOT RECOMMENDED OR SUPPORTED!' )
  parser.add_argument( '--omnisharp-completer', action = 'store_true',
                       help = 'Build C# semantic completion engine.' )
  parser.add_argument( '--gocode-completer', action = 'store_true',
                       help = 'Build Go semantic completion engine.' )
  parser.add_argument( '--system-boost', action = 'store_true',
                       help = 'Use the system boost instead of bundled one. '
                       'NOT RECOMMENDED OR SUPPORTED!')
  parser.add_argument( '--msvc', type = int, choices = [ 11, 12, 14 ],
                       default = 14, help = 'Choose the Microsoft Visual '
                       'Studio version (default: %(default)s).' )
  parser.add_argument( '--arch', type = int, choices = [ 32, 64 ],
                       help = 'Force architecture to 32 or 64 bits on '
                       'Windows (default: python interpreter architecture).' )
  args = parser.parse_args()

  if args.system_libclang and not args.clang_completer:
    sys.exit( "You can't pass --system-libclang without also passing "
              "--clang-completer as well." )
  return args


def GetCmakeArgs( parsed_args ):
  cmake_args = []
  if parsed_args.clang_completer:
    cmake_args.append( '-DUSE_CLANG_COMPLETER=ON' )

  if parsed_args.system_libclang:
    cmake_args.append( '-DUSE_SYSTEM_LIBCLANG=ON' )

  if parsed_args.system_boost:
    cmake_args.append( '-DUSE_SYSTEM_BOOST=ON' )

  extra_cmake_args = os.environ.get( 'EXTRA_CMAKE_ARGS', '' )
  cmake_args.extend( extra_cmake_args.split() )
  return cmake_args


def RunYcmdTests( build_dir ):
  tests_dir = p.join( build_dir, 'ycm', 'tests' )
  os.chdir( tests_dir )
  new_env = os.environ.copy()

  if OnWindows():
    new_env[ 'PATH' ] = DIR_OF_THIS_SCRIPT
  else:
    new_env[ 'LD_LIBRARY_PATH' ] = DIR_OF_THIS_SCRIPT

  subprocess.check_call( p.join( tests_dir, 'ycm_core_tests' ), env = new_env )


def BuildYcmdLibs( args ):
  build_dir = mkdtemp( prefix = 'ycm_build.' )

  try:
    full_cmake_args = [ '-G', GetGenerator( args ) ]
    if OnMac():
      full_cmake_args.extend( CustomPythonCmakeArgs() )
    full_cmake_args.extend( GetCmakeArgs( args ) )
    full_cmake_args.append( p.join( DIR_OF_THIS_SCRIPT, 'cpp' ) )

    os.chdir( build_dir )
    subprocess.check_call( [ 'cmake' ] + full_cmake_args )

    build_target = ( 'ycm_support_libs' if 'YCM_TESTRUN' not in os.environ else
                     'ycm_core_tests' )

    build_command = [ 'cmake', '--build', '.', '--target', build_target ]
    if OnWindows():
      build_command.extend( [ '--config', 'Release' ] )
    else:
      build_command.extend( [ '--', '-j', str( NumCores() ) ] )

    subprocess.check_call( build_command )

    if 'YCM_TESTRUN' in os.environ:
      RunYcmdTests( build_dir )
  finally:
    os.chdir( DIR_OF_THIS_SCRIPT )
    rmtree( build_dir )


def BuildOmniSharp():
  build_command = PathToFirstExistingExecutable(
    [ 'msbuild', 'msbuild.exe', 'xbuild' ] )
  if not build_command:
    sys.exit( 'msbuild or xbuild is required to build Omnisharp' )

  os.chdir( p.join( DIR_OF_THIS_SCRIPT, 'third_party', 'OmniSharpServer' ) )
  subprocess.check_call( [ build_command, '/property:Configuration=Release' ] )


def BuildGoCode():
  if not find_executable( 'go' ):
    sys.exit( 'go is required to build gocode' )

  os.chdir( p.join( DIR_OF_THIS_SCRIPT, 'third_party', 'gocode' ) )
  subprocess.check_call( [ 'go', 'build' ] )


def Main():
  CheckDeps()
  args = ParseArguments()
  BuildYcmdLibs( args )
  if args.omnisharp_completer:
    BuildOmniSharp()
  if args.gocode_completer:
    BuildGoCode()

if __name__ == '__main__':
  Main()
