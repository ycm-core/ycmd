ycmd: a code-completion & comprehension server
==============================================

[![Build status](https://dev.azure.com/YouCompleteMe/YCM/_apis/build/status/ycm-core.ycmd?branchName=master)](https://dev.azure.com/YouCompleteMe/YCM/_build/latest?definitionId=4&branchName=master)
[![Coverage status](https://img.shields.io/codecov/c/github/ycm-core/ycmd/master.svg)](https://codecov.io/gh/ycm-core/ycmd)

ycmd is a server that provides APIs for code-completion and other
code-comprehension use-cases like semantic GoTo commands (and others). For
certain filetypes, ycmd can also provide diagnostic errors and warnings.

ycmd was originally part of [YouCompleteMe][ycm]'s codebase, but has been split
out into a separate project so that it can be used in editors other than Vim.

Check [the API documentation][api-docs] if you want to implement a client. A
good way to learn how to interact with ycmd is by reading through (and running)
the [`example_client.py`][example-client] file. See the [README for the
examples][example-readme] folder for details on how to run the example client.

Known ycmd clients:
------------------

- [YouCompleteMe][ycm]: Vim client, stable and exposes all ycmd features.
- [emacs-ycmd][]: Emacs client.
- [you-complete-me][atom-you-complete-me]: Atom client.
- [YcmdCompletion][sublime-ycmd-completion]: Sublime client
- [sublime-ycmd][sublime-ycmd]: Sublime Text 3 client.
- [kak-ycmd][]: Kakoune client.
- [you-complete-me][vscode-you-complete-me]: VSCode client.
- [gycm][]: Geany client.
- [nano-ycmd][]: GNU nano client.

Feel free to send a pull request adding a link to your client here if you've
built one.

Building
--------
**If you're looking to develop ycmd, see the [instructions for running the
tests][test-setup].**

This is all for Ubuntu Linux. Details on getting ycmd running on other OS's can
be found in [YCM's instructions][ycm-install] (ignore the Vim-specific parts).
Note that **ycmd runs on Python 3.8.0+.**

First, install the minimal dependencies:
```
sudo apt install build-essential cmake python3-dev
```

Next, install the language specific dependencies you need:
- `sudo apt install golang-go` for Go.
- `sudo apt install npm` for JavaScript and TypeScript.
- `sudo apt install mono-devel` for C#.
- `sudo apt install openjdk-8-jre` for Java.

When you first clone the repository you'll need to update the submodules:
```
git submodule update --init --recursive
```

Then run `python3 build.py --all` or any of the specific completers listed by
`python3 build.py --help`. This should get you going.

For more detailed instructions on building ycmd, see [YCM's
instructions][ycm-install] (ignore the Vim-specific parts).

Supported compilers
-------------------

- GCC 8 and later
- Clang 7 and later
- Microsoft Visual Studio 2017 v 15.7 and later

API notes
---------

- All strings going into and out of the server are UTF-8 encoded.
- All lines end with `\n`.
- All line and column numbers are 1-based, not 0-based. They are also byte
  offsets, _not_ Unicode codepoint offsets.
- All file paths are full, absolute paths.
- All requests to the server _must_ include an [HMAC][] in the `x-ycm-hmac` HTTP
  header. The HMAC is computed from the shared secret passed to the server on
  startup and the request/response body. The digest algorithm is SHA-256. The
  server will also include the HMAC in its responses; you _must_ verify it
  before using the response. See [`example_client.py`][example-client] to see
  how it's done.
- API is documented in swagger and published on [the website][api-docs].

How ycmd works
--------------

There are several completion engines in ycmd. The most basic one is an
identifier-based completer that collects all of the identifiers in the file
provided in the completion request, other files of the same filetype that were
provided previously and any tags files produced by ctags. This engine is
non-semantic.

There are also several semantic engines in YCM. There's [clangd][clangd]-based
completer that both provide semantic completion for C-family languages.
There's also a Jedi-based completer for semantic completion for Python, an
OmniSharp-based completer for C#, a [gopls][gopls]-based completer for Go
(using [gopls][gopls] for jumping to definitions), a TSServer-based completer
for JavaScript and TypeScript, a [jdt.ls][jdtls]-based server for Java, and a
[RLS][]-based completer for Rust.  More will be added with time.


There are also other completion engines, like the filepath completer (part of
the identifier completer).

The server will automatically detect which completion engine would be the best
in any situation. On occasion, it queries several of them at once, merges the
outputs and presents the results.

Semantic engines are triggered only after semantic "triggers" are inserted in
the code. If the request received shows that the user's cursor is after the last
character in `string foo; foo.` in a C# file, this would trigger the semantic
engine to
examine members of `foo` because `.` is a [default semantic
trigger][trigger-defaults] for C# (triggers can be changed dynamically). If the
text were `string foo; foo.zoo`, semantic completion would still be triggered
(the trigger is behind the `zoo` word the user is typing) and the results would
be filtered with the `zoo` query.

Semantic completion can also be forced by setting `force_semantic: true` in
the JSON data for the completion request, _but you should only do this if the
user explicitly requested semantic completion with a keyboard shortcut_;
otherwise, leave it up to ycmd to decide when to use which engine.

The reason why semantic completion isn't always used even when available is
because the semantic engines can be slow and because most of the time, the
user doesn't actually need semantic completion.

There are two main use-cases for code-completion:

1. The user knows which name they're looking for, they just don't want to type
   the whole name.
2. The user either doesn't know the name they need or isn't sure what the name
   is. This is also known as the "API exploration" use-case.

The first use case is the most common one and is trivially addressed with the
identifier completion engine (which BTW is blazing fast). The second one needs
semantic completion.

### Completion string filtering

A critical thing to note is that the completion **filtering is NOT based on
the input being a string prefix of the completion** (but that works too). The
input needs to be a _[subsequence][] match_ of a completion. This is a fancy way
of saying that any input characters need to be present in a completion string in
the order in which they appear in the input. So `abc` is a subsequence of
`xaybgc`, but not of `xbyxaxxc`.

### Completion string ranking

The subsequence filter removes any completions that do not match the input, but
then the sorting system kicks in. It's a bit involved, but roughly speaking
"word boundary" (WB) subsequence character matches are "worth" more than non-WB
matches. In effect, this means given an input of "gua", the completion
"getUserAccount" would be ranked higher in the list than the "Fooguxa"
completion (both of which are subsequence matches). A word-boundary character
are all capital characters, characters preceded by an underscore and the first
letter character in the completion string.

### Auto-shutdown if no requests for a while

If the server hasn't received any requests for a while (controlled by the
`--idle_suicide_seconds` ycmd flag), it will shut itself down. This is useful
for cases where the process that started ycmd dies without telling ycmd to die
too or if ycmd hangs (this should be extremely rare).

If you're implementing a client for ycmd, ensure that you have some sort of
keep-alive background thread that periodically pings ycmd (just call the
`/healthy` handler, although any handler will do).

You can also turn this off by passing `--idle_suicide_seconds=0`, although that
isn't recommended.

### Exit codes

During startup, ycmd attempts to load the `ycm_core` library and exits with one
of the following return codes if unsuccessful:

- 3: unexpected error while loading the library;
- 4: the `ycm_core` library is missing;
- 7: the version of the `ycm_core` library is outdated.
- 8: server is started with python; recompile with python3.

User-level customization
-----------------------

You can provide settings to ycmd on server startup. There's a
[`default_settings.json`][def-settings] file that you can tweak. See the
[_Options_ section in YCM's _User Guide_][options] for a description on what
each option does. Pass the path to the modified settings file to ycmd as an
`--options_file=/path/to/file` flag.  Note that you must set the `hmac_secret`
setting (encode the value with [base64][]). Because the file you are passing
contains a secret token, ensure that you are creating the temporary file in a
secure way (the [`mkstemp()`][mkstemp] Linux system call is a good idea; use
something similar for other OS's).

After it starts up, ycmd will _delete_ the settings file you provided after
it reads it.

The settings file is something your editor should produce based on values your
user has configured. There's also an extra file (`.ycm_extra_conf.py`) your user
is supposed to provide to configure certain semantic completers. More
information on it can also be found in the [corresponding section of YCM's _User
Guide_][extra-conf-doc].

### `.ycm_extra_conf.py` specification

The `.ycm_extra_conf.py` module may define the following functions:

#### `Settings( **kwargs )`

This function allows users to configure the language completers on a per project
basis or globally. Currently, it is required by the libclang-based completer and
optional for other completers. The following arguments can be retrieved from
the `kwargs` dictionary and are common to all completers:

- `language`: an identifier of the completer that called the function. Its value
  is `python` for the Python completer and `cfamily` for the C-family completer.
  This argument is useful to configure several completers at once. For
  instance:

  ```python
  def Settings( **kwargs ):
    language = kwargs[ 'language' ]
    if language == 'cfamily':
      return {
        # Settings for the libclang and clangd-based completer.
      }
    if language == 'python':
      return {
        # Settings for the Python completer.
      }
    return {}
  ```

- `filename`: absolute path of the file currently edited.

- `client_data`: any additional data supplied by the client application.
  See the [YouCompleteMe documentation][extra-conf-vim-data-doc] for an
  example.

The return value is a dictionary whose content depends on the completer.

#### LSP based completers

LSP servers often support user configuration via the initialise request. These
are usually presented as options in the UI. Ycmd supports this using the
`.ycm_extra_conf.py` by allowing the user to specify the exact dictionary of
settings that are passed in the server initialise message. These options are
returned from `Settings` under the `ls` key. The python dictionary is converted
to json and included verbatim in the LSP initialize request. In order to
determine the set of options for a server, consult the server's documentation or
`package.json` file.
A `config_sections` object is a dictionary whose keys are "sections" and values
are pieces of settings (usually found in the `ls` object) corresponding to
those sections. This is even more underspecified and requires trial and error
to make it work. It is optional and only useful if you explicitly enable
`workspace/configuration` support.

Example of LSP configuration:
```python
def Settings( **kwargs ):
  if kwargs[ 'language' ] == 'java':
    return { 'ls': { 'java.rename.enabled' : False },
             # `config_sections` is not used for java...
             'config_sections': { 'section0': {} }
```

In addition, ycmd can use any language server, given a file type and a command
line. A user option `language_server` can be used to plug in a LSP server ycmd
wouldn't usually know about. The value is a list of dictionaries containing:

- `name`: the string representing the name of the server
- `cmdline`: the list representing the command line to execute the server
  (optional; mandatory if port not specified)
- `port`: optional. If specified, a TCP connection is used to this port. If set
  to `*`, an unused locall port is selected and made availble in the `cmdline`
  as `${port}` (see below examples).
- `filetypes`: list of supported filetypes.
- `project_root_files`: Tells ycmd which files indicate project root.
- `capabilities'`: Overrides the default LSP capabilities of ycmd.
  - If you enable `workspace/configuration` support, check the extra conf
    details, relevant to LSP servers.
- `additional_workspace_dirs`: Specifies statically known workspaces that should
  be open on LSP server startup.
- `triggerCharacters`: Override the LSP server's trigger characters for
  completion. This can be useful when the server obnoxiously requests completion
  on every character or for example on whitespace characters.

```json
{
  "language_server": [ {
    "name": "gopls",
    "cmdline": [ "/path/to/gopls", "-rpc.trace" ],
    "filetypes": [ "go" ],
    "project_root_files": [ "go.mod" ],
    "triggerCharacters": [ "." ]
  } ]
}
```

Or, to use a TCP connection:

```json
{
  "language_server": [ {
    "name": "godot",
    "port": "6008",
    "filetypes": [ "gdscript" ]
  } ]
}
```

Or, to use an unused  local port, set `port` to `*` and use `${port}` in the
`cmdline`:

```json
{
  "language_server": [ {
    "name": "someserver",
    "cmdline": [ "/path/to/some/server", "--port", "${port}" ],
    "port": "*",
    "filetypes": [ "somethign" ],
    "project_root_files": [ "somethingfile" ]
  } ]
}
```


When plugging in a completer in this way, the `kwargs[ 'language' ]` will be set
to the value of the `name` key, i.e. `gopls` in the above example.

A number of LSP completers are currently supported without `language_server`,
usch as:

- Java
- Rust
- Go
- C-family

One can also override the root directory, with `project_directory`.

```python
def Settings( **kwargs ):
  return { 'project_directory': 'src/' } # The path may be absolute as well.
```

Note: If an LSP based completer is configured for a language that's supported
"built-in", it overrides the built-in support.

##### C-family settings

The `Settings` function is called by the libclang and clangd-based completers to
get the compiler flags to use when compiling the current file. The absolute path
of this file is accessible under the `filename` key of the `kwargs` dictionary.

The return value expected by both completers is a dictionary containing the
following items:

- `flags`: (mandatory for libclang, optional for clangd) a list of compiler
  flags.

- `include_paths_relative_to_dir`: (optional) the directory to which the include
  paths in the list of flags are relative. Defaults to ycmd working directory
  for the libclang completer and `.ycm_extra_conf.py`'s directory for the
  clangd completer.

- `do_cache`: (optional) a boolean indicating whether or not the result of
  this call (i.e. the list of flags) should be cached for this file name.
  Defaults to `True`. If unsure, the default is almost always correct.

The libclang-based completer also supports the following items:

- `override_filename`: (optional) a string indicating the name of the file to
  parse as the translation unit for the supplied file name. This fairly advanced
  feature allows for projects that use a 'unity'-style build, or for header
  files which depend on other includes in other files.

- `flags_ready`: (optional) a boolean indicating that the flags should be
  used. Defaults to `True`. If unsure, the default is almost always correct.

A minimal example which simply returns a list of flags is:

```python
def Settings( **kwargs ):
  return {
    'flags': [ '-x', 'c++' ]
  }
```

##### Formatting settings

The configuration for `Format` subcommand can be specified with an extra conf for
[the java subserver][jdtls] and for the typescript subserver.
The formatter options can be found below:

- [Java configuration][jdt-formatter]
- [TSServer configuration][ts-formatter],

These servers support custom formatting options to be supplied in a different
way than the rest.  For this purpose the `Settings` function can return a
`formatter` property.

An example of the formatter configuration would be:

```python
def Settings( **kwargs ):
  return {
    'formatting_options': {
       'org.eclipse.jdt.core.formatter.lineSplit': 30, 
    }
  }
```

##### Python settings

The `Settings` function allows users to specify the Python interpreter and
the `sys.path` used by the completer to provide completion and code
comprehension. No additional arguments are passed.

The return value expected by the completer is a dictionary containing the
following items:

- `interpreter_path`: (optional) path to the Python interpreter. `~` and
  environment variables in the path are expanded. If not an absolute path, it
  will be searched through the `PATH`.

- `sys_path`: (optional) list of paths prepended to `sys.path`.

Usage example:

```python
def Settings( **kwargs ):
  return {
    'interpreter_path': '~/project/virtual_env/bin/python',
    'sys_path': [ '~/project/third_party/module' ]
  }
```

#### `PythonSysPath( **kwargs )`

Optional for Python support.

This function allows further customization of the Python path `sys.path`. Its
parameters are the possible items returned by the `Settings` function for the
Python completer:

- `interpreter_path`: path to the Python interpreter.

- `sys_path`: list of Python paths from `sys.path`.

The return value should be the modified list of Python paths.

See [ycmd's own `.ycm_extra_conf.py`][ycmd-extra-conf] for an example.

### Global extra conf file specification

The global extra module must expose the same functions as the
`.ycm_extra_conf.py` module with the following additions:

#### `YcmCorePreLoad()`

Optional.

This method, if defined, is called by the server prior to importing the c++
python plugin. It is not usually required and its use is for advanced users
only.

#### `Shutdown()`

Optional.

Called prior to the server exiting cleanly. It is not usually required and its
use is for advanced users only.

Backwards compatibility
-----------------------

ycmd's HTTP+JSON interface follows [SemVer][]. While ycmd has seen extensive use
over the last several years as part of YCM, the version number is below 1.0
because some parts of the API _might_ change slightly as people discover
possible problems integrating ycmd with other editors. In other words, the
current API might unintentionally be Vim-specific. We don't want that.

Note that ycmd's internal API's (i.e. anything other than HTTP+JSON) are **NOT**
covered by SemVer and _will_ randomly change underneath you. **DON'T** interact
with the Python/C++/etc code directly!

FAQ
---

### Is HMAC auth for requests/responses really necessary?

Without the HMAC auth, it's possible for a malicious website to impersonate the
user. Don't forget that evil.com can send requests to servers listening on
localhost if the user visits evil.com in a browser.

**This is not merely a theoretical concern**; a working proof-of-concept remote
code execution exploit [was created][exploit] for ycmd running on localhost. The
HMAC auth was added to block this attack vector.


Contributor Code of Conduct
---------------------------

Please note that this project is released with a [Contributor Code of
Conduct][ccoc]. By participating in this project you agree to abide by its
terms.

Contact
-------

If you have questions about the plugin or need help, please use the
[ycmd-users][] mailing list.

The author's homepage is <http://val.markovic.io>.

License
-------

This software is licensed under the [GPL v3 license][gpl].
© 2015-2019 ycmd contributors

[ycmd-users]: https://groups.google.com/forum/?hl=en#!forum/ycmd-users
[ycm]: http://ycm-core.github.io/YouCompleteMe/
[atom-you-complete-me]: https://atom.io/packages/you-complete-me
[sublime-ycmd-completion]: https://packagecontrol.io/packages/YcmdCompletion
[sublime-ycmd]: https://packagecontrol.io/packages/YouCompleteMe
[semver]: http://semver.org/
[hmac]: http://en.wikipedia.org/wiki/Hash-based_message_authentication_code
[exploit]: https://groups.google.com/d/topic/ycm-users/NZAPrvaYgxo/discussion
[example-client]: https://github.com/ycm-core/ycmd/blob/master/examples/example_client.py
[example-readme]: https://github.com/ycm-core/ycmd/blob/master/examples/README.md
[trigger-defaults]: https://github.com/ycm-core/ycmd/blob/master/ycmd/completers/completer_utils.py#L143
[subsequence]: http://en.wikipedia.org/wiki/Subsequence
[ycm-install]: https://github.com/ycm-core/YouCompleteMe/blob/master/README.md#mac-os-x
[def-settings]: https://github.com/ycm-core/ycmd/blob/master/ycmd/default_settings.json
[base64]: http://en.wikipedia.org/wiki/Base64
[mkstemp]: http://man7.org/linux/man-pages/man3/mkstemp.3.html
[options]: https://github.com/ycm-core/YouCompleteMe#options
[extra-conf-doc]: https://github.com/ycm-core/YouCompleteMe#c-family-semantic-completion
[emacs-ycmd]: https://github.com/abingham/emacs-ycmd
[gpl]: http://www.gnu.org/copyleft/gpl.html
[kak-ycmd]: https://github.com/mawww/kak-ycmd
[ccoc]: https://github.com/ycm-core/ycmd/blob/master/CODE_OF_CONDUCT.md
[dev-setup]: https://github.com/ycm-core/ycmd/blob/master/DEV_SETUP.md
[test-setup]: https://github.com/ycm-core/ycmd/blob/master/TESTS.md
[extra-conf-vim-data-doc]: https://github.com/ycm-core/YouCompleteMe#the-gycm_extra_conf_vim_data-option
[vscode-you-complete-me]: https://marketplace.visualstudio.com/items?itemName=RichardHe.you-complete-me
[gycm]: https://github.com/jakeanq/gycm
[nano-ycmd]: https://github.com/orsonteodoro/nano-ycmd
[jdtls]: https://github.com/eclipse/eclipse.jdt.ls
[jdt-formatter]: https://github.com/eclipse/eclipse.jdt.ls/blob/master/org.eclipse.jdt.ls.core/.settings/org.eclipse.jdt.core.prefs
[ts-formatter]: https://github.com/Microsoft/TypeScript/blob/master/lib/protocol.d.ts#L2384-L2421
[api-docs]: https://ycm-core.github.io/ycmd/
[ycmd-extra-conf]: https://github.com/ycm-core/ycmd/blob/master/.ycm_extra_conf.py
[clangd]: https://clang.llvm.org/extra/clangd.html
[gopls]: https://github.com/golang/tools/
[RLS]: https://github.com/rust-lang-nursery/rls
