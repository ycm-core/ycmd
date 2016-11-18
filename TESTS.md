# Running ycmd tests

This readme documents instructions on running the test suite.

The easiest way to run the ycmd test suite locally is to [set up your ycmd dev
environment using Vagrant][dev-setup] which will have everything installed and
ready to go. Reading this file is still useful because you'll learn how to skip
the build or parts of the test suite.

An alternative (canonical) reference is the scripts used for running the tests
on Travis CI. These can be found in `.travis.yml` and `./travis` directory.

## Requirements for running the tests

You need to have installed:

* nose (pip install nose)
* nose-exclude (pip install nose-exclude)
* mock (pip install mock)
* flake8 (pip install flake8)
* webtest (pip install webtest)
* hamcrest (pip install PyHamcrest)

See `test_requirements.txt` for specific versions. The simplest way to set this
up is to use a virtualenv, for example:

```bash
$ mkdir ~/YouCompleteMe/tests
$ virtualenv ~/YouCompleteMe/tests
$ source ~/YouCompleteMe/tests/bin/activate
$ pip install -r test_requirements.txt
```

You also need to have all of ycmd's completers' requirements. See the
installation guide for details, but typically this involves manually installing:

* mono
* gocode
* typescript
* node
* npm

If you are unwilling or unable to install the requirements for all of the
completers, you can exclude certain completers with the `--no-completer`
option.

### mono non-standard path

Note: if your installation of mono is in a non-standard location,
OmniSharpServer will not start. Ensure that it is in a standard location, or
change the paths in `OmniSharpServer/OmniSharp/Solution/CSharpProject.cs`

## Running the tests

To run the full suite, just run `run_tests.py`. Options are:

* `--skip-build`: don't attempt to run the build `build.py`, e.g. if you use
a non-standard build environment (e.g. `cmake28`, self-build of clang, etc.)
* `--no-completers`: Do not build or test with listed semantic completion engine(s).
* `--completers`: Only build and test with listed semantic completion engine(s).
* `--msvc`: The Microsoft Visual Studio version to build with.
 (default: 14). Windows only.
* `--arch`: Force architecture to 32 or 64 bits on Windows (default: python
interpreter architecture). Windows Only.
* `--coverage`: Generate code coverage data

Remaining arguments are passed to "nosetests" directly. This means that you
can run a specific script or a specific test as follows:

* Specific test: `./run_tests.py ycmd/tests/<module_name>.py:<function name>`
* Specific script: `./run_tests.py ycmd.tests.<module_name>`

For example:

* `./run_tests.py ycmd/tests/subcommands_test.py:RunCompleterCommand_GetType_test`
* `./run_tests.py ycmd.tests.subcommands_test`

NOTE: you must have UTF8 support in your terminal when you do this, e.g.:

    > LANG=en_GB.utf8 ./run_tests.py --skip-build

## Coverage testing

We can generate coverage data for both the C++ layer and the Python layer. The
CI system will pass this coverage data to codecov.io where you can view coverage
after pushing a branch.

C++ coverage testing is available only on Linux/Mac and uses gcov.
Stricly speaking, we use the `-coverage` option to your compiler, which in the
case of GNU and LLVM compilers, generate gcov-compatible data.

For Python, there's a coverage module which works nicely with `nosetests`. This
is very useful for highlighting areas of your code which are not covered by the
automated integration tests.

Run it like this:

```
$ ./run_tests.py --coverage
```

This will print a summary and generate HTML output in `./cover`

More information: https://coverage.readthedocs.org and
https://nose.readthedocs.org/en/latest/plugins/cover.html

## Troubleshooting

### All the tests fail with some missing package.

Check the list of pip packages to install above. If there is one not listed,
install it and add it to the list.

### All the CsCompleter tests fail on unix.

Likely to be a problem with the OmniSharpServer.

* Check that you have compiled OmniSharpServer in `third-party/OmniSharpServer`
* Check that OmniSharpServer starts manually from ycmd/tests/testdata with

    > mono ../../../third_party/OmniSharpServer/OmniSharp/bin/Debug/OmniSharp.exe -s testy/testy.sln

### You get one or all of the following failures

    ERROR: ycmd.tests.get_completions_test.GetCompletions_CsCompleter_PathWithSpace_test
    FAIL: ycmd.completers.general.tests.filename_completer_test.FilenameCompleter_test.QuotedIncludeCompletion_test
    FAIL: ycmd.completers.general.tests.filename_completer_test.FilenameCompleter_test.SystemPathCompletion_test

Ensure that you have UTF-8 support in your environment (see above)

[dev-setup]: https://github.com/Valloric/ycmd/blob/master/DEV_SETUP.md
