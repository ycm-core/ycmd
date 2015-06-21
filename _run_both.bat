@echo off
cd /d %~dp0
echo _build_llvm.bat
_build_llvm.bat auto
cd /d %~dp0
echo _build_ycmd.bat
_build_ycmd.bat auto
