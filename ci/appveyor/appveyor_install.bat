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
  set python=C:\Python27
) else (
  set python=C:\Python27-x64
)

set PATH=%python%;%python%\Scripts;%PATH%
python --version
:: Manually setting PYTHONHOME for python 2.7.11 fix the following error when
:: running core tests: "ImportError: No module named site"
:: TODO: check if this is still needed when python 2.7.12 is released.
set PYTHONHOME=%python%

appveyor DownloadFile https://raw.github.com/pypa/pip/master/contrib/get-pip.py
python get-pip.py
pip install -r test_requirements.txt
if %errorlevel% neq 0 exit /b %errorlevel%

::
:: Typescript configuration
::

:: Since npm executable is a batch file, we need to prefix it with a call
:: statement. See https://github.com/npm/npm/issues/2938
call npm install -g typescript
if %errorlevel% neq 0 exit /b %errorlevel%

::
:: Rust configuration
::

:: The gnu rust compiler is used since, on windows 10, there is a workaround
:: needed for the msvc versions. However, the workaround sets Omnisharp build
:: config to 64-bit release mode which results in a failed build.
appveyor DownloadFile https://static.rust-lang.org/dist/rust-1.5.0-i686-pc-windows-gnu.exe
rust-1.5.0-i686-pc-windows-gnu.exe /VERYSILENT /NORESTART /DIR="C:\Program Files (x86)\Rust"
:: TODO: MinGW can be removed once the msvc rust compiler is used.
set PATH=C:\Program Files (x86)\Rust\bin;C:\MinGW\bin;%PATH%

rustc -Vv
cargo -V
