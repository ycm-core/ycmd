#!/bin/sh

set -e

SCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"

command_exists() {
  hash "$1" 2>/dev/null ;
}

cmake_install() {
  if [ `uname -s` = "Darwin" ]; then
    homebrew_cmake_install
  else
    linux_cmake_install
  fi
}

homebrew_cmake_install() {
  if command_exists brew; then
    brew install cmake
  else
    echo "Homebrew was not found installed in your system."
    echo "Go to http://mxcl.github.com/homebrew/ and follow the instructions."
    echo "Or install CMake somehow and retry."
    exit 1
  fi
}

python_finder() {
  # The CMake 'FindPythonLibs' Module does not work properly.
  # So we are forced to do its job for it.
  python_prefix=$(python-config --prefix | sed 's/^[ \t]*//')
  if [ -f "${python_prefix}/Python" ]; then
    python_library="${python_prefix}/Python"
    python_include="${python_prefix}/Headers"
  else
    which_python=$(python -c 'import sys;i=sys.version_info;print "python%d.%d" % (i.major, i.minor)')
    lib_python="${python_prefix}/lib/lib${which_python}"
    if [ -f "${lib_python}.a" ]; then
      python_library="${lib_python}.a"
    # This check is for for CYGWIN
    elif [ -f "${lib_python}.dll.a" ]; then
      python_library="${lib_python}.dll.a"
    else
      python_library="${lib_python}.dylib"
    fi
    python_include="${python_prefix}/include/${which_python}"
  fi

  echo "-DPYTHON_LIBRARY=${python_library} -DPYTHON_INCLUDE_DIR=${python_include}"
}

num_cores() {
  if [ -n "${YCM_CORES}" ]; then
    # Useful while building on machines with lot of CPUs but small amount of
    # memory/swap
    num_cpus=${YCM_CORES};
  elif command_exists nproc; then
    num_cpus=$(nproc)
  elif [ `uname -s` = "Linux" ]; then
    num_cpus=$(grep -c ^processor /proc/cpuinfo)
  else
    # Works on Mac, FreeBSD and OpenBSD
    num_cpus=$(sysctl -n hw.ncpu)
  fi
  echo $num_cpus
}


install() {
  build_dir=`mktemp -d -t ycm_build.XXXXXX`
  cd "${build_dir}"

  if [ `uname -s` = "Darwin" ]; then
    cmake -G "Unix Makefiles" $(python_finder) "$@" . "${SCRIPT_DIR}/cpp"
  else
    cmake -G "Unix Makefiles" "$@" . "${SCRIPT_DIR}/cpp"
  fi

  make -j $(num_cores) ycm_support_libs
  cd -
  rm -rf "${build_dir}"
}

testrun() {
  build_dir=`mktemp -d -t ycm_build.XXXXXX`
  cd "${build_dir}"

  cmake -G "Unix Makefiles" "$@" . "${SCRIPT_DIR}/cpp"
  make -j $(num_cores) ycm_core_tests
  cd ycm/tests
  LD_LIBRARY_PATH="${SCRIPT_DIR}" ./ycm_core_tests

  cd -
  rm -rf "${build_dir}"
}

linux_cmake_install() {
  echo "Please install CMake using your package manager and retry."
  exit 1
}

usage() {
  echo "Usage: $0 [--clang-completer [--system-libclang]] [--system-boost] [--omnisharp-completer]"
  exit 0
}

check_third_party_libs() {
  libs_present=true
  for folder in "${SCRIPT_DIR}"/third_party/*; do
    num_files_in_folder=$(find "${folder}" -maxdepth 1 -mindepth 1 | wc -l)
    if [ $num_files_in_folder -eq 0 ]; then
      libs_present=false
    fi
  done

  if ! $libs_present; then
    echo "Some folders in ./third_party are empty; you probably forgot to run:"
    printf "\n\tgit submodule update --init --recursive\n\n"
    exit 1
  fi
}

cmake_args=""
omnisharp_completer=false
for flag in $@; do
  case "$flag" in
    --clang-completer)
      cmake_args="-DUSE_CLANG_COMPLETER=ON"
      ;;
    --system-libclang)
      cmake_args="$cmake_args -DUSE_SYSTEM_LIBCLANG=ON"
      ;;
    --system-boost)
      cmake_args="$cmake_args -DUSE_SYSTEM_BOOST=ON"
      ;;
    --omnisharp-completer)
      omnisharp_completer=true
      ;;
    *)
      usage
      ;;
  esac
done

if [ $cmake_args = *-DUSE_SYSTEM_LIBCLANG=ON* ] && \
   [ $cmake_args != *-DUSE_CLANG_COMPLETER=ON* ]; then
  usage
fi

check_third_party_libs

if ! command_exists cmake; then
  echo "CMake is required to build YouCompleteMe."
  cmake_install
fi

if [ -z "$YCM_TESTRUN" ]; then
  install $cmake_args $EXTRA_CMAKE_ARGS
else
  testrun $cmake_args $EXTRA_CMAKE_ARGS
fi

if $omnisharp_completer; then
  buildcommand="msbuild"
  if ! command_exists msbuild; then
    buildcommand="msbuild.exe"
    if ! command_exists msbuild.exe; then
      buildcommand="xbuild"
      if ! command_exists xbuild; then
        echo "msbuild or xbuild is required to build Omnisharp"
        exit 1
      fi
    fi
  fi

  build_dir="${SCRIPT_DIR}/third_party/OmniSharpServer"

  cd "${build_dir}"
  $buildcommand
  cd "${ycm_dir}"
fi
