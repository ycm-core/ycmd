# OS X-specific installation

# There's a homebrew bug which causes brew update to fail the first time. Run
# it twice to workaround. https://github.com/Homebrew/homebrew/issues/42553
brew update || brew update
brew install node.js || brew outdated node.js || brew upgrade node.js
brew install go || brew outdated go || brew upgrade go

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
