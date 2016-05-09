#!/usr/bin/env python

# Passing an environment variable containing unicode literals to a subprocess
# on Windows and Python2 raises a TypeError. Since there is no unicode
# string in this script, we don't import unicode_literals to avoid the issue.
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from shutil import rmtree
from tempfile import mkdtemp
import errno
import re
import multiprocessing
import os
import os.path as p
import platform
import shlex
import subprocess
import sys

PY_MAJOR, PY_MINOR = sys.version_info[ 0 : 2 ]
if not ( ( PY_MAJOR == 2 and PY_MINOR >= 6 ) or
         ( PY_MAJOR == 3 and PY_MINOR >= 3 ) or
         PY_MAJOR > 3 ):
  sys.exit( 'ycmd requires Python >= 2.6 or >= 3.3; '
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

import argparse

NO_DYNAMIC_PYTHON_ERROR = (
  'ERROR: found static Python library ({library}) but a dynamic one is '
  'required. You must use a Python compiled with the {flag} flag. '
  'If using pyenv, you need to run the command:\n'
  '  export PYTHON_CONFIGURE_OPTS="{flag}"\n'
  'before installing a Python version.' )
NO_PYTHON_LIBRARY_ERROR = 'ERROR: unable to find an appropriate Python library.'

LIBRARY_LDCONFIG_REGEX = re.compile(
  '(?P<library>\S+) \(.*\) => (?P<path>\S+)' )


def OnLinux():
  return platform.system() == 'Linux'


def OnMac():
  return platform.system() == 'Darwin'


def OnWindows():
  return platform.system() == 'Windows'


def OnTravisOrAppVeyor():
  return 'CI' in os.environ


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
    extensions = ['']

  for extension in extensions:
    executable_name = executable + extension
    if not os.path.isfile( executable_name ):
      for path in paths:
        executable_path = os.path.join(path, executable_name )
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


def CheckDeps():
  if not PathToFirstExistingExecutable( [ 'cmake' ] ):
    sys.exit( 'Please install CMake and retry.')


# Shamelessly stolen from https://gist.github.com/edufelipe/1027906
def CheckOutput( *popen_args, **kwargs ):
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


def GetPythonNameOnUnix():
  python_name = 'python' + str( PY_MAJOR ) + '.' + str( PY_MINOR )
  # Python 3 has an 'm' suffix on Unix platforms, for instance libpython3.3m.so.
  if PY_MAJOR == 3:
    python_name += 'm'
  return python_name


def GetStandardPythonLocationsOnUnix( prefix, name ):
  return ( '{0}/lib/lib{1}'.format( prefix, name ),
           '{0}/include/{1}'.format( prefix, name ) )


def FindPythonLibrariesOnLinux():
  python_name = GetPythonNameOnUnix()
  python_library_root, python_include = GetStandardPythonLocationsOnUnix(
    sys.exec_prefix, python_name )

  python_library = python_library_root + '.so'
  if p.isfile( python_library ):
    return python_library, python_include

  python_library = python_library_root + '.a'
  if p.isfile( python_library ):
    sys.exit( NO_DYNAMIC_PYTHON_ERROR.format( library = python_library,
                                              flag = '--enable-shared' ) )

  # On some distributions (Ubuntu for instance), the Python system library is
  # not installed in its default path: /usr/lib. We use the ldconfig tool to
  # find it.
  python_library = 'lib' + python_name + '.so'
  ldconfig_output = CheckOutput( [ 'ldconfig', '-p' ] ).strip().decode( 'utf8' )
  for line in ldconfig_output.splitlines():
    match = LIBRARY_LDCONFIG_REGEX.search( line )
    if match and match.group( 'library' ) == python_library:
      return match.group( 'path' ), python_include

  sys.exit( NO_PYTHON_LIBRARY_ERROR )


def FindPythonLibrariesOnMac():
  python_prefix = sys.exec_prefix

  python_library = p.join( python_prefix, 'Python' )
  if p.isfile( python_library ):
    return python_library, p.join( python_prefix, 'Headers' )

  python_name = GetPythonNameOnUnix()
  python_library_root, python_include = GetStandardPythonLocationsOnUnix(
    python_prefix, python_name )

  # On MacOS, ycmd does not work with statically linked python library.
  # It typically manifests with the following error when there is a
  # self-compiled python without --enable-framework (or, technically
  # --enable-shared):
  #
  #   Fatal Python error: PyThreadState_Get: no current thread
  #
  # The most likely explanation for this is that both the ycm_core.so and the
  # python binary include copies of libpython.a (or whatever included
  # objects). When the python interpreter starts it initializes only the
  # globals within its copy, so when ycm_core.so's copy starts executing, it
  # points at its own copy which is uninitialized.
  #
  # Some platforms' dynamic linkers (ld.so) are able to resolve this when
  # loading shared libraries at runtime[citation needed], but OSX seemingly
  # cannot.
  #
  # So we do 2 things special on OS X:
  #  - look for a .dylib first
  #  - if we find a .a, raise an error.
  python_library = python_library_root + '.dylib'
  if p.isfile( python_library ):
    return python_library, python_include

  python_library = python_library_root + '.a'
  if p.isfile( python_library ):
    sys.exit( NO_DYNAMIC_PYTHON_ERROR.format( library = python_library,
                                              flag = '--enable-framework' ) )

  sys.exit( NO_PYTHON_LIBRARY_ERROR )


def FindPythonLibrariesOnWindows():
  python_prefix = sys.exec_prefix
  python_name = 'python' + str( PY_MAJOR ) + str( PY_MINOR )

  python_library = p.join( python_prefix, 'libs', python_name + '.lib' )
  if p.isfile( python_library ):
    return python_library, p.join( python_prefix, 'include' )

  sys.exit( NO_PYTHON_LIBRARY_ERROR )


def FindPythonLibraries():
  if OnLinux():
    return FindPythonLibrariesOnLinux()

  if OnMac():
    return FindPythonLibrariesOnMac()

  if OnWindows():
    return FindPythonLibrariesOnWindows()

  sys.exit( 'ERROR: your platform is not supported by this script. Follow the '
            'Full Installation Guide instructions in the documentation.' )


def CustomPythonCmakeArgs():
  # The CMake 'FindPythonLibs' Module does not work properly.
  # So we are forced to do its job for it.
  print( 'Searching Python {major}.{minor} libraries...'.format(
    major = PY_MAJOR, minor = PY_MINOR ) )

  python_library, python_include = FindPythonLibraries()

  print( 'Found Python library: {0}'.format( python_library ) )
  print( 'Found Python headers folder: {0}'.format( python_include ) )

  return [
    '-DPYTHON_LIBRARY={0}'.format( python_library ),
    '-DPYTHON_INCLUDE_DIR={0}'.format( python_include )
  ]


def GetGenerator( args ):
  if OnWindows():
    if args.msvc == 14:
      generator = 'Visual Studio 14'
    elif args.msvc == 12:
      generator = 'Visual Studio 12'
    else:
      generator = 'Visual Studio 11'

    if platform.architecture()[ 0 ] == '64bit':
      generator = generator + ' Win64'
    return generator

  if PathToFirstExistingExecutable( ['ninja'] ):
    return 'Ninja'
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
  parser.add_argument( '--racer-completer', action = 'store_true',
                       help = 'Build rust semantic completion engine.' )
  parser.add_argument( '--system-boost', action = 'store_true',
                       help = 'Use the system boost instead of bundled one. '
                       'NOT RECOMMENDED OR SUPPORTED!')
  parser.add_argument( '--msvc', type = int, choices = [ 11, 12, 14 ],
                       default = 14, help = 'Choose the Microsoft Visual '
                       'Studio version (default: %(default)s).' )
  parser.add_argument( '--tern-completer',
                       action = 'store_true',
                       help   = 'Enable tern javascript completer' ),
  parser.add_argument( '--all',
                       action = 'store_true',
                       help   = 'Enable all supported completers',
                       dest   = 'all_completers' )

  args = parser.parse_args()

  if ( args.system_libclang and
       not args.clang_completer and
       not args.all_completers ):
    sys.exit( "You can't pass --system-libclang without also passing "
              "--clang-completer or --all as well." )
  return args


def GetCmakeArgs( parsed_args ):
  cmake_args = []
  if parsed_args.clang_completer or parsed_args.all_completers:
    cmake_args.append( '-DUSE_CLANG_COMPLETER=ON' )

  if parsed_args.system_libclang:
    cmake_args.append( '-DUSE_SYSTEM_LIBCLANG=ON' )

  if parsed_args.system_boost:
    cmake_args.append( '-DUSE_SYSTEM_BOOST=ON' )

  use_python2 = 'ON' if PY_MAJOR == 2 else 'OFF'
  cmake_args.append( '-DUSE_PYTHON2=' + use_python2 )

  extra_cmake_args = os.environ.get( 'EXTRA_CMAKE_ARGS', '' )
  # We use shlex split to properly parse quoted CMake arguments.
  cmake_args.extend( shlex.split( extra_cmake_args ) )
  return cmake_args


def RunYcmdTests( build_dir ):
  tests_dir = p.join( build_dir, 'ycm', 'tests' )
  os.chdir( tests_dir )
  new_env = os.environ.copy()

  if OnWindows():
    # We prepend the folder of the ycm_core_tests executable to the PATH
    # instead of overwriting it so that the executable is able to find the
    # python35.dll library.
    new_env[ 'PATH' ] = DIR_OF_THIS_SCRIPT + ';' + new_env[ 'PATH' ]
  else:
    new_env[ 'LD_LIBRARY_PATH' ] = DIR_OF_THIS_SCRIPT

  subprocess.check_call( p.join( tests_dir, 'ycm_core_tests' ), env = new_env )


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


def BuildYcmdLib( args ):
  build_dir = mkdtemp( prefix = 'ycm_build.' )

  try:
    full_cmake_args = [ '-G', GetGenerator( args ) ]
    full_cmake_args.extend( CustomPythonCmakeArgs() )
    full_cmake_args.extend( GetCmakeArgs( args ) )
    full_cmake_args.append( p.join( DIR_OF_THIS_SCRIPT, 'cpp' ) )

    os.chdir( build_dir )
    subprocess.check_call( [ 'cmake' ] + full_cmake_args )

    build_target = ( 'ycm_core' if 'YCM_TESTRUN' not in os.environ else
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
    rmtree( build_dir, ignore_errors = OnTravisOrAppVeyor() )


def BuildOmniSharp():
  build_command = PathToFirstExistingExecutable(
    [ 'msbuild', 'msbuild.exe', 'xbuild' ] )
  if not build_command:
    sys.exit( 'msbuild or xbuild is required to build Omnisharp' )

  os.chdir( p.join( DIR_OF_THIS_SCRIPT, 'third_party', 'OmniSharpServer' ) )
  subprocess.check_call( [ build_command, '/property:Configuration=Release' ] )


def BuildGoCode():
  if not FindExecutable( 'go' ):
    sys.exit( 'go is required to build gocode' )

  os.chdir( p.join( DIR_OF_THIS_SCRIPT, 'third_party', 'gocode' ) )
  subprocess.check_call( [ 'go', 'build' ] )
  os.chdir( p.join( DIR_OF_THIS_SCRIPT, 'third_party', 'godef' ) )
  subprocess.check_call( [ 'go', 'build' ] )


def BuildRacerd():
  """
  Build racerd. This requires a reasonably new version of rustc/cargo.
  """
  if not FindExecutable( 'cargo' ):
    sys.exit( 'cargo is required for the rust completer' )

  os.chdir( p.join( DIR_OF_THIRD_PARTY, 'racerd' ) )
  args = [ 'cargo', 'build' ]
  # We don't use the --release flag on Travis/AppVeyor because it makes building
  # racerd 2.5x slower and we don't care about the speed of the produced racerd.
  if not OnTravisOrAppVeyor():
    args.append( '--release' )
  subprocess.check_call( args )


def SetUpTern():
  paths = {}
  for exe in [ 'node', 'npm' ]:
    path = FindExecutable( exe )
    if not path:
      sys.exit( '"' + exe + '" is required to set up ternjs' )
    else:
      paths[ exe ] = path

  # We install Tern into a runtime directory. This allows us to control
  # precisely the version (and/or git commit) that is used by ycmd.  We use a
  # separate runtime directory rather than a submodule checkout directory
  # because we want to allow users to install third party plugins to
  # node_modules of the Tern runtime.  We also want to be able to install our
  # own plugins to improve the user experience for all users.
  #
  # This is not possible if we use a git submodle for Tern and simply run 'npm
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
  TERN_RUNTIME_DIR = os.path.join( DIR_OF_THIS_SCRIPT,
                                   'third_party',
                                   'tern_runtime' )
  try:
    os.makedirs( TERN_RUNTIME_DIR )
  except Exception:
    # os.makedirs throws if the dir already exists, it also throws if the
    # permissions prevent creating the directory. There's no way to know the
    # difference, so we just let the call to os.chdir below throw if this fails
    # to create the target directory.
    pass

  os.chdir( TERN_RUNTIME_DIR )
  subprocess.check_call( [ paths[ 'npm' ], 'install', '--production' ] )


def WritePythonUsedDuringBuild():
  path = p.join( DIR_OF_THIS_SCRIPT, 'PYTHON_USED_DURING_BUILDING' )
  with open( path, 'w' ) as f:
    f.write( sys.executable )


def Main():
  CheckDeps()
  args = ParseArguments()
  ExitIfYcmdLibInUseOnWindows()
  BuildYcmdLib( args )
  if args.omnisharp_completer or args.all_completers:
    BuildOmniSharp()
  if args.gocode_completer or args.all_completers:
    BuildGoCode()
  if args.tern_completer or args.all_completers:
    SetUpTern()
  if args.racer_completer or args.all_completers:
    BuildRacerd()
  WritePythonUsedDuringBuild()


if __name__ == '__main__':
  Main()
