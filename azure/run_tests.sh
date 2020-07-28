# Exit immediately if a command returns a non-zero status.
set -e

test -d "$HOME/.pyenv/bin" && export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init -)"

pyenv global ${YCM_PYTHON_VERSION}

# It is quite easy to get the steps to configure Python wrong. Verify that the
# version of Python actually in the PATH and used is the version that was
# requested, and fail the build if we broke the setup.
python_version=$(python -c 'import sys; print( "{}.{}.{}".format( *sys.version_info[:3] ) )')
echo "Checking python version (actual ${python_version} vs expected ${YCM_PYTHON_VERSION})"
test ${python_version} == ${YCM_PYTHON_VERSION}

# Add the Cargo executable to PATH
PATH="${HOME}/.cargo/bin:${PATH}"

# JDT requires Java 11
if [[ -d /usr/lib/jvm/adoptopenjdk-11-hotspot-amd64 ]]; then
  export JAVA_HOME='/usr/lib/jvm/adoptopenjdk-11-hotspot-amd64'
  export PATH="${JAVA_HOME}/bin:${PATH}"
else
  export JAVA_HOME='/Library/Java/JavaVirtualMachines/adoptopenjdk-11.jdk/Contents/Home'
fi
java -version
javac -version

python run_tests.py

set +e
