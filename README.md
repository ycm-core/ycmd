ycmd: a code-completion & comprehension server
==============================================

[![Build Status](https://travis-ci.org/Valloric/ycmd.svg?branch=master)](https://travis-ci.org/Valloric/ycmd)
[![Build status](https://ci.appveyor.com/api/projects/status/6fetp5xwb0kkuv2w/branch/master?svg=true)](https://ci.appveyor.com/project/Valloric/ycmd)

ycmd is a server that provides APIs for code-completion and other
code-comprehension use-cases like semantic GoTo commands (and others). For
certain filetypes, ycmd can also provide diagnostic errors and warnings.

ycmd was originally part of [YouCompleteMe][ycm]'s codebase, but has been split
out into a separate project so that it can be used in editors other than Vim.

The best way to learn how to interact with ycmd is by reading through (and
running) the [`example_client.py`][example-client] file. See the [README for the
examples][example-readme] folder for details on how to run the example client.

Known ycmd clients:
------------------

- [YouCompleteMe][ycm]: Vim client, stable and exposes all ycmd features.
- [emacs-ycmd][]: Emacs client, still a bit experimental.
- [you-complete-me][atom-you-complete-me]: Atom client.
- [kak-ycmd][]: Kakoune client.

Feel free to send a pull request adding a link to your client here if you've
built one.

Building
--------

[Clients commonly build and set up ycmd for you; you are unlikely to need to
build ycmd yourself unless you want to build a new client.]

This is all for Ubuntu Linux. Details on getting ycmd running on other OS's can be
found in [YCM's instructions][ycm-install] (ignore the Vim-specific parts).

First, install the dependencies:
```
sudo apt-get install build-essential cmake python-dev
```

When you first clone the repository you'll need to update the submodules:
```
git submodule update --init --recursive
```

Then run `./build.py --clang-completer --omnisharp-completer --gocode-completer`.
This should get you going.

For more detailed instructions on building ycmd, see [YCM's
instructions][ycm-install] (ignore the Vim-specific parts).

API notes
---------

- All strings going into and out of the server are UTF-8 encoded.
- All line and column numbers are 1-based, not 0-based. They are also byte
  offsets, _not_ Unicode codepoint offsets.
- All file paths are full, absolute paths.
- All requests to the server _must_ include an [HMAC][] in the `x-ycm-hmac` HTTP
  header. The HMAC is computed from the shared secret passed to the server on
  startup and the request/response body. The digest algorithm is SHA-256. The
  server will also include the HMAC in its responses; you _must_ verify it
  before using the response. See [`example_client.py`][example-client] to see how it's done.

How ycmd works
--------------

There are several completion engines in ycmd. The most basic one is an
identifier-based completer that collects all of the identifiers in the file
provided in the completion request, other files of the same filetype that were
provided previously and any tags files produced by ctags. This engine is
non-semantic.

There are also several semantic engines in YCM. There's a libclang-based
completer that provides semantic completion for C-family languages.  There's also a
Jedi-based completer for semantic completion for Python, an OmniSharp-based
completer for C#, a [Gocode][gocode]-based completer for Go, and a TSServer-based
completer for TypeScript. More will be added with time.

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


Backwards compatibility
-----------------------

ycmd's HTTP+JSON interface follows [SemVer][]. While ycmd has seen extensive use
over the last several months as part of YCM, the version number is below 1.0
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

Contact
-------

If you have questions about the plugin or need help, please use the
[ycmd-users][] mailing list.

The author's homepage is <http://val.markovic.io>.

License
-------

This software is licensed under the [GPL v3 license][gpl].
© 2015 ycmd contributors

[ycmd-users]: https://groups.google.com/forum/?hl=en#!forum/ycm-users
[ycm]: http://valloric.github.io/YouCompleteMe/
[atom-you-complete-me]: https://atom.io/packages/you-complete-me
[semver]: http://semver.org/
[hmac]: http://en.wikipedia.org/wiki/Hash-based_message_authentication_code
[exploit]: https://groups.google.com/d/topic/ycm-users/NZAPrvaYgxo/discussion
[example-client]: https://github.com/Valloric/ycmd/blob/master/examples/example_client.py
[example-readme]: https://github.com/Valloric/ycmd/blob/master/examples/README.md
[trigger-defaults]: https://github.com/Valloric/ycmd/blob/master/ycmd/completers/completer_utils.py#L143
[subsequence]: http://en.wikipedia.org/wiki/Subsequence
[ycm-install]: https://github.com/Valloric/YouCompleteMe/blob/master/README.md#mac-os-x-super-quick-installation
[def-settings]: https://github.com/Valloric/ycmd/blob/master/ycmd/default_settings.json
[base64]: http://en.wikipedia.org/wiki/Base64
[mkstemp]: http://man7.org/linux/man-pages/man3/mkstemp.3.html
[options]: https://github.com/Valloric/YouCompleteMe#options
[extra-conf-doc]: https://github.com/Valloric/YouCompleteMe#c-family-semantic-completion-engine-usage
[emacs-ycmd]: https://github.com/abingham/emacs-ycmd
[gpl]: http://www.gnu.org/copyleft/gpl.html
[gocode]: https://github.com/nsf/gocode
[kak-ycmd]: https://github.com/mawww/kak-ycmd
