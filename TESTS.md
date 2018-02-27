# Running ycmd tests

This readme documents instructions on running the test suite.

An alternative (canonical) reference is the scripts used for running the tests
on [Travis][], [CircleCI][], and [AppVeyor][]. These can be found in
`.travis.yml`, `appveyor.yml`, and the `ci` and `.circleci` directories.

## Requirements for running the tests

You need to have installed all the requirements in `test_requirements.txt`. The
simplest way to set this up is to use a [virtualenv][], for example:

```sh
$ mkdir ~/YouCompleteMe/tests
$ virtualenv ~/YouCompleteMe/tests
$ source ~/YouCompleteMe/tests/bin/activate
$ pip install -r test_requirements.txt
```

You also need to have all of ycmd's completers' requirements. See the
installation guide for details, but typically this involves manually installing:

* [Mono][]
* [Go][]
* [Node.js and npm][npm-install]
* [TypeScript][]
* [rustup][]

If you are unwilling or unable to install the requirements for all of the
completers, you can exclude certain completers with the `--no-completer`
option.

### mono non-standard path

Note: if your installation of mono is in a non-standard location,
OmniSharpServer will not start. Ensure that it is in a standard location, or
change the paths in `OmniSharpServer/OmniSharp/Solution/CSharpProject.cs`

## Running the tests

To run the full suite, just run `run_tests.py`. Options are:

* `--skip-build`: don't attempt to run the `build.py` script. Useful once
  everything is built;
* `--no-completers`: do not build or test with listed semantic completion engine(s);
* `--completers`: only build and test with listed semantic completion engine(s);
* `--msvc`: the Microsoft Visual C++ version to build with (default: 15).
  Windows only;
* `--coverage`: generate code coverage data.

Remaining arguments are passed to "nosetests" directly. This means that you
can run a specific script or a specific test as follows:

* Specific script: `./run_tests.py ycmd/tests/<module_name>.py`
* Specific test: `./run_tests.py ycmd/tests/<module_name>.py:<function name>`

For example:

* `./run_tests.py ycmd/tests/subcommands_test.py`
* `./run_tests.py ycmd/tests/subcommands_test.py:Subcommands_Basic_test`

NOTE: you must have UTF-8 support in your terminal when you do this, e.g.:

```sh
LANG=en_GB.utf8 ./run_tests.py --skip-build
```

## Coverage testing

We can generate coverage data for both the C++ layer and the Python layer. The
CI system will pass this coverage data to [codecov.io][] where you can view
coverage after pushing a branch.

C++ coverage testing is available only on Linux/Mac and uses gcov.
Stricly speaking, we use the `-coverage` option to your compiler, which in the
case of GNU and LLVM compilers, generate gcov-compatible data.

For Python, there's a coverage module which works nicely with `nosetests`. This
is very useful for highlighting areas of your code which are not covered by the
automated integration tests.

Run it like this:

```sh
./run_tests.py --coverage
```

This will print a summary and generate HTML output in `./cover`.

More information: https://coverage.readthedocs.org and
https://nose.readthedocs.org/en/latest/plugins/cover.html

## Troubleshooting

### All the tests fail with some missing package.

Make sure you have installed all the packages in `test_requirements.txt` with
`pip install -r test_requirements.txt`.

### All the CsCompleter tests fail on unix.

Likely to be a problem with the OmniSharpServer.

* Check that you have compiled OmniSharpServer in `third-party/OmniSharpServer`
* Check that OmniSharpServer starts manually from `ycmd/tests/cs/testdata` with
  ```sh
  mono ../../../third_party/OmniSharpServer/OmniSharp/bin/Debug/OmniSharp.exe -s testy/testy.sln
  ```

### You get one or all of the following failures

    ERROR: ycmd.tests.cs.get_completions_test.GetCompletions_PathWithSpace_test
    FAIL: ycmd.tests.filename_completer_test.FilenameCompleter_test.SystemPathCompletion_test

Ensure that you have UTF-8 support in your environment (see above).

[travis]: https://travis-ci.org/Valloric/ycmd
[circleci]: https://circleci.com/gh/Valloric/ycmd
[appveyor]: https://ci.appveyor.com/project/Valloric/ycmd
[virtualenv]: https://packaging.python.org/guides/installing-using-pip-and-virtualenv/
[mono]: http://www.mono-project.com/download/stable/
[go]: https://golang.org/doc/install
[npm-install]: https://docs.npmjs.com/getting-started/installing-node
[typescript]: https://www.typescriptlang.org/#download-links
[rustup]: https://www.rustup.rs/
[codecov]: https://codecov.io/
