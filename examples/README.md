# ycmd example client

The example client **requires** Python 3.4+ (unlike ycmd which also runs on
Python 2).

First make sure you have built ycmd; see the top-level README for details.

Then install all the Python requirements with [pip][] (run as admin/super user):

```
pip install -r requirements.txt --use-mirrors
```

Then just run `./example_client.py` from the console. It will start `ycmd`, send
it some example requests while logging the full HTTP request & response and then
shut everything down.

The best way to learn how to use ycmd is to play around with the example client;
tweak the code, send other requests etc. Start by looking at the `Main()`
function at the bottom of the file.

NOTE: Everything in this folder and below is licensed under the [Apache2
license][apache], not the GPLv3 like the rest of ycmd.

[pip]: http://pip.readthedocs.org/en/latest/
[apache]: http://www.apache.org/licenses/LICENSE-2.0
