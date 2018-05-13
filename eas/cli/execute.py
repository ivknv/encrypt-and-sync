#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .common import make_config, show_error

from .console import Console

__all__ = ["execute", "execute_script"]

def execute(env, s):
    config, ret = make_config(env)

    if config is None:
        return ret

    console = Console(config, env)

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
