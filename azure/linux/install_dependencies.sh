# Exit immediately if a command returns a non-zero status.
set -e

#
# Compiler setup
#
sudo apt-get update
sudo apt-get install libsqlite3-dev
if [ "${YCM_COMPILER}" == "clang" ]; then
  sudo apt-get install clang-7
  sudo update-alternatives --install /usr/bin/cc cc /usr/bin/clang-7 100
  sudo update-alternatives --install /usr/bin/c++ c++ /usr/bin/clang++-7 100
else
  sudo apt-get install gcc-8 g++-8
  sudo update-alternatives --install /usr/bin/cc cc /usr/bin/gcc-8 100
  sudo update-alternatives --install /usr/bin/c++ c++ /usr/bin/g++-8 100
fi

if [ "${YCM_CLANG_TIDY}" ]; then
  wget -O - https://apt.llvm.org/llvm-snapshot.gpg.key | sudo apt-key add -
  sudo apt-get update
  sudo apt-get install -y clang-tidy valgrind
  sudo update-alternatives --install /usr/bin/clang-tidy clang-tidy /usr/bin/clang-tidy-10 100
fi

#
# Go setup
#

# Create manually the cache folder before pip does to avoid the error
#
#   failed to initialize build cache at /home/vsts/.cache/go-build: mkdir /home/vsts/.cache/go-build: permission denied
#
# while installing the Go completer.
mkdir ${HOME}/.cache


#
# Python setup
#
sudo apt-get install -y build-essential \
                        libssl-dev \
                        zlib1g-dev \
                        libbz2-dev \
                        libreadline-dev \
                        libsqlite3-dev \
                        wget \
                        curl \
                        llvm \
                        libncurses5-dev \
                        libncursesw5-dev \
                        xz-utils \
                        tk-dev \
                        libffi-dev \
                        liblzma-dev \
                        python-openssl \
                        git
curl https://pyenv.run | bash
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init -)"

# In order to work with ycmd, Python *must* be built as a shared library. This
# is set via the PYTHON_CONFIGURE_OPTS option.
PYTHON_CONFIGURE_OPTS="--enable-shared" \
CFLAGS="-I$(brew --prefix openssl)/include" \
LDFLAGS="-L$(brew --prefix openssl)/lib" \
pyenv install ${YCM_PYTHON_VERSION}
pyenv global ${YCM_PYTHON_VERSION}

pip install -r test_requirements.txt

# Enable coverage for Python subprocesses. See:
# http://coverage.readthedocs.io/en/latest/subprocess.html
echo -e "import coverage\ncoverage.process_startup()" > \
${HOME}/.pyenv/versions/${YCM_PYTHON_VERSION}/lib/python${YCM_PYTHON_VERSION%.*}/site-packages/sitecustomize.py

set +e
