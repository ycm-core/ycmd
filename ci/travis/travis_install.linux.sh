# Linux-specific installation

# We can't use sudo, so we have to approximate the behaviour of the following:
# $ sudo update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-6 90

mkdir ${HOME}/bin

ln -s /usr/bin/g++-4.8 ${HOME}/bin/c++
ln -s /usr/bin/gcc-4.8 ${HOME}/bin/cc
ln -s /usr/bin/gcov-4.8 ${HOME}/bin/gcov

export PATH=${HOME}/bin:${PATH}

# In order to work with ycmd, python *must* be built as a shared library. This
# is set via the PYTHON_CONFIGURE_OPTS option.
export PYTHON_CONFIGURE_OPTS="--enable-shared"

# Pre-installed Node.js is too old. Install latest Node.js v4 LTS.
nvm install 4
