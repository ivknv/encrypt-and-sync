#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from .common import show_error
from . import common

__all__ = ["encrypt", "encrypt_path"]

READ_BLOCK_SIZE = 1024 ** 2 # Bytes

def encrypt(env, paths):
    assert(len(paths) > 0)

    config, ret = common.make_config(env)

    if config is None:
        return ret

    if len(paths) == 1:
        dest = paths[0]
    else:
        dest = paths.pop()
        if len(paths) > 2 and not os.path.isdir(dest):
            show_error("Error: destination must be a directory")
            return 1

    for path in paths:
        try:
            f = config.temp_encrypt(path)
        except FileNotFoundError:
            show_error("Error: no such file or directory: %r" % path)
            return 1
        except IsADirectoryError:
            show_error("Error: %r is a directory" % path)
            return 1

        if os.path.isdir(dest):
            out_path = os.path.join(dest, os.path.split(path)[1])
        else:
            out_path = dest

        try:
            with open(out_path, "wb") as out:
                block = f.read(READ_BLOCK_SIZE)
                while block:
                    out.write(block)
                    block = f.read(READ_BLOCK_SIZE)
        except FileNotFoundError:
            show_error("Error: no such file or directory: %r" % out_path)
            return 1
        except IsADirectoryError:
            show_error("Error: %r is a directory" % out_path)
            return 1

    return 0

def encrypt_path(env, paths, prefix, encoding):
    config, ret = common.make_config(env)

    if config is None:
        return ret

    for path in paths:
        print(config.encrypt_path(path, prefix, filename_encoding=encoding)[0])

    return 0
