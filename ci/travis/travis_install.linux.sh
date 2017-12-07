# Linux-specific installation

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

export PATH=${HOME}/bin:${PATH}

# In order to work with ycmd, python *must* be built as a shared library. This
# is set via the PYTHON_CONFIGURE_OPTS option.
export PYTHON_CONFIGURE_OPTS="--enable-shared"

# Pre-installed Node.js is too old. Install latest Node.js v4 LTS.
nvm install 4

# Libuv is required for Omnisharp-Roslyn and isn't in accessible repos
curl -sSL https://github.com/libuv/libuv/archive/v1.18.0.tar.gz | tar zxfv - -C /tmp && cd /tmp/libuv-1.18.0/
sh autogen.sh
./configure --prefix=$HOME/libuvinstall
make
make install
export LD_LIBRARY_PATH="$HOME/libuvinstall/lib"
cd $OLDPWD
