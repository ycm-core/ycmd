# ycmd example client

First, install all the Python requirements with [pip][]:

```
pip install -r requirements.txt --use-mirrors
```

Then just run `./example_client.py` from the console. It will start `ycmd`, send
it some example requests while logging the full HTTP request & response and then
shut everything down.

The best way to learn how to use ycmd is to play around with the example client;
tweak the code, send other requests etc.

[pip]: http://pip.readthedocs.org/en/latest/
