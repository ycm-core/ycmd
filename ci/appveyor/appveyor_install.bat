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
:: Manually setting PYTHONHOME for python 2.7.11 fix the following error when
:: running core tests: "ImportError: No module named site"
:: TODO: check if this is still needed when python 2.7.12 is released.
if %python% == 27 (
  set PYTHONHOME=%python_path%
)

appveyor DownloadFile https://bootstrap.pypa.io/get-pip.py
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

appveyor DownloadFile https://static.rust-lang.org/dist/rust-1.6.0-x86_64-pc-windows-msvc.exe
rust-1.6.0-x86_64-pc-windows-msvc.exe /VERYSILENT /NORESTART /DIR="C:\Program Files\Rust"
set PATH=C:\Program Files\Rust\bin;%PATH%

rustc -Vv
cargo -V
