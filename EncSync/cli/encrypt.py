#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

from .. import Encryption

from . import common

global_vars = common.global_vars

READ_BLOCK_SIZE = 1024 ** 2 # Bytes

def encrypt(paths):
    encsync = common.make_encsync()

    if encsync is None:
        return

    assert(len(paths) > 0)

    if len(paths) == 1:
        dest = paths[0]
    else:
        dest = paths.pop()
        if len(paths) > 2 and not os.path.isdir(dest):
            print("Error: Destination must be a directory", file=sys.stderr)
            return

    for path in paths:
        f = encsync.temp_encrypt(path)

        if os.path.isdir(dest):
            out_path = os.path.join(dest, os.path.split(path)[1])
        else:
            out_path = dest

        with open(out_path, "wb") as out:
            block = f.read(READ_BLOCK_SIZE)
            while block:
                out.write(block)
                block = f.read(READ_BLOCK_SIZE)

def encrypt_config(in_path, out_path):
    if common.make_encsync() is None:
        return

    key = global_vars["master_password_sha256"]

    with open(in_path, "rb") as in_f:
        data = Encryption.encrypt_data(in_f.read(), key)
        with open(out_path, "wb") as out_f:
            out_f.write(data)

def encrypt_filename(paths, prefix):
    encsync = common.make_encsync()

    if encsync is None:
        return

    for path in paths:
        print(encsync.encrypt_path(path, prefix)[0])
