@echo off
cd /d %~dp0

SET PYTHON_PATH=C:\Python27

SET PATH=C:\Program Files (x86)\CMake\bin;

if not exist ycmd_build mkdir ycmd_build
cd ycmd_build

SET LLVM_PATH=%~dp0\llvm_build\Release

cmake -DPYTHON_EXECUTABLE=%PYTHON_PATH%\python.exe  -DPYTHON_INCLUDE_DIRS=%PYTHON_PATH%\include -DPYTHON_LIBRARIES=%PYTHON_PATH%\libs\python27.lib -DPATH_TO_LLVM_ROOT=%LLVM_PATH% -G "Visual Studio 12 2013 Win64" ..\cpp

IF ERRORLEVEL 1 goto ERROR
IF ERRORLEVEL 0 goto QUIT

:ERROR

echo Error!

pause

:QUIT

rem exit
