::
:: Python configuration
::

set python_installer_extension=%YCM_PYTHON_INSTALLER_URL:~-3%

if "%python_installer_extension%" == "exe" (
  curl %YCM_PYTHON_INSTALLER_URL% -o C:\python-installer.exe
  C:\python-installer.exe /quiet TargetDir=C:\Python
) else (
  curl %YCM_PYTHON_INSTALLER_URL% -o C:\python-installer.msi
  msiexec /i C:\python-installer.msi TARGETDIR=C:\Python /qn
)

C:\Python\Scripts\pip install -r test_requirements.txt

:: Enable coverage for Python subprocesses. See:
:: http://coverage.readthedocs.io/en/latest/subprocess.html
C:\Python\python -c "with open('C:\Python\Lib\site-packages\sitecustomize.py', 'w') as f: f.write('import coverage\ncoverage.process_startup()')"

::
:: Go configuration
::

curl https://dl.google.com/go/go1.12.4.windows-amd64.msi -o C:\go-installer.msi
msiexec /i C:\go-installer.msi TARGETDIR=C:\Go /qn
