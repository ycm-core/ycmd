#!/usr/bin/env python

import os
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

sys.path.insert( 0, p.abspath( p.join( DIR_OF_THIRD_PARTY, 'sh' ) ) )
sys.path.insert( 0, p.abspath( p.join( DIR_OF_THIRD_PARTY, 'argparse' ) ) )

import sh
import platform
import argparse
import multiprocessing
from distutils.spawn import find_executable


def OnMac():
  return platform.system() == 'Darwin'


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


def CustomPythonCmakeArgs():
  # The CMake 'FindPythonLibs' Module does not work properly.
  # So we are forced to do its job for it.

  python_prefix = sh.python_config( '--prefix' ).strip()
  if p.isfile( p.join( python_prefix, '/Python' ) ):
    python_library = p.join( python_prefix, '/Python' )
    python_include = p.join( python_prefix, '/Headers' )
  else:
    which_python = sh.python(
      '-c',
      'import sys;i=sys.version_info;print "python%d.%d" % (i[0], i[1])'
      ).strip()
    lib_python = '{0}/lib/lib{1}'.format( python_prefix, which_python ).strip()

    if p.isfile( '{0}.a'.format( lib_python ) ):
      python_library = '{0}.a'.format( lib_python )
    # This check is for CYGWIN
    elif p.isfile( '{0}.dll.a'.format( lib_python ) ):
      python_library = '{0}.dll.a'.format( lib_python )
    else:
      python_library = '{0}.dylib'.format( lib_python )
    python_include = '{0}/include/{1}'.format( python_prefix, which_python )

  return [
    '-DPYTHON_LIBRARY={0}'.format( python_library ),
    '-DPYTHON_INCLUDE_DIR={0}'.format( python_include )
  ]


def ParseArguments():
  parser = argparse.ArgumentParser()
  parser.add_argument( '--clang-completer', action = 'store_true',
                       help = 'Build C-family semantic completion engine.')
  parser.add_argument( '--system-libclang', action = 'store_true',
                       help = 'Use system libclang instead of downloading one '
                       'from llvm.org. NOT RECOMMENDED OR SUPPORTED!' )
  parser.add_argument( '--omnisharp-completer', action = 'store_true',
                       help = 'Build C# semantic completion engine.' )
  parser.add_argument( '--system-boost', action = 'store_true',
                       help = 'Use the system boost instead of bundled one. '
                       'NOT RECOMMENDED OR SUPPORTED!')
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
  tests_dir = p.join( build_dir, 'ycm/tests' )
  sh.cd( tests_dir )
  new_env = os.environ.copy()
  new_env[ 'LD_LIBRARY_PATH' ] = DIR_OF_THIS_SCRIPT
  sh.Command( p.join( tests_dir, 'ycm_core_tests' ) )(
    _env = new_env, _out = sys.stdout )


def BuildYcmdLibs( cmake_args ):
  build_dir = unicode( sh.mktemp( '-d', '-t', 'ycm_build.XXXXXX' ) ).strip()

  try:
    full_cmake_args = [ '-G', 'Unix Makefiles' ]
    if OnMac():
      full_cmake_args.extend( CustomPythonCmakeArgs() )
    full_cmake_args.extend( cmake_args )
    full_cmake_args.append( p.join( DIR_OF_THIS_SCRIPT, 'cpp' ) )

    sh.cd( build_dir )
    sh.cmake( *full_cmake_args, _out = sys.stdout )

    build_target = ( 'ycm_support_libs' if 'YCM_TESTRUN' not in os.environ else
                     'ycm_core_tests' )
    sh.make( '-j', NumCores(), build_target, _out = sys.stdout,
             _err = sys.stderr )

    if 'YCM_TESTRUN' in os.environ:
      RunYcmdTests( build_dir )
  finally:
    sh.cd( DIR_OF_THIS_SCRIPT )
    sh.rm( '-rf', build_dir )


def BuildOmniSharp():
  build_command = PathToFirstExistingExecutable(
    [ 'msbuild', 'msbuild.exe', 'xbuild' ] )
  if not build_command:
    sys.exit( 'msbuild or xbuild is required to build Omnisharp' )

  sh.cd( p.join( DIR_OF_THIS_SCRIPT, 'third_party/OmniSharpServer' ) )
  sh.Command( build_command )( _out = sys.stdout )


def ApplyWorkarounds():
  # Some OSs define a 'make' ENV VAR and this confuses sh when we try to do
  # sh.make. See https://github.com/Valloric/YouCompleteMe/issues/1401
  os.environ.pop('make', None)


def Main():
  ApplyWorkarounds()
  CheckDeps()
  args = ParseArguments()
  BuildYcmdLibs( GetCmakeArgs( args ) )
  if args.omnisharp_completer:
    BuildOmniSharp()

if __name__ == "__main__":
  Main()
