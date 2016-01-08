# Linux-specific installation

# We can't use sudo, so we have to approximate the behaviour of the following:
# $ sudo update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-4.8 90

mkdir ${HOME}/bin

ln -s /usr/bin/g++-4.8 ${HOME}/bin/g++
ln -s /usr/bin/gcc-4.8 ${HOME}/bin/gcc
ln -s ${HOME}/bin/g++ ${HOME}/bin/c++

export PATH=${HOME}/bin:${PATH}

virtualenv -p python${YCMD_PYTHON_VERSION} ${YCMD_VENV_DIR}
