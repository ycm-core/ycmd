# Exit immediately if a command returns a non-zero status.
set -e

#
# Python setup
#

brew install pyenv

eval "$(pyenv init -)"

# In order to work with ycmd, Python *must* be built as a shared library. The
# most compatible way to do this on macOS is with --enable-framework. This is
# set via the PYTHON_CONFIGURE_OPTS option.
PYTHON_CONFIGURE_OPTS="--enable-framework" \
pyenv install ${YCM_PYTHON_VERSION}
pyenv global ${YCM_PYTHON_VERSION}

pip install -r test_requirements.txt

# Enable coverage for Python subprocesses. See:
# http://coverage.readthedocs.io/en/latest/subprocess.html
echo -e "import coverage\ncoverage.process_startup()" > \
${HOME}/.pyenv/versions/${YCM_PYTHON_VERSION}/lib/python${YCM_PYTHON_VERSION%.*}/site-packages/sitecustomize.py

set +e
