# Linux-specific installation

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

