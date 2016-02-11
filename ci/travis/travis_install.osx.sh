# OS X-specific installation

# There's a homebrew bug which causes brew update to fail the first time. Run
# it twice to workaround. https://github.com/Homebrew/homebrew/issues/42553
brew update || brew update

# install node, go, ninja, pyenv and dependencies
for pkg in node.js go ninja readline autoconf pkg-config openssl pyenv; do
  # install package, or upgrade it if it is already installed
  brew install $pkg || brew outdated $pkg || brew upgrade $pkg
done

# We use homebrew's defaults for PYENV_ROOT etc.
eval "$(pyenv init -)"

if [ "${YCMD_PYTHON_VERSION}" == "2.6" ]; then
  PYENV_VERSION="2.6.6"
elif [ "${YCMD_PYTHON_VERSION}" == "2.7" ]; then
  PYENV_VERSION="2.7.6"
else
  PYENV_VERSION="3.3.0"
fi

# In order to work with ycmd, python *must* be built as a shared library. The
# most compatible way to do this on OS X is with --enable-framework. This is
# set via the PYTHON_CONFIGURE_OPTS option
PYTHON_CONFIGURE_OPTS="--enable-framework" pyenv install --skip-existing ${PYENV_VERSION}
pyenv rehash
pyenv global ${PYENV_VERSION}

YCMD_VENV_DIR=${HOME}/venvs/ycmd_test

# virtualenv is not installed by default on OS X under python2.6, and we don't
# have sudo, so we install it manually. There is no "latest" link, so we have
# to install a specific version.
VENV_VERSION=14.0.6

curl -O https://pypi.python.org/packages/source/v/virtualenv/virtualenv-${VENV_VERSION}.tar.gz
tar xvfz virtualenv-${VENV_VERSION}.tar.gz
python virtualenv-${VENV_VERSION}/virtualenv.py -p python${YCMD_PYTHON_VERSION} ${YCMD_VENV_DIR}

# virtualenv script is noisy, so don't print every command
set +v
source ${YCMD_VENV_DIR}/bin/activate
set -v

