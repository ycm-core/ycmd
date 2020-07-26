:: Add the Python, MSBuild, Cargo, and Go executables to PATH.
set "PATH=C:\Python;C:\Python\Scripts;%PATH%"
set "PATH=%MSBUILD_PATH%;%PATH%"
set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
set "PATH=C:\Go\bin;%PATH%"

:: JDT requires Java 11
set "JAVA_HOME=C:\Program Files\Java\jdk-11.0.8+10"
set "PATH=%JAVA_HOME%\bin;%PATH%"
java -version
javac -version

:: Prevent the already installed version of Go to conflict with ours.
set GOROOT=

python run_tests.py --msvc %MSVC%
