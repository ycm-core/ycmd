# OS X-specific installation

# There's a homebrew bug which causes brew update to fail the first time. Run
# it twice to workaround. https://github.com/Homebrew/homebrew/issues/42553
brew update || brew update
brew install node.js || brew outdated node.js || brew upgrade node.js
brew install go || brew outdated go || brew upgrade go
brew install ninja

# TODO: In theory, we should be able to just use the pyenv python setup from
# travis_install.linux.sh for both Linux and OS X. In practice, we get:
#   Fatal Python error: PyThreadState_Get: no current thread
# on OS X. So we do something special for OS X. We shouldn't have to though.

YCMD_VENV_DIR=${HOME}/venvs/ycmd_test

# OS X comes with 2 versions of python by default, and a neat system
# (versioner) to switch between them:
#   /usr/bin/python2.7 - python 2.7
#   /usr/bin/python2.6 - python 2.6
#
# We just set the system default to match it
# http://stackoverflow.com/q/6998545
defaults write com.apple.versioner.python Version ${YCMD_PYTHON_VERSION}

# virtualenv is not installed by default on OS X under python2.6, and we don't
# have sudo, so we install it manually. There is no "latest" link, so we have
# to install a specific version.
VENV_VERSION=13.1.2

curl -O https://pypi.python.org/packages/source/v/virtualenv/virtualenv-${VENV_VERSION}.tar.gz
tar xvfz virtualenv-${VENV_VERSION}.tar.gz
python virtualenv-${VENV_VERSION}/virtualenv.py -p python${YCMD_PYTHON_VERSION} ${YCMD_VENV_DIR}

# virtualenv doesn't copy python-config https://github.com/pypa/virtualenv/issues/169
# but our build system uses it
cp /usr/bin/python${YCMD_PYTHON_VERSION}-config ${YCMD_VENV_DIR}/bin/python-config

# virtualenv script is noisy, so don't print every command
set +v
source ${YCMD_VENV_DIR}/bin/activate
set -v

