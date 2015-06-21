@echo off
cd /d %~dp0

REM Follow http://clang.llvm.org/get_started.html
REM clone the latest llvm/clang source code take about 361MB disk space
IF NOT EXIST llvm-src (
svn co http://llvm.org/svn/llvm-project/llvm/trunk llvm-src
cd llvm-src\tools
svn co http://llvm.org/svn/llvm-project/cfe/trunk clang
cd ..\..
)

if not exist llvm_build mkdir llvm_build
cd llvm_build

set PATH=C:\Program Files (x86)\CMake\bin;

REM open in Visual studio 2013 and build, it will take about 6.65GB disk space
cmake -DCMAKE_BUILD_TYPE=Release -G "Visual Studio 12 2013 Win64" ..\llvm-src


IF ERRORLEVEL 1 goto ERROR
IF ERRORLEVEL 0 goto QUIT

:ERROR

echo Error!

pause

:QUIT

rem exit
