#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .common import make_encsync, show_error

from .Console import Console

def execute(env, s):
    encsync, ret = make_encsync(env)

    if encsync is None:
        return ret

    console = Console(encsync)
    console.env.parent = env

    return console.execute(s)

def execute_script(env, path):
    try:
        with open(path, "r") as f:
            script = f.read()
    except FileNotFoundError:
        show_error("Error: no such file or directory: %r" % path)
    except IsADirectoryError:
        show_error("Error: %r is a directory" % path)

    execute(env, script)