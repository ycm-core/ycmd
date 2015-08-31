# Running ycmd tests

This readme documents instructions on running the test suite

## Requirements for running the tests

You need to have installed:

* nose (pip install nose)
* mock (pip install mock)
* flake8 (pip install flake8)
* webtest (pip install webtest)
* hamcrest (pip install PyHamcrest)

See test_requirements.txt for specific minimum versions

You also need to have build requirements for all of:

* ycmd + libClang. See https://github.com/Valloric/YouCompleteMe
* OmniSharpServer. See https://github.com/OmniSharp/omnisharp-server

### mono non-standard path

Note: if your installation of mono is in a non-standard location,
OmniSharpServer will not start. Ensure that it is in a standard location, or
change the paths in `OmniSharpServer/OmniSharp/Solution/CSharpProject.cs`

A patch will be submitted upstream to read paths from the environment.

## Running the tests

To run the full suite, just run `run_tests.py`. Options are:

* `--skip-build`: don't attempt to run the build `build.py`, e.g. if you use
a non-standard build environment (e.g. `cmake28`, self-build of clang, etc.)
* `--no-clang-completer`: don't attempt to test the clang completer. Can also
be set via environment variable `USE_CLANG_COMPLETER`.

Remaining arguments are passed to "nosetests" directly. This means that you 
can run a specific script or a specific test as follows:

* Specific test: `./run_tests.py ycmd/tests/<module_name>.py:<function name>`
* Specific script: `./run_tests.py ycmd.tests.<module_name>`

For example:

* `./run_tests.py ycmd/tests/subcommands_test.py:RunCompleterCommand_GetType_test`
* `./run_tests.py ycmd.tests.subcommands_test`

NOTE: you must have UTF8 support in your terminal when you do this, e.g.:

    > LANG=en_GB.utf8 ./run_tests.py --skip-build

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

### Some of the CsCompleter tests just hang

I think this is a timing issue of some sort because running the test suite
again appears to work.

