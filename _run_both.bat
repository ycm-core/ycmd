@echo off
cd /d %~dp0
echo _build_llvm.bat
call _build_llvm.bat auto
cd /d %~dp0
echo _build_ycmd.bat
call _build_ycmd.bat auto
