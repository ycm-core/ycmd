# Setting up for ycmd development

We use Vagrant for development. The VM will have **all** dependencies already
set up correctly so you won't have to do anything. (If you find something
missing, please file a bug.)

NOTE: The virtual machine that is created requires 3GB of RAM, so you likely
need at least 8GB of RAM to use this environment.

1. Install [Vagrant][].
2. `cd` into the folder where you checked out ycmd.
3. `$ vagrant up && vagrant ssh`. This will take a while because the VM is being
   built and set up. Only needs to happen once though.
4. You are now in the VM. Run the tests with `$ ./run_tests.py`.
5. Hack away. When done, exit the ssh connection with `exit`.
6. `$ vagrant suspend` so that you can quickly get back to hacking later.
7. Later on: `$ vagrant resume && vagrant ssh`. This will be _much_ faster.

That's it!

You can switch between Python versions with `pyenv global 2.6.6` and `pyenv
global 3.3.0`.

If you ever feel like you've screwed up the VM, just kill it with
`vagrant destroy` and then run `vagrant up` again to get to a clean state.

# Debugging the Python layer

There are a number of Python debuggers. Presented here are just a couple of
options known to work for certain developers on the ycmd project.

The options presented are:

- Using [`ipdb`][ipdb] (this is known not to work well on OS X).
- Using [pyclewn][] and attaching to the running Python process.

## Using `ipdb`

1. If you're not using vagrant, install `ipdb` (`pip install ipdb`).
2. At the point in the code you want to break, add the following lines:

```python
import ipdb; ipdb.set_trace()
```

3. Run the tests without `flake8`, e.g.

```sh
./run_tests.py --skip-build --no-flake8 ycmd/tests/get_completions_test.py
```

4. The test breaks at your code breakpoint and offers a command interface to
   debug.

See the `ipdb` docs for more info.

## Using `pyclewn` in Vim

The procedure is similar to using `ipdb` but you attach to the suspended process
and use Vim as a graphical debugger:

1. Install [pyclewna][pyclewn-install]

2. At the point you want to break, add the following lines:

```python
import clewn.vim as clewn; clewn.pdb()
```

3. Run the tests without `flake8`, e.g.

```sh
./run_tests.py --skip-build --no-flake8 ycmd/tests/get_completions_test.py
```

4. The tests will pause at the breakpoint. Now within Vim attach the debugger
   with `:Pyclewn pdb`. Hope that it works. It can be a bit flaky.

See the pyclewn docs for more info.

# Debugging the C++ layer (C++ Python library)

If you want to debug the c++ code using gdb (or your favourite graphical
debugger, e.g. [pyclewn][] in Vim), there are a few things you need to do:

1. Ensure your Python is built with debug enabled. In the vagrant system that's
   as simple as:

```sh
    vagrant up
    vagrant ssh
    export OPT='-g' # Ensure Python binary has debugging info
    export PYTHON_CONFIGURE_OPTS='--enable-shared --with-pydebug'
    pyenv install 2.7.11 # or whatever version
```

   On OS X, you need a working debugger. You can either use `lldb`
   which comes with XCode or `brew install gdb`. Note: If you use `gdb` from
   homebrew, then you need to sign the binary otherwise you can't debug
   anything. See later steps for a link.

2. Build ycm_core library with debugging information (and link against debug
   Python):

```sh
    pyenv shell 2.7.11
    ./build.py --all --enable-debug
```

3. Enable debugging in the OS. On Linux (Ubuntu at least, which is what all of
   our tests are run on), you must set the following sysctl parameter (you can
   make it permanent if you like by adding it to `/etc/sysctl.conf` or via any
   other appropriate mechanism):

```sh
     sudo sysctl kernel.yama.ptrace_scope=0
```

   On OS X it is more fiddly:
     - The binary must be signed. See
       https://sourceware.org/gdb/wiki/BuildingOnDarwin
     - You *can not* debug system Python. Again: you *must* use a Python that is
       *not* the one provided by Apple. Use pyenv. That is the rule.
       Don't argue.

  Don't ask why. It's for security.

3. Here you have choices: either use a Python debugger to break the tests, or
   manually use Vim to simulate the scenario you want to debug. In any case, you
   will need the PID of the running Python process hosting ycmd to attach to.
   Getting this is left as an exercise, but one approach is to simply
   install vim with `apt-get install vim` and to get a copy of YouCompleteMe
   into `$HOME/.vim/bundle` and symlink `/vargant` as
   `$HOME/.vim/bundle/third_party/ycmd`. Anyway, once you have the PID you can
   simply attach to the Python process, for example:

   - `:YcmDebugInfo` to get the pid
   - `gdb: attach <PID>`
   - `break YouCompleteMe::FilterAndSortCandidates`


[vagrant]: https://www.vagrantup.com/
[pyclewn]: http://pyclewn.sourceforge.net
[pyclewn-install]: http://pyclewn.sourceforge.net/install.html
[ipdb]: https://pypi.python.org/pypi/ipdb
