#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from . import common
from .. import Encryption

global_vars = common.global_vars

READ_BLOCK_SIZE = 1024 ** 2 # Bytes

def decrypt(paths):
    encsync = common.make_encsync()

    if encsync is None:
        return

    assert(len(paths) > 0)

    if len(paths) == 1:
        dest = paths[0]
    else:
        dest = paths.pop()
        if len(paths) > 2 and not os.path.isdir(dest):
            raise ValueError("Destination must be a directory")

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

def decrypt_config(in_path, out_path):
    if common.make_encsync() is None:
        return

    key = global_vars["master_password_sha256"]

    with open(in_path, "rb") as in_f:
        data = Encryption.decrypt_data(in_f.read(), key)
        with open(out_path, "wb") as out_f:
            out_f.write(data)

def decrypt_filename(paths, prefix):
    encsync = common.make_encsync()

    if encsync is None:
        return

    for path in paths:
        print(encsync.decrypt_path(path, prefix)[0])
