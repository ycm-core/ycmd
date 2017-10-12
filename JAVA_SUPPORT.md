This document briefly describes the work done to support Java (and other
Language Server Protocol-based completion engines). 

# Overview

The [original PR][PR] implemented native support in ycmd for the Java language,
based on [jdt.ls][]. In summary, the following key features were added:

* Installation of jdt.ls (built from source with `build.py`)
* Management of the jdt.ls server instance, projects etc.
* A generic (ish) implementation of a [Language Server Protocol][lsp] client so
  far as is required for jdt.ls (easily extensible to other engines)
* Support for the following Java semantic engine features:
  * Semantic code completion, including automatic imports
  * As-you-type diagnostics
  * GoTo including GoToReferences
  * FixIt
  * RefactorRename
  * GetType
  * GetDoc

See the [trello board][trello] for a more complete picture.

## Overall design/goals

Key goals:

1. Support Java in ycmd and YCM; make it good enough to replace eclim and
   javacomplete2 for most people
2. Make it possible/easy to support other [lsp][] servers in future (but, don't
   suffer from yagni); prove that this works.

An overview of the objects involved can be seen on [this
card][design]. In short:

* 2 classes implement the language server protocol in the
  `language_server_completer.py` module:
 * `LanguageServerConnection` - an abstraction of the comminication with the
   server, which may be over stdio or any number of TCP/IP ports (or a domain
   socket, etc.). Only a single implementation is included (stdio), but
   [implementations for TCP/IP](https://github.com/puremourning/ycmd-1/commit/f3cd06245692b05031a64745054326273d52d12f)
   were written originally and dropped in favour of stdio's simplicity.
 * `LanguageServerCompleter` - an abstract base for any completer based on LSP,
   which implements as much standard functionality as possible including
   completions, diagnostics, goto, fixit, rename, etc.
* The `java_completer` itself implements the `LanguageServerCompleter`, boots
  the jdt.ls server, and instantiates a `LanguageServerConnection` for
  communication with jdt.ls.

The overall plan and some general discussion around the project can be found on
the [trello board][trello] I used for development.

## Threads, and why we need them

LSP is by its nature an asyncronous protocol. There are request-reply like
`requests` and unsolicited `notifications`. Receipt of the latter is mandatory,
so we cannot rely on their being a `bottle` thread executing a client request.

So we need a message pump and despatch thread. This is actually the
`LanguageServerConnection`, which implements `thread`. It's main method simply
listens on the socket/stream and despatches complete messages to the
`LanguageServerCompleter`. It does this:

* For `requests`: similarly to the TypeScript completer, using python `event`
  objects, wrapped in our `Response` class
* For `notifications`: via a synchronised `queue`. More on this later.

A representation of this is on the "Requests and notifications" page
of the [design][], including a rough sketch of the thread interaction.

### Some handling is done in the message pump.

While it is perhaps regrettable to do general processing directly in the message
pump, there are certain notifications which we have to handle immediately when
we get them, such as:

* Initialisation messages
* Diagnostics

In these cases, we allow some code to be executed inline within the message pump
thread, as there is no other thread guaranteed to execute. These are handled by
callback functions and state is protected mutexes.

## Startup sequence

See the 'initialisation sequence' tab on the [design][] for a bit of background.

In standard LSP, the initialisation sequence consists of an initialise
request-reply, followed by us sending the server an initialised notification. We
must not send any other requests until this has completed.

An additional wrinkle is that jdt.ls, being based on eclipse has a whole other
initialisation sequence during which time it is not fully functional, so we have
to determine when that has completed too. This is done by jdt.ls-specific
messages and controls the `ServerIsReady` response.

In order for none of these shenanigans to block the user, we must do them all
asynchronously, effectively in the message pump thread. In addition, we must
queue up any file contents changes during this period to ensure the server is up
to date when we start processing requests proper.

This is unfortunately complicated, but there were early issues with really bad
UI blocking that we just had to get rid of.

## Completion

Language server protocol requires that the client can apply textEdits,
rather than just simple text. This is not an optional feature, but ycmd
clients do not have this ability.

The protocol, however, restricts that the edit must include the original
requested completion position, so we can perform some simple text
manipulation to apply the edit to the current line and determine the
completion start column based on that.

In particular, the jdt.ls server returns textEdits that replace the
entered text for import completions, which is one of the most useful
completions.

We do this super inefficiently by attempting to normalise the TextEdits
into insertion_texts with the same start_codepoint. This is necessary
particularly due to the way that eclipse returns import completions for
packages.

We also include support for "additionalTextEdits" which
allow automatic insertion of, e.g.,  import statements when selecting
completion items. These are sent on the completion response as an
additional completer data item called 'fixits'. The client applies the
same logic as a standard FixIt once the selected completion item is
inserted.

## Diagnostics

Diagnostics in LSP are delivered asynchronously via `notifications`. Normally,
we would use the `OnFileReadyToParse` response to supply diagnostics, but due to
the lag between refreshing files and receiving diagnostics, this leads to a
horrible user experience where the diagnostics always lag one edit behind.

To resolve this, we use the long-polling mechanism added here (`ReceiveMessages`
request) to return diagnostics to the client asynchronously.

We deliver asynchronous diagnostics to the client in the same way that the
language server does, i.e. per-file. The client then fans them out or does
whatever makes sense for the client. This is necessary because it isn't possible
to know when we have received all diagnostics, and combining them into a single
message was becoming clunky and error prone.

In order to be relatively compatible with other clients, we also return
diagnostics on the file-ready-to-parse event, even though they might be
out of date wrt the code. The client is responsible for ignoring these
diagnostics when it handles the asynchronously delivered ones. This requires
that we hold the "latest" diagnostics for a file. As it turns out, this is also
required for FixIts.

## Projects

jdt.ls is based on eclipse. It is in fact an eclipse plugin. So it requires an
eclipse workspace. We try and hide this by creating an ad-hoc workspace for each
ycmd instance. This prevents the possibility of multiple "eclipse"  instances
using the same workspace, but can lead to unreasonable startup times for large
projects.

The jdt.ls team strongly suggest that we should re-use a workspace based on the
hash of the "project directory" (essentially the dir containing the project
file: `.project`, `pom.xml` or `build.gradle`). They also say, however, that
eclipse frequently corrupts its workspace.

So we have a hidden switch to re-use a workspace as the jdt.ls devs suggest. In
testing at work, this was _mandatory_ due to a slow SAN, but at home, startup
time is not an issue, even for large projects. I think we'll just have to see
how things go to decide which one we want to keep.

## Subcommands

### GetDoc/GetType

There is no GetType in LSP. There's only "hover". The hover response is
hilariously server-specific, so in the base `LanguageServerCompleter` we just
provide the ability to get the `hover` response and `JavaCompleter` extracts the
appropriate info from there. Thanks to @bstaletic for this!

### FixIt

FixIts are implemented as code actions, and require the diagnostic they relate
to to be send from us to the server, rather than just a position. We use the
stored diags and find the nearest one based on the `request_data`.

What's worse is that the LSP provides _no documentation_ for what the "Code
action" response should be, and it is 100% implementation-specific. They just
have this `command` abstraction which is basically "do a thing".

From what I've seen, most servers just end up with either a `WorkspaceEdit` or a
series of `TextEdits`, which is fine for us as that's what ycmd's protocol looks
like.

The solution is that we have a callback into the `JavaCompleter`  to handle the
(custom) `java.apply.workspaceEdit` "command".

### GoToReferences

Annoyingly, jdt.ls sometimes returns references to .class files within jar
archives using a custom `jdt://` protocol. We can't handle that, so we have to
dodge and weave so that we don't crash.

### Stopping the server

Much like the initialisation sequence, the LSP shutdown sequence is a bit
fiddly. 2 things are required:

1. A `shutdown` request-reply. The server tides up and _prepares to die!_
2. An `exit` notification. We tell the server to die.

This isn't so bad, but jdt.ls is buggy and actually dies without responding to
the `shutdown` request. So we have a bunch of code to handle that and to ensure
that the server dies eventually, as it had a habbit of getting stuck running,
particularly if we threw an exception.

[PR]: https://github.com/valloric/ycmd/pull/857
[jdt.ls]: https://github.com/eclipse/eclipse.jdt.ls
[lsp]: https://github.com/Microsoft/language-server-protocol/
[eclim]: http://eclim.org
[javacomplete2]: https://github.com/artur-shaik/vim-javacomplete2
[vscode-javac]: https://github.com/georgewfraser/vscode-javac
[VSCode]: https://code.visualstudio.com
[destign]: https://trello.com/c/78IkFBzp
[trello]: https://trello.com/b/Y6z8xag8/ycm-java-language-server
[client]: https://github.com/puremourning/YouCompleteMe/tree/language-server-java
