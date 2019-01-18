#!/bin/bash

# Exit immediately if a command returns a non-zero status.
set -e

# RVM overrides the cd, popd, and pushd shell commands, causing the
# "shell_session_update: command not found" error on macOS when executing those
# commands.
unset -f cd popd pushd

################
# Compiler setup
################

# We can't use sudo, so we have to approximate the behaviour of the following:
# $ sudo update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-4.9 90

mkdir -p ${HOME}/bin

if [ "${YCM_COMPILER}" == "clang" ]; then
  ln -s /usr/bin/clang++ ${HOME}/bin/c++
  ln -s /usr/bin/clang ${HOME}/bin/cc
  # Tell CMake to compile with libc++ when using Clang.
  export EXTRA_CMAKE_ARGS="${EXTRA_CMAKE_ARGS} -DHAS_LIBCXX11=ON"
else
  ln -s /usr/bin/g++-4.9 ${HOME}/bin/c++
  ln -s /usr/bin/gcc-4.9 ${HOME}/bin/cc
fi
ln -s /usr/bin/gcov-4.9 ${HOME}/bin/gcov
if [ -n "${YCM_CLANG_TIDY}" ]; then
  ln -s /usr/bin/clang-tidy-3.9 ${HOME}/bin/clang-tidy
fi

export PATH=${HOME}/bin:${PATH}

##############
# Python setup
##############

PYENV_ROOT="${HOME}/.pyenv"

if [ ! -d "${PYENV_ROOT}/.git" ]; then
  rm -rf ${PYENV_ROOT}
  git clone https://github.com/yyuu/pyenv.git ${PYENV_ROOT}
fi
pushd ${PYENV_ROOT}
git fetch --tags
git checkout v1.2.1
popd

export PATH="${PYENV_ROOT}/bin:${PATH}"

eval "$(pyenv init -)"

if [ "${YCMD_PYTHON_VERSION}" == "2.7" ]; then
  # Tests are failing on Python 2.7.0 with the exception "TypeError: argument
  # can't be <type 'unicode'>" and importing the coverage module fails on Python
  # 2.7.1.
  PYENV_VERSION="2.7.2"
else
  PYENV_VERSION="3.4.0"
fi

# In order to work with ycmd, python *must* be built as a shared library. This
# is set via the PYTHON_CONFIGURE_OPTS option.
export PYTHON_CONFIGURE_OPTS="--enable-shared"

pyenv install --skip-existing ${PYENV_VERSION}
pyenv rehash
pyenv global ${PYENV_VERSION}

# It is quite easy to get the above series of steps wrong. Verify that the
# version of python actually in the path and used is the version that was
# requested, and fail the build if we broke the travis setup
python_version=$(python -c 'import sys; print( "{0}.{1}".format( sys.version_info[0], sys.version_info[1] ) )')
echo "Checking python version (actual ${python_version} vs expected ${YCMD_PYTHON_VERSION})"
test ${python_version} == ${YCMD_PYTHON_VERSION}

pip install -r test_requirements.txt

# Enable coverage for Python subprocesses. See:
# http://coverage.readthedocs.io/en/latest/subprocess.html
echo -e "import coverage\ncoverage.process_startup()" > \
  ${PYENV_ROOT}/versions/${PYENV_VERSION}/lib/python${YCMD_PYTHON_VERSION}/site-packages/sitecustomize.py

############
# Rust setup
############

curl https://sh.rustup.rs -sSf | sh -s -- -y

export PATH="${HOME}/.cargo/bin:${PATH}"
rustup update
rustc -Vv
cargo -V

#################################
# JavaScript and TypeScript setup
#################################

# Pre-installed Node.js is too old. Install latest Node.js v4 LTS.
nvm install 4

###############
# Java 8 setup
###############
# Make sure we have the appropriate java for jdt.ls
set +e
jdk_switcher use oraclejdk8
set -e

java -version
JAVA_VERSION=$(java -version 2>&1 | awk -F '"' '/version/ {print $2}')
if [[ "$JAVA_VERSION" < "1.8" ]]; then
  echo "Java version $JAVA_VERSION is too old" 1>&2
  exit 1
fi

# Done. Undo settings which break travis scripts.
set +e
