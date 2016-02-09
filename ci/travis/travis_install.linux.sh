# Linux-specific installation

#############
# pyenv setup
#############

# DON'T exit if error
set +e
git clone https://github.com/yyuu/pyenv.git ~/.pyenv
git fetch --tags
git checkout v20160202
# Exit if error
set -e

export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"

eval "$(pyenv init -)"

if [ "${YCMD_PYTHON_VERSION}" == "2.6" ]; then
  PYENV_VERSION="2.6.6"
elif [ "${YCMD_PYTHON_VERSION}" == "2.7" ]; then
  PYENV_VERSION="2.7.6"
else
  PYENV_VERSION="3.3.0"
fi

pyenv install --skip-existing ${PYENV_VERSION}
pyenv rehash
pyenv global ${PYENV_VERSION}

# We can't use sudo, so we have to approximate the behaviour of the following:
# $ sudo update-alternatives --install /usr/bin/c++ c++ /usr/bin/clang++-3.7 100

mkdir ${HOME}/bin

ln -s /usr/bin/clang++-3.7 ${HOME}/bin/clang++
ln -s /usr/bin/clang-3.7 ${HOME}/bin/clang

ln -s /usr/bin/clang++-3.7 ${HOME}/bin/c++
ln -s /usr/bin/clang-3.7 ${HOME}/bin/cc

# These shouldn't be necessary, but just in case.
ln -s /usr/bin/clang++-3.7 ${HOME}/bin/g++
ln -s /usr/bin/clang-3.7 ${HOME}/bin/gcc

export PATH=${HOME}/bin:${PATH}

