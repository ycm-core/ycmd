# How to build ycmd on Windows with Visual Studio

Note: the relative path base in following text is ycmd git source code folder.


###1. Get the required tools.

- Visual studio 2013 or later.

- Subversion Get it from: http://subversion.apache.org/packages.html (TortoiseSVN is OK. We need svn.exe in PATH to build llvm/clang, and make sure svn.exe in cygwin not before it in PATH)

- Python27 x64 (Python3 is not yet supported ) Get it at:  http://www.python.org/download

- cmake (You should install it in the default `C:\Program Files (x86)\CMake`) Get it at: http://www.cmake.org/download

- LLVM Windows binary (Not sure, this will provide a compiler with clang (clang-cl.exe) for Visual Studio,you can choose `LLVM-vs2013` in Visual Studio. If error happens when build llvm/clang, you should install it. It's only 36.8MB.) Get it at: http://llvm.org/releases/3.6.1/LLVM-3.6.1-win32.exe 

###1.5. Quick

Edit `_build_ycmd.bat`, and change `PYTHON_PATH` to a correct one.

Click `_run_both.bat` and go out for a walk.

###2. Build llvm/clang

Run `_build_llvm.bat` (Where? the relative path base..)

This batch gets llvm/clang source code and generate a Visual Studio 2013 project files. So it maybe takes less than 10 minutes. The source code with .svn takes 360+MB disk space.

If no error, the batch should quit silently.

Now go to `llvm_build` folder, open `LLVM.svn` and change **Debug** mode to **Release** mode. In Solution Explorer, go to `ALL_BUILD`, right click on `ALL_BUILD` and choose build. It take about quite a long time to finish the build. CPU is 100% during the build. The `llvm_build` folder takes about 6.65GB disk space.

If error happens when svn clone code, we should delete `llvm-src` and run it again.

###3. Build ycmd

**Note**: Edit `_build_ycmd.bat`, and change `PYTHON_PATH` to a correct one.

Run `_build_ycmd.bat`

This batch generates `YouCompleteMe.sln` in ycmd_build folder. Open it with Visual Studio 2013. Change **Debug** mode to **Release** mode. In Solution Explorer, select `ycm_support_libs` and right click on it choose build. (Note `ycm_core_tests` and `gmock_main` `gtest_main` etc will fail, so we cannot build the whole solution.) Now you should find `libclang.dll` and `ycm_client_support.pyd` and `ycm_core.pyd`.

###4. Test

Open gvim.exe, you maybe see,
```bash
Runtime Error!

Program: $VIM\gvim.exe

R6034
An application has made an attempt to load the C runtime
library incorrectly.
Please contact the application's support team for more
information.
```
You can follow:

https://bitbucket.org/Haroogan/vim-youcompleteme-for-windows/

In my case, it is `C:\Program Files (x86)\Intel\iCLS Client\msvcr90.dll`. Remove `C:\Program Files (x86)\Intel\iCLS Client` from path. Now everything goes quite well.

###5. Cleanup

You can safely delete `llvm_build\Release\lib`.

###note

Note: [Haroogan](https://bitbucket.org/Haroogan)'s build is MingW-w64 based, while this instructions are Visual Studio based(I successfully build gvim.exe with all latest python2/3 perl ruby lua support in Visual Studio. Because all latest vim llvm/clang python2/3 perl ruby lua source codes with no extra patches can be built in Visual Studio 2013 x64 mode.).

This Visual studio build instructions contributed by [rexdf](http://github.com/rexdf).