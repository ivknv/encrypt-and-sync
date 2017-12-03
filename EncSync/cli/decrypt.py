#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from .common import show_error
from . import common

READ_BLOCK_SIZE = 1024 ** 2 # Bytes

def decrypt(env, paths):
    encsync, ret = common.make_encsync(env)

    if encsync is None:
        return ret

    assert(len(paths) > 0)

    if len(paths) == 1:
        dest = paths[0]
    else:
        dest = paths.pop()
        if len(paths) > 2 and not os.path.isdir(dest):
            show_error("Error: destination must be a directory")
            return 1

    for path in paths:
        f = encsync.temp_decrypt(path)

        if os.path.isdir(dest):
            out_path = os.path.join(dest, os.path.split(path)[1])
        else:
            out_path = dest

        with open(out_path, "wb") as out:
            block = f.read(READ_BLOCK_SIZE)
            while block:
                out.write(block)
                block = f.read(READ_BLOCK_SIZE)

    return 0

def decrypt_filename(env, paths, prefix, encoding):
    encsync, ret = common.make_encsync(env)

    if encsync is None:
        return ret

    for path in paths:
        print(encsync.decrypt_path(path, prefix, filename_encoding=encoding)[0])

    return 0
