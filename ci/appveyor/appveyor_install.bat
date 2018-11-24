:: Since we are caching target folder in racerd submodule and git cannot clone
:: a submodule in a non-empty folder, we move out the cached folder and move it
:: back after cloning submodules.
if exist third_party\racerd\target (
  move third_party\racerd\target racerd_target
)

git submodule update --init --recursive
:: Batch script will not exit if a command returns an error, so we manually do
:: it for commands that may fail.
if %errorlevel% neq 0 exit /b %errorlevel%

if exist racerd_target (
  move racerd_target third_party\racerd\target
)

::
:: Python configuration
::

if %arch% == 32 (
  set python_path=C:\Python%python%
) else (
  set python_path=C:\Python%python%-x64
)

set PATH=%python_path%;%python_path%\Scripts;%PATH%
python --version

appveyor DownloadFile https://bootstrap.pypa.io/get-pip.py
python get-pip.py
pip install -r test_requirements.txt
if %errorlevel% neq 0 exit /b %errorlevel%
pip install codecov
if %errorlevel% neq 0 exit /b %errorlevel%
del get-pip.py

:: Enable coverage for Python subprocesses. See:
:: http://coverage.readthedocs.io/en/latest/subprocess.html
python -c "with open('%python_path%\Lib\site-packages\sitecustomize.py', 'w') as f: f.write('import coverage\ncoverage.process_startup()')"

::
:: Rust configuration
::

appveyor DownloadFile https://static.rust-lang.org/rustup/dist/i686-pc-windows-gnu/rustup-init.exe
rustup-init.exe -y

set PATH=%USERPROFILE%\.cargo\bin;%PATH%
rustup update
rustc -Vv
cargo -V

::
:: Java Configuration (Java 8 required for jdt.ls)
::
if %arch% == 32 (
  set "JAVA_HOME=C:\Program Files (x86)\Java\jdk1.8.0"
) else (
  set "JAVA_HOME=C:\Program Files\Java\jdk1.8.0"
)

set PATH=%JAVA_HOME%\bin;%PATH%
java -version
