#!/usr/bin/env python

# Passing an environment variable containing unicode literals to a subprocess
# on Windows and Python2 raises a TypeError. Since there is no unicode
# string in this script, we don't import unicode_literals to avoid the issue.
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from shutil import rmtree
from tempfile import mkdtemp
import argparse
import errno
import hashlib
import multiprocessing
import os
import os.path as p
import platform
import re
import shlex
import shutil
import subprocess
import sys
import sysconfig
import tarfile
import tempfile

IS_64BIT = sys.maxsize > 2**32
PY_MAJOR, PY_MINOR, PY_PATCH = sys.version_info[ 0 : 3 ]
if not ( ( PY_MAJOR == 2 and PY_MINOR == 7 and PY_PATCH >= 1 ) or
         ( PY_MAJOR == 3 and PY_MINOR >= 4 ) or
         PY_MAJOR > 3 ):
  sys.exit( 'ycmd requires Python >= 2.7.1 or >= 3.4; '
            'your version of Python is ' + sys.version )

DIR_OF_THIS_SCRIPT = p.dirname( p.abspath( __file__ ) )
DIR_OF_THIRD_PARTY = p.join( DIR_OF_THIS_SCRIPT, 'third_party' )
LIBCLANG_DIR = p.join( DIR_OF_THIRD_PARTY, 'clang', 'lib' )

for folder in os.listdir( DIR_OF_THIRD_PARTY ):
  abs_folder_path = p.join( DIR_OF_THIRD_PARTY, folder )
  if p.isdir( abs_folder_path ) and not os.listdir( abs_folder_path ):
    sys.exit(
      'ERROR: folder {} in {} is empty; you probably forgot to run:\n'
      '\tgit submodule update --init --recursive\n'.format( folder,
                                                            DIR_OF_THIRD_PARTY )
    )

sys.path[ 0:0 ] = [ p.join( DIR_OF_THIRD_PARTY, 'requests_deps', 'requests' ),
                    p.join( DIR_OF_THIRD_PARTY,
                            'requests_deps',
                            'urllib3',
                            'src' ),
                    p.join( DIR_OF_THIRD_PARTY, 'requests_deps', 'chardet' ),
                    p.join( DIR_OF_THIRD_PARTY, 'requests_deps', 'certifi' ),
                    p.join( DIR_OF_THIRD_PARTY, 'requests_deps', 'idna' ) ]

import requests

NO_DYNAMIC_PYTHON_ERROR = (
  'ERROR: found static Python library ({library}) but a dynamic one is '
  'required. You must use a Python compiled with the {flag} flag. '
  'If using pyenv, you need to run the command:\n'
  '  export PYTHON_CONFIGURE_OPTS="{flag}"\n'
  'before installing a Python version.' )
NO_PYTHON_LIBRARY_ERROR = 'ERROR: unable to find an appropriate Python library.'
NO_PYTHON_HEADERS_ERROR = 'ERROR: Python headers are missing in {include_dir}.'

# Regular expressions used to find static and dynamic Python libraries.
# Notes:
#  - Python 3 library name may have an 'm' suffix on Unix platforms, for
#    instance libpython3.4m.so;
#  - the linker name (the soname without the version) does not always
#    exist so we look for the versioned names too;
#  - on Windows, the .lib extension is used instead of the .dll one. See
#    https://en.wikipedia.org/wiki/Dynamic-link_library#Import_libraries
STATIC_PYTHON_LIBRARY_REGEX = '^libpython{major}\\.{minor}m?\\.a$'
DYNAMIC_PYTHON_LIBRARY_REGEX = """
  ^(?:
  # Linux, BSD
  libpython{major}\\.{minor}m?\\.so(\\.\\d+)*|
  # OS X
  libpython{major}\\.{minor}m?\\.dylib|
  # Windows
  python{major}{minor}\\.lib|
  # Cygwin
  libpython{major}\\.{minor}\\.dll\\.a
  )$
"""

JDTLS_MILESTONE = '0.26.0'
JDTLS_BUILD_STAMP = '201810021912'
JDTLS_SHA256 = (
  '37c02deb37335668321643571e7316a231d94d07707325afdb83b16c953f2244'
)

TSSERVER_VERSION = '3.3.3333'

BUILD_ERROR_MESSAGE = (
  'ERROR: the build failed.\n\n'
  'NOTE: it is *highly* unlikely that this is a bug but rather\n'
  'that this is a problem with the configuration of your system\n'
  'or a missing dependency. Please carefully read CONTRIBUTING.md\n'
  'and if you\'re sure that it is a bug, please raise an issue on the\n'
  'issue tracker, including the entire output of this script\n'
  'and the invocation line used to run it.' )

CLANGD_VERSION = '8.0.0'
CLANGD_BINARIES_ERROR_MESSAGE = (
  'No prebuilt Clang {version} binaries for {platform}. '
  'You\'ll have to compile Clangd {version} from source '
  'or use your system Clangd. '
  'See the YCM docs for details on how to use a custom Clangd.' )


def MakeCleanDirectory( directory_path ):
  if p.exists( directory_path ):
    shutil.rmtree( directory_path )
  os.makedirs( directory_path )


def CheckFileIntegrity( file_path, check_sum ):
  with open( file_path, 'rb' ) as existing_file:
    existing_sha256 = hashlib.sha256( existing_file.read() ).hexdigest()
  return existing_sha256 == check_sum


def DownloadFileTo( download_url, file_path ):
  request = requests.get( download_url, stream = True )
  with open( file_path, 'wb' ) as package_file:
    package_file.write( request.content )
  request.close()


def OnMac():
  return platform.system() == 'Darwin'


def OnWindows():
  return platform.system() == 'Windows'


def OnFreeBSD():
  return platform.system() == 'FreeBSD'


def OnAArch64():
  return platform.machine().lower().startswith( 'aarch64' )


def OnArm():
  return platform.machine().lower().startswith( 'arm' )


def OnX86_64():
  return platform.machine().lower().startswith( 'x86_64' )


def OnCiService():
  return 'CI' in os.environ


def FindExecutableOrDie( executable, message ):
  path = FindExecutable( executable )

  if not path:
    sys.exit( "ERROR: Unable to find executable '{0}'. {1}".format(
      executable,
      message ) )

  return path


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


def PathToFirstExistingExecutable( executable_name_list ):
  for executable_name in executable_name_list:
    path = FindExecutable( executable_name )
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


def CheckCall( args, **kwargs ):
  quiet = kwargs.pop( 'quiet', False )
  status_message = kwargs.pop( 'status_message', None )

  if quiet:
    _CheckCallQuiet( args, status_message, **kwargs )
  else:
    _CheckCall( args, **kwargs )


def _CheckCallQuiet( args, status_message, **kwargs ):
  if not status_message:
    status_message = 'Running {}'.format( args[ 0 ] )

  # __future__ not appear to support flush= on print_function
  sys.stdout.write( status_message + '...' )
  sys.stdout.flush()

  with tempfile.NamedTemporaryFile() as temp_file:
    _CheckCall( args, stdout=temp_file, stderr=subprocess.STDOUT, **kwargs )

  print( "OK" )


def _CheckCall( args, **kwargs ):
  exit_message = kwargs.pop( 'exit_message', None )
  stdout = kwargs.get( 'stdout', None )

  try:
    subprocess.check_call( args, **kwargs )
  except subprocess.CalledProcessError as error:
    if stdout is not None:
      stdout.seek( 0 )
      print( stdout.read().decode( 'utf-8' ) )
      print( "FAILED" )

    if exit_message:
      sys.exit( exit_message )
    sys.exit( error.returncode )


def GetGlobalPythonPrefix():
  # In a virtualenv, sys.real_prefix points to the parent Python prefix.
  if hasattr( sys, 'real_prefix' ):
    return sys.real_prefix
  # In a pyvenv (only available on Python 3), sys.base_prefix points to the
  # parent Python prefix. Outside a pyvenv, it is equal to sys.prefix.
  if PY_MAJOR >= 3:
    return sys.base_prefix
  return sys.prefix


def GetPossiblePythonLibraryDirectories():
  prefix = GetGlobalPythonPrefix()

  if OnWindows():
    return [ p.join( prefix, 'libs' ) ]
  # On pyenv and some distributions, there is no Python dynamic library in the
  # directory returned by the LIBPL variable. Such library can be found in the
  # "lib" or "lib64" folder of the base Python installation.
  return [
    sysconfig.get_config_var( 'LIBPL' ),
    p.join( prefix, 'lib64' ),
    p.join( prefix, 'lib' )
  ]


def FindPythonLibraries():
  include_dir = sysconfig.get_config_var( 'INCLUDEPY' )
  if not p.isfile( p.join( include_dir, 'Python.h' ) ):
    sys.exit( NO_PYTHON_HEADERS_ERROR.format( include_dir = include_dir ) )

  library_dirs = GetPossiblePythonLibraryDirectories()

  # Since ycmd is compiled as a dynamic library, we can't link it to a Python
  # static library. If we try, the following error will occur on Mac:
  #
  #   Fatal Python error: PyThreadState_Get: no current thread
  #
  # while the error happens during linking on Linux and looks something like:
  #
  #   relocation R_X86_64_32 against `a local symbol' can not be used when
  #   making a shared object; recompile with -fPIC
  #
  # On Windows, the Python library is always a dynamic one (an import library to
  # be exact). To obtain a dynamic library on other platforms, Python must be
  # compiled with the --enable-shared flag on Linux or the --enable-framework
  # flag on Mac.
  #
  # So we proceed like this:
  #  - look for a dynamic library and return its path;
  #  - if a static library is found instead, raise an error with instructions
  #    on how to build Python as a dynamic library.
  #  - if no libraries are found, raise a generic error.
  dynamic_name = re.compile( DYNAMIC_PYTHON_LIBRARY_REGEX.format(
    major = PY_MAJOR, minor = PY_MINOR ), re.X )
  static_name = re.compile( STATIC_PYTHON_LIBRARY_REGEX.format(
    major = PY_MAJOR, minor = PY_MINOR ), re.X )
  static_libraries = []

  for library_dir in library_dirs:
    if not p.exists( library_dir ):
      continue

    # Files are sorted so that we found the non-versioned Python library before
    # the versioned one.
    for filename in sorted( os.listdir( library_dir ) ):
      if dynamic_name.match( filename ):
        return p.join( library_dir, filename ), include_dir

      if static_name.match( filename ):
        static_libraries.append( p.join( library_dir, filename ) )

  if static_libraries and not OnWindows():
    dynamic_flag = ( '--enable-framework' if OnMac() else
                     '--enable-shared' )
    sys.exit( NO_DYNAMIC_PYTHON_ERROR.format( library = static_libraries[ 0 ],
                                              flag = dynamic_flag ) )

  sys.exit( NO_PYTHON_LIBRARY_ERROR )


def CustomPythonCmakeArgs( args ):
  # The CMake 'FindPythonLibs' Module does not work properly.
  # So we are forced to do its job for it.
  if not args.quiet:
    print( 'Searching Python {major}.{minor} libraries...'.format(
      major = PY_MAJOR, minor = PY_MINOR ) )

  python_library, python_include = FindPythonLibraries()

  if not args.quiet:
    print( 'Found Python library: {0}'.format( python_library ) )
    print( 'Found Python headers folder: {0}'.format( python_include ) )

  return [
    '-DPYTHON_LIBRARY={0}'.format( python_library ),
    '-DPYTHON_INCLUDE_DIR={0}'.format( python_include )
  ]


def GetGenerator( args ):
  if args.ninja:
    return 'Ninja'
  if OnWindows():
    return 'Visual Studio {version}{arch}'.format(
        version = args.msvc, arch = ' Win64' if IS_64BIT else '' )
  return 'Unix Makefiles'


def ParseArguments():
  parser = argparse.ArgumentParser()
  parser.add_argument( '--clang-completer', action = 'store_true',
                       help = 'Enable C-family semantic completion engine '
                              'through libclang.' )
  parser.add_argument( '--clangd-completer', action = 'store_true',
                       help = 'Enable C-family semantic completion engine '
                              'through clangd lsp server.(EXPERIMENTAL)' )
  parser.add_argument( '--cs-completer', action = 'store_true',
                       help = 'Enable C# semantic completion engine.' )
  parser.add_argument( '--go-completer', action = 'store_true',
                       help = 'Enable Go semantic completion engine.' )
  parser.add_argument( '--rust-completer', action = 'store_true',
                       help = 'Enable Rust semantic completion engine.' )
  parser.add_argument( '--java-completer', action = 'store_true',
                       help = 'Enable Java semantic completion engine.' ),
  parser.add_argument( '--ts-completer', action = 'store_true',
                       help = 'Enable JavaScript and TypeScript semantic '
                              'completion engine.' ),
  parser.add_argument( '--system-boost', action = 'store_true',
                       help = 'Use the system boost instead of bundled one. '
                       'NOT RECOMMENDED OR SUPPORTED!' )
  parser.add_argument( '--system-libclang', action = 'store_true',
                       help = 'Use system libclang instead of downloading one '
                       'from llvm.org. NOT RECOMMENDED OR SUPPORTED!' )
  parser.add_argument( '--msvc', type = int, choices = [ 14, 15 ],
                       default = 15, help = 'Choose the Microsoft Visual '
                       'Studio version (default: %(default)s).' )
  parser.add_argument( '--ninja', action = 'store_true',
                       help = 'Use Ninja build system.' )
  parser.add_argument( '--all',
                       action = 'store_true',
                       help   = 'Enable all supported completers',
                       dest   = 'all_completers' )
  parser.add_argument( '--enable-coverage',
                       action = 'store_true',
                       help   = 'For developers: Enable gcov coverage for the '
                                'c++ module' )
  parser.add_argument( '--enable-debug',
                       action = 'store_true',
                       help   = 'For developers: build ycm_core library with '
                                'debug symbols' )
  parser.add_argument( '--build-dir',
                       help   = 'For developers: perform the build in the '
                                'specified directory, and do not delete the '
                                'build output. This is useful for incremental '
                                'builds, and required for coverage data' )
  parser.add_argument( '--quiet',
                       action = 'store_true',
                       help = 'Quiet installation mode. Just print overall '
                              'progress and errors' )
  parser.add_argument( '--skip-build',
                       action = 'store_true',
                       help = "Don't build ycm_core lib, just install deps" )
  parser.add_argument( '--no-regex',
                       action = 'store_true',
                       help = "Don't build the regex module" )
  parser.add_argument( '--clang-tidy',
                       action = 'store_true',
                       help = 'Run clang-tidy static analysis' )
  parser.add_argument( '--core-tests', nargs = '?', const = '*',
                       help = 'Run core tests and optionally filter them.' )

  # These options are deprecated.
  parser.add_argument( '--omnisharp-completer', action = 'store_true',
                       help = argparse.SUPPRESS )
  parser.add_argument( '--gocode-completer', action = 'store_true',
                       help = argparse.SUPPRESS )
  parser.add_argument( '--racer-completer', action = 'store_true',
                       help = argparse.SUPPRESS )
  parser.add_argument( '--tern-completer', action = 'store_true',
                       help = argparse.SUPPRESS )
  parser.add_argument( '--js-completer', action = 'store_true',
                       help = argparse.SUPPRESS )

  args = parser.parse_args()

  # coverage is not supported for c++ on MSVC
  if not OnWindows() and args.enable_coverage:
    # We always want a debug build when running with coverage enabled
    args.enable_debug = True

  if args.core_tests:
    os.environ[ 'YCM_TESTRUN' ] = '1'
  elif os.environ.get( 'YCM_TESTRUN' ):
    args.core_tests = '*'

  if not args.clang_tidy and os.environ.get( 'YCM_CLANG_TIDY' ):
    args.clang_tidy = True

  if ( args.system_libclang and
       not args.clang_completer and
       not args.all_completers ):
    sys.exit( 'ERROR: you can\'t pass --system-libclang without also passing '
              '--clang-completer or --all as well.' )
  return args


def FindCmake():
  return FindExecutableOrDie( 'cmake', 'CMake is required to build ycmd' )


def GetCmakeCommonArgs( args ):
  cmake_args = [ '-G', GetGenerator( args ) ]
  cmake_args.extend( CustomPythonCmakeArgs( args ) )
  return cmake_args


def GetCmakeArgs( parsed_args ):
  cmake_args = []
  if parsed_args.clang_completer or parsed_args.all_completers:
    cmake_args.append( '-DUSE_CLANG_COMPLETER=ON' )

  if parsed_args.clang_tidy:
    cmake_args.append( '-DUSE_CLANG_TIDY=ON' )

  if parsed_args.system_libclang:
    cmake_args.append( '-DUSE_SYSTEM_LIBCLANG=ON' )

  if parsed_args.system_boost:
    cmake_args.append( '-DUSE_SYSTEM_BOOST=ON' )

  if parsed_args.enable_debug:
    cmake_args.append( '-DCMAKE_BUILD_TYPE=Debug' )
    cmake_args.append( '-DUSE_DEV_FLAGS=ON' )

  # coverage is not supported for c++ on MSVC
  if not OnWindows() and parsed_args.enable_coverage:
    cmake_args.append( '-DCMAKE_CXX_FLAGS=-coverage' )

  use_python2 = 'ON' if PY_MAJOR == 2 else 'OFF'
  cmake_args.append( '-DUSE_PYTHON2=' + use_python2 )

  extra_cmake_args = os.environ.get( 'EXTRA_CMAKE_ARGS', '' )
  # We use shlex split to properly parse quoted CMake arguments.
  cmake_args.extend( shlex.split( extra_cmake_args ) )
  return cmake_args


def RunYcmdTests( args, build_dir ):
  tests_dir = p.join( build_dir, 'ycm', 'tests' )
  new_env = os.environ.copy()

  if OnWindows():
    # We prepend the ycm_core and Clang third-party directories to the PATH
    # instead of overwriting it so that the executable is able to find the
    # Python library.
    new_env[ 'PATH' ] = ( DIR_OF_THIS_SCRIPT + ';' +
                          LIBCLANG_DIR + ';' +
                          new_env[ 'PATH' ] )
  else:
    new_env[ 'LD_LIBRARY_PATH' ] = LIBCLANG_DIR

  tests_cmd = [ p.join( tests_dir, 'ycm_core_tests' ) ]
  if args.core_tests != '*':
    tests_cmd.append( '--gtest_filter={}'.format( args.core_tests ) )
  CheckCall( tests_cmd,
             env = new_env,
             quiet = args.quiet,
             status_message = 'Running ycmd tests' )


def RunYcmdBenchmarks( build_dir ):
  benchmarks_dir = p.join( build_dir, 'ycm', 'benchmarks' )
  new_env = os.environ.copy()

  if OnWindows():
    # We prepend the ycm_core and Clang third-party directories to the PATH
    # instead of overwriting it so that the executable is able to find the
    # Python library.
    new_env[ 'PATH' ] = ( DIR_OF_THIS_SCRIPT + ';' +
                          LIBCLANG_DIR + ';' +
                          new_env[ 'PATH' ] )
  else:
    new_env[ 'LD_LIBRARY_PATH' ] = LIBCLANG_DIR

  # Note we don't pass the quiet flag here because the output of the benchmark
  # is the only useful info.
  CheckCall( p.join( benchmarks_dir, 'ycm_core_benchmarks' ), env = new_env )


# On Windows, if the ycmd library is in use while building it, a LNK1104
# fatal error will occur during linking. Exit the script early with an
# error message if this is the case.
def ExitIfYcmdLibInUseOnWindows():
  if not OnWindows():
    return

  ycmd_library = p.join( DIR_OF_THIS_SCRIPT, 'ycm_core.pyd' )

  if not p.exists( ycmd_library ):
    return

  try:
    open( p.join( ycmd_library ), 'a' ).close()
  except IOError as error:
    if error.errno == errno.EACCES:
      sys.exit( 'ERROR: ycmd library is currently in use. '
                'Stop all ycmd instances before compilation.' )


def GetCMakeBuildConfiguration( args ):
  if OnWindows():
    if args.enable_debug:
      return [ '--config', 'Debug' ]
    return [ '--config', 'Release' ]
  return [ '--', '-j', str( NumCores() ) ]


def BuildYcmdLib( cmake, cmake_common_args, script_args ):
  if script_args.build_dir:
    build_dir = os.path.abspath( script_args.build_dir )
    if not os.path.exists( build_dir ):
      os.makedirs( build_dir )
  else:
    build_dir = mkdtemp( prefix = 'ycm_build_' )

  try:
    os.chdir( build_dir )

    configure_command = ( [ cmake ] + cmake_common_args +
                          GetCmakeArgs( script_args ) )
    configure_command.append( p.join( DIR_OF_THIS_SCRIPT, 'cpp' ) )

    CheckCall( configure_command,
               exit_message = BUILD_ERROR_MESSAGE,
               quiet = script_args.quiet,
               status_message = 'Generating ycmd build configuration' )

    build_targets = [ 'ycm_core' ]
    if script_args.core_tests:
      build_targets.append( 'ycm_core_tests' )
    if 'YCM_BENCHMARK' in os.environ:
      build_targets.append( 'ycm_core_benchmarks' )

    build_config = GetCMakeBuildConfiguration( script_args )

    for target in build_targets:
      build_command = ( [ cmake, '--build', '.', '--target', target ] +
                        build_config )
      CheckCall( build_command,
                 exit_message = BUILD_ERROR_MESSAGE,
                 quiet = script_args.quiet,
                 status_message = 'Compiling ycmd target: {0}'.format(
                   target ) )

    if script_args.core_tests:
      RunYcmdTests( script_args, build_dir )
    if 'YCM_BENCHMARK' in os.environ:
      RunYcmdBenchmarks( build_dir )
  finally:
    os.chdir( DIR_OF_THIS_SCRIPT )

    if script_args.build_dir:
      print( 'The build files are in: ' + build_dir )
    else:
      rmtree( build_dir, ignore_errors = OnCiService() )


def BuildRegexModule( cmake, cmake_common_args, script_args ):
  build_dir = mkdtemp( prefix = 'regex_build_' )

  try:
    os.chdir( build_dir )

    configure_command = [ cmake ] + cmake_common_args
    configure_command.append( p.join( DIR_OF_THIS_SCRIPT,
                                      'third_party', 'cregex' ) )

    CheckCall( configure_command,
               exit_message = BUILD_ERROR_MESSAGE,
               quiet = script_args.quiet,
               status_message = 'Generating regex build configuration' )

    build_config = GetCMakeBuildConfiguration( script_args )

    build_command = ( [ cmake, '--build', '.', '--target', '_regex' ] +
                      build_config )
    CheckCall( build_command,
               exit_message = BUILD_ERROR_MESSAGE,
               quiet = script_args.quiet,
               status_message = 'Compiling regex module' )
  finally:
    os.chdir( DIR_OF_THIS_SCRIPT )
    rmtree( build_dir, ignore_errors = OnCiService() )


def EnableCsCompleter( args ):
  build_command = PathToFirstExistingExecutable(
    [ 'msbuild', 'msbuild.exe', 'xbuild' ] )
  if not build_command:
    sys.exit( 'ERROR: msbuild or xbuild is required to build Omnisharp.' )

  os.chdir( p.join( DIR_OF_THIS_SCRIPT, 'third_party', 'OmniSharpServer' ) )
  CheckCall( [ build_command, '/property:Configuration=Release',
                              '/property:Platform=Any CPU',
                              '/property:TargetFrameworkVersion=v4.5' ],
             quiet = args.quiet,
             status_message = 'Building OmniSharp for C# completion' )


def EnableGoCompleter( args ):
  go = FindExecutableOrDie( 'go', 'go is required to build gocode.' )

  go_dir = p.join( DIR_OF_THIS_SCRIPT, 'third_party', 'go' )
  os.chdir( p.join( go_dir, 'src', 'github.com', 'mdempsky', 'gocode' ) )
  new_env = os.environ.copy()
  new_env[ 'GOPATH' ] = go_dir
  CheckCall( [ go, 'build' ],
             env = new_env,
             quiet = args.quiet,
             status_message = 'Building gocode for go completion' )
  os.chdir( p.join( go_dir, 'src', 'github.com', 'rogpeppe', 'godef' ) )
  CheckCall( [ go, 'build' ],
             env = new_env,
             quiet = args.quiet,
             status_message = 'Building godef for go definition' )


def EnableRustCompleter( args ):
  """
  Build racerd. This requires a reasonably new version of rustc/cargo.
  """
  cargo = FindExecutableOrDie( 'cargo',
                               'cargo is required for the Rust completer.' )

  os.chdir( p.join( DIR_OF_THIRD_PARTY, 'racerd' ) )
  command_line = [ cargo, 'build' ]
  # We don't use the --release flag on CI services because it makes building
  # racerd 2.5x slower and we don't care about the speed of the produced racerd.
  if not OnCiService():
    command_line.append( '--release' )
  CheckCall( command_line,
             quiet = args.quiet,
             status_message = 'Building racerd for Rust completion' )


def EnableJavaScriptCompleter( args ):
  npm = FindExecutableOrDie( 'npm', 'npm is required to set up Tern.' )

  # We install Tern into a runtime directory. This allows us to control
  # precisely the version (and/or git commit) that is used by ycmd.  We use a
  # separate runtime directory rather than a submodule checkout directory
  # because we want to allow users to install third party plugins to
  # node_modules of the Tern runtime.  We also want to be able to install our
  # own plugins to improve the user experience for all users.
  #
  # This is not possible if we use a git submodule for Tern and simply run 'npm
  # install' within the submodule source directory, as subsequent 'npm install
  # tern-my-plugin' will (heinously) install another (arbitrary) version of Tern
  # within the Tern source tree (e.g. third_party/tern/node_modules/tern. The
  # reason for this is that the plugin that gets installed has "tern" as a
  # dependency, and npm isn't smart enough to know that you're installing
  # *within* the Tern distribution. Or it isn't intended to work that way.
  #
  # So instead, we have a package.json within our "Tern runtime" directory
  # (third_party/tern_runtime) that defines the packages that we require,
  # including Tern and any plugins which we require as standard.
  os.chdir( p.join( DIR_OF_THIS_SCRIPT, 'third_party', 'tern_runtime' ) )
  CheckCall( [ npm, 'install', '--production' ],
             quiet = args.quiet,
             status_message = 'Setting up Tern for JavaScript completion' )


def EnableJavaCompleter( switches ):
  def Print( *args, **kwargs ):
    if not switches.quiet:
      print( *args, **kwargs )

  if switches.quiet:
    sys.stdout.write( 'Installing jdt.ls for Java support...' )
    sys.stdout.flush()

  TARGET = p.join( DIR_OF_THIRD_PARTY, 'eclipse.jdt.ls', 'target', )
  REPOSITORY = p.join( TARGET, 'repository' )
  CACHE = p.join( TARGET, 'cache' )

  JDTLS_SERVER_URL_FORMAT = ( 'http://download.eclipse.org/jdtls/milestones/'
                              '{jdtls_milestone}/{jdtls_package_name}' )
  JDTLS_PACKAGE_NAME_FORMAT = ( 'jdt-language-server-{jdtls_milestone}-'
                                '{jdtls_build_stamp}.tar.gz' )

  package_name = JDTLS_PACKAGE_NAME_FORMAT.format(
      jdtls_milestone = JDTLS_MILESTONE,
      jdtls_build_stamp = JDTLS_BUILD_STAMP )
  url = JDTLS_SERVER_URL_FORMAT.format(
      jdtls_milestone = JDTLS_MILESTONE,
      jdtls_package_name = package_name )
  file_name = p.join( CACHE, package_name )

  MakeCleanDirectory( REPOSITORY )

  if not p.exists( CACHE ):
    os.makedirs( CACHE )
  elif p.exists( file_name ) and not CheckFileIntegrity( file_name,
                                                         JDTLS_SHA256 ):
    Print( 'Cached tar file does not match checksum. Removing...' )
    os.remove( file_name )


  if p.exists( file_name ):
    Print( 'Using cached jdt.ls: {0}'.format( file_name ) )
  else:
    Print( "Downloading jdt.ls from {0}...".format( url ) )
    DownloadFileTo( url, file_name )

  Print( "Extracting jdt.ls to {0}...".format( REPOSITORY ) )
  with tarfile.open( file_name ) as package_tar:
    package_tar.extractall( REPOSITORY )

  Print( "Done installing jdt.ls" )

  if switches.quiet:
    print( 'OK' )


def EnableTypeScriptCompleter( args ):
  npm = FindExecutableOrDie( 'npm', 'npm is required to install TSServer.' )
  tsserver_folder = p.join( DIR_OF_THIRD_PARTY, 'tsserver' )
  CheckCall( [ npm, 'install', '-g', '--prefix', tsserver_folder,
               'typescript@{version}'.format( version = TSSERVER_VERSION ) ],
             quiet = args.quiet,
             status_message = 'Installing TSServer for JavaScript '
                              'and TypeScript completion' )


def GetClangdTarget():
  if OnWindows():
    return [
      ( 'clangd-{version}-win64',
        'fddbef35131212feda9bf2aa4a779c635abbace09763ab709dca236ea177611d' ),
      ( 'clangd-{version}-win32',
        '1ae8ad2e40ef2bc7798f8201ff5b071adab27a708f869568b9aabf5f9e5f02ad' ) ]
  if OnMac():
    return [
      ( 'clangd-{version}-x86_64-apple-darwin',
        'c0e8017b445db2fbd2d0b42c47ea2f711a8774320894585bc0fa2d2e0c04059f' ) ]
  if OnFreeBSD():
    return [
      ( 'clangd-{version}-amd64-unknown-freebsd11',
        'b31c93c280a7f543536715a4706ba3dda2583cd96cf2c34a6b84648773cabbf5' ),
      ( 'clangd-{version}-i386-unknown-freebsd11',
        'f48c9a5d2997d387a6473115e131d45a9ee764e6f149bed89d4f3ded336a7f00' ) ]
  if OnAArch64():
    return [
      ( 'clangd-{version}-aarch64-linux-gnu',
        '32de29f3dc735a7e2557f936d8d81438be367e1e4771088c44c8824b07963d04' ) ]
  if OnArm():
    return [
      ( 'clangd-{version}-armv7a-linux-gnueabihf',
        '711b80610d477fd4c830a43725b644901c58e9c825f09233b9f9d7382b2c2882' ) ]
  if OnX86_64():
    return [
      ( 'clangd-{version}-x86_64-unknown-linux-gnu',
        '29b2af2775ec3b7e70a64197bf49fd876903732ff038bb5de2486d1194af7817' ) ]
  sys.exit( CLANGD_BINARIES_ERROR_MESSAGE.format( version = CLANGD_VERSION,
                                                  platform = 'this system' ) )


def DownloadClangd( printer ):
  CLANGD_DIR = p.join( DIR_OF_THIRD_PARTY, 'clangd', )
  CLANGD_CACHE_DIR = p.join( CLANGD_DIR, 'cache' )
  CLANGD_OUTPUT_DIR = p.join( CLANGD_DIR, 'output' )

  target = GetClangdTarget()
  target_name, check_sum = target[ not IS_64BIT ]
  target_name = target_name.format( version = CLANGD_VERSION )
  file_name = '{}.tar.bz2'.format( target_name )
  download_url = 'https://dl.bintray.com/micbou/clangd/{}'.format( file_name )

  file_name = p.join( CLANGD_CACHE_DIR, file_name )

  MakeCleanDirectory( CLANGD_OUTPUT_DIR )

  if not p.exists( CLANGD_CACHE_DIR ):
    os.makedirs( CLANGD_CACHE_DIR )
  elif p.exists( file_name ) and not CheckFileIntegrity( file_name, check_sum ):
    printer( 'Cached Clangd archive does not match checksum. Removing...' )
    os.remove( file_name )

  if p.exists( file_name ):
    printer( 'Using cached Clangd: {}'.format( file_name ) )
  else:
    printer( "Downloading Clangd from {}...".format( download_url ) )
    DownloadFileTo( download_url, file_name )
    if not CheckFileIntegrity( file_name, check_sum ):
      sys.exit( 'ERROR: downloaded Clangd archive does not match checksum.' )

  printer( "Extracting Clangd to {}...".format( CLANGD_OUTPUT_DIR ) )
  with tarfile.open( file_name ) as package_tar:
    package_tar.extractall( CLANGD_OUTPUT_DIR )

  printer( "Done installing Clangd" )


def EnableClangdCompleter( Args ):
  if Args.quiet:
    sys.stdout.write( 'Setting up Clangd completer...' )
    sys.stdout.flush()

  def Print( msg ):
    if not Args.quiet:
      print( msg )

  DownloadClangd( Print )

  if Args.quiet:
    print( 'OK' )


def WritePythonUsedDuringBuild():
  path = p.join( DIR_OF_THIS_SCRIPT, 'PYTHON_USED_DURING_BUILDING' )
  with open( path, 'w' ) as f:
    f.write( sys.executable )


def DoCmakeBuilds( args ):
  cmake = FindCmake()
  cmake_common_args = GetCmakeCommonArgs( args )

  if not args.skip_build:
    ExitIfYcmdLibInUseOnWindows()
    BuildYcmdLib( cmake, cmake_common_args, args )
    WritePythonUsedDuringBuild()

  if not args.no_regex:
    BuildRegexModule( cmake, cmake_common_args, args )


def Main():
  args = ParseArguments()

  if not args.skip_build or not args.no_regex:
    DoCmakeBuilds( args )
  if args.cs_completer or args.omnisharp_completer or args.all_completers:
    EnableCsCompleter( args )
  if args.go_completer or args.gocode_completer or args.all_completers:
    EnableGoCompleter( args )
  if args.js_completer or args.tern_completer or args.all_completers:
    EnableJavaScriptCompleter( args )
  if args.rust_completer or args.racer_completer or args.all_completers:
    EnableRustCompleter( args )
  if args.java_completer or args.all_completers:
    EnableJavaCompleter( args )
  if args.ts_completer or args.all_completers:
    EnableTypeScriptCompleter( args )
  if args.clangd_completer:
    EnableClangdCompleter( args )


if __name__ == '__main__':
  Main()
