ycmd: a code-completion & comprehension server
==============================================

ycmd is a server that provides APIs for code-completion and other
code-comprehension use-cases like semantic GoTo commands (and others). For
certain filetypes, ycmd can also provide diagnostic errors and warnings.

ycmd was originally part of [YouCompleteMe][ycm]'s codebase, but has been split
out into a separate project so that it can be used in editors other than Vim.

The best way to learn how to interact with ycmd is by reading through the
`example_client.py` file _[NOTE: Which I haven't yet written]_.

API notes
---------

- All strings going into and out of the server are UTF-8 encoded.
- All line and column numbers are 1-based, not 0-based.
- All requests to the server _must_ include an [HMAC][] in the `x-ycm-hmac` HTTP
  header. The HMAC is computed from the shared secret passed to the server on
  startup and the request/response body. The digest algorithm is SHA-256. The
  server will also include the HMAC in its responses; you _must_ verify it
  before using the response. See `example_client.py` to see how it's done.

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

**This is not a theoretical concern**; a working proof-of-concept remote code
execution exploit [was created][exploit] for ycmd running on localhost. The HMAC
auth was added to block this attack vector.

Contact
-------

If you have questions about the plugin or need help, please use the
[ycmd-users][] mailing list.

The author's homepage is <http://val.markovic.io>.

Project Management
------------------

This open-source project is run by me, Strahinja Val Markovic. I also happen to
work for Google and the code I write here is under Google copyright (for the
sake of simplicity and other reasons). This does **NOT** mean that this is an
official Google product (it isn't) or that Google has (or wants to have)
anything to do with it.

License
-------

This software is licensed under the [GPL v3 license][gpl].
© 2014 Google Inc.

[ycmd-users]: https://groups.google.com/forum/?hl=en#!forum/ycm-users
[ycm]: http://valloric.github.io/YouCompleteMe/
[semver]: http://semver.org/
[hmac]: http://en.wikipedia.org/wiki/Hash-based_message_authentication_code
[exploit]: https://groups.google.com/d/topic/ycm-users/NZAPrvaYgxo/discussion
