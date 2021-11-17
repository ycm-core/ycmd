#!/usr/bin/env python3

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
from zipfile import ZipFile
import tempfile
import urllib.request


class InstallationFailed( Exception ):
  def __init__( self, message = None, exit_code = 1 ):
    self.message = message
    self.exit_code = exit_code

  def Print( self ):
    if self.message:
      print( '', file = sys.stderr )
      print( self.message, file = sys.stderr )

  def Exit( self ):
    sys.exit( self.exit_code )


IS_MSYS = 'MSYS' == os.environ.get( 'MSYSTEM' )

IS_64BIT = sys.maxsize > 2**32
PY_MAJOR, PY_MINOR = sys.version_info[ 0 : 2 ]
PY_VERSION = sys.version_info[ 0 : 3 ]
if PY_VERSION < ( 3, 6, 0 ):
  sys.exit( 'ycmd requires Python >= 3.6.0; '
            'your version of Python is ' + sys.version +
            '\nHint: Try running python3 ' + ' '.join( sys.argv ) )

DIR_OF_THIS_SCRIPT = p.dirname( p.abspath( __file__ ) )
DIR_OF_THIRD_PARTY = p.join( DIR_OF_THIS_SCRIPT, 'third_party' )
LIBCLANG_DIR = p.join( DIR_OF_THIRD_PARTY, 'clang', 'lib' )

for folder in os.listdir( DIR_OF_THIRD_PARTY ):
  abs_folder_path = p.join( DIR_OF_THIRD_PARTY, folder )
  if p.isdir( abs_folder_path ) and not os.listdir( abs_folder_path ):
    sys.exit(
      f'ERROR: folder { folder } in { DIR_OF_THIRD_PARTY } is empty; '
      'you probably forgot to run:\n'
      '\tgit submodule update --init --recursive\n'
    )


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
#    instance libpython3.6m.so;
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

JDTLS_MILESTONE = '0.68.0'
JDTLS_BUILD_STAMP = '202101202016'
JDTLS_SHA256 = (
  'df9c9b497ce86b1d57756b2292ad0f7bfaa76aed8a4b63a31c589e85018b7993'
)

RUST_TOOLCHAIN = 'nightly-2021-10-26'
RUST_ANALYZER_DIR = p.join( DIR_OF_THIRD_PARTY, 'rust-analyzer' )

BUILD_ERROR_MESSAGE = (
  'ERROR: the build failed.\n\n'
  'NOTE: it is *highly* unlikely that this is a bug but rather '
  'that this is a problem with the configuration of your system '
  'or a missing dependency. Please carefully read CONTRIBUTING.md '
  'and if you\'re sure that it is a bug, please raise an issue on the '
  'issue tracker, including the entire output of this script (with --verbose) '
  'and the invocation line used to run it.' )

CLANGD_VERSION = '13.0.0'
CLANGD_BINARIES_ERROR_MESSAGE = (
  'No prebuilt Clang {version} binaries for {platform}. '
  'You\'ll have to compile Clangd {version} from source '
  'or use your system Clangd. '
  'See the YCM docs for details on how to use a custom Clangd.' )


def RemoveDirectory( directory ):
  try_number = 0
  max_tries = 10
  while try_number < max_tries:
    try:
      shutil.rmtree( directory )
      return
    except OSError:
      try_number += 1
  raise RuntimeError(
    f'Cannot remove directory { directory } after { max_tries } tries.' )



def RemoveDirectoryIfExists( directory_path ):
  if p.exists( directory_path ):
    RemoveDirectory( directory_path )


def MakeCleanDirectory( directory_path ):
  RemoveDirectoryIfExists( directory_path )
  os.makedirs( directory_path )


def CheckFileIntegrity( file_path, check_sum ):
  with open( file_path, 'rb' ) as existing_file:
    existing_sha256 = hashlib.sha256( existing_file.read() ).hexdigest()
  return existing_sha256 == check_sum


def DownloadFileTo( download_url, file_path ):
  with urllib.request.urlopen( download_url ) as response:
    with open( file_path, 'wb' ) as package_file:
      package_file.write( response.read() )


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


def FindExecutableOrDie( executable, message ):
  path = FindExecutable( executable )

  if not path:
    raise InstallationFailed(
      f"ERROR: Unable to find executable '{ executable }'. { message }" )

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
        executable_path = p.join( path, executable_name )
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
  if status_message:
    print( status_message + '...', flush = True, end = '' )

  with tempfile.NamedTemporaryFile() as temp_file:
    _CheckCall( args, stdout=temp_file, stderr=subprocess.STDOUT, **kwargs )

  if status_message:
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
      raise InstallationFailed( exit_message )

    raise InstallationFailed( exit_code = error.returncode )


def GetGlobalPythonPrefix():
  # In a virtualenv, sys.real_prefix points to the parent Python prefix.
  if hasattr( sys, 'real_prefix' ):
    return sys.real_prefix
  # In a pyvenv (only available on Python 3), sys.base_prefix points to the
  # parent Python prefix. Outside a pyvenv, it is equal to sys.prefix.
  return sys.base_prefix


def GetPossiblePythonLibraryDirectories():
  prefix = GetGlobalPythonPrefix()

  if OnWindows() and not IS_MSYS:
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
    raise InstallationFailed(
      NO_PYTHON_HEADERS_ERROR.format( include_dir = include_dir ) )

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
    raise InstallationFailed(
      NO_DYNAMIC_PYTHON_ERROR.format( library = static_libraries[ 0 ],
                                      flag = dynamic_flag ) )

  raise InstallationFailed( NO_PYTHON_LIBRARY_ERROR )


def CustomPythonCmakeArgs( args ):
  # The CMake 'FindPythonLibs' Module does not work properly.
  # So we are forced to do its job for it.
  if not args.quiet:
    print( f'Searching Python { PY_MAJOR }.{ PY_MINOR } libraries...' )

  python_library, python_include = FindPythonLibraries()

  if not args.quiet:
    print( f'Found Python library: { python_library }' )
    print( f'Found Python headers folder: { python_include }' )

  return [
    f'-DPython3_LIBRARY={ python_library }',
    f'-DPython3_EXECUTABLE={ sys.executable }',
    f'-DPython3_INCLUDE_DIR={ python_include }'
  ]


def GetGenerator( args ):
  if args.ninja:
    return 'Ninja'
  if OnWindows() and not IS_MSYS:
    # The architecture must be specified through the -A option for the Visual
    # Studio 16 generator.
    if args.msvc == 16:
      return 'Visual Studio 16'
    if args.msvc == 17:
      return 'Visual Studio 17 2022'
    return f"Visual Studio { args.msvc }{ ' Win64' if IS_64BIT else '' }"
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
  parser.add_argument( '--system-libclang', action = 'store_true',
                       help = 'Use system libclang instead of downloading one '
                       'from llvm.org. NOT RECOMMENDED OR SUPPORTED!' )
  parser.add_argument( '--msvc', type = int, choices = [ 15, 16, 17 ],
                       default = 16, help = 'Choose the Microsoft Visual '
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

  # Historically, "verbose" mode was the default and --quiet was added. Now,
  # quiet is the default (but the argument is still allowed, to avoid breaking
  # scripts), and --verbose is added to get the full output.
  parser.add_argument( '--quiet',
                       action = 'store_true',
                       default = True, # This argument is deprecated
                       help = 'Quiet installation mode. Just print overall '
                              'progress and errors. This is the default, so '
                              'this flag is actually ignored. Ues --verbose '
                              'to see more output.' )
  parser.add_argument( '--verbose',
                       action = 'store_false',
                       dest = 'quiet',
                       help = 'Verbose installation mode; prints output from '
                              'build operations. Useful for debugging '
                              'build failures.' )

  parser.add_argument( '--skip-build',
                       action = 'store_true',
                       help = "Don't build ycm_core lib, just install deps" )
  parser.add_argument( '--valgrind',
                       action = 'store_true',
                       help = 'For developers: '
                              'Run core tests inside valgrind.' )
  parser.add_argument( '--clang-tidy',
                       action = 'store_true',
                       help = 'For developers: Run clang-tidy static analysis '
                              'on the ycm_core code itself.' )
  parser.add_argument( '--core-tests', nargs = '?', const = '*',
                       help = 'Run core tests and optionally filter them.' )
  parser.add_argument( '--cmake-path',
                       help = 'For developers: specify the cmake executable. '
                              'Useful for testing with specific versions, or '
                              'if the system is unable to find cmake.' )
  parser.add_argument( '--force-sudo',
                       action = 'store_true',
                       help = 'Compiling with sudo causes problems. If you'
                              ' know what you are doing, proceed.' )

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
    raise InstallationFailed(
      'ERROR: you can\'t pass --system-libclang without also passing '
      '--clang-completer or --all as well.' )
  return args


def FindCmake( args ):
  cmake_exe = [ 'cmake3', 'cmake' ]

  if args.cmake_path:
    cmake_exe.insert( 0, args.cmake_path )

  cmake = PathToFirstExistingExecutable( cmake_exe )
  if cmake is None:
    raise InstallationFailed(
      "ERROR: Unable to find cmake executable in any of"
      f" { cmake_exe }. CMake is required to build ycmd" )
  return cmake


def GetCmakeCommonArgs( args ):
  cmake_args = [ '-G', GetGenerator( args ) ]

  # Set the architecture for the Visual Studio 16/17 generator.
  if OnWindows() and args.msvc >= 16 and not args.ninja and not IS_MSYS:
    arch = 'x64' if IS_64BIT else 'Win32'
    cmake_args.extend( [ '-A', arch ] )

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

  if parsed_args.enable_debug:
    cmake_args.append( '-DCMAKE_BUILD_TYPE=Debug' )
    cmake_args.append( '-DUSE_DEV_FLAGS=ON' )

  # coverage is not supported for c++ on MSVC
  if not OnWindows() and parsed_args.enable_coverage:
    cmake_args.append( '-DCMAKE_CXX_FLAGS=-coverage' )

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

  tests_cmd = [ p.join( tests_dir, 'ycm_core_tests' ), '--gtest_brief' ]
  if args.core_tests != '*':
    tests_cmd.append( f'--gtest_filter={ args.core_tests }' )
  if args.valgrind:
    new_env[ 'PYTHONMALLOC' ] = 'malloc'
    tests_cmd = [ 'valgrind',
            '--gen-suppressions=all',
            '--error-exitcode=1',
            '--leak-check=full',
            '--show-leak-kinds=definite,indirect',
            '--errors-for-leak-kinds=definite,indirect',
            '--suppressions=' + p.join( DIR_OF_THIS_SCRIPT,
                                        'valgrind.suppressions' ) ] + tests_cmd
  CheckCall( tests_cmd,
      env = new_env,
      quiet = args.quiet,
      status_message = 'Running ycmd tests' )


def RunYcmdBenchmarks( args, build_dir ):
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
      raise InstallationFailed( 'ERROR: ycmd library is currently in use. '
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
                 status_message = f'Compiling ycmd target: { target }' )

    if script_args.core_tests:
      RunYcmdTests( script_args, build_dir )
    if 'YCM_BENCHMARK' in os.environ:
      RunYcmdBenchmarks( script_args, build_dir )
  finally:
    os.chdir( DIR_OF_THIS_SCRIPT )

    if script_args.build_dir:
      print( 'The build files are in: ' + build_dir )
    else:
      RemoveDirectory( build_dir )


def BuildRegexModule( script_args ):
  build_dir = p.join( DIR_OF_THIRD_PARTY, 'regex-build', '3' )
  lib_dir = p.join( DIR_OF_THIRD_PARTY, 'regex-build' )

  try:
    os.chdir( p.join( DIR_OF_THIRD_PARTY, 'mrab-regex' ) )

    RemoveDirectoryIfExists( build_dir )
    RemoveDirectoryIfExists( lib_dir )

    try:
      import setuptools # noqa
      CheckCall( [ sys.executable,
                   'setup.py',
                   'build',
                   '--build-base=' + build_dir,
                   '--build-lib=' + lib_dir ],
                 exit_message = 'Failed to build regex module.',
                 quiet = script_args.quiet,
                 status_message = 'Building regex module' )
    except ImportError:
      pass # Swallow the error - ycmd will fall back to the standard `re`.

  finally:
    RemoveDirectoryIfExists( build_dir )
    os.chdir( DIR_OF_THIS_SCRIPT )


def EnableCsCompleter( args ):
  def WriteStdout( text ):
    if not args.quiet:
      sys.stdout.write( text )
      sys.stdout.flush()

  if args.quiet:
    sys.stdout.write( 'Installing Omnisharp for C# support...' )
    sys.stdout.flush()

  build_dir = p.join( DIR_OF_THIRD_PARTY, "omnisharp-roslyn" )
  try:
    MkDirIfMissing( build_dir )
    os.chdir( build_dir )

    download_data = GetCsCompleterDataForPlatform()
    version = download_data[ 'version' ]

    WriteStdout( f"Installing Omnisharp { version }\n" )

    CleanCsCompleter( build_dir, version )
    package_path = DownloadCsCompleter( WriteStdout, download_data )
    ExtractCsCompleter( WriteStdout, build_dir, package_path )

    WriteStdout( "Done installing Omnisharp\n" )

    if args.quiet:
      print( 'OK' )
  finally:
    os.chdir( DIR_OF_THIS_SCRIPT )


def MkDirIfMissing( path ):
  try:
    os.mkdir( path )
  except OSError:
    pass


def CleanCsCompleter( build_dir, version ):
  for file_name in os.listdir( build_dir ):
    file_path = p.join( build_dir, file_name )
    if file_name == version:
      continue
    if os.path.isfile( file_path ):
      os.remove( file_path )
    elif os.path.isdir( file_path ):
      import shutil
      shutil.rmtree( file_path )


def DownloadCsCompleter( writeStdout, download_data ):
  file_name = download_data[ 'file_name' ]
  download_url = download_data[ 'download_url' ]
  check_sum = download_data[ 'check_sum' ]
  version = download_data[ 'version' ]

  MkDirIfMissing( version )

  package_path = p.join( version, file_name )
  if ( p.exists( package_path )
       and not CheckFileIntegrity( package_path, check_sum ) ):
    writeStdout( 'Cached Omnisharp file does not match checksum.\n' )
    writeStdout( 'Removing...' )
    os.remove( package_path )
    writeStdout( 'DONE\n' )

  if p.exists( package_path ):
    writeStdout( f'Using cached Omnisharp: { file_name }\n' )
  else:
    writeStdout( f'Downloading Omnisharp from { download_url }...' )
    DownloadFileTo( download_url, package_path )
    writeStdout( 'DONE\n' )

  return package_path


def ExtractCsCompleter( writeStdout, build_dir, package_path ):
  writeStdout( f'Extracting Omnisharp to { build_dir }...' )
  if OnWindows():
    with ZipFile( package_path, 'r' ) as package_zip:
      package_zip.extractall()
  else:
    with tarfile.open( package_path ) as package_tar:
      package_tar.extractall()
  writeStdout( 'DONE\n' )


def GetCsCompleterDataForPlatform():
  ####################################
  # GENERATED BY update_omnisharp.py #
  # DON'T MANUALLY EDIT              #
  ####################################
  DATA = {
    'win32': {
      'version': 'v1.35.4',
      'download_url': ( 'https://github.com/OmniSharp/omnisharp-roslyn/release'
                        's/download/v1.35.4/omnisharp.http-win-x86.zip' ),
      'file_name': 'omnisharp.http-win-x86.zip',
      'check_sum': ( 'f6a44ec4e9edfbb4cb13626b09859d3dcd9b92e202f00b484d3c5956'
                     '4dfa236b' ),
    },
    'win64': {
      'version': 'v1.35.4',
      'download_url': ( 'https://github.com/OmniSharp/omnisharp-roslyn/release'
                        's/download/v1.35.4/omnisharp.http-win-x64.zip' ),
      'file_name': 'omnisharp.http-win-x64.zip',
      'check_sum': ( '18ea074d099592c211929754cbc616e9b640b4143d60b20b374e015b'
                     '97932703' ),
    },
    'macos': {
      'version': 'v1.35.4',
      'download_url': ( 'https://github.com/OmniSharp/omnisharp-roslyn/release'
                        's/download/v1.35.4/omnisharp.http-osx.tar.gz' ),
      'file_name': 'omnisharp.http-osx.tar.gz',
      'check_sum': ( '5e7e4870605ea53c1588d6a11e31a277b062b29477c3486d43a3c609'
                     '99f1cae8' ),
    },
    'linux32': {
      'version': 'v1.35.4',
      'download_url': ( 'https://github.com/OmniSharp/omnisharp-roslyn/release'
                        's/download/v1.35.4/omnisharp.http-linux-x86.tar.gz' ),
      'file_name': 'omnisharp.http-linux-x86.tar.gz',
      'check_sum': ( '5998daa508e79e2e1f1bbf018ef59a7b82420506cb6fa3fa75a54248'
                     '94f89c19' ),
    },
    'linux64': {
      'version': 'v1.35.4',
      'download_url': ( 'https://github.com/OmniSharp/omnisharp-roslyn/release'
                        's/download/v1.35.4/omnisharp.http-linux-x64.tar.gz' ),
      'file_name': 'omnisharp.http-linux-x64.tar.gz',
      'check_sum': ( 'a1b89e5cb67afedfc17515eae565c58a31c36d660dde7f15e4de4ef8'
                     '5e464b1c' ),
    },
  }
  if OnWindows():
    return DATA[ 'win64' if IS_64BIT else 'win32' ]
  else:
    if OnMac():
      return DATA[ 'macos' ]
    return DATA[ 'linux64' if IS_64BIT else 'linux32' ]


def EnableGoCompleter( args ):
  go = FindExecutableOrDie( 'go', 'go is required to build gopls.' )

  new_env = os.environ.copy()
  new_env[ 'GO111MODULE' ] = 'on'
  new_env[ 'GOPATH' ] = p.join( DIR_OF_THIS_SCRIPT, 'third_party', 'go' )
  new_env.pop( 'GOROOT', None )
  new_env[ 'GOBIN' ] = p.join( new_env[ 'GOPATH' ], 'bin' )
  CheckCall( [ go, 'get', 'golang.org/x/tools/gopls@v0.7.1' ],
             env = new_env,
             quiet = args.quiet,
             status_message = 'Building gopls for go completion' )


def WriteToolchainVersion( version ):
  path = p.join( RUST_ANALYZER_DIR, 'TOOLCHAIN_VERSION' )
  with open( path, 'w' ) as f:
    f.write( version )


def ReadToolchainVersion():
  try:
    filepath = p.join( RUST_ANALYZER_DIR, 'TOOLCHAIN_VERSION' )
    with open( filepath ) as f:
      return f.read().strip()
  except OSError:
    return None


def EnableRustCompleter( switches ):
  if switches.quiet:
    sys.stdout.write( 'Installing rust-analyzer for Rust support...' )
    sys.stdout.flush()

  toolchain_version = ReadToolchainVersion()
  if toolchain_version != RUST_TOOLCHAIN:
    install_dir = mkdtemp( prefix = 'rust_install_' )

    new_env = os.environ.copy()
    new_env[ 'RUSTUP_HOME' ] = install_dir

    rustup_init = p.join( install_dir, 'rustup-init' )

    if OnWindows():
      rustup_cmd = [ rustup_init ]
      rustup_url = f"https://win.rustup.rs/{ 'x86_64' if IS_64BIT else 'i686' }"
    else:
      rustup_cmd = [ 'sh', rustup_init ]
      rustup_url = 'https://sh.rustup.rs'

    DownloadFileTo( rustup_url, rustup_init )

    new_env[ 'CARGO_HOME' ] = install_dir

    CheckCall( rustup_cmd + [ '-y',
                              '--default-toolchain', 'none',
                              '--no-modify-path' ],
               env = new_env,
               quiet = switches.quiet )

    rustup = p.join( install_dir, 'bin', 'rustup' )

    try:
      CheckCall( [ rustup, 'toolchain', 'install', RUST_TOOLCHAIN ],
                 env = new_env,
                 quiet = switches.quiet )

      for component in [ 'rust-src',
                         'rust-analyzer-preview',
                         'rustfmt',
                         'clippy' ]:
        CheckCall( [ rustup, 'component', 'add', component,
                     '--toolchain', RUST_TOOLCHAIN ],
                   env = new_env,
                   quiet = switches.quiet )

      toolchain_dir = subprocess.check_output(
        [ rustup, 'run', RUST_TOOLCHAIN, 'rustc', '--print', 'sysroot' ],
        env = new_env
      ).rstrip().decode( 'utf8' )

      if p.exists( RUST_ANALYZER_DIR ):
        RemoveDirectory( RUST_ANALYZER_DIR )
      os.makedirs( RUST_ANALYZER_DIR )

      for folder in os.listdir( toolchain_dir ):
        shutil.move( p.join( toolchain_dir, folder ), RUST_ANALYZER_DIR )

      WriteToolchainVersion( RUST_TOOLCHAIN )
    finally:
      RemoveDirectory( install_dir )

  if switches.quiet:
    print( 'OK' )


def EnableJavaScriptCompleter( args ):
  npm = FindExecutableOrDie( 'npm', 'npm is required to set up Tern.' )
  os.chdir( p.join( DIR_OF_THIS_SCRIPT, 'third_party', 'tern_runtime' ) )
  CheckCall( [ npm, 'install', '--production' ],
             quiet = args.quiet,
             status_message = 'Setting up Tern for JavaScript completion' )


def CheckJavaVersion( required_version ):
  java = FindExecutableOrDie(
    'java',
    f'java { required_version } is required to install JDT.LS' )
  java_version = None
  try:
    new_env = os.environ.copy()
    new_env.pop( 'JAVA_TOOL_OPTIONS', None )
    new_env.pop( '_JAVA_OPTIONS', None )
    java_version = int(
      subprocess.check_output(
        [ java, p.join( DIR_OF_THIS_SCRIPT, 'CheckJavaVersion.java' ) ],
        stderr=subprocess.STDOUT,
        env = new_env )
      .decode( 'utf-8' )
      .strip() )
  except subprocess.CalledProcessError:
    pass

  if java_version is None or java_version < required_version:
    print( f'\n\n*** WARNING ***: jdt.ls requires Java { required_version }.'
           ' You must set the option java_binary_path to point to a working '
           f'java { required_version }.\n\n' )


def EnableJavaCompleter( switches ):
  def Print( *args, **kwargs ):
    if not switches.quiet:
      print( *args, **kwargs )

  if switches.quiet:
    sys.stdout.write( 'Installing jdt.ls for Java support...' )
    sys.stdout.flush()

  CheckJavaVersion( 11 )

  TARGET = p.join( DIR_OF_THIRD_PARTY, 'eclipse.jdt.ls', 'target', )
  REPOSITORY = p.join( TARGET, 'repository' )
  CACHE = p.join( TARGET, 'cache' )

  JDTLS_SERVER_URL_FORMAT = ( 'http://download.eclipse.org/jdtls/snapshots/'
                              '{jdtls_package_name}' )
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
    Print( f'Using cached jdt.ls: { file_name }' )
  else:
    Print( f"Downloading jdt.ls from { url }..." )
    DownloadFileTo( url, file_name )

  Print( f"Extracting jdt.ls to { REPOSITORY }..." )
  with tarfile.open( file_name ) as package_tar:
    package_tar.extractall( REPOSITORY )

  Print( "Done installing jdt.ls" )

  if switches.quiet:
    print( 'OK' )


def EnableTypeScriptCompleter( args ):
  RemoveDirectoryIfExists( p.join( DIR_OF_THIRD_PARTY, 'tsserver', 'bin' ) )
  RemoveDirectoryIfExists( p.join( DIR_OF_THIRD_PARTY, 'tsserver', 'lib' ) )
  npm = FindExecutableOrDie( 'npm', 'npm is required to install TSServer.' )
  os.chdir( p.join( DIR_OF_THIRD_PARTY, 'tsserver' ) )
  CheckCall( [ npm, 'install', '--production' ],
             quiet = args.quiet,
             status_message = 'Setting up TSserver for TypeScript completion' )


def GetClangdTarget():
  if OnWindows():
    return [
      ( 'clangd-{version}-win64',
        '5f4f8612af3f10bb52fd97d6196ac1653802f04f179d2069cf2c1fa861e167b5' ),
      ( 'clangd-{version}-win32',
        '1554db0f7e7a8b1e98746aa2e9f650d753cfbdc4ad5892d4b94725b7701bc635' ) ]
  if OnMac():
    return [
      ( 'clangd-{version}-x86_64-apple-darwin',
        '07f8ee76b47a021c1dc646339a0de564682ed3eb38c9af7c621a13462b372234' ) ]
  if OnFreeBSD():
    return [
      ( 'clangd-{version}-amd64-unknown-freebsd13',
        'eba47cc50bea3bebd5f8a8d1c8890dd1d93bf5c7759306f56ea6edb7ee9df23e' ),
      ( 'clangd-{version}-i386-unknown-freebsd13',
        'b5c9e316be51a09cb72a0eec865d990877ce1312aff1612b776735a920aeac05' ) ]
  if OnAArch64():
    return [
      ( 'clangd-{version}-aarch64-linux-gnu',
        'e4696956476680522f388e1650cd088d6c299ae71c371c397b5cec492b9ced4c' ) ]
  if OnArm():
    return [
      None, # First list index is for 64bit archives. ARMv7 is 32bit only.
      ( 'clangd-{version}-armv7a-linux-gnueabihf',
        'e2e8aa20b7b4d9b3c0955211f42950120d650a4fb4bef3e4140bdf147b903e8e' ) ]
  if OnX86_64():
    return [
      ( 'clangd-{version}-x86_64-unknown-linux-gnu',
        '5fc913b474a142a1796a598167a1227552eb4346b5f500a0594c876165f408ad' ) ]
  raise InstallationFailed(
    CLANGD_BINARIES_ERROR_MESSAGE.format( version = CLANGD_VERSION,
                                          platform = 'this system' ) )


def DownloadClangd( printer ):
  CLANGD_DIR = p.join( DIR_OF_THIRD_PARTY, 'clangd', )
  CLANGD_CACHE_DIR = p.join( CLANGD_DIR, 'cache' )
  CLANGD_OUTPUT_DIR = p.join( CLANGD_DIR, 'output' )

  target = GetClangdTarget()
  target_name, check_sum = target[ not IS_64BIT ]
  target_name = target_name.format( version = CLANGD_VERSION )
  file_name = f'{ target_name }.tar.bz2'
  download_url = ( 'https://github.com/ycm-core/llvm/releases/download/'
                   f'{ CLANGD_VERSION }/{ file_name }' )

  file_name = p.join( CLANGD_CACHE_DIR, file_name )

  MakeCleanDirectory( CLANGD_OUTPUT_DIR )

  if not p.exists( CLANGD_CACHE_DIR ):
    os.makedirs( CLANGD_CACHE_DIR )
  elif p.exists( file_name ) and not CheckFileIntegrity( file_name, check_sum ):
    printer( 'Cached Clangd archive does not match checksum. Removing...' )
    os.remove( file_name )

  if p.exists( file_name ):
    printer( f'Using cached Clangd: { file_name }' )
  else:
    printer( f"Downloading Clangd from { download_url }..." )
    DownloadFileTo( download_url, file_name )
    if not CheckFileIntegrity( file_name, check_sum ):
      raise InstallationFailed(
        'ERROR: downloaded Clangd archive does not match checksum.' )

  printer( f"Extracting Clangd to { CLANGD_OUTPUT_DIR }..." )
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

  if not Args.quiet:
    print( 'Clangd completer enabled. If you are using .ycm_extra_conf.py '
           'files, make sure they use Settings() instead of the old and '
           'deprecated FlagsForFile().' )


def WritePythonUsedDuringBuild():
  path = p.join( DIR_OF_THIS_SCRIPT, 'PYTHON_USED_DURING_BUILDING' )
  with open( path, 'w' ) as f:
    f.write( sys.executable )


def BuildWatchdogModule( script_args ):
  DIR_OF_WATCHDOG_DEPS = p.join( DIR_OF_THIRD_PARTY, 'watchdog_deps' )
  build_dir = p.join( DIR_OF_WATCHDOG_DEPS, 'watchdog', 'build', '3' )
  lib_dir = p.join( DIR_OF_WATCHDOG_DEPS, 'watchdog', 'build', 'lib3' )
  try:
    os.chdir( p.join( DIR_OF_WATCHDOG_DEPS, 'watchdog' ) )

    RemoveDirectoryIfExists( build_dir )
    RemoveDirectoryIfExists( lib_dir )

    try:
      import setuptools # noqa
      CheckCall( [ sys.executable,
                   'setup.py',
                   'build',
                   '--build-base=' + build_dir,
                   '--build-lib=' + lib_dir ],
                 exit_message = 'Failed to build watchdog module.',
                 quiet = script_args.quiet,
                 status_message = 'Building watchdog module' )
    except ImportError:
      if OnMac():
        print( 'WARNING: setuptools unavailable. Watchdog will fall back to '
               'the slower kqueue filesystem event API.\n'
               'To use the faster fsevents, install setuptools and '
               'rerun this script.' )
      os.makedirs( lib_dir )
      shutil.copytree( p.join( 'src', 'watchdog' ),
                       p.join( lib_dir, 'watchdog' ) )
  finally:
    RemoveDirectoryIfExists( build_dir )
    os.chdir( DIR_OF_THIS_SCRIPT )


def DoCmakeBuilds( args ):
  cmake = FindCmake( args )
  cmake_common_args = GetCmakeCommonArgs( args )

  ExitIfYcmdLibInUseOnWindows()
  BuildYcmdLib( cmake, cmake_common_args, args )
  WritePythonUsedDuringBuild()

  BuildRegexModule( args )
  BuildWatchdogModule( args )


def PrintReRunMessage():
  print( '',
         'The installation failed; please see above for the actual error. '
         'In order to get more information, please re-run the command, '
         'adding the --verbose flag. If you think this is a bug and you '
         'raise an issue, you MUST include the *full verbose* output.',
         '',
         'For example, run:' + shlex.join( [ sys.executable ] +
                                           sys.argv +
                                           [ '--verbose' ] ),
         '',
         file = sys.stderr,
         sep = '\n' )


def Main(): # noqa: C901
  args = ParseArguments()

  if 'SUDO_COMMAND' in os.environ:
    if args.force_sudo:
      print( 'Forcing build with sudo. If it breaks, keep the pieces.' )
    else:
      sys.exit( 'This script should not be run with sudo.' )

  try:
    if not args.skip_build:
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
    if args.clangd_completer or args.all_completers:
      EnableClangdCompleter( args )
  except InstallationFailed as e:
    e.Print()
    if args.quiet:
      PrintReRunMessage()
    e.Exit()
  except Exception as e:
    if args.quiet:
      print( f"FAILED with exception { type( e ).__name__ }: { e }" )
      PrintReRunMessage()
    else:
      raise


if __name__ == '__main__':
  Main()
