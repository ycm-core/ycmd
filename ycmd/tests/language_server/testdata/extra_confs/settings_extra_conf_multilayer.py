def Settings(**kwargs):
    return {
        "ls": {
            "java": {"rename": {"enabled": False}},
            "foo": {"baz": "from_conf_file", "nested": {"key": "from_conf_file"}},
        }
    }
