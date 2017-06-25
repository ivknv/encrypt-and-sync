#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .common import show_error

DEFAULT_CONFIG = """\
sync-threads 2
scan-threads 2
download-threads 2

upload-limit inf
download-limit inf

targets {

}

encrypted-dirs {

}"""

def make_config(env, path):
    try:
        with open(path, "w") as f:
            f.write(DEFAULT_CONFIG)
    except FileNotFoundError:
        show_error("Error: no such file or directory: %r" % path)
        return 1
    except IsADirectoryError:
        show_error("Error: %r is a directory" % path)
        return 1

    return 0
