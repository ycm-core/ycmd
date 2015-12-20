#!/bin/bash

set -ev

####################
# OS-specific setup
####################

# Requirements of OS-specific install:
#  - install any software which is not installed by Travis configuration
#  - set up everything necessary so that pyenv can build python
source ci/travis/travis_install.${TRAVIS_OS_NAME}.sh

#############
# pyenv setup
#############

export PYENV_ROOT="${HOME}/.pyenv"

if [ ! -d "${PYENV_ROOT}/.git" ]; then
  git clone https://github.com/yyuu/pyenv.git ${PYENV_ROOT}
fi
pushd ${PYENV_ROOT}
git fetch --tags
git checkout v20160202
popd

export PATH="${PYENV_ROOT}/bin:${PATH}"

eval "$(pyenv init -)"

if [ "${YCMD_PYTHON_VERSION}" == "2.6" ]; then
  PYENV_VERSION="2.6.6"
elif [ "${YCMD_PYTHON_VERSION}" == "2.7" ]; then
  PYENV_VERSION="2.7.6"
else
  PYENV_VERSION="3.3.6"
fi

pyenv install --skip-existing ${PYENV_VERSION}
pyenv rehash
pyenv global ${PYENV_VERSION}

# It is quite easy to get the above series of steps wrong. Verify that the
# version of python actually in the path and used is the version that was
# requested, and fail the build if we broke the travis setup
python_version=$(python -c 'import sys; print( "{0}.{1}".format( sys.version_info[0], sys.version_info[1] ) )')
echo "Checking python version (actual ${python_version} vs expected ${YCMD_PYTHON_VERSION})"
test ${python_version} == ${YCMD_PYTHON_VERSION}


############
# pip setup
############

pip install -U pip wheel setuptools
pip install -r test_requirements.txt
npm install -g typescript

# Enable coverage for Python subprocesses. See:
# http://coverage.readthedocs.org/en/coverage-4.0.3/subprocess.html
echo -e "import coverage\ncoverage.process_startup()" > \
  ${PYENV_ROOT}/versions/${PYENV_VERSION}/lib/python${YCMD_PYTHON_VERSION}/site-packages/sitecustomize.py

############
# rust setup
############

# Need rust available, but travis doesn't give it to you without language: rust
pushd ${HOME}
git clone --recursive https://github.com/brson/multirust
cd multirust
git reset --hard f3974f2b966476ad656afba311b50a9c23fe6d2e
./build.sh
./install.sh --prefix=${HOME}
popd

multirust update stable
multirust default stable

# The build infrastructure prints a lot of spam after this script runs, so make
# sure to disable printing, and failing on non-zero exit code after this script
# finishes
set +ev
